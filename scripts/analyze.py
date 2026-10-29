"""All models. Reads the review panel and the season weather; writes results/models.json,
results/*.csv and tables/*.csv. No figures here (make_figures.py) and no copy
(export_numbers.py).

Fixed effects are absorbed by projecting every variable off the stacked fixed-effect
dummies (sparse least squares, scipy's lsqr) and the remaining coefficients are estimated by OLS on the demeaned data,
with standard errors clustered by region (CR1: G/(G-1) x (N-1)/(N-K), where K
counts the fixed effects as well).
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
TAB = ROOT / "tables"
SPLIT = 17.0  # °C: the boundary between Jones's intermediate and warm groups
RAIN_UNIT = 100.0  # harvest rain coefficients are per 100 mm


# ---------------------------------------------------------------- estimation helpers
def demean(M, fes, w=None):
    """Residualize the columns of M on the fixed effects fes (weighted if w is given):
    a sparse least-squares projection onto the stacked dummy matrix."""
    M = np.asarray(M, float)
    w = np.ones(len(M)) if w is None else np.asarray(w, float)
    blocks = []
    for f in fes:
        c, u = pd.factorize(f)
        blocks.append(sp.csr_matrix((np.ones(len(c)), (np.arange(len(c)), c)), shape=(len(c), len(u))))
    D = sp.hstack(blocks).tocsr()
    sw = np.sqrt(w)
    Dw = sp.diags(sw) @ D
    out = np.empty_like(M)
    for j in range(M.shape[1]):
        yw = M[:, j] * sw
        sol = lsqr(Dw, yw, atol=1e-14, btol=1e-14, iter_lim=100000)[0]
        out[:, j] = M[:, j] - D @ sol
    return out


def fe_ols(df, y, xs, fes, cluster="region", w=None):
    """OLS of y on xs with fixed effects fes absorbed; clustered SEs."""
    d = df.dropna(subset=[y] + xs).reset_index(drop=True)
    wt = None if w is None else d[w].to_numpy(float)
    M = demean(d[[y] + xs].to_numpy(), [d[f] for f in fes], wt)
    Y, X = M[:, 0], M[:, 1:]
    sw = np.ones(len(d)) if wt is None else wt
    Xw = X * sw[:, None]
    bread = np.linalg.inv(X.T @ Xw)
    beta = bread @ (Xw.T @ Y)
    e = Y - X @ beta
    g = pd.factorize(d[cluster])[0]
    # K counts the absorbed fixed effects too (as a dummy-variable regression would), the
    # conservative choice for the small-sample factor
    n_fe = sum(d[f].nunique() for f in fes) - (len(fes) - 1)
    G, N, K = g.max() + 1, len(d), X.shape[1] + n_fe
    S = np.zeros((G, X.shape[1]))
    np.add.at(S, g, Xw * e[:, None])
    V = bread @ (S.T @ S) @ bread * (G / (G - 1)) * ((N - 1) / (N - K))
    se = np.sqrt(np.diag(V))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), G - 1)
    crit = stats.t.ppf(0.975, G - 1)
    coefs = {x: {"b": float(b), "se": float(s), "p": float(pp), "lo": float(b - crit * s), "hi": float(b + crit * s)}
             for x, b, s, pp in zip(xs, beta, se, p)}
    r2_within = 1 - (e @ (e * sw)) / (Y @ (Y * sw))
    return {"coefs": coefs, "n": int(N), "clusters": int(G), "within_r2": float(r2_within),
            "vcov": V.tolist(), "xs": xs}


def lincomb(fit, weights):
    """Estimate and SE of a linear combination of coefficients."""
    xs = fit["xs"]
    a = np.array([weights.get(x, 0.0) for x in xs])
    b = np.array([fit["coefs"][x]["b"] for x in xs])
    V = np.array(fit["vcov"])
    est, se = float(a @ b), float(np.sqrt(a @ V @ a))
    crit = stats.t.ppf(0.975, fit["clusters"] - 1)
    p = float(2 * stats.t.sf(abs(est / se), fit["clusters"] - 1))
    return {"b": est, "se": se, "p": p, "lo": est - crit * se, "hi": est + crit * se}


def slim(fit):
    return {k: v for k, v in fit.items() if k != "vcov"}


# ---------------------------------------------------------------- data
def load():
    p = pd.read_csv(ROOT / "data/reviews_panel.csv.gz")
    s = pd.read_csv(ROOT / "data/weather_seasons.csv")
    nrm = pd.read_csv(ROOT / "data/region_normals.csv")
    nxt = s[["region", "vintage", "gst_anom", "harvest_rain_anom"]].copy()
    nxt["vintage"] -= 1
    nxt = nxt.rename(columns={"gst_anom": "gst_anom_next", "harvest_rain_anom": "harvest_rain_anom_next"})
    d = (p.merge(s, on=["region", "vintage"], how="left")
          .merge(nxt, on=["region", "vintage"], how="left")
          .merge(nrm[["region", "band", "hemisphere"]], on="region"))
    assert d.gst_anom.notna().all() and d.gst_anom_next.notna().all()
    counts = d.variety.value_counts()
    d["variety_fe"] = d.variety.where(d.variety.map(counts) >= 20, "(other)")
    d["warm"] = (d.gst_normal >= SPLIT).astype(int)
    d["cool"] = 1 - d.warm
    d["rain"] = d.harvest_rain_anom / RAIN_UNIT
    d["rain_next"] = d.harvest_rain_anom_next / RAIN_UNIT
    d["gst_normal_c"] = d.gst_normal - SPLIT
    d["gst_x_normal"] = d.gst_anom * d.gst_normal_c
    for g in ("cool", "warm"):
        d[f"gst_{g}"] = d.gst_anom * d[g]
        d[f"gst_next_{g}"] = d.gst_anom_next * d[g]
        d[f"rain_{g}"] = d.rain * d[g]
    for b in ("cool", "intermediate", "warm", "hot"):
        d[f"gst_b_{b}"] = d.gst_anom * (d.band == b)
    d["gdd_anom100"] = d.gdd_anom / 100
    for g in ("cool", "warm"):
        d[f"gdd_{g}"] = d.gdd_anom100 * d[g]
        d[f"heat_{g}"] = d.heat_days_anom * d[g]
    d["log_price"] = np.log(d.price)
    d["t"] = d.vintage - 2008
    return d


FE = ["region", "vintage", "variety_fe", "taster"]
TWO = ["gst_cool", "gst_warm", "rain"]


def main():
    d = load()
    out = {"split_c": SPLIT, "rain_unit_mm": RAIN_UNIT}
    reg = d.groupby("region").agg(band=("band", "first"), warm=("warm", "first"), n=("points", "size"))
    out["regions"] = {"total": int(len(reg)), "cool_group": int((reg.warm == 0).sum()),
                      "warm_group": int((reg.warm == 1).sum()),
                      "by_band": reg.band.value_counts().to_dict(),
                      "reviews_cool_group": int(reg.n[reg.warm == 0].sum()),
                      "reviews_warm_group": int(reg.n[reg.warm == 1].sum())}

    m = {}
    # 1. spec model: continuous interaction with the region's normal GST
    m["main_interaction"] = fe_ols(d, "points", ["gst_anom", "gst_x_normal", "rain"], FE)
    # 2. two groups split at 17 °C (headline)
    m["two_group"] = fe_ols(d, "points", TWO, FE)
    m["two_group"]["diff_warm_minus_cool"] = lincomb(m["two_group"], {"gst_warm": 1, "gst_cool": -1})
    # 3. four Jones bands
    bands = [b for b in ("cool", "intermediate", "warm", "hot") if (d.band == b).any()]
    m["four_band"] = fe_ols(d, "points", [f"gst_b_{b}" for b in bands] + ["rain"], FE)
    # 4. rain by group too
    m["rain_by_group"] = fe_ols(d, "points", ["gst_cool", "gst_warm", "rain_cool", "rain_warm"], FE)
    # 5. region-specific linear trends in place of vintage-year fixed effects
    dt = d.copy()
    for r in dt.region.unique():
        dt[f"trend_{r}"] = dt.t * (dt.region == r)
    trend_cols = [c for c in dt.columns if c.startswith("trend_")]
    f = fe_ols(dt, "points", TWO + trend_cols, ["region", "variety_fe", "taster"])
    f["coefs"] = {k: v for k, v in f["coefs"].items() if not k.startswith("trend_")}
    keep = [i for i, x in enumerate(f["xs"]) if not x.startswith("trend_")]
    f["vcov"] = np.array(f["vcov"])[np.ix_(keep, keep)].tolist(); f["xs"] = [f["xs"][i] for i in keep]
    m["region_trends"] = f
    # 6. adds log price (section 9, decision 1)
    m["with_price"] = fe_ols(d, "points", TWO + ["log_price"], FE)
    m["two_group_price_sample"] = fe_ols(d[d.price.notna()], "points", TWO, FE)
    # 7. placebo: next season's weather
    m["placebo_next_only"] = fe_ols(d, "points", ["gst_next_cool", "gst_next_warm", "rain_next"], FE)
    m["placebo_joint"] = fe_ols(d, "points", TWO + ["gst_next_cool", "gst_next_warm", "rain_next"], FE)
    # 8. heat measures
    m["gdd"] = fe_ols(d, "points", ["gdd_cool", "gdd_warm", "rain"], FE)
    m["heat_days"] = fe_ols(d, "points", TWO + ["heat_cool", "heat_warm"], FE)
    # 9. cell level: region-vintage mean scores
    cell = d.groupby(["region", "vintage"]).agg(points=("points", "mean"), n=("points", "size"),
                                                 gst_cool=("gst_cool", "first"), gst_warm=("gst_warm", "first"),
                                                 rain=("rain", "first")).reset_index()
    m["cell_weighted"] = fe_ols(cell, "points", TWO, ["region", "vintage"], w="n")
    m["cell_unweighted"] = fe_ols(cell, "points", TWO, ["region", "vintage"])
    # 10. without the unnamed-taster reviews
    m["named_tasters"] = fe_ols(d[d.taster != "(no taster named)"], "points", TWO, FE)
    # 11. northern hemisphere only
    m["north_only"] = fe_ols(d[d.hemisphere == "N"], "points", TWO, FE)

    out["models"] = {k: slim(v) for k, v in m.items()}

    # ---- leave one region out on the two-group model, to see whether one region carries it
    loo = []
    for r in sorted(d.region.unique()):
        f = fe_ols(d[d.region != r], "points", TWO, FE)
        loo.append({"dropped": r, "gst_cool": f["coefs"]["gst_cool"]["b"], "gst_warm": f["coefs"]["gst_warm"]["b"]})
    loo = pd.DataFrame(loo)
    loo.to_csv(RES / "leave_one_region_out.csv", index=False)
    out["leave_one_region_out"] = {g: {"min": float(loo[g].min()), "max": float(loo[g].max()),
                                       "min_region": loo.dropped[loo[g].idxmin()],
                                       "max_region": loo.dropped[loo[g].idxmax()]}
                                   for g in ("gst_cool", "gst_warm")}

    # ---- per-region slopes (descriptive; each from that region's own 17 or fewer vintages)
    res = demean(d[["points"]].to_numpy(), [d[f] for f in FE])[:, 0]
    d["resid_fe"] = res
    cells = d.groupby(["region", "vintage"]).agg(adj=("resid_fe", "mean"), raw=("points", "mean"),
                                                  n=("points", "size"), gst_anom=("gst_anom", "first"),
                                                  rain=("harvest_rain_anom", "first"),
                                                  gst=("gst", "first")).reset_index()
    cells.round(4).to_csv(RES / "region_vintage_cells.csv", index=False)
    slopes = []
    for r, c in cells.groupby("region"):
        b = np.polyfit(c.gst_anom, c.adj, 1, w=np.sqrt(c.n))[0] if len(c) >= 5 else np.nan
        slopes.append({"region": r, "slope": b, "vintages": len(c)})
    slopes = pd.DataFrame(slopes).merge(reg.reset_index(), on="region")
    slopes.round(4).to_csv(RES / "region_slopes.csv", index=False)
    out["region_slopes"] = {"positive": int((slopes.slope > 0).sum()), "negative": int((slopes.slope < 0).sum())}

    # ---- out of sample: leave one vintage out
    out["out_of_sample"] = oos(d)
    out["eda"] = eda(d)

    (RES / "models.json").write_text(json.dumps(out, indent=1, default=float))
    rows = []
    for name, f in out["models"].items():
        for x, c in f["coefs"].items():
            rows.append({"model": name, "term": x, **{k: round(v, 4) for k, v in c.items()}, "n": f["n"], "clusters": f["clusters"]})
    pd.DataFrame(rows).to_csv(TAB / "model_coefficients.csv", index=False)
    tg = out["models"]["two_group"]["coefs"]
    print(json.dumps({k: round(v["b"], 3) for k, v in tg.items()}), json.dumps({k: round(v["p"], 3) for k, v in tg.items()}))
    print(json.dumps(out["regions"]))


def eda(d):
    """Descriptive tables: regions, vintages, taster coverage, and the warming trend."""
    s = pd.read_csv(ROOT / "data/weather_seasons.csv")
    nrm = pd.read_csv(ROOT / "data/region_normals.csv").set_index("region")
    reg = d.groupby("region").agg(reviews=("points", "size"), vintages=("vintage", "nunique"),
                                  tasters=("taster", "nunique"), mean_points=("points", "mean"),
                                  sd_points=("points", "std"), median_price=("price", "median"))
    top = d.groupby("region").taster.agg(lambda x: x.value_counts(normalize=True).iloc[0])
    reg["top_taster_share"] = top
    reg = reg.join(nrm[["gst_normal", "band", "hemisphere", "gst_sd", "om_elevation_m"]])
    reg.round(3).sort_values("gst_normal").to_csv(TAB / "regions_summary.csv")
    vin = d.groupby("vintage").agg(reviews=("points", "size"), regions=("region", "nunique"),
                                   mean_points=("points", "mean"), median_price=("price", "median"))
    vin["mean_gst_anom"] = s.groupby("vintage").gst_anom.mean()
    vin.round(3).to_csv(TAB / "vintages_summary.csv")
    tas = d.groupby("taster").agg(reviews=("points", "size"), regions=("region", "nunique"),
                                  countries=("region", lambda x: x.str.split(" / ").str[0].nunique()))
    tas.sort_values("reviews", ascending=False).to_csv(TAB / "tasters_summary.csv")
    m = s.groupby("vintage").gst_anom.mean()
    b = np.polyfit(m.index, m.values, 1)[0]
    m2 = m.loc[2000:2016]
    b2 = np.polyfit(m2.index, m2.values, 1)[0]
    return {
        "warming_per_decade_1991_2020": float(10 * b),
        "warming_per_decade_2000_2016": float(10 * b2),
        "regions_one_taster_over_90pct": int((top > 0.9).sum()),
        "regions_one_taster_over_50pct": int((top > 0.5).sum()),
        "gst_normal_min": float(nrm.gst_normal.min()), "gst_normal_max": float(nrm.gst_normal.max()),
        "gst_normal_min_region": nrm.gst_normal.idxmin(), "gst_normal_max_region": nrm.gst_normal.idxmax(),
        "gst_anom_sd_panel": float(s[s.vintage.between(2000, 2016)].gst_anom.std()),
        "harvest_rain_anom_sd_panel": float(s[s.vintage.between(2000, 2016)].harvest_rain_anom.std()),
        "points_mean": float(d.points.mean()), "points_sd": float(d.points.std()),
        "vintage_mean_points_min": float(vin.mean_points.min()), "vintage_mean_points_max": float(vin.mean_points.max()),
        "median_price": float(d.price.median()),
    }


def oos(d):
    """Leave one vintage out. Cells are region x variety x vintage. Baseline predicts a
    held-out cell by its region-variety mean from the other vintages; the weather model
    adds the two-group temperature and rain terms, fitted with region-variety fixed
    effects on the other vintages. RMSE is weighted by reviews per cell."""
    d = d.copy()
    d["rv"] = d.region + " | " + d.variety
    xs = TWO
    err_b, err_w, wts, per = [], [], [], []
    for v in sorted(d.vintage.unique()):
        tr, te = d[d.vintage != v], d[d.vintage == v]
        f = fe_ols(tr, "points", xs, ["rv"])
        beta = np.array([f["coefs"][x]["b"] for x in xs])
        mu_rv = tr.groupby("rv").points.mean()
        xbar_rv = tr.groupby("rv")[xs].mean()
        cell = te.groupby("rv").agg(points=("points", "mean"), n=("points", "size"), **{x: (x, "first") for x in xs})
        cell = cell[cell.index.isin(mu_rv.index)]
        base = mu_rv.loc[cell.index].to_numpy()
        wx = base + (cell[xs].to_numpy() - xbar_rv.loc[cell.index].to_numpy()) @ beta
        eb, ew = cell.points.to_numpy() - base, cell.points.to_numpy() - wx
        err_b.append(eb); err_w.append(ew); wts.append(cell.n.to_numpy())
        per.append({"vintage": int(v), "cells": len(cell),
                    "rmse_baseline": float(np.sqrt(np.average(eb ** 2, weights=cell.n))),
                    "rmse_weather": float(np.sqrt(np.average(ew ** 2, weights=cell.n)))})
    eb, ew, w = map(np.concatenate, (err_b, err_w, wts))
    pd.DataFrame(per).round(4).to_csv(RES / "out_of_sample_by_vintage.csv", index=False)
    rb, rw = float(np.sqrt(np.average(eb ** 2, weights=w))), float(np.sqrt(np.average(ew ** 2, weights=w)))
    return {"cells": int(len(w)), "rmse_baseline": rb, "rmse_weather": rw,
            "improvement_pct": 100 * (rb - rw) / rb,
            "vintages_weather_better": int(sum(p["rmse_weather"] < p["rmse_baseline"] for p in per)),
            "vintages": len(per)}


if __name__ == "__main__":
    main()
