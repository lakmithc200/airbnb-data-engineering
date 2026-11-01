# Data interpretation and assumptions

| Field or artifact | Interpretation / handling |
|---|---|
| Archive date | URL partition `2026-09-14`; not necessarily the actual listing scrape date. |
| Observed scrape date | `2026-09-16` for all Albany listings; used for recent-review windows. |
| price | Listed local-currency nightly amount; not realised ADR or total stay cost. Currency comes from config. |
| price_quote_* | Profiled source fields; not silently substituted into the target. |
| available = f | Unavailable, for an unknown reason; never actual booked occupancy. |
| Missing calendar price | H5, seasonal pricing and revenue scenarios unavailable; no constant-price imputation. |
| Unknown availability | Retained as null; excluded from known-state denominators. |
| host_since | Account-registration proxy, not necessarily hosting start. |
| hosts_time_as_user_years/months | When registration date is absent, interpret as additive duration components; valid years 0-100 and months 0-11. Approximate account tenure, not an exact date. The older published dictionary does not document these new fields. |
| bathrooms_text | Strictly parse explicit numeric bath labels or half-bath labels; do not infer ambiguous text. Shared/private describes usage, not a reduction in physical count. |
| bedrooms = 0 | Valid studio-like case; price per bedroom is null. |
| neighbourhood_cleansed | Source spatial label; preferred to a host's free-text area description. |
| Boundary null geometry | One source feature has no geometry; omit from map, retain its other records. |
| Coordinates | Approximate source locations; no property-level accuracy claims. |
| Host portfolio | Listings in this city snapshot only; account count is not ownership count. |
| Review series | Historical reviews for surviving listings, not historical market supply or actual bookings. |
| Review date duplicates | Multiple reviews on the same date are valid when IDs differ. Summary rows lack IDs. |
| Missing prices/ratings | Keep rows for supply analysis; omit from corresponding summaries and label denominators. |
| Price outliers | Flag with 1.5 IQR bounds; retain pending domain evidence. |

The schema profile covers all downloaded CSV columns and boundary properties. Names, text, URLs, identifiers and raw quote fields have example values redacted in shared profiles. Raw files and fuzzy candidate IDs stay local and are ignored by Git.

## Statistical contract

H1 and H2: one-sided Welch tests for an increase; H3: two-sided difference, with exactly 10 reviews excluded. One deterministic listing per host is selected before outcome filtering. This prevents accounts appearing in multiple nominally independent groups but may underrepresent their portfolios.

Report normality and variance diagnostics; Welch allows unequal variances, not arbitrary protection from extreme skew. A 20%-trimmed Welch sensitivity analysis and rank comparisons are included. The primary Holm family covers estimable H1-H5 tests; the trimmed sensitivity family covers H1-H3 separately. Confidence intervals are two-sided 95% intervals, even for directional tests. Neither test family establishes causality.

H4 uses Kruskal-Wallis for distributional differences in wards with at least five eligible hosts. It deliberately does not claim an ANOVA result for mean prices. H5, when possible, compares within-listing weekend/weekday means and then averages paired differences by host.

Price-group mean intervals resample hosts with all their group listings (500 replicates, seed 42). Intervals are absent below five hosts. These intervals are approximate uncertainty summaries for the observed sample, not sampling guarantees for all accommodation in Albany.

OLS uses complete cases, log price, four structural/tenure predictors and host-clustered standard errors. VIF measures multicollinearity. The model is associative and omits important confounders such as quality and location.

## Predictive contract

The train/test boundary is host-level; test size is 20% of hosts, not exactly 20% of listings. Five-fold group CV is computed only within training data. Median/mode imputation, scaling and encoding are fitted inside folds. Price-derived variables are excluded. Hyperparameters are fixed, and the selected model minimizes training CV MAE.

All positive prices, including outliers, are retained. The median baseline wins this snapshot. No trained pickle is shipped as an operational model; the code reproduces the benchmark and saves evaluation artifacts. No temporal, multi-city, causal or deployment performance is claimed.
