"""Write every number the site, write-up and README quote into results/numbers.json
and site/numbers.json. The templates never type a result; build_site.py fills them.
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
MINUS = "−"


def sg(x, d=2):
    """Signed number with a true minus sign."""
    s = f"{abs(x):.{d}f}"
    if round(x, d) == 0:
        return s
    return ("+" if x > 0 else MINUS) + s


def un(x, d=2):
    s = f"{abs(x):.{d}f}"
    return (MINUS + s) if x < 0 and round(x, d) != 0 else s


def pv(p):
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}" if p < 0.1 else f"p = {p:.2f}"


def put(n, key, c, d=2):
    n[key] = sg(c["b"], d)
    n[key + "Abs"] = f"{abs(c['b']):.{d}f}"
    n[key + "Lo"] = un(c["lo"], d)
    n[key + "Hi"] = un(c["hi"], d)
    n[key + "P"] = pv(c["p"])
    n[key + "Ci"] = f"{un(c['lo'], d)} to {un(c['hi'], d)}"


def main():
    M = json.loads((RES / "models.json").read_text())
    C = json.loads((RES / "panel_counts.json").read_text())
    mm = M["models"]
    e = M["eda"]
    elev = pd.read_csv(ROOT / "tables/elevation_check.csv")
    n = {
        "nReviewsAll": f"{C['reviews_all']:,}",
        "nVintage": f"{C['reviews_with_vintage']:,}",
        "nReviews0016": f"{C['reviews_2000_2016']:,}",
        "nPanel": f"{C['panel_reviews']:,}",
        "nPanelPrice": f"{C['panel_reviews_with_price']:,}",
        "nRegions": C["regions"],
        "nCatchAll": C["labels_dropped_catch_all"],
        "nTasters": C["panel_tasters"] - (1 if C["panel_no_taster"] else 0),
        "nNoTaster": f"{C['panel_no_taster']:,}",
        "nVarieties": C["panel_varieties"],
        "nCool": M["regions"]["cool_group"],
        "nWarm": M["regions"]["warm_group"],
        "nReviewsCool": f"{M['regions']['reviews_cool_group']:,}",
        "nReviewsWarm": f"{M['regions']['reviews_warm_group']:,}",
        "split": f"{M['split_c']:.0f}",
        "elevPass": int((elev.check == "pass").sum()),
        "elevUnchecked": int((elev.check == "no elevation in source").sum()),
        "elevMaxDist": f"{elev.distance_m.max():.0f}",
        "warmingDecade": f"{e['warming_per_decade_1991_2020']:.2f}",
        "warmingDecadePanel": f"{e['warming_per_decade_2000_2016']:.2f}",
        "gstMin": f"{e['gst_normal_min']:.1f}", "gstMax": f"{e['gst_normal_max']:.1f}",
        "gstMinRegion": e["gst_normal_min_region"].split(" / ")[-1],
        "gstMaxRegion": e["gst_normal_max_region"].split(" / ")[-1],
        "anomSd": f"{e['gst_anom_sd_panel']:.2f}",
        "rainSd": f"{e['harvest_rain_anom_sd_panel']:.0f}",
        "pointsMean": f"{e['points_mean']:.1f}", "pointsSd": f"{e['points_sd']:.1f}",
        "oneTaster90": e["regions_one_taster_over_90pct"],
        "oneTaster50": e["regions_one_taster_over_50pct"],
        "slopesPos": M["region_slopes"]["positive"], "slopesNeg": M["region_slopes"]["negative"],
    }
    for b, k in M["regions"]["by_band"].items():
        n[f"nBand_{b}"] = k
    for b in ("cool", "intermediate", "warm", "hot"):
        n.setdefault(f"nBand_{b}", 0)

    t = mm["two_group"]["coefs"]
    put(n, "cool", t["gst_cool"]); put(n, "warm", t["gst_warm"]); put(n, "rain", t["rain"])
    put(n, "diff", mm["two_group"]["diff_warm_minus_cool"])
    n["withinR2"] = f"{mm['two_group']['within_r2']:.4f}"
    n["withinR2Pct"] = f"{100 * mm['two_group']['within_r2']:.2f}"
    i = mm["main_interaction"]["coefs"]
    put(n, "intAnom", i["gst_anom"]); put(n, "intSlope", i["gst_x_normal"]); put(n, "intRain", i["rain"])
    for b in ("cool", "intermediate", "warm", "hot"):
        k = f"gst_b_{b}"
        if k in mm["four_band"]["coefs"]:
            put(n, f"band_{b}", mm["four_band"]["coefs"][k])
    rb = mm["rain_by_group"]["coefs"]
    put(n, "rainCool", rb["rain_cool"]); put(n, "rainWarm", rb["rain_warm"])
    for key, model in [("trend", "region_trends"), ("price", "with_price"), ("priceSample", "two_group_price_sample"),
                       ("cellW", "cell_weighted"), ("cellU", "cell_unweighted"), ("named", "named_tasters"),
                       ("north", "north_only")]:
        c = mm[model]["coefs"]
        put(n, key + "Cool", c["gst_cool"]); put(n, key + "Warm", c["gst_warm"])
    put(n, "logPrice", mm["with_price"]["coefs"]["log_price"])
    p = mm["placebo_next_only"]["coefs"]
    put(n, "plcCool", p["gst_next_cool"]); put(n, "plcWarm", p["gst_next_warm"]); put(n, "plcRain", p["rain_next"])
    pj = mm["placebo_joint"]["coefs"]
    put(n, "jointCool", pj["gst_cool"]); put(n, "jointWarm", pj["gst_warm"])
    put(n, "plcjCool", pj["gst_next_cool"]); put(n, "plcjWarm", pj["gst_next_warm"])
    g = mm["gdd"]["coefs"]
    put(n, "gddCool", g["gdd_cool"]); put(n, "gddWarm", g["gdd_warm"])
    h = mm["heat_days"]["coefs"]
    put(n, "heatCool", h["heat_cool"], 3); put(n, "heatWarm", h["heat_warm"], 3)
    lo = M["leave_one_region_out"]
    n["looCoolMin"], n["looCoolMax"] = sg(lo["gst_cool"]["min"]), sg(lo["gst_cool"]["max"])
    n["looWarmMin"], n["looWarmMax"] = sg(lo["gst_warm"]["min"]), sg(lo["gst_warm"]["max"])
    n["looCoolMinRegion"] = lo["gst_cool"]["min_region"].split(" / ")[-1]
    n["looCoolMaxRegion"] = lo["gst_cool"]["max_region"].split(" / ")[-1]
    n["looWarmMinRegion"] = lo["gst_warm"]["min_region"].split(" / ")[-1]
    n["looWarmMaxRegion"] = lo["gst_warm"]["max_region"].split(" / ")[-1]
    o = M["out_of_sample"]
    n["oosCells"] = f"{o['cells']:,}"
    n["rmseBase"], n["rmseWeather"] = f"{o['rmse_baseline']:.3f}", f"{o['rmse_weather']:.3f}"
    n["oosImprove"] = f"{o['improvement_pct']:.1f}"
    n["oosBetter"], n["oosVintages"] = o["vintages_weather_better"], o["vintages"]
    # size in context: one standard deviation of the season anomaly
    n["coolPerSd"] = sg(t["gst_cool"]["b"] * e["gst_anom_sd_panel"])
    n["warmPerSd"] = sg(t["gst_warm"]["b"] * e["gst_anom_sd_panel"])

    (RES / "numbers.json").write_text(json.dumps(n, indent=1, ensure_ascii=False))
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site/numbers.json").write_text(json.dumps(n, indent=1, ensure_ascii=False))
    print(f"{len(n)} numbers written")


if __name__ == "__main__":
    main()
