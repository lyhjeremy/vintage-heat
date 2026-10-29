"""Turn daily weather into one row per region and vintage, plus the 1991-2020 normals.

Temperatures are ERA5-Land (fetch_weather.py); harvest rain is ERA5 (fetch_rain.py),
because Open-Meteo serves no ERA5-Land precipitation.
Per growing season (see fetch_weather.py for the dates):
  gst          mean of the daily mean temperature, (Tmax + Tmin) / 2, in °C (Jones)
  gdd          growing degree days above 10 °C, sum of max(0, Tmean - 10) (Winkler)
  heat_days    days with Tmax above 35 °C
  harvest_rain total precipitation, September and October (north) or March and April (south), mm
Each variable also gets an anomaly: the season's value minus the region's 1991-2020 mean.

Also runs the elevation spot check: the elevation Open-Meteo used for the point (its
90 m terrain model, to which it downscales the ERA5-Land temperatures) must sit within
300 m of the elevation the coordinate source gives. Writes data/weather_seasons.csv,
data/region_normals.csv and tables/elevation_check.csv.
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
VARS = ["gst", "gdd", "heat_days", "harvest_rain"]
BANDS = [(-np.inf, 15, "cool"), (15, 17, "intermediate"), (17, 19, "warm"), (19, np.inf, "hot")]


def band(t):
    for lo, hi, name in BANDS:
        if lo <= t < hi:
            return name


def main():
    regions = pd.read_csv(ROOT / "data/regions.csv")
    regions = regions[regions.included].reset_index(drop=True)
    d = pd.read_csv(ROOT / "data/raw/weather_daily.csv.gz", parse_dates=["time"]).drop(columns="precip", errors="ignore")
    if d[["tmax", "tmin"]].isna().any().any():
        raise SystemExit("missing daily temperatures")
    # the fetch covered all 60 rows of regions.csv; keep only the included regions
    d = d[d.region.isin(regions.region)]
    rain = pd.read_csv(ROOT / "data/raw/rain_daily.csv.gz")
    rain = rain[rain.region.isin(regions.region)]
    if rain.precip.isna().any():
        raise SystemExit("missing daily rain")
    d = d.merge(regions[["region", "hemisphere"]], on="region")
    d["tmean"] = (d.tmax + d.tmin) / 2

    s = d.groupby(["region", "vintage"]).agg(
        days=("tmean", "size"),
        gst=("tmean", "mean"),
        gdd=("tmean", lambda x: np.clip(x - 10, 0, None).sum()),
        heat_days=("tmax", lambda x: int((x > 35).sum())),
    )
    s["harvest_rain"] = rain.groupby(["region", "vintage"]).precip.sum()
    assert (rain.groupby(["region", "vintage"]).size() == 61).all()
    s = s.reset_index()
    assert s.days.isin([214, 213, 212]).all(), s.days.value_counts()
    assert len(s) == len(regions) * 30

    normals = s.groupby("region")[VARS].mean().add_suffix("_normal")
    normals["gst_sd"] = s.groupby("region").gst.std()
    normals["band"] = normals.gst_normal.map(band)
    s = s.merge(normals, on="region")
    for v in VARS:
        s[f"{v}_anom"] = s[v] - s[f"{v}_normal"]
    s = s.drop(columns=[c for c in s.columns if c.endswith("_normal") and c != "gst_normal"] + ["gst_sd", "band"])
    s.round(4).to_csv(ROOT / "data/weather_seasons.csv", index=False)

    elev = d.groupby("region").om_elevation_m.first()
    normals = normals.join(elev).join(regions.set_index("region")[["hemisphere", "lat", "lon"]])
    normals.round(3).to_csv(ROOT / "data/region_normals.csv")

    e = regions.set_index("region")[["source_elev_min_m", "source_elev_max_m", "elev_source", "elev_source_note", "moved"]].join(elev)
    lo, hi = e.source_elev_min_m, e.source_elev_max_m
    e["distance_m"] = np.where(e.om_elevation_m < lo, lo - e.om_elevation_m,
                               np.where(e.om_elevation_m > hi, e.om_elevation_m - hi, 0))
    e.loc[lo.isna(), "distance_m"] = np.nan
    e["check"] = np.where(lo.isna(), "no elevation in source", np.where(e.distance_m <= 300, "pass", "FAIL"))
    e.to_csv(ROOT / "tables/elevation_check.csv")
    print(e.check.value_counts().to_string())
    if (e.check == "FAIL").any():
        raise SystemExit(e[e.check == "FAIL"])
    print(normals.band.value_counts().to_string())


if __name__ == "__main__":
    main()
