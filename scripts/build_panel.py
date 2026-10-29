"""Parse the reviews into the analysis panel.

0. Exact duplicate rows in the source CSV (9,983 of them) are dropped on load.
1. Vintage: the first four-digit number in the title that falls in 1950 to 2017 (the
   spec's rule; a winery name such as "1912 Winemakers" is skipped, not taken).
2. Region label: country / province / region_1, or country / province when region_1
   is empty.
3. Inclusion rule, on vintages 2000 to 2016: at least 400 reviews and at least 10
   distinct vintages. Catch-all labels that span more than one climate are dropped
   (CATCH_ALL below), and the three generic Bordeaux AOC labels are merged.
4. The set of regions that passes must equal the included rows of data/regions.csv
   exactly. That list was frozen before any weather was fetched and re-frozen on
   2026-10-29 after the duplicate fix (docs/decisions.md). The script stops if not.

Writes data/reviews_panel.csv.gz and tables/region_inclusion.csv, and the counts to
results/panel_counts.json.
"""
import json, pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/winemag-data-130k-v2.csv"

CATCH_ALL = {
    "US / California / California": "state-wide label",
    "US / Oregon / Oregon": "state-wide label",
    "US / Washington / Washington": "state-wide label",
    "US / Virginia / Virginia": "state-wide label",
    "US / California / Central Coast": "super-AVA running about 400 km from the Bay Area to Santa Barbara",
    "Italy / Tuscany / Toscana": "region-wide IGT",
    "Italy / Sicily & Sardinia / Sicilia": "island-wide DOC and IGT",
}
MERGE = {
    "France / Bordeaux / Bordeaux": "France / Bordeaux / Bordeaux (generic)",
    "France / Bordeaux / Bordeaux Blanc": "France / Bordeaux / Bordeaux (generic)",
    "France / Bordeaux / Bordeaux Supérieur": "France / Bordeaux / Bordeaux (generic)",
}
MIN_REVIEWS, MIN_VINTAGES = 400, 10
YEARS = (2000, 2016)


def vintage(title):
    """First four-digit number in the title between 1950 and 2017, else None."""
    for y in re.findall(r"(?<!\d)(\d{4})(?!\d)", str(title)):
        if 1950 <= int(y) <= 2017:
            return int(y)
    return None


def label(df):
    lab = df.country + " / " + df.province + " / " + df.region_1.fillna("")
    return lab.where(df.region_1.notna(), df.country + " / " + df.province)


def main():
    df = pd.read_csv(RAW, index_col=0)
    n_all = len(df)
    df = df.drop_duplicates()
    n_dupes = n_all - len(df)
    df["vintage"] = df.title.map(vintage).astype(float)
    n_vintage = int(df.vintage.notna().sum())
    df = df[df.vintage.between(*YEARS)].copy()
    df["vintage"] = df.vintage.astype(int)
    df["label"] = label(df)
    df["region"] = df.label.replace(MERGE)

    g = df.groupby("region").agg(reviews=("points", "size"), vintages=("vintage", "nunique"))
    g["passes_counts"] = (g.reviews >= MIN_REVIEWS) & (g.vintages >= MIN_VINTAGES)
    g["dropped_reason"] = g.index.map(lambda r: CATCH_ALL.get(r, ""))
    g["included"] = g.passes_counts & (g.dropped_reason == "")
    inc = g[g.passes_counts].sort_values("reviews", ascending=False)
    (ROOT / "tables").mkdir(exist_ok=True)
    inc.drop(columns="passes_counts").to_csv(ROOT / "tables/region_inclusion.csv")

    frozen = pd.read_csv(ROOT / "data/regions.csv")
    frozen = frozen[frozen.included]
    chosen = set(g.index[g.included])
    if chosen != set(frozen.region):
        raise SystemExit(f"region list differs from data/regions.csv: "
                         f"{sorted(chosen ^ set(frozen.region))}")

    p = df[df.region.isin(chosen)].copy()
    p["taster"] = p.taster_name.fillna("(no taster named)")
    p["variety"] = p.variety.fillna("(no variety)")
    p = p[["region", "label", "vintage", "points", "price", "variety", "taster", "winery"]]
    p.to_csv(ROOT / "data/reviews_panel.csv.gz", index=False, compression="gzip")

    counts = {
        "reviews_all": n_all,
        "duplicate_rows_dropped": n_dupes,
        "reviews_unique": n_all - n_dupes,
        "reviews_with_vintage": n_vintage,
        "reviews_2000_2016": int(len(df)),
        "labels_passing_counts": int(g.passes_counts.sum()),
        "labels_dropped_catch_all": int((g.passes_counts & (g.dropped_reason != "")).sum()),
        "regions": len(chosen),
        "panel_reviews": int(len(p)),
        "panel_reviews_with_price": int(p.price.notna().sum()),
        "panel_tasters": int(p.taster.nunique()),
        "panel_varieties": int(p.variety.nunique()),
        "panel_no_taster": int((p.taster == "(no taster named)").sum()),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/panel_counts.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
