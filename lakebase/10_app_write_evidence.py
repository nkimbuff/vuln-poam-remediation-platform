# Databricks notebook source
# MAGIC %pip install -q "psycopg[binary]" databricks-sdk "protobuf<5" --upgrade
# MAGIC %restart_python

# COMMAND ----------
# Read-only evidence: what the operational store recorded from real use of the portal (owner/status/closure writes).
# The portal writes ops.status_history and ops.poams.closure_evidence; this notebook only SELECTs. Emails are redacted.
import re, psycopg
from databricks.sdk import WorkspaceClient
EP = "projects/vuln-poam-ops/branches/production/endpoints/primary"
w = WorkspaceClient()
conn = psycopg.connect(host=w.postgres.get_endpoint(name=EP).status.hosts.host, dbname="databricks_postgres",
        user=w.current_user.me().user_name, password=w.postgres.generate_database_credential(endpoint=EP).token,
        sslmode="require", autocommit=True)
red = lambda s: re.sub(r"^[^@]+@", "***@", s) if s and "@" in s else s
out = []
def log(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)

log("status_history rows:", conn.execute("select count(*) from ops.status_history").fetchone()[0])
log("by transition and writer (redacted):")
for r in conn.execute("select changed_by, old_status, new_status, count(*) from ops.status_history group by 1,2,3 order by 4 desc").fetchall():
    log("  ", red(r[0]), "|", r[1], "->", r[2], "| n =", r[3])
log("most recent 8 transitions:")
for r in conn.execute("select id, finding_id, old_status, new_status, changed_by, changed_at from ops.status_history order by id desc limit 8").fetchall():
    log("  ", r[0], r[1], r[2], "->", r[3], red(r[4]), r[5].isoformat(timespec="seconds"))
log("closed POA&Ms with closure evidence (evidence text shown, first 90 chars):")
for r in conn.execute("select poam_id, finding_id, status, left(closure_evidence, 90), updated_at from ops.poams where closure_evidence is not null order by updated_at desc").fetchall():
    log("  ", r[0], r[1], r[2], "|", r[3], "|", r[4].isoformat(timespec="seconds"))
log("findings by status:", dict(conn.execute("select status, count(*) from ops.findings group by 1").fetchall()))
log("findings with an owner:", conn.execute("select count(*) from ops.findings where owner is not null").fetchone()[0])
dbutils.notebook.exit("\n".join(out))
