"""Publication figures; no listing coordinates or review text are exported."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

INK, TEAL, GOLD = "#142e3b", "#127c80", "#de9e45"


def create(tables, results, residuals, boundaries, folder, currency="USD"):
    folder.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.labelcolor": INK, "text.color": INK,
                         "axes.titleweight": "bold", "figure.facecolor": "white"})
    files = {}
    def save(name, fig):
        for axis in fig.axes:
            axis.set_xlabel(axis.get_xlabel().replace("USD",currency))
            axis.set_ylabel(axis.get_ylabel().replace("USD",currency))
        fig.tight_layout(pad=1.8)
        target = folder / f"{name}.png"
        fig.savefig(target, dpi=180, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        files[name] = target
    l, c, r = (tables[k] for k in ["listings", "calendar", "reviews"])
    fig, ax = plt.subplots(figsize=(9, 4.3))
    positive = l.loc[l.price.gt(0), "price"]
    ax.hist(positive, bins=np.geomspace(positive.min(), positive.max()*1.001, 30), color=TEAL, edgecolor="white")
    ax.set(xscale="log", xlabel="Nightly listed price (USD, logarithmic scale)", ylabel="Listings", title="The price distribution spans several market segments")
    ax.axvline(positive.median(), color=GOLD, lw=2, label=f"Median {currency} {positive.median():.2f}")
    ax.legend(frameon=False)
    save("price_distribution", fig)
    fig, ax = plt.subplots(figsize=(9, 4.3))
    rooms = [(k, v.loc[v.price.gt(0), "price"]) for k,v in l.groupby("room_type")]
    rooms = [(k,v) for k,v in rooms if len(v)]
    ax.boxplot([v for _,v in rooms], tick_labels=[f"{k}\nn={len(v)}" for k,v in rooms], showfliers=False, patch_artist=True, boxprops={"facecolor": "#b6dcda"}, medianprops={"color": INK})
    ax.set(ylabel="Listed nightly price (USD)", title="Room type is a necessary comparison filter")
    save("room_prices", fig)
    n = pd.DataFrame(results["neighbourhoods"]).sort_values("median_price")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.barh(n.neighbourhood, n.median_price, color=TEAL)
    ax.set(xlabel="Median listed nightly price (USD)", title="Neighbourhood medians reflect different property mixes")
    save("neighbourhood_prices", fig)
    features = json.loads(boundaries.read_text(encoding="utf-8"))["features"]
    counts = l.groupby("neighbourhood").size().to_dict()
    patches, values = [], []
    for feature in features:
        geometry = feature["geometry"]
        if geometry is None:
            continue
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        for polygon in polygons:
            patches.append(Polygon(polygon[0], closed=True))
            values.append(counts.get(feature["properties"].get("neighbourhood"), 0))
    fig, ax = plt.subplots(figsize=(9, 5))
    pc = PatchCollection(patches, cmap="YlGnBu", edgecolor="white", linewidth=.8)
    pc.set_array(np.asarray(values))
    ax.add_collection(pc)
    ax.autoscale_view()
    ax.set_aspect(1/np.cos(np.radians(l.latitude.mean())))
    ax.set(xlabel="Longitude", ylabel="Latitude", title="Supply footprint by Albany ward")
    fig.colorbar(pc, ax=ax, label="Listing count (not area-normalized density)")
    save("supply_map", fig)
    portfolio = l.groupby("host_id").size().sort_values(ascending=False).to_numpy()
    fig, ax = plt.subplots(figsize=(9, 4.3))
    ax.plot(np.arange(1,len(portfolio)+1)/len(portfolio)*100, np.cumsum(portfolio)/len(l)*100, color=TEAL, lw=2.5)
    ax.plot([0,100],[0,100], "--", color="#b8c3cb", label="Equal portfolio sizes")
    ax.set(xlabel="Cumulative share of hosts, largest first (%)", ylabel="Cumulative share of listings (%)", title="A small set of operators controls a large share of supply", xlim=(0,100), ylim=(0,100))
    ax.legend(frameon=False)
    save("host_concentration", fig)
    monthly = pd.DataFrame(results["calendar_months"])
    fig, ax = plt.subplots(figsize=(9, 4.3))
    ax.plot(monthly.month, monthly.available_share*100, color=TEAL, marker="o")
    ax.set(ylabel="Available listing-days / known listing-days (%)", title="Forward availability is a snapshot, not booked occupancy", ylim=(0,100))
    ax.tick_params(axis="x", rotation=45)
    save("availability", fig)
    reviews = pd.DataFrame(results["review_months"]).tail(36)
    fig, ax = plt.subplots(figsize=(9, 4.3))
    ax.bar(reviews.month, reviews.reviews, color=TEAL)
    ax.set(ylabel="Published reviews", title="Review activity for listings surviving in this snapshot")
    ax.set_xticks(np.arange(0,len(reviews),3), reviews.month.iloc[::3], rotation=45)
    save("reviews", fig)
    fig, ax = plt.subplots(figsize=(9, 4.3))
    ax.hist(l.review_scores_rating.dropna(), bins=20, color=TEAL, edgecolor="white")
    ax.set(xlabel="Overall review rating (0-5)", ylabel="Rated listings", title="High ratings leave limited separation between listings")
    save("ratings", fig)
    cols = ["price", "accommodates", "bedrooms", "bathrooms", "number_of_reviews", "availability_365"]
    corr = l[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(9, 5))
    im=ax.imshow(corr, vmin=-1,vmax=1,cmap="BrBG")
    labels=[x.replace("_", " ") for x in cols]
    ax.set_xticks(range(len(cols)),labels,rotation=35,ha="right")
    ax.set_yticks(range(len(cols)),labels)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j,i,f"{corr.iloc[i,j]:.2f}",ha="center",va="center",color="white" if abs(corr.iloc[i,j])>.6 else INK)
    fig.colorbar(im,ax=ax,label="Spearman correlation")
    ax.set_title("Structural features co-vary with listed price")
    save("correlation",fig)
    model = results["models"]
    if model["status"] == "ok":
        scores=pd.DataFrame(model["scores"])
        fig, ax = plt.subplots(figsize=(9,4.3))
        x=np.arange(len(scores))
        ax.bar(x-.18,scores.cv_mae,.36,label="Training group CV",color=TEAL)
        ax.bar(x+.18,scores.test_mae,.36,label="Held-out hosts",color=GOLD)
        ax.set_xticks(x,[v.replace("_","\n") for v in scores.model])
        ax.set(ylabel="Mean absolute error (USD/night)",title="Model selection uses training CV only; lower error is better")
        ax.legend(frameon=False)
        save("models",fig)
        importance=pd.DataFrame(model["importance"]).head(8).sort_values("mae_increase")
        fig,ax=plt.subplots(figsize=(9,4.3))
        ax.barh(importance.feature,importance.mae_increase,xerr=importance["std"],color=TEAL)
        ax.axvline(0,color=INK,lw=.7)
        ax.set(xlabel="Increase in holdout MAE after shuffling (USD)",title=f"Permutation importance: {model['explained_model']}")
        save("importance",fig)
        fig,ax=plt.subplots(figsize=(9,4.3))
        ax.scatter(residuals.price,residuals.residual,color=TEAL,alpha=.65,s=23)
        ax.axhline(0,color=GOLD,lw=2)
        ax.set(xlabel="Observed listed price (USD)",ylabel="Observed minus predicted (USD)",title="Residuals reveal where the selected model falls short")
        save("residuals",fig)
    return files
