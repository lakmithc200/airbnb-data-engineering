"""Exploratory statistics and reproducible, host-separated model evaluation."""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.multitest import multipletests
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor


def records(df):
    """JSON-safe records with real nulls for unavailable/non-finite values."""
    import json
    return json.loads(df.to_json(orient="records", date_format="iso"))


def finite(value):
    return float(value) if np.isfinite(value) else None


def compare(a, b, key, question, alternative="two-sided"):
    a, b = np.asarray(a.dropna(), dtype=float), np.asarray(b.dropna(), dtype=float)
    result = {"id": key, "question": question, "test": "Welch independent t test",
              "alternative": alternative, "n_a": len(a), "n_b": len(b),
              "unit": "one deterministic listing per host", "null": "group means are equal"}
    if min(len(a), len(b)) < 5:
        return result | {"status": "not estimable", "reason": "Fewer than five hosts in a group"}
    test = stats.ttest_ind(a, b, equal_var=False, alternative=alternative)
    pooled = np.sqrt(((len(a)-1)*a.var(ddof=1)+(len(b)-1)*b.var(ddof=1))/(len(a)+len(b)-2))
    va, vb = a.var(ddof=1)/len(a), b.var(ddof=1)/len(b)
    se = np.sqrt(va+vb)
    df = (va+vb)**2/(va**2/(len(a)-1)+vb**2/(len(b)-1)) if se else np.inf
    margin = stats.t.ppf(.975, df)*se
    delta = a.mean()-b.mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        normal_a = stats.shapiro(a[:5000]).pvalue
        normal_b = stats.shapiro(b[:5000]).pvalue
        levene = stats.levene(a, b, center="median").pvalue
    trimmed = stats.ttest_ind(a, b, equal_var=False, trim=.2, alternative=alternative)
    rank = stats.mannwhitneyu(a, b, alternative=alternative)
    return result | {"status": "ok", "statistic": finite(test.statistic), "p_value": finite(test.pvalue),
                     "mean_a": float(a.mean()), "mean_b": float(b.mean()), "difference": float(delta),
                     "ci95_low": finite(delta-margin), "ci95_high": finite(delta+margin),
                     "cohens_d": finite(delta/pooled) if pooled else None,
                     "shapiro_p_a": finite(normal_a), "shapiro_p_b": finite(normal_b), "levene_p": finite(levene),
                     "trimmed_20pct_p": finite(trimmed.pvalue), "trimmed_mean_difference": float(stats.trim_mean(a,.2)-stats.trim_mean(b,.2)),
                     "rank_sensitivity_p": finite(rank.pvalue), "probability_a_exceeds_b": float(rank.statistic/(len(a)*len(b))),
                     "caveat": "Exploratory association; host selection changes the estimand. Welch allows unequal variance; skew and small groups weaken normal approximation."}


def hypotheses(l, c):
    # Stable host-level representative prevents a multi-listing operator from
    # appearing in both independent samples. All-listing EDA is kept separately.
    h = l.sort_values("id").drop_duplicates("host_id")
    p = h[h.price.gt(0)]
    results = [compare(p.loc[p.room_type.eq("entire home/apt"), "price"], p.loc[p.room_type.eq("private room"), "price"], "H1", "Entire home vs private room mean nightly price", "greater"),
               compare(h.loc[h.superhost.eq(True).fillna(False), "review_scores_rating"], h.loc[h.superhost.eq(False).fillna(False), "review_scores_rating"], "H2", "Superhost vs non-superhost mean rating", "greater"),
               compare(p.loc[p.number_of_reviews.gt(10), "price"], p.loc[p.number_of_reviews.lt(10), "price"], "H3", "More than 10 vs fewer than 10 reviews: mean price")]
    groups = [v.price.to_numpy() for _, v in p.groupby("neighbourhood") if len(v) >= 5]
    h4 = {"id": "H4", "question": "Price distributions differ across neighbourhoods", "test": "Kruskal-Wallis", "unit": "one deterministic listing per host", "null": "eligible neighbourhood price distributions are equal", "minimum_group_hosts": 5, "groups": len(groups)}
    if len(groups) >= 2 and len(np.unique(np.concatenate(groups))) > 1:
        t = stats.kruskal(*groups)
        n, k = sum(map(len, groups)), len(groups)
        h4.update(status="ok", statistic=finite(t.statistic), p_value=finite(t.pvalue), n=n,
                  epsilon_squared=max(0, float((t.statistic-k+1)/(n-k))),
                  caveat="Rank test chosen for skew; distributions, not necessarily means/medians. Shape equality is not assumed; excluded small areas are not tested.")
    else:
        h4.update(status="not estimable", reason="Insufficient eligible groups or variation")
    results.append(h4)
    paired = c[c.price.gt(0)].groupby(["listing_id", "weekend"]).price.mean().unstack()
    h5 = {"id": "H5", "question": "Weekend minus weekday nightly price", "test": "One-sample t test of host-average paired differences", "null": "mean within-host difference is zero"}
    if True in paired and False in paired:
        diff = (paired[True]-paired[False]).dropna().rename("difference").to_frame()
        diff = diff.join(l.set_index("id").host_id).groupby("host_id").difference.mean()
        if len(diff) >= 5 and diff.std() > 0:
            t = stats.ttest_1samp(diff, 0)
            ci = stats.t.interval(.95, len(diff)-1, loc=diff.mean(), scale=stats.sem(diff))
            h5.update(status="ok", n=len(diff), statistic=finite(t.statistic), p_value=finite(t.pvalue), difference=float(diff.mean()), ci95_low=float(ci[0]), ci95_high=float(ci[1]), cohens_d=float(diff.mean()/diff.std()))
        else:
            h5.update(status="not estimable", reason="Insufficient paired hosts or zero variance")
    else:
        h5.update(status="not estimable", reason="Calendar contains no usable paired nightly prices; listing price is not a substitute")
    results.append(h5)
    eligible = [x for x in results if x.get("p_value") is not None]
    if eligible:
        adjusted = multipletests([x["p_value"] for x in eligible], method="holm")[1]
        for item, value in zip(eligible, adjusted):
            item["p_holm"] = float(value)
            item["reject_at_005"] = bool(value < .05)
    sensitivity = [x for x in results if x.get("trimmed_20pct_p") is not None]
    if sensitivity:
        for item, value in zip(sensitivity, multipletests([x["trimmed_20pct_p"] for x in sensitivity], method="holm")[1]):
            item["trimmed_p_holm"] = float(value)
    return results


def cluster_mean_ci(frame, seed=42, repetitions=500):
    """Resample hosts, preserve every selected host's listings (ratio estimator)."""
    g = frame[frame.price.gt(0)].groupby("host_id").price.agg(["sum", "count"])
    if len(g) < 5:
        return (None, None)
    rng = np.random.default_rng(seed)
    sums, counts = g["sum"].to_numpy(), g["count"].to_numpy()
    draws = rng.integers(0, len(g), (repetitions, len(g)))
    estimates = sums[draws].sum(axis=1)/counts[draws].sum(axis=1)
    return tuple(float(x) for x in np.quantile(estimates, [.025, .975]))


def group_summary(l, by, seed):
    rows = []
    for label, g in l.groupby(by):
        p = g.loc[g.price.gt(0), "price"]
        low, high = cluster_mean_ci(g, seed)
        rows.append({by: label, "listings": len(g), "hosts": g.host_id.nunique(), "priced": len(p),
                     "median_price": finite(p.median()), "mean_price": finite(p.mean()), "mean_ci95_low": low, "mean_ci95_high": high,
                     "average_rating": finite(g.review_scores_rating.mean()), "unavailable_share": finite(g.unavailable_share.mean()),
                     "reviews_last_365d": int(g.reviews_last_365d.sum())})
    return rows


def regression(l):
    cols = ["accommodates", "bedrooms", "bathrooms", "host_tenure_years"]
    data = l[l.price.gt(0)].dropna(subset=cols + ["host_id"]).copy()
    if len(data) < 30 or data.host_id.nunique() < 10:
        return {"status": "not estimable", "reason": "Too few complete cases/hosts"}
    x = sm.add_constant(data[cols].astype(float), has_constant="add")
    fit = sm.OLS(np.log(data.price), x).fit(cov_type="cluster", cov_kwds={"groups": data.host_id.to_numpy()})
    ci = fit.conf_int()
    coefficients = []
    for i, col in enumerate(x):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            vif = variance_inflation_factor(x.to_numpy(), i) if i else np.nan
        coefficients.append({"feature": col, "coefficient": float(fit.params[col]), "p_value": finite(fit.pvalues[col]),
                             "ci95_low": finite(ci.loc[col, 0]), "ci95_high": finite(ci.loc[col, 1]), "vif": finite(vif)})
    return {"status": "ok", "n": len(data), "hosts": data.host_id.nunique(), "r_squared": float(fit.rsquared),
            "coefficients": coefficients, "method": "Complete-case log-price OLS with host-clustered standard errors",
            "caveat": "Associational reduced model; location and property quality confound effects. Missing values select the sample; coefficients are not causal price recommendations."}


def models(l, seed):
    numeric = ["accommodates", "bedrooms", "bathrooms", "beds", "latitude", "longitude", "amenity_count", "host_tenure_years"]
    categorical = ["room_type", "property_type", "neighbourhood"]
    features = numeric + categorical
    frame = l[l.price.gt(0)].reset_index(drop=True)
    if len(frame) < 60 or frame.host_id.nunique() < 15:
        return {"status": "not estimable", "reason": "Need at least 60 priced listings and 15 hosts"}, pd.DataFrame(), pd.DataFrame()
    x = frame[features].astype(object).where(frame[features].notna(), np.nan)
    for col in numeric:
        x[col] = x[col].astype(float)
    y, groups = frame.price, frame.host_id
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(x, y, groups))
    train_hosts, test_hosts = set(groups.iloc[train]), set(groups.iloc[test])
    assert not train_hosts & test_hosts
    prep = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)), ("scale", StandardScaler())]), numeric),
        ("category", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical),
    ])
    candidates = {"median_baseline": DummyRegressor(strategy="median"), "ridge": Ridge(alpha=10),
                  "extra_trees": ExtraTreesRegressor(n_estimators=200, min_samples_leaf=4, random_state=seed, n_jobs=1),
                  "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=150, max_leaf_nodes=15, l2_regularization=5, random_state=seed)}
    scores, fitted, predictions = [], {}, {}
    folds = GroupKFold(n_splits=min(5, len(train_hosts)))
    for name, estimator in candidates.items():
        pipe = Pipeline([("prepare", clone(prep)), ("model", estimator)])
        cv = -cross_val_score(pipe, x.iloc[train], y.iloc[train], groups=groups.iloc[train], cv=folds, scoring="neg_mean_absolute_error", n_jobs=1)
        pipe.fit(x.iloc[train], y.iloc[train])
        predicted = pipe.predict(x.iloc[test])
        scores.append({"model": name, "cv_mae": float(cv.mean()), "cv_mae_std": float(cv.std()),
                       "test_mae": float(mean_absolute_error(y.iloc[test], predicted)),
                       "test_rmse": float(np.sqrt(mean_squared_error(y.iloc[test], predicted))),
                       "test_mape_pct": float(100*mean_absolute_percentage_error(y.iloc[test], predicted))})
        fitted[name], predictions[name] = pipe, predicted
    winner = min(scores, key=lambda s: s["cv_mae"])["model"]
    # Explain a structural model even when the baseline wins; label it separately.
    explained = min([s for s in scores if s["model"] != "median_baseline"], key=lambda s: s["cv_mae"])["model"]
    perm = permutation_importance(fitted[explained], x.iloc[test], y.iloc[test], scoring="neg_mean_absolute_error", n_repeats=10, random_state=seed, n_jobs=1)
    importance = pd.DataFrame({"feature": features, "mae_increase": perm.importances_mean, "std": perm.importances_std}).sort_values("mae_increase", ascending=False)
    residuals = frame.iloc[test][["neighbourhood", "room_type", "price"]].copy()
    residuals["prediction"] = predictions[winner]
    residuals["residual"] = residuals.price-residuals.prediction
    residuals["absolute_error"] = residuals.residual.abs()
    bias = residuals.groupby("neighbourhood").agg(n=("price", "size"), mae=("absolute_error", "mean"), mean_residual=("residual", "mean"))
    return {"status": "ok", "train_rows": len(train), "test_rows": len(test), "train_hosts": len(train_hosts), "test_hosts": len(test_hosts),
            "host_overlap": 0, "folds": folds.n_splits, "selection": "lowest training group-CV MAE", "selected_model": winner,
            "explained_model": explained, "scores": scores, "features": features,
            "importance": records(importance), "neighbourhood_errors": records(bias[bias.n.ge(3)].reset_index()),
            "caveat": "One city, one snapshot and one group holdout. No temporal or cross-city validation; no deployment claim. MAPE is sensitive to cheap listings."}, residuals, importance


def analyze(tables, config):
    l, c, r = (tables[k] for k in ["listings", "calendar", "reviews"])
    p = l.loc[l.price.gt(0), "price"]
    portfolio = l.groupby("host_id").size().sort_values(ascending=False)
    top = max(1, int(np.ceil(len(portfolio)*.1)))
    monthly = c.groupby("month").agg(days=("date", "size"), known_days=("available", "count"), available_share=("available", "mean"), median_price=("price", "median"), priced_days=("price", "count"), median_minimum_nights=("minimum_nights", "median")).reset_index()
    reviews = r.assign(month=r.date.dt.strftime("%Y-%m")).groupby("month").size().rename("reviews").reset_index()
    numeric = ["price", "accommodates", "bedrooms", "bathrooms", "minimum_nights", "availability_365", "number_of_reviews", "review_scores_rating", "host_tenure_years"]
    summary = {"listings": len(l), "hosts": len(portfolio), "reviews": len(r), "calendar_rows": len(c),
               "priced_listings": len(p), "missing_or_nonpositive_price": int((~l.price.gt(0)).sum()),
               "median_price": finite(p.median()), "mean_price": finite(p.mean()), "p90_price": finite(p.quantile(.9)),
               "top_10pct_host_supply_share": float(portfolio.head(top).sum()/len(l)),
               "rated_listings": int(l.review_scores_rating.notna().sum()), "mean_rating": finite(l.review_scores_rating.mean()),
               "mean_unavailable_share": finite(l.unavailable_share.mean())}
    hypotheses_result = hypotheses(l, c)
    model_result, residuals, importance = models(l, config["seed"])
    priced_unavailable = c.loc[c.available.eq(False).fillna(False) & c.price.gt(0), "price"]
    scenarios = {"priced_unavailable_days": len(priced_unavailable), "total_known_unavailable_days": int(c.available.eq(False).sum()),
                 "method": "Sum observed prices on unavailable days, multiplied by a hypothetical booked fraction. Excludes missing prices, taxes, fees and costs; not measured revenue.",
                 "gross_scenarios": {str(f): float(priced_unavailable.sum()*f) for f in [.25, .5, .75]} if len(priced_unavailable) else None}
    results = {"summary": summary, "neighbourhoods": group_summary(l, "neighbourhood", config["seed"]),
               "room_types": group_summary(l, "room_type", config["seed"]), "host_segments": group_summary(l, "host_segment", config["seed"]),
               "calendar_months": records(monthly), "review_months": records(reviews), "hypotheses": hypotheses_result,
               "regression": regression(l), "models": model_result, "revenue_scenarios": scenarios,
               "descriptive": records(l[numeric].describe().reset_index()),
               "correlations": records(l[numeric].corr(method="spearman").reset_index())}
    return results, residuals, importance
