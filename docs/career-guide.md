# Make this project your own

This is an AI-assisted starting point for practical experience. The most valuable next step is to run, modify and explain it yourself.

## A five-minute demonstration

1. Open the offline explorer. Explain the source date, 500 listings and the difference between unavailable and booked.
2. Filter to a ward and a room type. Point out price coverage and how the comparable set changes.
3. Open the report's quality section. Explain the 33 missing prices and why fuzzy matches were retained.
4. Open `sql/analytics.sql` against the DuckDB file. Demonstrate the listing/calendar join and its grain.
5. Show the model comparison. Explain why a simple baseline winning is a useful result, and why a random listing split could leak host-specific information.

## Four learning sessions

### Session 1: Understand the data

Read `configs/albany.json`, `schema_profile.json` and `docs/assumptions.md`. Explain why the archive date differs from the observed scrape date, why reviewer text stays out of the warehouse, and why a 19-digit ID must not become a float. Run the large-ID unit test and deliberately remove the protection to see what can go wrong in another tool.

### Session 2: Own the engineering

Trace `cli.py -> pipeline.py -> ingest.py -> quality.py -> warehouse.py`. Run offline twice and observe the unchanged-run skip. Change a local generated output and confirm the hash check requests regeneration. Add a quality rule for minimum nights greater than maximum nights and write a test demonstrating the behavior you want.

### Session 3: Defend the analysis

Reproduce a ward price query. Compare mean and median; explain the influence of the USD 11,680 maximum. Read H1's raw/trimmed results and explain why a test of arithmetic means differs from a rank test. Explain account-level dependence, Holm correction, survivor bias and partial review months.

### Session 4: Extend it independently

Choose one meaningful extension, record your design before coding, and open your own follow-up PR. Recommended: ingest the next public Albany snapshot and build a change report for listing arrivals/departures and price coverage. Preserve date-specific records instead of overwriting history.

## Interview questions you should be able to answer

| Question | What a strong answer should cover |
|---|---|
| Why DuckDB? | Analytical SQL without a server; fit to local scale; concurrency/operations trade-offs. |
| What is the calendar fact's grain? | One listing/day within one city/snapshot; a later scrape is a different observation. |
| How is the run idempotent? | Source/config/code/environment fingerprint plus verification of output hashes. |
| How do you handle schema changes? | Fail on required keys, retain optional nulls, explicit tested fallbacks, report missing capabilities. |
| Why not delete similar listings? | Multiple units can share names; fuzzy matching is evidence for review, not proof of duplication. |
| Can you calculate revenue? | Not realised revenue; calendar lacks prices and unavailable does not imply booked. |
| Why did advanced models lose? | Heavy-tailed target, limited sample and structural signals; demonstrate metrics instead of claiming success. |
| What would production need? | Monitoring, snapshot freshness checks, locks, atomic bundle publication, scalable storage and operational ownership. |
| What did AI do? | Code/design/report assistance; identify actual validation and your own later contributions honestly. |

## Honest CV wording

After you have personally run and understood the project:

> Built and validated an AI-assisted Python/SQL portfolio pipeline for 500 Albany rental listings, 182,500 calendar records and 30,251 reviews, including source checksums, a DuckDB dimensional model, data-quality tests and an offline analytics report.

After implementing a substantive extension yourself, add the exact contribution and measured result. Do not claim production deployment, business revenue improvement, independent authorship or professional employment experience from this project alone.

## Suggested follow-up backlog

- Add snapshot-to-snapshot diffs and reasoned deletion semantics.
- Evaluate a log-target or absolute-error model using a predeclared protocol and a new untouched validation snapshot.
- Add confidence intervals across repeated host splits and larger subgroup samples.
- Add automated schema drift alerts and an operational run lock.
- Validate a second city without mixing currencies.
- Add a small review-text experiment only after defining labels, language handling and privacy requirements.
