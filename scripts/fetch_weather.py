"""Download daily growing-season weather for every region in data/regions.csv.

Source: Open-Meteo historical weather API, ERA5-Land reanalysis (models=era5_land),
daily maximum and minimum 2 m temperature and precipitation. Free, no key.

One request per hemisphere per vintage, carrying every region of that hemisphere as a
multi-location query and covering only that vintage's growing season:
  north: 1 April to 31 October of the vintage year
  south: 1 October of the previous year to 30 April of the vintage year
Vintages 1991 to 2020 are fetched: the 1991-2020 normal needs all thirty, and the
analysis (2000-2016) and the placebo (2001-2017) sit inside that range.

Open-Meteo weighs a request by days/14 x variables/10 per location, so one northern
season costs about 245 of the free tier's 5,000 calls an hour. The script paces itself
to stay under 4,700 an hour, caches every response under $VH_CACHE (default
~/data-cache/vintage-heat/openmeteo) and skips anything already cached, so it can be
stopped and restarted. A 429 waits and retries with a growing delay.
Writes data/raw/weather_daily.csv.gz.
"""
import json, os, pathlib, sys, time
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = pathlib.Path(os.environ.get("VH_CACHE", pathlib.Path.home() / "data-cache/vintage-heat/openmeteo"))
URL = "https://archive-api.open-meteo.com/v1/archive"
VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]  # precipitation comes back empty for era5_land; see fetch_rain.py
YEARS = range(1991, 2021)
HOURLY_BUDGET = 4700


def season(hemi, year):
    if hemi == "N":
        return f"{year}-04-01", f"{year}-10-31"
    return f"{year - 1}-10-01", f"{year}-04-30"


def weight(n_loc, start, end):
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    return n_loc * max(1, days / 14 * len(VARS) / 10)


def fetch(regs, hemi, year, spent):
    path = CACHE / f"{hemi}_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    start, end = season(hemi, year)
    w = weight(len(regs), start, end)
    now = time.time()
    spent[:] = [(t, x) for t, x in spent if now - t < 3600]
    while sum(x for _, x in spent) + w > HOURLY_BUDGET:
        wait = 3600 - (now - spent[0][0]) + 5
        print(f"  hourly budget reached, waiting {wait/60:.1f} min", flush=True)
        time.sleep(max(wait, 5))
        now = time.time()
        spent[:] = [(t, x) for t, x in spent if now - t < 3600]
    params = {"latitude": ",".join(f"{v:.4f}" for v in regs.lat),
              "longitude": ",".join(f"{v:.4f}" for v in regs.lon),
              "start_date": start, "end_date": end, "daily": ",".join(VARS),
              "models": "era5_land", "timezone": "auto"}
    delay = 60
    while True:
        try:
            r = requests.get(URL, params=params, timeout=300)
        except requests.RequestException as e:
            print(f"  {type(e).__name__}; retrying in {delay}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 3600)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            print(f"  429: {r.text[:160]}; waiting {delay}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 3600)
            continue
        r.raise_for_status()
        break
    spent.append((time.time(), w))
    data = r.json()
    if isinstance(data, dict):
        data = [data]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    print(f"  {hemi} {year}: {len(data)} locations, weight {w:.0f}", flush=True)
    time.sleep(2)
    return data


def main():
    # every row, including the five regions excluded on 2026-10-29, so the request
    # layout matches the cached responses; build_weather.py keeps only included ones
    regions = pd.read_csv(ROOT / "data/regions.csv")
    frames = []
    # count requests already made in the last hour (from cache file times) against the budget
    spent = []
    for f in sorted(CACHE.glob("*.json"), key=lambda f: f.stat().st_mtime):
        if time.time() - f.stat().st_mtime < 3600:
            hemi, year = f.stem.split("_")
            n = int((regions.hemisphere == hemi).sum())
            spent.append((f.stat().st_mtime, weight(n, *season(hemi, int(year)))))
    for year in YEARS:
        for hemi in ("N", "S"):
            regs = regions[regions.hemisphere == hemi].reset_index(drop=True)
            data = fetch(regs, hemi, year, spent)
            assert len(data) == len(regs)
            for reg, d in zip(regs.itertuples(), data):
                df = pd.DataFrame(d["daily"]).rename(columns={
                    "temperature_2m_max": "tmax", "temperature_2m_min": "tmin",
                    "precipitation_sum": "precip"})
                df.insert(0, "region", reg.region)
                df.insert(1, "vintage", year)
                df["om_elevation_m"] = d.get("elevation")
                frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(ROOT / "data/raw/weather_daily.csv.gz", index=False, compression="gzip")
    print(f"wrote {len(out):,} rows; missing tmax {out.tmax.isna().sum()}, precip {out.precip.isna().sum()}")


if __name__ == "__main__":
    sys.exit(main())
