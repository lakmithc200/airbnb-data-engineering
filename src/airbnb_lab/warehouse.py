"""Snapshot-grained star schema; publish database only after all checks pass."""
from pathlib import Path
import duckdb
import pandas as pd


def build(tables: dict, destination: Path, config: dict) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = destination.with_suffix(".pending.duckdb")
    pending.unlink(missing_ok=True)
    l, c, r = (tables[x] for x in ("listings", "calendar", "reviews"))
    hosts = l[["host_id", "host_portfolio_size", "host_segment"]].drop_duplicates("host_id")
    neighbourhoods = pd.DataFrame({"neighbourhood": sorted(l.neighbourhood.unique())})
    dates = pd.DataFrame({"date": pd.concat([c.date, r.date]).drop_duplicates().sort_values()})
    dates["year"] = dates.date.dt.year
    dates["month"] = dates.date.dt.month
    dates["weekend"] = dates.date.dt.dayofweek.ge(5)
    with duckdb.connect(str(pending)) as con:
        con.execute("BEGIN")
        for name, df in [("dim_host", hosts), ("dim_neighbourhood", neighbourhoods), ("dim_date", dates), ("dim_listing", l), ("fact_calendar", c), ("fact_review", r)]:
            con.register("frame", df)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM frame")
        con.execute("ALTER TABLE dim_host ADD PRIMARY KEY (host_id)")
        con.execute("ALTER TABLE dim_neighbourhood ADD PRIMARY KEY (neighbourhood)")
        con.execute("ALTER TABLE dim_date ADD PRIMARY KEY (date)")
        con.execute("ALTER TABLE dim_listing ADD PRIMARY KEY (id)")
        con.execute("ALTER TABLE fact_calendar ADD PRIMARY KEY (listing_id, date)")
        con.execute("ALTER TABLE fact_review ADD PRIMARY KEY (id)")
        # Foreign-key assertions are explicit, since CTAS does not retain constraints.
        for table in ["fact_calendar", "fact_review"]:
            if con.execute(f"SELECT count(*) FROM {table} f ANTI JOIN dim_listing l ON f.listing_id=l.id").fetchone()[0]:
                raise ValueError(f"Orphan listing reference in {table}")
        con.execute("CREATE TABLE snapshot_metadata(city VARCHAR, snapshot_date DATE, currency VARCHAR)")
        con.execute("INSERT INTO snapshot_metadata VALUES (?, ?, ?)", [config["city"], config["snapshot_date"], config["currency"]])
        con.execute("""CREATE VIEW mart_neighbourhood AS
          SELECT neighbourhood, count(*) listings, count(price) priced_listings,
            median(price) FILTER (WHERE price>0) median_price,
            avg(review_scores_rating) average_rating,
            avg(unavailable_share) mean_unavailable_share,
            sum(reviews_last_365d) reviews_last_365d
          FROM dim_listing GROUP BY neighbourhood""")
        con.execute("""CREATE VIEW mart_calendar_month AS
          SELECT month, count(*) listing_days, count(available) known_days,
            avg(CAST(available AS INTEGER)) available_share,
            median(price) FILTER (WHERE price>0) median_price,
            count(price) priced_days, median(minimum_nights) median_minimum_nights
          FROM fact_calendar GROUP BY month""")
        con.execute("COMMIT")
        counts = {name: con.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in ["dim_listing", "dim_host", "fact_calendar", "fact_review"]}
    pending.replace(destination)
    return counts
