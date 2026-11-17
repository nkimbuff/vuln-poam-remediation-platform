"""Describe objects the pipeline does NOT manage: gold_findings_secure (view) and finding_priority (table).
Pipeline tables carry their descriptions in lakeflow/pipeline.py (schema COMMENTs), which survive refreshes.
Re-run this script after re-running the ML notebook, because saveAsTable(overwrite) resets finding_priority.
Usage: DATABRICKS_CONFIG_PROFILE=fevm-stable python3 -I governance/06_static_comments.py"""
import json, subprocess
WH = "593bc2838d9d1192"; CAT = "serverless_stable_seg9n6_catalog"; S = f"{CAT}.vuln_poam"

def sql(stmt):
    r = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json",
                        json.dumps({"warehouse_id": WH, "statement": stmt, "wait_timeout": "50s"})], capture_output=True, text=True)
    d = json.loads(r.stdout); st = d["status"]
    if st["state"] != "SUCCEEDED": raise SystemExit(f'FAILED: {st.get("error",{}).get("message")}\n{stmt[:120]}')
    return d.get("result", {}).get("data_array", [])
esc = lambda t: t.replace("'", "''")

# 1) secure view: reuse the descriptions already on gold_findings so wording stays consistent
gold = dict(sql(f"SELECT column_name, comment FROM {CAT}.information_schema.columns WHERE table_schema='vuln_poam' AND table_name='gold_findings'"))
view_cols = [r[0] for r in sql(f"SELECT column_name FROM {CAT}.information_schema.columns WHERE table_schema='vuln_poam' AND table_name='gold_findings_secure' ORDER BY ordinal_position")]
body = sql(f"SELECT view_definition FROM {CAT}.information_schema.views WHERE table_schema='vuln_poam' AND table_name='gold_findings_secure'")[0][0]
cols = ", ".join(f"{c} COMMENT '{esc(gold.get(c) or '')}'" for c in view_cols)
sql(f"CREATE OR REPLACE VIEW {S}.gold_findings_secure ({cols}) COMMENT 'Gold findings with hostname and IP masked for users outside isso_analysts/admins. Source for the Genie space.' AS {body}")
sql(f"GRANT SELECT ON VIEW {S}.gold_findings_secure TO `account users`")  # CREATE OR REPLACE keeps grants; re-assert anyway

# 2) ML scores table
sql(f"COMMENT ON TABLE {S}.finding_priority IS 'ML remediation priority per finding: score 0-1 (higher = remediate first) and rank. Model trained on a seeded synthetic label.'")
for c, t in {"finding_id": gold["finding_id"], "priority_score": "Predicted probability of ISSO escalation from the UC-registered finding_priority_model (0-1).",
             "priority_rank": "1 = highest priority across all findings (rank by priority_score descending)."}.items():
    sql(f"ALTER TABLE {S}.finding_priority ALTER COLUMN {c} COMMENT '{esc(t)}'")
print("static comments applied")
