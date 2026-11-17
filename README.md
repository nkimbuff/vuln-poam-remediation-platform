# Federal Grant Fraud, Improper Payment & Audit Readiness Platform

## Customer problem
Federal civilian agencies (HHS, DOL, SBA, DOT) distribute billions in grants annually, yet struggle to prevent improper payments and detect recipient fraud before disbursement. Audit teams spend months manually cross-referencing awardee data against debarment lists and historical audit findings, causing clawbacks and slow disbursement.

## Architecture (end-to-end Databricks journey)
1. **Lakeflow (ingestion):** USAspending-style awards, SAM.gov-style exclusions, synthetic invoice claims; Bronze → Silver → Gold.
2. **Unity Catalog (governance):** column masking on PII/EINs, CUI/PII tags, full lineage for OIG audit trails.
3. **Lakebase (operational serving):** Gold risk profiles and award balances synced to managed Postgres for sub-second hold/approve actions.
4. **ML / Gen AI:** anomaly/risk model registered in UC; Mosaic AI Agent Framework RAG over 2 CFR Part 200 generates plain-English audit justifications.
5. **Genie:** natural-language analytics on Gold tables.
6. **Databricks App:** Grant Officer Triage Portal reading/writing holds in Lakebase, showing risk briefs, embedding Genie.

## Talk track
**Hook:** shift from "pay and chase" to "verify before disbursement", cutting manual audit review time by up to 60% with full OIG traceability.

- **Executive sponsor:** lineage and policy enforcement via Unity Catalog (OMB A-123 controls, FedRAMP High / IL5); every high-risk drawdown caught pre-disbursement lowers improper payment rates.
- **Domain owner:** no SQL or tool-hopping; Gen AI cites the exact 2 CFR 200 clause plus drawdown history.

**Demo narrative:** Ingest & Govern → Real-Time Intelligence → Operational Action (hold in Lakebase, follow-ups via Genie).

**Discovery question:** Where do reviewers spend the most manual hours today: pre-award entity vetting, or post-award invoice and drawdown auditing?

## Submission checklist
- [ ] Executed notebooks with outputs (.ipynb/.html) plus .log/.json for Lakeflow runs, UC GRANT/DESCRIBE, Lakebase latency/row counts, ML/Gen AI inference, Genie SQL/text
- [ ] Deck: Slide 1 KPIs & improper payment impact; 2 Exec vs Domain Owner value; 3 Architecture; 4 Live triage workflow & OIG governance
