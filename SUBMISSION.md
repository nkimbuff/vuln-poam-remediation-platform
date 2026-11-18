# Submission Map

**Problem:** federal defense cyber teams track vulnerability findings in emailed spreadsheets and hand-build POA&Ms, so remediation cycles run past 30 days on stale evidence.
**Data:** synthetic only (seeded generators in `data_gen/`). No customer data.
**Built and run:** 2026-11-17 and 2026-11-18, on a Databricks serverless workspace (AWS), Unity Catalog `vuln_poam` schema, a Lakebase Postgres project, and a deployed Databricks App.

## Two audiences

| Audience | Document |
|---|---|
| **Executive sponsor** (CISO or program sponsor; measured on audit posture, program risk, budget) | [EXECUTIVE_BRIEF.md](EXECUTIVE_BRIEF.md) |
| **ISSO and technical implementer** (triage, ownership, pipeline) | [README.md](README.md) and the stages below |

## Stage map

| Stage | Code | Text evidence (run output) |
|---|---|---|
| Synthetic data and landing | `data_gen/generate_scans.py` | `evidence/01_data_landing.log` |
| **Lakeflow** (Auto Loader, expectations, quarantine, gold) | `lakeflow/pipeline.py`, `lakeflow/pipeline_settings.json` | `evidence/02_lakeflow_pipeline_run.log`, `evidence/02_lakeflow_pipeline_events.json` |
| **Unity Catalog** (tags, masking function, secure view, grants, lineage) | `governance/02_unity_catalog.sql`, `governance/06_static_comments.py` | `evidence/03_unity_catalog.log`, `evidence/08_descriptions.log` |
| **Lakebase** (operational store, latency) | `lakebase/04_lakebase_sync.py`, `lakebase/04b_grant_app_role.py` | `evidence/04_lakebase.log`, `evidence/10_portal_writes.log` |
| **ML and Gen AI** (UC-registered model, LLM POA&M drafts) | `ml/05_priority_model_and_poam_drafts.py` | `evidence/05_ml_genai.log` |
| **Genie** | `genie/space_payload.json` | `evidence/06_genie.log` |
| **Databricks App** (triage portal) | `app/app.py`, `app/app.yaml` | `evidence/07_app.log`, `evidence/10_portal_writes.log` |
| Scale test (about 300,000 findings, isolated schema) | `data_gen/generate_scans_scale.py` | `evidence/09_scale_test.log` |

## How AI was used

See [AI_WORKFLOW.md](AI_WORKFLOW.md): the AI in the product (model, LLM drafting, Genie) and the AI-assisted engineering workflow, including the mistakes it made and how they were caught.

## What was not verified

- Masking as a **non-administrator** (built and tested as an admin).
- The **in-portal Genie tab** (the Genie space itself is tested in `evidence/06`).
- Scale: the 300,000-finding run covers ingest to the prioritized tables, not Lakebase sync, scoring, or the portal at that size, and each run was done once.
- The model's label is synthetic; its AUC does not indicate real predictive power.
- Not built: deadline alerting, cross-scanner deduplication, automatic closure verification.
