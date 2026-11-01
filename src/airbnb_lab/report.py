"""A data-driven portfolio report: results and limitations share equal billing."""
from html import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, KeepTogether

INK = colors.HexColor("#142e3b")
TEAL = colors.HexColor("#127c80")
PALE = colors.HexColor("#e9f2f0")
WIDTH = A4[0]-104


def fmt(value, digits=2):
    if value is None:
        return "Not available"
    return f"{value:,.{digits}f}"


def create(config, result, audit, profiles, figures, path):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Kicker",fontName="Helvetica-Bold",fontSize=9,leading=12,textColor=TEAL,spaceAfter=12))
    styles.add(ParagraphStyle(name="Heading",fontName="Helvetica-Bold",fontSize=25,leading=29,textColor=INK,spaceAfter=18))
    styles.add(ParagraphStyle(name="Text",fontName="Helvetica",fontSize=10.5,leading=15.5,textColor=INK,spaceAfter=11))
    styles.add(ParagraphStyle(name="SmallText",fontName="Helvetica",fontSize=8.4,leading=11.5,textColor=INK,spaceAfter=8))
    styles.add(ParagraphStyle(name="CaptionText",fontName="Helvetica",fontSize=8.5,leading=12,textColor=TEAL,spaceAfter=14))
    styles.add(ParagraphStyle(name="CellText",fontName="Helvetica",fontSize=8,leading=11,textColor=INK))
    pages=[]
    s=result["summary"]
    def p(text, style="Text"):
        text = text.replace("USD",config["currency"])
        if config["currency"] != "USD":
            text = text.replace("$",config["currency"]+" ")
        return Paragraph(text,styles[style])
    def table(headers, rows, widths=None):
        data=[[p(escape(str(v)),"CellText") for v in row] for row in [headers]+rows]
        t=Table(data,colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PALE),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("LINEBELOW",(0,0),(-1,-1),.4,colors.HexColor("#d6e2e2"))]))
        return t
    def callout(text):
        t=Table([[p(text,"Text")]],colWidths=[WIDTH])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("BOX",(0,0),(-1,-1),.5,colors.HexColor("#c6dcd7")),("TOPPADDING",(0,0),(-1,-1),13),("BOTTOMPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14)]))
        return t
    figure_no=0
    def figure(key, caption, height=260):
        nonlocal figure_no
        if key not in figures:
            return [callout("This figure is unavailable because its input analysis could not be estimated.")]
        figure_no+=1
        image=Image(str(figures[key]))
        scale=min(WIDTH/image.imageWidth,height/image.imageHeight)
        image.drawWidth=image.imageWidth*scale
        image.drawHeight=image.imageHeight*scale
        return [image,p(f"Figure {figure_no}. {caption}","CaptionText")]
    def page(title, blocks, tag="RESEARCH & ENGINEERING"):
        pages.append((title,[p(tag,"Kicker"),p(title,"Heading")]+blocks))

    page("Airbnb<br/>Market Lab",[
        p(f"{escape(config['display_name'])} | Snapshot {config['snapshot_date']}"),
        p("A personal data engineering and market intelligence project", "Kicker"),
        Spacer(1,20),
        table(["LISTINGS", "HOSTS", "REVIEW RECORDS"],[[f"{s['listings']:,}",f"{s['hosts']:,}",f"{s['reviews']:,}"]]),
        Spacer(1,24),
        p("<b>From source files to defensible decisions.</b> This project ingests a real public snapshot, checks its quality, builds a dimensional warehouse, explores market structure and tests how well listing attributes predict published prices."),
        p("The purpose is practical learning and a reviewable portfolio: reproducible code, explicit assumptions, visible failures and evidence-backed communication. No hiring or assessment outcome is claimed."),
        callout(f"<b>Headline:</b> Median positive listed price is ${fmt(s['median_price'])}; {s['missing_or_nonpositive_price']} listings have no usable positive price. Calendar prices are {'present' if audit['calendar_price_column_present'] else 'absent'} in the source."),
        Spacer(1,16),
        p("Source: Inside Airbnb, CC BY 4.0. Independent project; not affiliated with Airbnb. Prices are in the configured local currency (USD for Albany).", "SmallText")
    ],"PERSONAL PORTFOLIO / VERSION 1.0")
    # Contents inserted after all sections are known.
    pages.append(("Reading guide",[]))
    page("Executive brief",[
        p(f"The snapshot contains {s['listings']:,} listings operated by {s['hosts']:,} observed hosts. Of those listings, {s['priced_listings']:,} have a positive published price. The median is ${fmt(s['median_price'])}, while the mean is ${fmt(s['mean_price'])}; the difference makes segment-specific comparisons preferable to a single city average."),
        p(f"The largest 10% of observed hosts control {s['top_10pct_host_supply_share']:.1%} of listings. This is a useful concentration signal for supply monitoring. It does not identify business ownership: one account may represent multiple owners, and one owner may use several accounts."),
        p(f"The mean listing-level unavailable share is {s['mean_unavailable_share']:.1%}. Calendar state does not reveal the reason for unavailability. No realised occupancy, booking growth or income figure is inferred from it."),
        table(["Decision", "Evidence", "Practical next step"],[
            ["Build comparable groups","Prices vary with property mix","Filter by room type, capacity and ward before comparing prices."],
            ["Track missing prices","Some listings lack a usable price","Keep missing-price supply visible and avoid median imputation in descriptive reports."],
            ["Use model errors as a guardrail","Evaluation separates hosts","Treat predictions as experiments until repeat snapshots validate stability."],
            ["Delay income claims","Calendar pricing is unavailable here","Obtain verified booking and transaction data before estimating realised returns."]
        ],[110,145,WIDTH-255]),
        Spacer(1,15),callout("The most valuable result is a repeatable evidence trail. Every headline can be traced to source hashes, cleaning rules, analytical tables and generated artifacts.")
    ])
    page("Scope and success criteria",[
        p("The project focuses on one market so that ingestion, validation, modeling and communication can be tested together. Albany was already selected in the starter repository. Its manageable size supports a complete local run without paid services."),
        table(["Implemented workstream", "What completion means"],[
            ["Source understanding","All seven configured files downloaded; tabular schemas profiled; source dictionary and caveats reviewed."],
            ["Data engineering","Verified raw cache, deterministic cleaning, referential checks, DuckDB star schema and run metadata."],
            ["Analysis","Price/supply/review/availability summaries, statistical tests, confidence intervals and regression diagnostics."],
            ["Prediction","Three model families plus a median baseline; host-separated holdout and group cross-validation."],
            ["Communication","Offline explorer, generated report, notebook, SQL examples and a learning guide."]
        ],[140,WIDTH-140]),
        Spacer(1,16),p("Success means a reviewer can reproduce the results and identify what the data cannot answer. It does not mean a production pricing service, a complete census of all rentals or a causal evaluation of host behavior."),
        p("Cross-city work, demand forecasting, NLP, LLM integration and cloud deployment are deliberately deferred. Those extensions require additional validation, source history or evaluation labels. Adding them without those prerequisites would dilute the reliability of the core project."),
        p("The supplied brief informed the topic selection. The original confidential document is not copied into project artifacts or source control.","SmallText")
    ])
    page("Source inventory and semantics",[
        table(["Input", "Rows / features", "Grain and purpose"],[[k, f"{v.get('rows',v.get('features',0)):,}", desc] for k,desc in [
            ("listings","One source listing; detailed attributes and price"),("calendar","Listing and calendar date; future availability"),("reviews","Review ID; listing reference and publication date"),("listings_summary","Summary listing attributes; reconciliation input"),("reviews_summary","Listing and date; repeated same-day reviews are valid"),("neighbourhoods","Ward names and optional group"),("boundaries","Ward polygons for geographic context")]
            for v in [profiles[k]]],[115,90,WIDTH-205]),
        Spacer(1,14),p(f"The archive label is {config['snapshot_date']}, while the observed listing scrape date is {audit['as_of_date']}. Tenure and recent-review windows use the observed scrape date; the archive label remains the partition key."),
        p("Identifiers are strings throughout ingestion and cleaning. Some listing IDs exceed the exact integer range of common floating-point formats. Converting them through floats would silently break joins."),
        p("A host is an account, a listing is an advertised accommodation unit, and a review is a published guest review. Summary review rows have no unique review ID; repeated listing/date pairs are not automatically duplicates."),
        p("Source dictionary notes: price is in local currency; host registration date may predate hosting; geographic coordinates are approximate. Newer account-duration fields are interpreted as years plus months/12 when host_since is absent; this is an explicit schema assumption, not an exact reconstructed date.","SmallText")
    ])
    page("Data quality: evidence first",[
        table(["Check", "Observed result", "Treatment"],[
            ["Missing listing price",audit['missing_listing_prices'],"Keep listing; exclude from price statistics/models."],
            ["Negative listing price",audit['negative_listing_prices'],"Replace invalid price with null; report the count."],
            ["Duplicate listing keys",audit['listings_duplicate_keys_removed'],"Deterministically retain last input record."],
            ["Calendar orphan/invalid rows",audit['calendar_invalid_or_orphan_rows_removed'],"Remove before warehouse publication."],
            ["Review orphan/invalid/future rows",audit['reviews_invalid_future_or_orphan_rows_removed'],"Remove and count; retained source files permit diagnosis."],
            ["Calendar coverage",f"{audit['calendar_days_min']}-{audit['calendar_days_max']} days/listing","Expose coverage; denominators use known states."],
            ["Review-count reconciliation",audit['listing_review_count_mismatches'],"Compare detailed review counts to listing totals."],
            ["IQR price outliers",audit['price_iqr_outliers_retained'],"Flag and retain; unusual is not necessarily wrong."]
        ],[158,82,WIDTH-240]),
        Spacer(1,14),p("schema_profile.json covers row counts, null fractions, cardinality, inferred types and safe example values for every CSV column. Source files are read as strings first, so inference is descriptive rather than an implicit conversion policy."),
        p("Required-column failures stop the pipeline. Optional-field gaps produce nulls or an explicit unavailable analysis. A successful run means the configured checks passed, not that source values are objectively true."),
        callout("Quality metrics are not hidden cleanup details: they determine which business questions remain answerable.")
    ])
    page("Cleaning decisions and duplicates",[
        p("Currency strings are parsed with an explicit export format: a leading currency symbol, optional comma thousands separators and a decimal point. Malformed strings are not guessed. Negative prices become null, while zero prices remain visible but are excluded from positive-price comparisons."),
        p(f"Dates use a fixed ISO format. Geographic/rating/availability domains are checked. {audit.get('bathrooms_recovered_from_text',0)} bathroom counts are recovered from explicit text such as '1.5 shared baths'; ambiguous text remains null. {audit.get('account_tenure_recovered_from_duration',0)} account tenures use source years/months because registration dates are absent. Zero/missing bedrooms do not produce price-per-bedroom values."),
        p("Exact duplicate keys use a stable keep-last policy in source order. This is operationally reproducible, but it is not a claim that the final duplicate is the most accurate. A source revision can be compared using the archived raw hashes."),
        p(f"The title-similarity heuristic flagged {audit['fuzzy_candidate_pair_count']} candidate pairs within host and room/capacity blocks. A similarity score of at least 0.92 identifies records for inspection. Separate units often have nearly identical names, so no fuzzy candidate is automatically deleted."),
        table(["Field family", "Policy", "Reason"],[
            ["Categorical labels","Trim, normalize whitespace/case","Avoid accidental groups caused by formatting."],
            ["Missing numeric values","Retain null in analytical tables","Preserve uncertainty and unbiased denominators."],
            ["ML predictors","Training-fold median / mode imputation","Prevent leakage from held-out records."],
            ["Public outputs","Exclude identity/text/coordinates","Share aggregate evidence without republishing personal profiles."]
        ],[115,168,WIDTH-283]),
        Spacer(1,14),p("Fuzzy comparisons are capped at 200 records per block and can miss renamed units or cross-account duplicates. This heuristic is a review aid, not an entity-resolution system.","SmallText")
    ])
    page("Architecture and lineage",[
        table(["Layer", "Artifact", "Transformation"],[
            ["Source","Inside Airbnb dated URLs","Pinned city/snapshot config; seven files."],
            ["Raw","data/raw/city/date","Retry downloads; validate gzip; hash each file."],
            ["Extracted","data/extracted/city/date","Recreate CSV/GeoJSON cache from verified raw bytes."],
            ["Validated","In-memory typed frames","Key checks, domain checks, deduplication, quality audit."],
            ["Warehouse","data/warehouse/city/date.duckdb","Atomic database replacement after assertions."],
            ["Analysis","outputs/city/date/analysis.json","Summaries, tests, regression and model evaluation."],
            ["Presentation","Figures, explorer and this report","Generated from analysis results; no manual headline edits."]
        ],[75,175,WIDTH-250]),
        Spacer(1,18),p("A run fingerprint combines source checksums, city configuration, package code and dependency versions. The pipeline skips unchanged work only when every recorded output still matches its hash. A missing or damaged artifact forces regeneration."),
        p("The database is built in a temporary sibling file and moved into place after primary-key constraints and orphan assertions pass. Source downloads are promoted from partial files only after length and gzip integrity checks."),
        p("Report files are written during the run, and the success manifest is published last. Consumers should use only runs marked successful. Full cross-file transactional publication and concurrent-writer locking are future hardening work."),
        callout("Lineage rule: no analysis reads directly from an unverified network response. Raw bytes remain available locally for every result.")
    ])
    page("Dimensional model and SQL",[
        table(["Table", "Primary key", "Meaning"],[
            ["dim_listing","id","Listing snapshot plus review/calendar features."],
            ["dim_host","host_id","Observed account portfolio in this city."],
            ["dim_neighbourhood","neighbourhood","Observed ward label."],
            ["dim_date","date","Dates occurring in calendar/reviews."],
            ["fact_calendar","listing_id + date","Availability, optional price and stay rules."],
            ["fact_review","id","Listing reference and review date only."],
            ["snapshot_metadata","single row","City, archive date and currency."]
        ],[125,125,WIDTH-250]),
        Spacer(1,15),p("fact_calendar.listing_id and fact_review.listing_id join to dim_listing.id. Listing rows refer to host and neighbourhood dimensions; both facts refer to dim_date. Primary keys are enforced in DuckDB; referential integrity is asserted during publication."),
        p("Each database contains one city snapshot. Its effective grain includes the city and archive date encoded in the database path. This prevents overwriting history and avoids treating a review repeated in later snapshots as a newly written review."),
        p("The enriched listing dimension intentionally contains derived measures for convenient exploration. A larger warehouse would split slowly changing listing attributes from snapshot facts and use explicit compound or surrogate keys."),
        p("Two views expose ward metrics and monthly calendar summaries. sql/analytics.sql demonstrates price comparison, supply concentration, availability denominators and review activity. A date spine would be preferable for zero-filled time series in a production BI layer."),
        callout("DuckDB was chosen for local analytical SQL with no server setup. SQLite was viable for storage; PostgreSQL adds operational overhead at this scale.")
    ])
    page("Repeatability and operation",[
        p("Start with Python 3.11 or later, create a virtual environment, install the pinned dependencies, and run the command-line pipeline. The default config pins Albany rather than silently switching to a newer release."),
        table(["Command", "Purpose"],[
            ["python -m airbnb_lab.cli ingest","Download or validate source cache."],
            ["python -m airbnb_lab.cli run","Build all analytical outputs and report."],
            ["python -m airbnb_lab.cli run --offline","Rebuild or skip using only verified local inputs."],
            ["python -m airbnb_lab.cli run --force --offline","Regenerate even when inputs and code match."],
            ["python -m pytest -q","Run synthetic-data correctness tests."]
        ],[255,WIDTH-255]),
        Spacer(1,16),p("Incremental behavior is snapshot-level: a new date creates a separate raw partition, warehouse and output folder. Unchanged snapshots skip work. Row-level CDC, deletion tracking and Type 2 dimension intervals are not implemented."),
        p("Download retries use bounded exponential delay. Failures leave an error/status record and exit nonzero. The CI workflow runs unit and integration tests against synthetic data without depending on public downloads."),
        p("Docker Compose supplies a reproducible local execution path and persistent data/output mounts. It is a delivery configuration, not evidence of a cloud deployment. The environment verification notes identify whether Docker was executable on the authoring machine."),
        p("For a second city, supply its official path, date, currency and source file map. The code accepts configurations, but this release has been validated on Albany only. Numeric comparisons across currencies must not be pooled without a justified conversion design.")
    ])
    page("Price structure and comparisons",[
        *figure("price_distribution","Positive prices only; outliers remain in both the underlying statistics and this log-scale histogram."),
        p(f"Across {s['priced_listings']} priced listings, the median is ${fmt(s['median_price'])}; the 90th percentile is ${fmt(s['p90_price'])}. The mean of ${fmt(s['mean_price'])} gives more weight to expensive units. Neither measure is a transaction-weighted average."),
        p("A prospective host or market analyst should start with a comparable set rather than the city-wide mean. Room type, capacity, property category and location describe materially different offerings. The explorer exposes room and ward filters for this reason."),
        p("Missing prices are not assigned the overall median. Doing so would mechanically narrow the distribution and exaggerate coverage. Outliers are retained because a high price may be valid for a large or unusual property."),
        callout("Action: show the median, the number of priced listings and the number excluded together whenever a price benchmark is presented.")
    ])
    page("Room type and neighbourhood",[
        *figure("room_prices","Box plots hide individual outlier markers for readability; no records are removed from analysis.",230),
        table(["Room type", "Listings", "Priced", "Median USD"],[[x['room_type'],x['listings'],x['priced'],fmt(x['median_price'])] for x in result['room_types']],[190,80,80,WIDTH-350]),
        Spacer(1,15),p("Ward medians are published in neighbourhoods.csv, together with counts, rating summaries and confidence intervals for mean prices. Higher median prices may reflect a greater share of entire homes or larger units, so location should not be interpreted as the sole cause."),
        p("Confidence intervals resample hosts rather than individual listings. A selected host contributes all listings in that group, preserving within-host dependence. Groups with fewer than five hosts have no interval reported. Intervals are conditional on this observed snapshot, not guarantees about the whole rental market."),
        p("Action: use ward comparisons to form questions for deeper comparable-property research. Do not treat a small ward's rank as a stable investment ranking.")
    ])
    page("Geographic supply footprint",[
        *figure("supply_map","Official source ward boundaries coloured by listing count; not units per square kilometre.",315),
        p(f"The geographic view uses neighbourhood polygons rather than exact listing points. It describes the distribution of advertised supply across source-defined wards. {profiles['boundaries'].get('null_geometries',0)} source features have null geometry and cannot be drawn; their listings remain in non-map summaries."),
        p("Counts are not area-normalized density: wards differ in area, land use and housing stock. Without a valid housing denominator, the map cannot tell us what share of local housing is used for short stays."),
        p("Action: identify wards for follow-up supply monitoring, then compare room-type composition and review activity. A concentration of advertisements is not by itself evidence of legal status, displacement or property-level profitability."),
        p("No external basemap, geocoding API or paid key is required. City-centre premiums are deferred because no defensible centre definition or travel-time model has been introduced.","SmallText")
    ])
    page("Host concentration and supply",[
        *figure("host_concentration","Hosts ordered from largest to smallest observed city portfolio."),
        p(f"The top 10% of {s['hosts']} observed host accounts control {s['top_10pct_host_supply_share']:.1%} of the {s['listings']} listings. Portfolio size counts only listings in this city's snapshot and is separate from platform-reported global host counts."),
        p("The project labels accounts as single-listing or multiple-listing. Multiple listings can indicate professional activity, but this is a segmentation heuristic, not a verified commercial classification. A manager may act on behalf of several owners."),
        p("Action: monitor concentration across future snapshots and compare operator segments within room type. Large portfolios can affect aggregate pricing or availability without reflecting a market-wide change."),
        p("For model validation, all listings from the same account are kept on the same side of the train/test boundary. This makes the exercise closer to predicting prices for an unseen host and avoids an obvious source of overoptimistic evaluation.")
    ])
    page("Forward availability and demand",[
        *figure("availability","Monthly share of known calendar states that are available; edge months cover partial periods."),
        p(f"Each listing contributes {audit['calendar_days_min']}-{audit['calendar_days_max']} calendar observations. The chart is a forward-looking view from one scrape. Far-future dates may be unavailable because hosts have not opened their calendars; near-term dates may be blocked or booked."),
        p("The denominator is known availability states, not an unconditional 365. Unknown states remain missing. Monthly totals include partial first and last months, and therefore comparisons should use shares and coverage rather than raw counts alone."),
        p("Calendar nightly prices are missing in this snapshot. Weekend price testing, seasonal price curves and gross revenue scenarios are therefore explicitly unavailable. Repeating a listing's current price across 365 days would invent observations." if not audit['calendar_price_column_present'] else "Revenue sensitivity scenarios, where available, use only priced unavailable days and hypothetical booked fractions. They exclude unknown prices and all costs; they are not realised revenue."),
        callout("Action: collect repeated snapshots before studying changes in availability. Observing a transition still does not reveal whether a booking caused it.")
    ])
    page("Reviews and service signals",[
        *figure("reviews","Last 36 observed review months for listings present in the current snapshot; final month is partial."),
        p(f"The retained review table contains {s['reviews']:,} records. Recent-review frequency counts reviews in the 365 days ending at the observed scrape date. It is a demand-related proxy rather than a count of bookings or guests."),
        p(f"There are {s['rated_listings']} listings with an overall rating; the unweighted mean is {fmt(s['mean_rating'])} out of five. High values compress differences and can make a small numerical improvement look more meaningful than it is."),
        p("Review publication can lag a stay. Listings removed before this snapshot are absent from the historical series, creating survivor bias. The final month is incomplete, so a decline at the end is not evidence that bookings are falling."),
        p("Action: combine recent-review volume, minimum evidence thresholds and rating subdimensions before investigating service issues. Review text analysis is deferred; no guest text is sent to an external AI service.")
    ])
    page("Statistical design and findings",[
        p("H1-H3 compare one deterministic representative listing per host, selected by string-sorted listing ID before filtering. This limits within-host dependence but changes the target from all listings to selected host representatives. Missing outcomes are removed per test. H3 excludes exactly ten reviews."),
        table(["Question", "Test", "Holm p", "Result"],[[x['id']+": "+x['question'],x['test'],fmt(x.get('p_holm'),4),"Evidence against null" if x.get('reject_at_005') else ("Insufficient evidence" if x.get('status')=='ok' else "Not estimable")] for x in result['hypotheses']],[185,140,65,WIDTH-390]),
        Spacer(1,13),p("H1 and H2 use one-sided alternatives; H3 is two-sided. Welch tests do not assume equal variances. Shapiro-Wilk and median-centred Levene diagnostics are saved in analysis.json, alongside sample sizes, mean differences, two-sided 95% intervals and Cohen's d."),
        p("H4 uses Kruskal-Wallis on wards with at least five eligible hosts because price distributions are skewed. It tests distributional differences, not specifically equality of means. Its epsilon-squared effect size is reported in the machine-readable results. H5 requires within-listing weekday/weekend prices and then averages differences by host."),
        p("Holm adjustment covers the estimable hypothesis family. Failure to reject is not proof of equivalence. Statistical significance does not establish business importance, and no result is causal: property mix, selection and measurement limitations remain."),
        p("Because normality diagnostics indicate substantial departures, analysis.json also reports a 20%-trimmed Welch sensitivity test (Holm-adjusted across H1-H3), a rank test and probability-of-superiority effects. These target trimmed means/distributions, not the original arithmetic means. Compare conclusions rather than treating them as interchangeable proofs.","SmallText")
    ])
    reg=result['regression']
    page("Price associations and regression",[
        *figure("correlation","Pairwise Spearman correlations; missing pairs are omitted, so effective sample sizes vary.",260),
        p(f"The exploratory log-price OLS uses {reg.get('n',0)} complete cases and {reg.get('hosts',0)} host clusters. Its R-squared is {fmt(reg.get('r_squared'),3)}. Predictors are capacity, bedrooms, bathrooms and host tenure; clustered standard errors allow errors within a host to be related."),
        p("Coefficients, confidence limits, p-values and variance inflation factors are saved in analysis.json. Bedroom and capacity effects may be unstable when those attributes move together. VIF is a diagnostic for this dependence, not an instruction to automatically delete a predictor."),
        p("This reduced model omits location and unobserved quality. A coefficient describes conditional association within the selected complete-case sample. It should not be presented as the price increase caused by adding a bedroom or earning another year of host tenure."),
        callout("Action: use correlations and regression to identify questions and confounding, then judge predictive usefulness separately on held-out hosts.")
    ])
    m=result['models']
    page("Predictive modeling protocol",[
        p("The target is the positive published nightly listing price in USD. It is neither achieved booking revenue nor an optimal recommended price. All valid priced records, including expensive observations, remain eligible."),
        table(["Stage", "Design", "Reason"],[
            ["Holdout",f"{m.get('test_rows',0)} rows from {m.get('test_hosts',0)} unseen hosts","One fixed 20% host split; seed 42."],
            ["Training",f"{m.get('train_rows',0)} rows from {m.get('train_hosts',0)} hosts","Group cross-validation keeps host accounts together."],
            ["Preparation","Fold-local numeric median and categorical mode; one-hot encoding","No fitting transformations on the holdout."],
            ["Comparison","Median baseline, Ridge, Extra Trees, histogram gradient boosting","Compare a simple reference and three model families."],
            ["Selection","Lowest mean training group-CV MAE","Holdout performance does not select the winner."],
            ["Reporting","MAE, RMSE and MAPE; residual slices","Different metrics expose different failure modes."]
        ],[80,215,WIDTH-295]),
        Spacer(1,15),p("Features use structural and location attributes, amenity count, room/property type and account tenure. Price-per-bedroom, neighbourhood price aggregates, source revenue estimates and target-derived fields are deliberately excluded."),
        p("The fixed parameter choices are modest rather than extensively tuned. One seed and one city do not establish stable generalisation. No temporal split can be demonstrated with only one snapshot, and unseen-city behavior has not been tested."),
        callout("Selected model: <b>"+escape(m.get('selected_model','not estimable'))+"</b>. Selection criterion: training group-CV mean absolute error.")
    ])
    page("Model evidence and failure modes",[
        *figure("models","Training cross-validation and holdout errors shown separately. All scores are computed, not hand-entered.",235),
        table(["Model", "CV MAE", "Test MAE", "Test RMSE", "MAPE %"],[[x['model'],fmt(x['cv_mae']),fmt(x['test_mae']),fmt(x['test_rmse']),fmt(x['test_mape_pct'])] for x in m.get('scores',[])],[165,80,80,85,WIDTH-410]),
        Spacer(1,14),p("Permutation importance measures the increase in holdout MAE after shuffling one raw predictor. It is generated for the best non-baseline model by training CV, even if the median baseline is selected overall. Correlated features can share importance, and negative importance can occur through noise."),
        p("The residual figure and neighbourhood error table reveal uneven performance. Neighbourhood error slices with fewer than three test records are omitted. This is a diagnostic, not a fairness certification; small samples prevent reliable subgroup guarantees."),
        p("Action: compare any future model against the median baseline, repeat host splits, validate on a later snapshot and establish acceptable error by use case before deployment. A low average error alone is not sufficient for automatic pricing.")
    ])
    page("Recommendations and roadmap",[
        table(["Priority", "Recommendation", "Evidence / prerequisite"],[
            ["Now","Publish segmented benchmarks with coverage","Real prices, missingness and room/ward composition are observable."],
            ["Now","Retain quality and source manifests","Hashes and row counts make refreshes auditable."],
            ["Next","Add a second dated snapshot","Test change tracking, survivor effects and model stability."],
            ["Next","Add robust statistical sensitivity checks","Skew and representative-host selection can influence inference."],
            ["Later","Scale ingestion by city/date partitions","Add job orchestration, locks, failure alerts and bounded concurrency."],
            ["Later","Consider NLP or AI assistance","Need language checks, privacy review and an evaluation set first."]
        ],[52,235,WIDTH-287]),
        Spacer(1,16),p("For 50 or more cities, store immutable raw objects and partition analytical data by city, scrape date and calendar month. Use a job queue with per-city retries and a centralized metadata catalog. Avoid materializing every full review corpus in pandas memory."),
        p("A cloud design could pair object storage with scheduled container jobs and a query engine, but no paid resources were provisioned. Cost, latency and freshness targets must be agreed before selecting a managed platform."),
        p("Open limitations include absent calendar prices, incomplete price coverage, source selection/survivor bias, uncertain calendar semantics and only one validated market. Row-level CDC, true bookings/revenue, causal inference, NLP/RAG, live deployment and automated business recommendations are not claimed as completed."),
        callout("Portfolio focus: explain why a missing capability remains missing. A transparent boundary is more useful than a confident number unsupported by the source.")
    ])
    page("Ownership, learning and sources",[
        p("<b>AI assistance.</b> OpenAI Codex assisted with project design, Python and SQL implementation, tests, documentation and generated-report narrative. The exact underlying model version is not exposed in this artifact. No claim is made that the code was independently written by the project owner."),
        p("The key user direction was to treat the brief as a personal career-development project and build it with clear heads-ups. Validation includes actual source downloads, warehouse assertions, synthetic edge-case tests, end-to-end execution and rendered artifact inspection. See docs/verification.md for the final executed checks."),
        p("Meaningful corrections include retaining large IDs as strings, accounting for the archive/scrape date mismatch, declining to invent missing calendar prices, grouping model validation by host and retaining fuzzy duplicate candidates rather than deleting them."),
        p("<b>Learning ownership.</b> Before using this work in an interview, run the pipeline yourself, change a quality rule, inspect a SQL join and reproduce one figure. Describe which parts were AI-assisted and which extensions you personally implemented. docs/career-guide.md provides a walkthrough and honest CV wording."),
        table(["Reference", "Use"],[
            ["insideairbnb.com/get-the-data/","Dated source downloads; CC BY 4.0 attribution."],
            ["insideairbnb.com/data-assumptions/","Calendar and geographic interpretation caveats."],
            ["Inside Airbnb Data Dictionary (linked in README)","Source field meanings; currency and account-tenure interpretation."],
            ["scikit-learn: GroupShuffleSplit documentation","Group-separated validation semantics."],
            ["SciPy: scipy.stats.ttest_ind documentation","Welch and directional test implementation."]
        ],[250,WIDTH-250]),
        Spacer(1,13),p("Source files remain local and ignored by Git. Public outputs are aggregated or exclude identifiers and review text. The original project brief is not redistributed. Findings describe this frozen snapshot, not the current market.","SmallText")
    ],"TRANSPARENCY & NEXT STEPS")
    contents=[]
    for index,(title,_) in enumerate(pages):
        if index > 1:
            contents.append([title.replace("<br/>"," "),str(index+1)])
    pages[1]=( "Reading guide", [p("HOW TO REVIEW THIS PROJECT","Kicker"),p("Reading guide","Heading"),
        p("Start with the executive brief for the business story, then read the quality and modeling sections to understand what supports it. The repository contains executable evidence behind every result."),
        table(["Section","Page"],contents,[WIDTH-45,45]),Spacer(1,14),
        p("Companion artifacts: explorer.html for filters; analysis.json for statistical detail; schema_profile.json for source fields; quality_report.json for validation counts; sql/analytics.sql for warehouse queries.","SmallText")])
    story=[]
    for i,(_,blocks) in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.extend(blocks)
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(1)
        canvas.line(52,A4[1]-38,A4[0]-52,A4[1]-38)
        canvas.setFont("Helvetica",8)
        canvas.setFillColor(INK)
        canvas.drawString(52,29,"AIRBNB MARKET LAB  /  Independent portfolio research")
        canvas.drawRightString(A4[0]-52,29,str(doc.page))
        canvas.restoreState()
    path.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=52,leftMargin=52,topMargin=57,bottomMargin=48,
                          title="Airbnb Market Lab - Albany portfolio report",author="Airbnb Market Lab; AI-assisted personal project")
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
