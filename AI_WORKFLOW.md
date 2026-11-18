# How AI Was Used to Build This

Two different kinds of AI appear in this project. They are kept separate here because they answer different questions.

## 1. AI inside the product (what the customer gets)

| Where | What it does | Guardrail |
|---|---|---|
| Priority model (`ml/05_priority_model_and_poam_drafts.py`) | A gradient-boosted classifier, registered in Unity Catalog through MLflow, scores every finding from six inputs (CVSS, exploit availability, system criticality, days open, past SLA, scans seen) | Trained on a **seeded synthetic label**; the AUC (about 0.75) shows the pipeline works, not predictive power |
| POA&M drafting (same notebook) | An LLM served on Databricks (`databricks-claude-opus-5-5`, called with `ai_query`) drafts the weakness, milestones, resources, and a scheduled completion date from each finding's facts only | The prompt forbids inventing versions, hosts, or dates; a person reviews and approves every draft; drafts are written to `ops.poams` and logged in `evidence/05_ml_genai.log` |
| Genie space (`genie/`) | Natural-language questions over the governed tables, with the generated SQL visible | Reads only governed tables; transcripts in `evidence/06_genie.log` |

## 2. AI that helped build the solution (the engineering workflow)

**Tool:** Claude Code (Anthropic's coding agent, running Claude Sonnet 5.5) working from the builder's terminal. It drove the Databricks CLI and REST APIs, the GitHub CLI, serverless notebook jobs, and web search, and it wrote commits with the `Co-authored-by` trailer the builder's organization requires.

**Where it acted as a force multiplier**

| Work | AI contribution | Human contribution |
|---|---|---|
| Synthetic data (`data_gen/`) | Wrote the seeded generators, including the persistence-across-weeks logic that makes SLA breaches emerge from age | Chose the scenario, accepted the synthetic-only and public-repo constraints, and approved the plan |
| Lakeflow pipeline (`lakeflow/`) | Wrote bronze, silver, and gold tables with expectations and a quarantine table; deployed and ran them; read the event log | Reviewed outcomes; asked the follow-up question that led to the comment-persistence work (below) |
| Governance (`governance/`) | Wrote the masking function, secure view, tags, and grants; worked around tag-policy rejections | Set the governance requirements (masking, sensitivity tagging) in the brief |
| Lakebase, ML, app (`lakebase/`, `ml/`, `app/`) | Created the Postgres project and roles, the notebooks, the model, and the Streamlit app; deployed and checked it | Exercised the deployed portal by hand (see `evidence/10_portal_writes.log`) |
| Evidence | Captured the real output of every stage into `evidence/` rather than describing it | Decided what to commit and what stays local |
| Scale test (`data_gen/generate_scans_scale.py`) | Built an isolated 300,000-finding run and measured it | Accepted the suggestion to measure scale rather than assert it |

**Where AI made mistakes, and how they were caught.** These are in the evidence logs, not removed from them.

| Mistake | How it was caught | Fix |
|---|---|---|
| Aggregated findings before validating them, so 14 planted dirty rows vanished and validation reported zero failures | The quarantine count didn't match the planted dirty rows | Validate each row first (`evidence/02`) |
| First quarantine logic matched nothing | Quarantine table was empty while expectations reported failures | Define quarantine as the inverse of the validation rule |
| First data set had no overdue findings, which hid the problem the demo is about | The Genie answer showed zero overdue everywhere | Regenerated to 10 weekly scans |
| An evidence log labeled counts "after update 1" that were queried after update 2 | Rereading the log against the earlier run output | Relabeled and noted the discrepancy (`evidence/09`) |
| Column comments typed by hand don't survive a pipeline refresh | The builder questioned it; the agent then tested four approaches | Descriptions defined in the pipeline's table schema (`evidence/08`) |
| Library and API friction (SDK too old, protobuf conflict, tag-policy values, SQL tool refusing DDL) | Job failures with exact errors | Pinned versions, switched to the CLI and notebooks |

**Verification practice.** Nothing was reported as working without reading it back: row counts by query, expectation pass and fail counts from the pipeline event log, latency measured in a notebook, deployment confirmed by status and HTTP health checks, and Genie answers captured with their SQL.

**Limits of the AI-assisted process.** The agent can't click a browser, so the portal's in-app behavior was exercised by the builder and recorded in Lakebase (`evidence/10_portal_writes.log`). Two things were not exercised and are stated as such: the in-portal Genie tab, and masking as a non-administrator.
