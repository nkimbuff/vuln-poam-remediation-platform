# Vulnerability Findings to Accountable Remediation (POA&M) on Databricks

End-to-end prototype: scan evidence in, governed findings and POA&Ms out, with ISSOs working from one shared app. **All data is synthetic** (seeded generator in `data_gen/`).

## Customer problem (federal / defense IT security)
- Scan findings are exchanged as emailed, team-owned Excel files.
- Each system needs manual reconciliation and POA&M preparation.
- Remediation cycles exceed 30 days, so evidence goes stale and monthly reviews are missed.
- Result: ISSOs struggle to make time-sensitive remediation decisions.

**Goal:** cut end-to-end cycle time from scan evidence to accountable action.

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
- [x] Lakeflow pipeline run (1,194 bronze -> 1,176 valid + 18 quarantined -> 763 findings)
- [x] UC governance (tags, mask function + secure view, grants, lineage)
- [ ] Lakebase
- [ ] ML / Gen AI
- [ ] Genie
- [ ] App
