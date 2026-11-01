"""Profiling and explicit cleaning rules. IDs never pass through floating point."""
from __future__ import annotations

from difflib import SequenceMatcher
from itertools import combinations
import json
import numpy as np
import pandas as pd

PRIVATE = ("name", "description", "comments", "reviewer", "url", "about", "overview", "license", "raw", "verifications")


def money(series: pd.Series) -> pd.Series:
    clean = series.astype("string").str.strip().str.replace(r"^[$£€]", "", regex=True)
    # Restrict separators to the documented US-style export, do not guess locale.
    valid = clean.str.fullmatch(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?").fillna(False)
    return pd.to_numeric(clean.where(valid).str.replace(",", "", regex=False), errors="coerce").astype(float)


def number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)


def bathrooms_from_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.lower()
    numeric = text.str.extract(r"^(\d+(?:\.\d+)?)\s+(?:(?:shared|private)\s+)?baths?$", expand=False)
    parsed = number(numeric)
    return parsed.mask(text.isin(["half-bath", "shared half-bath", "private half-bath"]), .5)


def profile(df: pd.DataFrame) -> dict:
    cols = {}
    for name in df:
        s = df[name]
        nonnull = s.dropna()
        numeric = pd.to_numeric(nonnull, errors="coerce")
        inferred = "numeric" if len(nonnull) and numeric.notna().all() else "string"
        sensitive = any(word in name for word in PRIVATE) or name.endswith("_id") or name in {"latitude", "longitude", "id"}
        cols[name] = {"storage_type": str(s.dtype), "inferred_type": inferred,
                      "null_count": int(s.isna().sum()), "null_rate": float(s.isna().mean()) if len(s) else 0,
                      "distinct": int(s.nunique()),
                      "samples": [] if sensitive else [str(v)[:80] for v in nonnull.drop_duplicates().head(3)],
                      "sample_redacted": sensitive}
        if inferred == "numeric" and name not in {"id", "listing_id", "host_id", "reviewer_id"}:
            finite = numeric[np.isfinite(numeric)]
            if len(finite):
                cols[name].update(min=float(finite.min()), max=float(finite.max()))
        if name in {"price", "adjusted_price", "price_quote_total_price", "price_quote_price_per_night"}:
            parsed = money(s).dropna()
            cols[name]["semantic_type"] = "local-currency amount"
            if len(parsed):
                cols[name].update(parsed_min=float(parsed.min()), parsed_max=float(parsed.max()))
        if name == "date" or name.endswith("_date") or name in {"host_since", "last_scraped", "first_review", "last_review", "calendar_last_scraped"}:
            parsed = pd.to_datetime(s, errors="coerce", format="%Y-%m-%d").dropna()
            cols[name]["semantic_type"] = "ISO date"
            if len(parsed):
                cols[name].update(parsed_min=str(parsed.min().date()), parsed_max=str(parsed.max().date()))
    return {"rows": len(df), "columns": len(df.columns), "exact_duplicate_rows": int(df.duplicated().sum()), "fields": cols}


def require(df, columns, entity):
    missing = set(columns) - set(df)
    if missing:
        raise ValueError(f"{entity} missing required columns: {sorted(missing)}")


def valid_id(s):
    return s.astype("string").str.fullmatch(r"[1-9]\d*").fillna(False)


def unique_rows(df, keys, label, audit):
    duplicate = df.duplicated(keys, keep="last")
    audit[f"{label}_duplicate_keys_removed"] = int(duplicate.sum())
    return df.loc[~duplicate].copy()


def clean_inputs(raw: dict, config: dict) -> tuple[dict, dict]:
    audit = {}
    l = raw["listings"].copy()
    require(l, ["id", "host_id", "price", "room_type", "neighbourhood_cleansed", "latitude", "longitude"], "listings")
    valid = valid_id(l.id) & valid_id(l.host_id)
    audit["listings_invalid_keys_removed"] = int((~valid).sum())
    l = unique_rows(l.loc[valid], ["id"], "listings", audit)
    # Currency is supplied by the city config, not inferred from dollar symbols.
    l["price"] = money(l.price)
    audit["negative_listing_prices"] = int(l.price.lt(0).sum())
    l.loc[l.price.lt(0), "price"] = np.nan
    audit["missing_listing_prices"] = int(l.price.isna().sum())
    audit["zero_listing_prices"] = int(l.price.eq(0).sum())
    numeric = ["latitude", "longitude", "accommodates", "bedrooms", "beds", "bathrooms", "minimum_nights", "maximum_nights", "availability_365", "number_of_reviews", "reviews_per_month", "review_scores_rating"]
    numeric += [c for c in l if c.startswith("review_scores_") and c not in numeric]
    for col in numeric:
        l[col] = number(l[col]) if col in l else np.nan
    bath_text = l.get("bathrooms_text", pd.Series(index=l.index, dtype="string"))
    parsed_baths = bathrooms_from_text(bath_text)
    audit["bathrooms_recovered_from_text"] = int((l.bathrooms.isna() & parsed_baths.notna()).sum())
    l["bathrooms"] = l.bathrooms.fillna(parsed_baths)
    for col, low, high in [("latitude", -90, 90), ("longitude", -180, 180), ("availability_365", 0, 365)]:
        bad = l[col].notna() & ~l[col].between(low, high)
        audit[f"invalid_{col}"] = int(bad.sum())
        l.loc[bad, col] = np.nan
    for col in [c for c in l if c.startswith("review_scores_")]:
        bad = l[col].notna() & ~l[col].between(0, 5)
        audit[f"invalid_{col}"] = int(bad.sum())
        l.loc[bad, col] = np.nan
    for col in ["accommodates", "bedrooms", "beds", "bathrooms", "minimum_nights", "maximum_nights", "number_of_reviews", "reviews_per_month"]:
        low = 1 if col in {"accommodates", "minimum_nights", "maximum_nights"} else 0
        bad = l[col].notna() & l[col].lt(low)
        audit[f"invalid_{col}"] = int(bad.sum())
        l.loc[bad, col] = np.nan
    for col in ["host_since", "last_scraped", "first_review", "last_review"]:
        original = l[col] if col in l else pd.Series(pd.NA, index=l.index)
        l[col] = pd.to_datetime(original, errors="coerce", format="%Y-%m-%d")
        audit[f"invalid_{col}"] = int((original.notna() & l[col].isna()).sum())
    as_of = l.last_scraped.max()
    if pd.isna(as_of):
        as_of = pd.Timestamp(config["snapshot_date"])
    audit["as_of_date"] = as_of.strftime("%Y-%m-%d")
    audit["snapshot_label"] = config["snapshot_date"]
    l["neighbourhood"] = l.neighbourhood_cleansed.astype("string").str.strip().str.replace(r"\s+", " ", regex=True).fillna("Unknown")
    for col in ["room_type", "property_type"]:
        l[col] = l[col].astype("string").str.strip().str.lower().fillna("unknown") if col in l else "unknown"
    l["superhost"] = l.get("host_is_superhost", pd.Series(index=l.index, dtype="string")).map({"t": True, "f": False}).astype("boolean")
    l["host_tenure_years"] = ((as_of - l.host_since).dt.days / 365.25).where(l.host_since.le(as_of))
    # Newer snapshots provide elapsed account duration instead of host_since.
    # Treat years/months as components; do not invent an exact registration date.
    years = number(l.get("hosts_time_as_user_years", pd.Series(index=l.index, dtype="string")))
    months = number(l.get("hosts_time_as_user_months", pd.Series(index=l.index, dtype="string")))
    duration = (years + months/12).where(years.between(0,100) & months.between(0,11))
    audit["account_tenure_recovered_from_duration"] = int((l.host_tenure_years.isna() & duration.notna()).sum())
    l["host_tenure_years"] = l.host_tenure_years.fillna(duration)
    l["price_per_bedroom"] = l.price / l.bedrooms.where(l.bedrooms.gt(0))
    l["host_portfolio_size"] = l.groupby("host_id").id.transform("size")
    l["host_segment"] = np.where(l.host_portfolio_size.eq(1), "single listing", "multiple listings")
    def amenity_count(value):
        try:
            parsed = json.loads(value)
            return len(parsed) if isinstance(parsed, list) else np.nan
        except (ValueError, TypeError):
            return np.nan
    l["amenity_count"] = l.get("amenities", pd.Series(index=l.index, dtype="string")).map(amenity_count)
    l["host_response_rate_pct"] = number(l.get("host_response_rate", pd.Series(index=l.index, dtype="string")).astype("string").str.rstrip("%"))
    l.loc[~l.host_response_rate_pct.between(0, 100), "host_response_rate_pct"] = np.nan
    positive = l.loc[l.price.gt(0), "price"]
    q1, q3 = positive.quantile([.25, .75]) if len(positive) else (np.nan, np.nan)
    l["price_outlier_iqr"] = l.price.gt(q3 + 1.5 * (q3 - q1)) | l.price.lt(max(0, q1 - 1.5 * (q3 - q1)))
    audit["price_iqr_outliers_retained"] = int(l.price_outlier_iqr.sum())
    audit["fuzzy_candidate_pairs"] = fuzzy_candidates(l)

    c = raw["calendar"].copy()
    require(c, ["listing_id", "date", "available"], "calendar")
    c["date"] = pd.to_datetime(c.date, errors="coerce", format="%Y-%m-%d")
    valid = valid_id(c.listing_id) & c.date.notna() & c.listing_id.isin(l.id)
    audit["calendar_invalid_or_orphan_rows_removed"] = int((~valid).sum())
    c = unique_rows(c.loc[valid], ["listing_id", "date"], "calendar", audit)
    audit["calendar_price_column_present"] = "price" in c
    c["price"] = money(c.price) if "price" in c else np.nan
    audit["negative_calendar_prices"] = int(c.price.lt(0).sum())
    c.loc[c.price.lt(0), "price"] = np.nan
    c["available"] = c.available.map({"t": True, "f": False}).astype("boolean")
    audit["calendar_unknown_availability"] = int(c.available.isna().sum())
    for col in ["minimum_nights", "maximum_nights"]:
        c[col] = number(c[col]) if col in c else np.nan
        c.loc[c[col].lt(1), col] = np.nan
    c["weekend"] = c.date.dt.dayofweek.ge(5)
    c["month"] = c.date.dt.strftime("%Y-%m")
    r = raw["reviews"].copy()
    require(r, ["id", "listing_id", "date"], "reviews")
    r["date"] = pd.to_datetime(r.date, errors="coerce", format="%Y-%m-%d")
    valid = valid_id(r.id) & valid_id(r.listing_id) & r.listing_id.isin(l.id) & r.date.notna() & r.date.le(as_of)
    audit["reviews_invalid_future_or_orphan_rows_removed"] = int((~valid).sum())
    r = unique_rows(r.loc[valid], ["id"], "reviews", audit)
    r = r[["id", "listing_id", "date"]]  # No reviewer identity or text in analytical tables.
    recent = r[r.date.gt(as_of - pd.Timedelta(days=365))].groupby("listing_id").size()
    all_reviews = r.groupby("listing_id").size()
    l["observed_review_count"] = l.id.map(all_reviews).fillna(0).astype(int)
    l["reviews_last_365d"] = l.id.map(recent).fillna(0).astype(int)
    availability = c.groupby("listing_id").agg(calendar_days=("date", "size"), known_days=("available", "count"), available_days=("available", "sum"))
    availability["unavailable_share"] = 1 - availability.available_days / availability.known_days.where(availability.known_days.gt(0))
    l = l.merge(availability, how="left", left_on="id", right_index=True, validate="one_to_one")
    audit["listings_without_calendar"] = int(l.calendar_days.isna().sum())
    audit["calendar_days_min"] = int(availability.calendar_days.min()) if len(availability) else 0
    audit["calendar_days_max"] = int(availability.calendar_days.max()) if len(availability) else 0
    audit["listing_review_count_mismatches"] = int(l.number_of_reviews.ne(l.observed_review_count).sum())
    audit["rows_clean"] = {"listings": len(l), "calendar": len(c), "reviews": len(r)}
    safe = ["id", "host_id", "neighbourhood", "room_type", "property_type", "price", "latitude", "longitude"] + numeric[2:]
    safe += ["superhost", "host_tenure_years", "price_per_bedroom", "host_portfolio_size", "host_segment", "amenity_count", "host_response_rate_pct", "price_outlier_iqr", "observed_review_count", "reviews_last_365d", "calendar_days", "known_days", "available_days", "unavailable_share"]
    return {"listings": l[list(dict.fromkeys(safe))], "calendar": c, "reviews": r}, audit


def fuzzy_candidates(l):
    """Flag similar titles within a host; never auto-delete separate units."""
    pairs = []
    if "name" not in l:
        return pairs
    for _, group in l.groupby("host_id"):
        # Block by room type and capacity to bound comparisons.
        for _, block in group.groupby(["room_type", "accommodates"], dropna=False):
            if len(block) > 200:
                continue
            for a, b in combinations(block.to_dict("records"), 2):
                if pd.isna(a["name"]) or pd.isna(b["name"]):
                    continue
                score = SequenceMatcher(None, str(a["name"]).lower(), str(b["name"]).lower()).ratio()
                if score >= .92:
                    pairs.append({"listing_a": a["id"], "listing_b": b["id"], "similarity": round(score, 3)})
    return pairs
