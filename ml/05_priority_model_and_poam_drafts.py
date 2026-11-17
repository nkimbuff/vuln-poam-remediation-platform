# Databricks notebook source
# MAGIC %pip install -q "psycopg[binary]" databricks-sdk "protobuf<5" --upgrade
# MAGIC %restart_python

# COMMAND ----------
# ML: remediation-priority model (UC-registered) + Gen AI: POA&M draft per top finding.
# IMPORTANT: no real remediation outcomes exist (synthetic data), so the training label is a SEEDED
# synthetic "escalated by ISSO" outcome. This demonstrates the MLOps path (MLflow -> UC -> scoring ->
# operational store), not real predictive power.
import json, numpy as np, pandas as pd, mlflow, psycopg
from mlflow.models import infer_signature
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from databricks.sdk import WorkspaceClient

CAT = "serverless_stable_seg9n6_catalog.vuln_poam"
MODEL = f"{CAT}.finding_priority_model"
LLM = "databricks-claude-opus-5-5"
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s)

pdf = spark.table(f"{CAT}.gold_findings").toPandas()
crit_w = {"MISSION_CRITICAL": 3, "HIGH": 2, "MODERATE": 1}
X = pd.DataFrame({"cvss": pdf.cvss, "exploit": pdf.exploit_available.astype(int),
                  "crit": pdf.criticality.map(crit_w).fillna(1), "age_days": pdf.age_days,
                  "overdue": pdf.is_overdue.astype(int), "scans_seen": pdf.scans_seen})
rng = np.random.default_rng(7)
logit = -4.0 + 0.35*X.cvss + 1.4*X.exploit + 0.6*X.crit + 0.04*X.age_days + 0.8*X.overdue + rng.normal(0, 0.8, len(X))
y = (rng.random(len(X)) < 1/(1+np.exp(-logit))).astype(int)
log(f"rows={len(X)} synthetic positive rate={y.mean():.2f}")

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=7, stratify=y)
mlflow.set_registry_uri("databricks-uc")
with mlflow.start_run(run_name="finding_priority_gbm") as run:
    m = GradientBoostingClassifier(random_state=7).fit(Xtr, ytr)
    auc = roc_auc_score(yte, m.predict_proba(Xte)[:, 1])
    mlflow.log_metric("test_auc", auc)
    info = mlflow.sklearn.log_model(m, "model", signature=infer_signature(Xtr, m.predict_proba(Xtr)[:, 1]),
                                    registered_model_name=MODEL)
    ver = max(int(v.version) for v in mlflow.MlflowClient().search_model_versions("name='" + MODEL + "'"))
    log(f"mlflow run={run.info.run_id} test_auc={auc:.3f} registered={MODEL} version={ver}")
imp = dict(zip(X.columns, np.round(m.feature_importances_, 3))); log("feature_importances:", imp)

# COMMAND ----------
pdf["priority_score"] = m.predict_proba(X)[:, 1].round(4)
pdf["priority_rank"] = pdf.priority_score.rank(ascending=False, method="first").astype(int)
spark.createDataFrame(pdf[["finding_id", "priority_score", "priority_rank"]]).write.mode("overwrite") \
     .saveAsTable(f"{CAT}.finding_priority")
log("wrote", f"{CAT}.finding_priority", len(pdf), "rows; top 5:")
top = pdf.sort_values("priority_rank").head(5)
log(top[["finding_id", "system_id", "cve_id", "severity", "cvss", "age_days", "priority_score"]].to_string(index=False))

# COMMAND ----------
# Gen AI: draft a POA&M entry per top-5 finding, grounded only in the supplied facts.
facts = top.to_dict("records")
def facts_txt(r):
    return (f"System {r['system_id']} ({r['system_name']}, criticality {r['criticality']}, team {r['owner_team']}); "
            f"{r['cve_id']} severity {r['severity']} CVSS {r['cvss']}, exploit available: {r['exploit_available']}; "
            f"first seen {r['first_seen']}, age {r['age_days']} days, SLA due {r['sla_due_date']}, overdue: {r['is_overdue']}.")
drafts = {}
for r in facts:
    prompt = ("You draft POA&M entries for an ISSO. Use ONLY the facts given; do not invent patch versions, "
              "hosts or dates beyond the SLA due date. Return JSON with keys weakness, milestone, resources, "
              "scheduled_completion (YYYY-MM-DD, not later than SLA due date unless overdue), rationale.\nFacts: " + facts_txt(r))
    out = spark.sql("SELECT ai_query(:m, :p) AS r", args={"m": LLM, "p": prompt}).first()["r"]
    out = out.strip().removeprefix("```json").removesuffix("```").strip()
    try: drafts[r["finding_id"]] = json.loads(out)
    except Exception: drafts[r["finding_id"]] = {"weakness": out[:500], "milestone": "", "resources": "", "scheduled_completion": None, "rationale": "unparsed"}
    log("DRAFT", r["finding_id"], json.dumps(drafts[r["finding_id"]])[:700])

# COMMAND ----------
# Push scores + drafts into Lakebase for the app.
w = WorkspaceClient(); EP = "projects/vuln-poam-ops/branches/production/endpoints/primary"
host = w.postgres.get_endpoint(name=EP).status.hosts.host; tok = w.postgres.generate_database_credential(endpoint=EP).token
conn = psycopg.connect(host=host, dbname="databricks_postgres", user=w.current_user.me().user_name, password=tok,
                       sslmode="require", autocommit=True)
with conn.cursor() as cur:
    cur.executemany("update ops.findings set priority_score=%s where finding_id=%s",
                    [(float(s), f) for f, s in zip(pdf.finding_id, pdf.priority_score)])
    for i, (fid, d) in enumerate(drafts.items(), 1):
        pid = f"POAM-{i:04d}"
        sc = d.get("scheduled_completion"); sc = sc if isinstance(sc, str) and len(sc) == 10 else None
        cur.execute("""insert into ops.poams(poam_id, finding_id, weakness, milestone, scheduled_completion, resources, status)
                       values (%s,%s,%s,%s,%s,%s,'DRAFT') on conflict (poam_id) do update set weakness=excluded.weakness,
                       milestone=excluded.milestone, scheduled_completion=excluded.scheduled_completion,
                       resources=excluded.resources, updated_at=now()""",
                    (pid, fid, d.get("weakness"), d.get("milestone"), sc, d.get("resources")))
        cur.execute("update ops.findings set poam_id=%s where finding_id=%s", (pid, fid))
log("lakebase: scored", conn.execute("select count(*) from ops.findings where priority_score is not null").fetchone()[0],
    "findings; poams:", conn.execute("select count(*) from ops.poams").fetchone()[0])
dbutils.notebook.exit("\n".join(LOG))
