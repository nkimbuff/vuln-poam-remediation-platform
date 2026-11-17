"""ISSO Triage Portal: prioritized findings, POA&M drafts, owner/status/closure updates (Lakebase), Genie Q&A."""
import os, pandas as pd, psycopg, streamlit as st
from databricks.sdk import WorkspaceClient

EP = os.environ["LAKEBASE_ENDPOINT"]; SPACE = os.environ["GENIE_SPACE_ID"]
STATUSES = ["OPEN", "IN_PROGRESS", "BLOCKED", "CLOSED"]
st.set_page_config(page_title="ISSO Triage Portal", layout="wide")

@st.cache_resource(ttl=2400)  # OAuth db tokens expire (~1h); rebuild the connection before that
def conn():
    w = WorkspaceClient()
    user = os.environ.get("DATABRICKS_CLIENT_ID") or w.current_user.me().user_name
    return psycopg.connect(host=w.postgres.get_endpoint(name=EP).status.hosts.host, dbname="databricks_postgres",
        user=user, password=w.postgres.generate_database_credential(endpoint=EP).token, sslmode="require", autocommit=True)

def q(sql, args=()):
    with conn().cursor() as c:
        c.execute(sql, args); cols = [d.name for d in c.description]; return pd.DataFrame(c.fetchall(), columns=cols)

st.title("ISSO Triage Portal")
st.caption("Synthetic data. One workflow from scan evidence to accountable remediation.")
k = q("select count(*) total, count(*) filter (where is_overdue and status<>'CLOSED') overdue, "
      "count(*) filter (where status='CLOSED') closed, count(*) filter (where owner is null) unassigned from ops.findings").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Findings", int(k.total)); c2.metric("Overdue (not closed)", int(k.overdue))
c3.metric("Closed", int(k.closed)); c4.metric("Unassigned", int(k.unassigned))

tab1, tab2, tab3 = st.tabs(["Triage queue", "Finding & POA&M", "Ask Genie"])
with tab1:
    f1, f2, f3 = st.columns(3)
    sev = f1.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH"])
    stat = f2.multiselect("Status", STATUSES, default=["OPEN", "IN_PROGRESS", "BLOCKED"])
    only_over = f3.checkbox("Overdue only", True)
    df = q("select finding_id, system_id, criticality, cve_id, severity, cvss, age_days, sla_due_date, is_overdue, "
           "priority_score, owner, status, poam_id from ops.findings where severity = any(%s) and status = any(%s) "
           "and (is_overdue or not %s) order by priority_score desc nulls last limit 200", (sev, stat, only_over))
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} shown (max 200), ordered by ML priority score")

with tab2:
    fid = st.text_input("finding_id", value=(df.finding_id.iloc[0] if len(df) else ""))
    if fid:
        r = q("select * from ops.findings where finding_id=%s", (fid,))
        if r.empty: st.warning("Not found")
        else:
            r = r.iloc[0]; st.json({k: str(v) for k, v in r.items() if k in
                ("system_id", "cve_id", "severity", "cvss", "age_days", "sla_due_date", "is_overdue", "priority_score")})
            owner = st.text_input("Owner", value=r.owner or ""); new = st.selectbox("Status", STATUSES, index=STATUSES.index(r.status))
            evidence = st.text_area("Closure evidence (required to close)")
            if st.button("Save"):
                if new == "CLOSED" and not evidence.strip(): st.error("Closure evidence required.")
                else:
                    who = st.context.headers.get("X-Forwarded-Email", "unknown") if hasattr(st, "context") else "unknown"
                    with conn().cursor() as c:
                        c.execute("update ops.findings set owner=%s, status=%s, updated_at=now() where finding_id=%s", (owner or None, new, fid))
                        c.execute("insert into ops.status_history(finding_id,old_status,new_status,changed_by) values (%s,%s,%s,%s)", (fid, r.status, new, who))
                        if r.poam_id and evidence.strip():
                            c.execute("update ops.poams set closure_evidence=%s, status=%s, updated_at=now() where poam_id=%s",
                                      (evidence, "CLOSED" if new == "CLOSED" else "OPEN", r.poam_id))
                    st.success("Saved to Lakebase"); st.rerun()
            if r.poam_id:
                st.subheader(f"POA&M {r.poam_id}"); st.dataframe(q("select * from ops.poams where poam_id=%s", (r.poam_id,)).T)
            st.subheader("History"); st.dataframe(q("select old_status,new_status,changed_by,changed_at from ops.status_history where finding_id=%s order by id desc", (fid,)))

with tab3:
    question = st.text_input("Ask about findings, SLA breaches, or system risk")
    if question:
        w = WorkspaceClient()
        with st.spinner("Genie is working..."):
            m = w.genie.start_conversation_and_wait(SPACE, question)
        for a in (m.attachments or []):
            if a.text: st.write(a.text.content)
            if a.query:
                st.code(a.query.query, language="sql")
                res = w.genie.get_message_attachment_query_result(SPACE, m.conversation_id, m.id, a.attachment_id)
                sr = res.statement_response
                st.dataframe(pd.DataFrame(sr.result.data_array or [], columns=[c.name for c in sr.manifest.schema.columns]))
