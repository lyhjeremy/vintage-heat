"""Write assets/data.json for the vintage explorer.

Per region and vintage: the season's temperature anomaly, the mean score against
expectation (the review residual after region, vintage-year, variety and taster fixed
effects, averaged over the region's reviews of that vintage), the review count and the
raw mean score. Plus the two-group model's slope and interval for the fitted line.
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    M = json.loads((ROOT / "results/models.json").read_text())
    cells = pd.read_csv(ROOT / "results/region_vintage_cells.csv")
    slopes = pd.read_csv(ROOT / "results/region_slopes.csv").set_index("region")
    nrm = pd.read_csv(ROOT / "data/region_normals.csv").set_index("region")
    two = M["models"]["two_group"]["coefs"]
    groups = {
        "cool": {"b": round(two["gst_cool"]["b"], 3), "lo": round(two["gst_cool"]["lo"], 3),
                 "hi": round(two["gst_cool"]["hi"], 3), "regions": M["regions"]["cool_group"]},
        "warm": {"b": round(two["gst_warm"]["b"], 3), "lo": round(two["gst_warm"]["lo"], 3),
                 "hi": round(two["gst_warm"]["hi"], 3), "regions": M["regions"]["warm_group"]},
    }
    regions = []
    for r, c in cells.groupby("region"):
        parts = r.split(" / ")
        name = parts[-1].replace(" (WA)", "").replace(" (generic)", ", generic AOCs")
        if len(parts) == 2:
            name = f"{parts[1]}"
        regions.append({
            "key": r, "name": name, "full": r.replace(" / ", ", "),
            "normal": round(float(nrm.loc[r, "gst_normal"]), 2), "band": nrm.loc[r, "band"],
            "group": "warm" if nrm.loc[r, "gst_normal"] >= M["split_c"] else "cool",
            "n": int(c.n.sum()), "slope": round(float(slopes.loc[r, "slope"]), 3),
            "v": [[int(x.vintage), round(x.gst_anom, 3), round(x.adj, 3), int(x.n), round(x.raw, 2)]
                  for x in c.sort_values("vintage").itertuples()],
        })
    out = {"split": M["split_c"], "groups": groups, "regions": regions}
    (ROOT / "assets/data.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    print(f"assets/data.json: {len(regions)} regions")


if __name__ == "__main__":
    main()
