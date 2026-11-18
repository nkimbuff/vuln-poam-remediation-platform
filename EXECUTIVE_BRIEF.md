# Executive Brief: Funding a Time-Boxed Pilot to Cut Remediation Time

**For:** the CISO or program sponsor who funds this and answers for audit posture, mission risk, and budget.
**Not for:** the day-to-day ISSO workflow, which is covered in the [README](README.md).
**Data:** all figures below come from a synthetic data set (20 systems, 10 weekly scans). They show what the platform makes visible, not what it saves in your agency. Where a number is an illustration or a proposed target, it says so.

## The decision

Approve a **2 to 4 week pilot (planned at 4) on one system**, with a go/no-go at the end against metrics agreed up front. The pilot answers one question that matters to a funding decision: *how much faster does a scanner finding become an owned, evidence-backed action, and does it stay that way?* The spend to find out is small and time-boxed. Platform cost is usage-based, and a sized estimate comes after the pilot is scoped.

## The problem, in the sponsor's terms

Vulnerability findings travel as emailed spreadsheets, each team keeps its own copy, and POA&Ms are built by hand. Remediation cycles run past 30 days, so the evidence is stale when someone acts. For a sponsor that shows up as:

- **Audit and compliance exposure:** POA&M records that aren't current, closures without proof, and a trail assembled from email after the fact.
- **Program risk:** mission-critical systems carrying known critical findings longer than policy allows.
- **Cost:** skilled security staff spending cycles on reconciliation and typing instead of risk decisions.

## What the build makes visible (measured on synthetic data)

| Sponsor question | What the platform shows | Figure (synthetic data) |
|---|---|---|
| How big is the overdue backlog? | Findings past their SLA, by severity | 476 of 1,158 findings (41%) past SLA; 285 of those are critical |
| Is anyone accountable? | Findings with a named owner | None had an owner when the data was freshly loaded |
| How stale is the worst exposure? | Age of the oldest open critical findings | 63 days against a 15-day SLA |
| Can we prove what happened? | Per-finding history and closure evidence | Every status change is written to a history table with who and when, and the portal requires evidence to close; the closed findings in the log carry evidence text ([evidence](evidence/10_portal_writes.log)) |
| Will it hold at agency scale? | Pipeline run at about 300,000 findings | Initial load about 72 s; one more weekly scan about 104 s ([evidence](evidence/09_scale_test.log)). Ingest-to-prioritized-tables only |

## The scorecard a sponsor would hold the pilot to

These are the measures the pilot would baseline and then compare. **Targets are proposals to agree in scoping, not results.**

| Metric you're measured on | Today (baseline to capture) | How the platform moves it | How the pilot measures it | Proposed target |
|---|---|---|---|---|
| **Audit and compliance posture:** POA&M currency and closure-with-evidence rate | Share of open weaknesses with an owner, due date, and current POA&M; share of closures with evidence | One governed record per finding; drafted POA&M; closure blocked without evidence; full history | Sample of closed findings and POA&M completeness each cycle | 100% of closures carry evidence (the workflow enforces this); POA&M complete for every open critical and high |
| **Program risk reduction:** overdue critical and high findings | Count and age of overdue critical and high findings per cycle | Queue ranked by risk; owner assigned; SLA visibility | Overdue criticals and highs and their oldest age, cycle over cycle | Agreed in scoping against the baseline |
| **Time to action:** scan landing to an owned, drafted action | The team's current figure (described as 30-plus days end to end) | Reconciliation, prioritization, and drafting removed from the path | Timestamp of scan landing versus first owned, drafted POA&M | **One business day** (proposed) |
| **Budget and staff time:** hours of reconciliation and POA&M drafting per cycle | Hours per cycle, from your team | Pipeline replaces manual consolidation; draft replaces blank page | Time study before versus after on one system | Reduction agreed in scoping |

**Illustration, not a result:** if reconciling and documenting one finding by hand takes 5 minutes, the 1,158 findings in the demo data are about 96 staff-hours per cycle. Multiply by your loaded labor rate and your number of cycles. Replace the 5 minutes with your measured figure before using this in a business case.

## What it costs

Usage-based: compute and storage consumed. For a one-system pilot the drivers are pipeline run frequency, the portal and database compute, and scan volume. There is no sized figure yet, and I won't guess one; it comes from scoping. The pilot needs roughly a part-time data engineer, an ISSO champion, and someone to set up the scanner exports from your side (staffing to be confirmed in scoping).

## Risks, stated plainly

| Risk | Status |
|---|---|
| Results are on synthetic data | True. The pilot exists to replace assumptions with your numbers |
| Priority model trained on a synthetic label | Its accuracy figure proves the pipeline works, not predictive power. On real data it would be retrained on your escalation decisions and compared against a simple rule |
| Masking of host and IP verified only as an administrator | Verify as a non-administrator before any real data |
| Alerting on approaching deadlines, cross-scanner deduplication, and automatic closure verification | Not built; they are the first pilot items |
| Compliance accreditation of the environment | Depends on the cloud, region, and deployment you choose; not claimed here |
| AI drafting POA&Ms | A person reviews and approves every draft; the model never files anything |

## The ask

1. Name the system for the pilot and the ISSO champion.
2. Agree the four metrics above and their baselines.
3. Hold a scoping session so a sized estimate and a go/no-go date can follow.

*Companion documents: [README](README.md) (the build), [SUBMISSION.md](SUBMISSION.md) (where each stage's evidence lives), [AI_WORKFLOW.md](AI_WORKFLOW.md) (how AI was used to build this).*
