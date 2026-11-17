# Federal Grant Fraud, Improper Payment & Audit Readiness Platform

Databricks reference build using public/synthetic data only (USAspending-style awards, SAM.gov-style exclusions, synthetic invoice claims). No customer data or identifiers in this repo.

## Component map
| Dir | Component |
|---|---|
| lakeflow/ | Lakeflow Connect + Declarative Pipelines (Bronze → Silver → Gold) |
| governance/ | Unity Catalog: masking (EIN/PII), CUI/PII tags, lineage, GRANTs |
| lakebase/ | Gold → Lakebase (Postgres) sync for risk profiles and award balances |
| ml/ | Anomaly / risk-scoring model registered in Unity Catalog |
| genai/ | Mosaic AI Agent Framework RAG over 2 CFR Part 200 for audit justifications |
| genie/ | Genie space on Gold tables |
| app/ | Grant Officer Triage Portal (Databricks Apps) |
| evidence/ | Executed notebooks (.ipynb/.html) and .log/.json run outputs |
| deck/ | 4-slide deck following the talk track |

## Conventions
- Never commit secrets, tokens, or real PII/EINs.
- Evidence must be text-readable with cell outputs visible.
