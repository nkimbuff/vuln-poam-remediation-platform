# Databricks notebook source
# MAGIC %pip install -q "psycopg[binary]" databricks-sdk --upgrade
# MAGIC %restart_python

# COMMAND ----------
# Sync Gold findings into Lakebase (Postgres) and measure operational read/write latency.
import time, json, statistics, random, psycopg
from databricks.sdk import WorkspaceClient

CAT = "serverless_stable_seg9n6_catalog.vuln_poam"
ENDPOINT = "projects/vuln-poam-ops/branches/production/endpoints/primary"
w = WorkspaceClient()
ep = w.postgres.get_endpoint(name=ENDPOINT)
host = ep.status.hosts.host
cred = w.postgres.generate_database_credential(endpoint=ENDPOINT)
user = w.current_user.me().user_name
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s)

conn = psycopg.connect(host=host, port=5432, dbname="databricks_postgres", user=user,
                       password=cred.token, sslmode="require", autocommit=True)
log("connected", host, "as", user, "| server:", conn.execute("select version()").fetchone()[0][:40])

# COMMAND ----------
conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
conn.execute("""CREATE TABLE IF NOT EXISTS ops.findings (
  finding_id text PRIMARY KEY, system_id text, system_name text, criticality text, owner_team text,
  hostname text, cve_id text, severity text, cvss double precision, exploit_available boolean,
  first_seen date, last_seen date, sla_due_date date, age_days int, is_overdue boolean,
  priority_score double precision, owner text, status text NOT NULL DEFAULT 'OPEN',
  poam_id text, updated_at timestamptz NOT NULL DEFAULT now())""")
conn.execute("""CREATE TABLE IF NOT EXISTS ops.poams (
  poam_id text PRIMARY KEY, finding_id text REFERENCES ops.findings(finding_id), weakness text,
  milestone text, scheduled_completion date, resources text, status text DEFAULT 'DRAFT',
  closure_evidence text, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now())""")
conn.execute("""CREATE TABLE IF NOT EXISTS ops.status_history (
  id bigserial PRIMARY KEY, finding_id text, old_status text, new_status text, changed_by text,
  changed_at timestamptz DEFAULT now())""")
RESET = True  # rebuild: clear operational tables so stale finding_ids from earlier data don't linger. Set False to preserve ISSO edits.
if RESET:
    conn.execute("TRUNCATE ops.poams, ops.status_history, ops.findings RESTART IDENTITY CASCADE")
    log("RESET=True: operational tables truncated")
log("tables ready: ops.findings, ops.poams, ops.status_history")

# COMMAND ----------
# Reload from Gold, preserving any ISSO edits already made in the operational store.
rows = spark.sql(f"""SELECT finding_id, system_id, system_name, criticality, owner_team, hostname, cve_id,
  severity, cvss, exploit_available, first_seen, last_seen, sla_due_date, age_days, is_overdue
  FROM {CAT}.gold_findings""").collect()
t0 = time.time()
with conn.cursor() as cur:
    cur.executemany("""INSERT INTO ops.findings (finding_id, system_id, system_name, criticality, owner_team,
      hostname, cve_id, severity, cvss, exploit_available, first_seen, last_seen, sla_due_date, age_days, is_overdue)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON CONFLICT (finding_id) DO UPDATE SET last_seen=EXCLUDED.last_seen, age_days=EXCLUDED.age_days,
        is_overdue=EXCLUDED.is_overdue, updated_at=now()""", [tuple(r) for r in rows])
log(f"synced {len(rows)} gold rows -> ops.findings in {time.time()-t0:.2f}s")
log("row counts:", conn.execute("select count(*) from ops.findings").fetchone()[0], "findings;",
    dict(conn.execute("select status, count(*) from ops.findings group by 1").fetchall()))

# COMMAND ----------
# Operational latency: point reads + status writes (hold / assign owner), as the app will do.
ids = [r[0] for r in conn.execute("select finding_id from ops.findings order by random() limit 200").fetchall()]
def timed(fn, n):
    out = []
    for i in range(n):
        t = time.perf_counter(); fn(ids[i % len(ids)]); out.append((time.perf_counter() - t) * 1000)
    return out
def read(fid): conn.execute("select * from ops.findings where finding_id=%s", (fid,)).fetchone()
def write(fid):
    conn.execute("update ops.findings set owner=%s, status='IN_PROGRESS', updated_at=now() where finding_id=%s",
                 (f"isso.{random.randint(1,5)}@example.gov", fid))
    conn.execute("insert into ops.status_history(finding_id,old_status,new_status,changed_by) values (%s,'OPEN','IN_PROGRESS',%s)", (fid, user))
for name, fn in (("read", read), ("write", write)):
    fn(ids[0]); ms = sorted(timed(fn, 100))
    log(f"latency {name}: n=100 p50={statistics.median(ms):.1f}ms p95={ms[94]:.1f}ms max={ms[-1]:.1f}ms")
log("after writes:", dict(conn.execute("select status, count(*) from ops.findings group by 1").fetchall()),
    "| history rows:", conn.execute("select count(*) from ops.status_history").fetchone()[0])
dbutils.notebook.exit("\n".join(LOG))
