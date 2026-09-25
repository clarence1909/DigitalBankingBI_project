"""Analysis 5, segments: k-means on behaviour, with k chosen by silhouette score.

Customers who opened by Feb 2026 are described by their last six months
(Mar to Aug 2026). Customers with no transactions of their own in those six
months are 'Dormant' by rule, since there is no behaviour to cluster; k-means
runs on everyone else, using four features:

  * average month-end balance (log)
  * card purchases a month (log)
  * card share of money spent (card / card + transfers + bills)
  * share of months active

k is the value from 2 to 8 with the highest silhouette score. Segments are
named from their profile, not their cluster number, so the names survive a
rerun that numbers the clusters differently.
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.config import EXTRACTS_DIR, SEED

from . import common as C

K_RANGE = range(2, 9)
SAMPLE = 8000

ACTIONS = {
    "Savers": ("Protect the relationship: tiered savings and FD ladders, and a retention offer "
               "before large deposits mature.", "Treasurer"),
    "Card-first spenders": ("Card rewards and instalment plans; they keep little in savings, so lend "
                            "with care.", "Head of Cards"),
    "Everyday bankers": ("Win the salary: salary-crediting incentives, and the best audience for "
                         "personal financing.", "Head of Product"),
    "Transfers only": ("Get the card into use: in-app activation nudges and first-purchase cashback.",
                       "Head of Cards"),
    "Occasional users": ("Low-cost re-engagement: bill reminders and DuitNow QR prompts.",
                         "Head of Product"),
    "Dormant": ("Win back only where it is cheap; stop paying bonuses to channels that produce them.",
                "Head of Growth"),
}
ORDER = list(ACTIONS)


def features(con):
    return con.execute("""
        WITH w AS (
            SELECT m.*
            FROM marts.fct_customer_monthly AS m
            JOIN marts.dim_customer AS c ON c.customer_id = m.customer_id
            WHERE m.month_start BETWEEN DATE '2026-03-01' AND DATE '2026-08-01'
              AND c.cohort_month <= DATE '2026-02-01'
        )
        SELECT
            customer_id,
            avg(casa_balance + fd_balance)                                      AS avg_balance,
            avg(card_txns)                                                      AS card_txns,
            coalesce(sum(card_spend) / nullif(sum(card_spend) + sum(transfers_and_bills_out), 0), 0) AS card_share,
            avg(CASE WHEN is_active THEN 1.0 ELSE 0.0 END)                      AS active_share,
            avg(customer_txns)                                                  AS txns,
            avg(CASE WHEN salary_in > 0 THEN 1.0 ELSE 0.0 END)                  AS salary_share,
            sum(card_spend)                                                     AS card_spend,
            sum(casa_balance + fd_balance) FILTER (WHERE month_start = DATE '2026-08-01') AS deposits_aug
        FROM w
        GROUP BY customer_id
        ORDER BY customer_id
    """).df()


def name_clusters(profile):
    """Map cluster numbers to names using their median behaviour."""
    names, left = {}, list(profile.index)

    def take(name, cluster):
        names[cluster] = name
        left.remove(cluster)

    take("Savers", profile.loc[left, "avg_balance"].idxmax())
    take("Card-first spenders", profile.loc[left, "card_share"].idxmax())
    take("Occasional users", profile.loc[left, "active_share"].idxmin())
    rest = profile.loc[left].sort_values("card_share", ascending=False).index.tolist()
    if rest:
        take("Everyday bankers", rest[0])
    for i, cluster in enumerate(rest[1:]):
        take("Transfers only" if i == 0 else f"Other group {i}", cluster)
    return names


def run(con):
    f = features(con)
    f["deposits_aug"] = f["deposits_aug"].fillna(0)
    active = f[f["active_share"] > 0].copy()
    X = np.column_stack([np.log1p(active["avg_balance"]), np.log1p(active["card_txns"]),
                         active["card_share"], active["active_share"]])
    Xs = StandardScaler().fit_transform(X)
    scores = {}
    models = {}
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(Xs)
        scores[k] = float(silhouette_score(Xs, km.labels_, sample_size=SAMPLE, random_state=SEED))
        models[k] = km
    k = max(scores, key=scores.get)
    active["cluster"] = models[k].labels_
    profile = active.groupby("cluster")[["avg_balance", "card_share", "active_share", "txns"]].median()
    profile["active_share"] = active.groupby("cluster")["active_share"].mean()
    names = name_clusters(profile)
    f["segment"] = "Dormant"
    f.loc[active.index, "segment"] = active["cluster"].map(names)

    seg = f.groupby("segment").agg(customers=("customer_id", "size"), deposits=("deposits_aug", "sum"),
                                   card_spend=("card_spend", "sum"), median_balance=("avg_balance", "median"),
                                   median_txns=("txns", "median"), salary_share=("salary_share", "mean"))
    seg["share_of_customers"] = seg["customers"] / seg["customers"].sum()
    seg["share_of_deposits"] = seg["deposits"] / seg["deposits"].sum()
    seg["share_of_card_spend"] = seg["card_spend"] / seg["card_spend"].sum()
    seg = seg.reindex([s for s in ORDER if s in seg.index] + [s for s in seg.index if s not in ORDER])
    seg["action"] = [ACTIONS.get(s, ("", ""))[0] for s in seg.index]
    seg["owner"] = [ACTIONS.get(s, ("", ""))[1] for s in seg.index]

    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    out = seg.reset_index()[["segment", "customers", "share_of_customers", "deposits", "share_of_deposits",
                             "card_spend", "share_of_card_spend", "median_balance", "median_txns", "salary_share",
                             "action", "owner"]]
    out.to_csv(EXTRACTS_DIR / "customer_segments.csv", index=False, float_format="%.4f", lineterminator="\n")

    # Chart: three small multiples sharing the segment axis, one measure each
    fig, axes = C.new_figure(ncols=3, height=5.2, sharey=True)
    fig.subplots_adjust(left=0.17, right=0.97, bottom=0.08, wspace=0.12)
    y = np.arange(len(seg))[::-1]
    for ax, col, label in zip(axes, ["share_of_customers", "share_of_deposits", "share_of_card_spend"],
                              ["Share of customers", "Share of deposits", "Share of card spend"]):
        ax.barh(y, seg[col], height=0.55, color=C.BLUE)
        for yi, v in zip(y, seg[col]):
            ax.text(v + 0.015, yi, C.pct(v, 0), va="center", fontsize=9.5, color=C.INK)
        ax.set_xlim(0, 1.12)
        ax.set_xticks([])
        ax.set_title(label, loc="left", fontsize=10.5, color=C.INK_2)
        C.style_axis(ax, grid_axis="none")
        ax.spines["bottom"].set_visible(False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(seg.index)
    savers, spenders = seg.loc["Savers"], seg.loc["Card-first spenders"]
    title = (f"Savers are {C.pct(savers['share_of_customers'], 0)} of customers but hold "
             f"{C.pct(savers['share_of_deposits'], 0)} of deposits; card-first spenders make "
             f"{C.pct(spenders['share_of_card_spend'], 0)} of card spend")
    C.titles(fig, title, f"k-means on four behaviour features, k = {k} chosen by silhouette score "
                         f"({scores[k]:.2f}), plus dormant customers. Customers who opened by Feb 2026, "
                         f"behaviour Mar to Aug 2026.", extra_top=0.1)
    path = C.save(fig, "05_customer_segments.png")

    dormant = seg.loc["Dormant"]
    everyday = seg.loc["Everyday bankers"] if "Everyday bankers" in seg.index else None
    numbers = {
        "k": k, "silhouette_by_k": {str(kk): round(v, 4) for kk, v in scores.items()},
        "segments": out.drop(columns=["action", "owner"]).round(4).to_dict(orient="records"),
        "customers_segmented": int(len(f)),
    }
    finding = [
        f"k-means on four behaviour features, with k = {k} chosen by silhouette score ({scores[k]:.2f}), splits "
        f"active customers into {k} segments; a further {C.pct(dormant['share_of_customers'], 0)} of customers "
        f"made no transactions of their own in six months.",
        f"Deposits are concentrated: savers are {C.pct(savers['share_of_customers'], 0)} of customers and hold "
        f"{C.pct(savers['share_of_deposits'], 0)} of deposits (median balance {C.rm(savers['median_balance'])}), "
        f"so a few rate-sensitive customers drive the CASA ratio.",
        f"Card-first spenders make {C.pct(spenders['share_of_card_spend'], 0)} of card spend with a median balance "
        f"of {C.rm(spenders['median_balance'])}"
        + (f", and everyday bankers, who mostly have their salary paid in, make "
           f"{C.pct(everyday['share_of_card_spend'], 0)}." if everyday is not None else "."),
    ]
    return {"id": "segments", "title": title, "chart": path, "finding": finding, "numbers": numbers,
            "segment_table": out.round(4).to_dict(orient="records")}
