"""Download harvest-month precipitation for every region in data/regions.csv.

Open-Meteo returns no precipitation for its ERA5-Land model (the field comes back
empty), so rain comes from ERA5 (models=era5, 0.25 degree grid), the reanalysis
ERA5-Land is driven by. Only the two harvest months are fetched:
  north: 1 September to 31 October of the vintage year
  south: 1 March to 30 April of the vintage year
Vintages 1991 to 2020, one multi-location request per hemisphere per vintage. Cached
under $VH_CACHE like fetch_weather.py. Writes data/raw/rain_daily.csv.gz.
"""
import json, os, pathlib, time
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = pathlib.Path(os.environ.get("VH_CACHE", pathlib.Path.home() / "data-cache/vintage-heat/openmeteo"))
URL = "https://archive-api.open-meteo.com/v1/archive"
YEARS = range(1991, 2021)


def window(hemi, year):
    return (f"{year}-09-01", f"{year}-10-31") if hemi == "N" else (f"{year}-03-01", f"{year}-04-30")


def fetch(regs, hemi, year):
    path = CACHE / f"rain_{hemi}_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    start, end = window(hemi, year)
    params = {"latitude": ",".join(f"{v:.4f}" for v in regs.lat),
              "longitude": ",".join(f"{v:.4f}" for v in regs.lon),
              "start_date": start, "end_date": end, "daily": "precipitation_sum",
              "models": "era5", "timezone": "auto"}
    delay = 60
    while True:
        try:
            r = requests.get(URL, params=params, timeout=300)
        except requests.RequestException as e:
            print(f"  {type(e).__name__}; retrying in {delay}s", flush=True)
            time.sleep(delay); delay = min(delay * 2, 3600); continue
        if r.status_code == 429 or r.status_code >= 500:
            print(f"  {r.status_code}: {r.text[:160]}; waiting {delay}s", flush=True)
            time.sleep(delay); delay = min(delay * 2, 3600); continue
        r.raise_for_status()
        break
    data = r.json()
    data = data if isinstance(data, list) else [data]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    print(f"  rain {hemi} {year}: {len(data)} locations", flush=True)
    time.sleep(8)  # about 60 weighted calls per request; stays well under 600 a minute
    return data


def main():
    regions = pd.read_csv(ROOT / "data/regions.csv")
    frames = []
    for year in YEARS:
        for hemi in ("N", "S"):
            regs = regions[regions.hemisphere == hemi].reset_index(drop=True)
            data = fetch(regs, hemi, year)
            assert len(data) == len(regs)
            for reg, d in zip(regs.itertuples(), data):
                df = pd.DataFrame(d["daily"]).rename(columns={"precipitation_sum": "precip"})
                df.insert(0, "region", reg.region)
                df.insert(1, "vintage", year)
                frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(ROOT / "data/raw/rain_daily.csv.gz", index=False, compression="gzip")
    print(f"wrote {len(out):,} rows; missing precip {out.precip.isna().sum()}")


if __name__ == "__main__":
    main()
