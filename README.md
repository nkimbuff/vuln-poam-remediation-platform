# Vulnerability Findings to Accountable Remediation (POA&M) on Databricks

End-to-end prototype: scan evidence in, governed findings and POA&Ms out, with ISSOs working from one shared app. **All data is synthetic** (seeded generator in `data_gen/`).

## Customer problem (federal / defense IT security)
- Scan findings are exchanged as emailed, team-owned Excel files.
- Each system needs manual reconciliation and POA&M preparation.
- Remediation cycles exceed 30 days, so evidence goes stale and monthly reviews are missed.
- Result: ISSOs struggle to make time-sensitive remediation decisions.

**Goal:** cut end-to-end cycle time from scan evidence to accountable action.

## Two audiences, two stories

| Audience | What they care about | Read |
|---|---|---|
| **Executive sponsor** (CISO or program sponsor who funds this) | Audit and compliance posture, program risk reduction, budget and staff time, and a decision they can make: fund a time-boxed pilot | [EXECUTIVE_BRIEF.md](EXECUTIVE_BRIEF.md) |
| **ISSO and technical implementer** | Triage, ownership, evidence-backed closure, and how the pipeline and governance work | This README and [SUBMISSION.md](SUBMISSION.md) |

How AI was used, both inside the product and to build it, is in [AI_WORKFLOW.md](AI_WORKFLOW.md).

## Journey
| Stage | Databricks capability | What it does here |
|---|---|---|
| Ingest | Lakeflow Declarative Pipelines + Auto Loader | New scan files are validated, standardized, deduped (Bronze → Silver → Gold) |
| Govern | Unity Catalog | Tags, masking on host/owner fields, grants, lineage from scan to POA&M to closure |
| Serve | Lakebase (Postgres) | Operational `findings` / `poams` tables the app reads and writes with low latency |
| Intelligence | ML + Gen AI | Remediation-priority model registered in UC; LLM drafts POA&M entries |
| Query | Genie | Natural-language questions over Gold tables |
| Surface | Databricks Apps | One workflow to update owners, POA&Ms and closure evidence |

## Layout
`data_gen/` synthetic scans · `lakeflow/` pipeline · `governance/` UC SQL · `lakebase/` · `ml/` · `genai/` · `genie/` · `app/` · `evidence/` executed outputs (text)

Catalog/schema used: `serverless_stable_seg9n6_catalog.vuln_poam`.

## Status
- [x] Repo + workspace schema/volume
- [x] Synthetic data landed
- [x] Lakeflow pipeline run (4,053 bronze -> 3,993 valid + 60 quarantined -> 1,158 findings, 476 overdue)
- [x] UC governance (tags, mask function + secure view, grants, lineage)
- [x] Lakebase (1,158 findings synced; read p50 2.8ms, write p50 11ms)
- [x] ML / Gen AI (UC model, scores, 5 LLM POA&M drafts)
- [x] Genie (space + 3 NL questions with SQL and results)
- [x] App deployed; its write path (owner, status, closure evidence, history) is evidenced in `evidence/10_portal_writes.log` (the in-portal Genie tab is not evidenced)
- [x] Scale test: about 300,000 findings in an isolated schema (`evidence/09_scale_test.log`; ingest to prioritized tables only)
- [x] Executive brief, AI workflow account, and submission map ([EXECUTIVE_BRIEF.md](EXECUTIVE_BRIEF.md), [AI_WORKFLOW.md](AI_WORKFLOW.md), [SUBMISSION.md](SUBMISSION.md))

## Evidence
`evidence/01..07_*.log` hold the text output of each stage (row counts, expectations, UC tags/grants/lineage, Lakebase latency, model + LLM output, Genie SQL/results, app deploy). Each log notes its own caveats.

## Known limitations
- ML label is seeded synthetic; AUC demonstrates the MLOps path only.
- UC masking is on a secure view; the build ran as an admin, so the masked path was not exercised.
- Gold is rebuilt from scans each run; findings that disappear from scans are not auto-closed.

## Table and column descriptions
Pipeline tables get descriptions from `lakeflow/pipeline.py` (`COLS` + `schema=` with COMMENTs) because manual comments on pipeline-managed tables are reset on refresh (tested; see `evidence/08_descriptions.log`). `governance/06_static_comments.py` describes the objects the pipeline does not manage (`gold_findings_secure`, `finding_priority`); re-run it after the ML notebook.
