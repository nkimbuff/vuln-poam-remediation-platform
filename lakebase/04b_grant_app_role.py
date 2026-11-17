# Databricks notebook source
# MAGIC %pip install -q "psycopg[binary]" databricks-sdk "protobuf<5" --upgrade
# MAGIC %restart_python

# COMMAND ----------
import psycopg
from databricks.sdk import WorkspaceClient
APP_ROLE = "84f80175-eea8-4c78-8291-107975e9c361"   # app service principal client id
EP = "projects/vuln-poam-ops/branches/production/endpoints/primary"
w = WorkspaceClient()
conn = psycopg.connect(host=w.postgres.get_endpoint(name=EP).status.hosts.host, dbname="databricks_postgres",
        user=w.current_user.me().user_name, password=w.postgres.generate_database_credential(endpoint=EP).token,
        sslmode="require", autocommit=True)
for stmt in [f'GRANT USAGE ON SCHEMA ops TO "{APP_ROLE}"',
             f'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ops TO "{APP_ROLE}"',
             f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ops TO "{APP_ROLE}"']:
    conn.execute(stmt); print("OK:", stmt)
print(conn.execute("select grantee, table_name, string_agg(privilege_type, ',') from information_schema.role_table_grants where table_schema='ops' and grantee=%s group by 1,2 order by 2", (APP_ROLE,)).fetchall())
