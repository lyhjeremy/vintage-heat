# Vintage Heat

Do hot growing seasons make better wine, or only better wine in cool places? This project joins {{nPanel}} Wine Enthusiast reviews from {{nRegions}} wine regions (vintages 2000 to 2016) to reanalysis weather for each region's growing season (ERA5-Land temperatures, ERA5 rain), and estimates how much a season warmer or wetter than the region's 1991-2020 normal moves a critic's score.

[Interactive site](https://lyhjeremy.github.io/vintage-heat/) · [Write-up](https://lyhjeremy.github.io/vintage-heat/overview/)

Design and copy follow [these standards](https://github.com/lyhjeremy/lyhjeremy/blob/main/DESIGN_STANDARDS.md).

## Results

A growing season 1 °C warmer than a region's normal moved scores by {{cool}} points in cool regions and {{warm}} points in warm ones. Both are small next to a score standard deviation of {{pointsSd}} points, the gap between them is not statistically clear, and no climate group shows a significant negative effect.

- In the {{nCool}} regions whose normal season is below {{split}} °C, a season 1 °C warmer than normal moved scores by {{cool}} points (95% interval {{coolCi}}, {{coolP}}). In the {{nWarm}} regions at {{split}} °C and above it moved them by {{warm}} points ({{warmCi}}, {{warmP}}). The difference between the two is {{diff}} points ({{diffP}}).
- By Jones's four bands: cool {{band_cool}} ({{nBand_cool}} regions, {{band_coolP}}), intermediate {{band_intermediate}} ({{nBand_intermediate}}, {{band_intermediateP}}), warm {{band_warm}} ({{nBand_warm}}, {{band_warmP}}), hot {{band_hot}} ({{nBand_hot}}, {{band_hotP}}) points per °C. The cool band's small p-value rests on {{nBand_cool}} clusters, too few for a clustered standard error to be trusted.
- Harvest rain: {{rain}} points per 100 mm more than normal ({{rainCi}}, {{rainP}}).
- Placebo: the following year's season, which cannot affect the wine, gives {{plcCool}} (below {{split}} °C, {{plcCoolP}}) and {{plcWarm}} (above, {{plcWarmP}}).
- Out of sample, leaving out one vintage at a time, the weather terms cut the error in predicting region-variety mean scores from {{rmseBase}} to {{rmseWeather}} points ({{oosImprove}}%).
- With region linear trends in place of vintage-year fixed effects, both estimates shrink and lose significance: {{trendCool}} ({{trendCoolP}}) and {{trendWarm}} ({{trendWarmP}}). On the {{nPanelPrice}} reviews with a price, adding log price moves the cool estimate from {{priceSampleCool}} to {{priceCool}} and the warm one from {{priceSampleWarm}} to {{priceWarm}}. If price carried vintage reputation, both should shrink; the cool one {{priceCoolDir}} slightly and the warm one {{priceWarmDir}}.
- Weather explains {{withinR2Pct}}% of the score variation left after the region, year, variety and taster fixed effects.

![Effect of a season 1 °C warmer than normal, by climate group, with 95% intervals](figures/02_band_effects.png)

## Data

| Source | What | Span |
|---|---|---|
| Wine Enthusiast reviews (`winemag-data-130k-v2`, Kaggle, via a public GitHub mirror) | {{nReviewsAll}} reviews; {{nPanel}} in the {{nRegions}} regions, vintages 2000 to 2016 | vintages to 2017 |
| Open-Meteo historical weather API, ERA5-Land | daily maximum and minimum temperature at one point per region, growing season only | 1991 to 2020 |
| Open-Meteo historical weather API, ERA5 | daily precipitation in the two harvest months (Open-Meteo returns no ERA5-Land rain) | 1991 to 2020 |
| Wikipedia and Wikidata | coordinates and elevation for each region's point | as of October 2026 |
| Natural Earth | 1:110m land outlines for the map | |

The source file has {{nDupes}} exact duplicate rows, which are dropped. Vintage is the first four-digit number from 1950 to 2017 in the wine's title. A region is `country / province / region_1` (or `country / province` where `region_1` is empty) with at least 400 reviews and 10 vintages from 2000 to 2016; {{nCatchAll}} catch-all labels such as "California" and "Toscana" are dropped. The region list was frozen in `data/regions.csv` before any weather was fetched. Every data decision is in [`docs/decisions.md`](docs/decisions.md).

## Method

Growing season: April to October in the north, October to April in the south. Per season and region: mean temperature (GST), growing degree days above 10 °C, days above 35 °C, and harvest rain (September and October, or March and April). Each is expressed as an anomaly against the region's 1991-2020 mean.

The main model is a review-level regression of points on the GST anomaly (separately for regions below and above {{split}} °C normal GST) and the harvest-rain anomaly, with fixed effects for region, vintage year, variety and taster, and standard errors clustered by region. Vintage-year effects absorb anything common to a year across all regions, including the warming trend and the market mood, so the weather effect comes from regions having different years from each other. Robustness runs: a continuous interaction with normal GST, Jones's four bands, region linear trends in place of year effects, log price added, region-vintage means (weighted and unweighted), named tasters only, northern hemisphere only, degree days and heat days, a leave-one-region-out sweep, a placebo with next year's weather, and a leave-one-vintage-out prediction test.

Stack: Python (pandas, NumPy, SciPy, matplotlib; statsmodels for the estimator test), and plain HTML, CSS and JavaScript with no libraries for the site. Hosted on GitHub Pages.

## How to run

```bash
pip install -r requirements.txt
python scripts/fetch_data.py       # reviews into data/raw/ (gitignored)
python scripts/fetch_weather.py    # Open-Meteo temperatures, about 8,300 weighted calls; paces itself under the hourly limit
python scripts/fetch_rain.py       # Open-Meteo ERA5 harvest rain, about 1,800 weighted calls
python scripts/run_all.py          # panel, weather table, models, figures, numbers, site
python -m pytest tests/            # (pytest is in requirements.txt) checks the fixed-effects estimator against statsmodels
```

`run_all.py` runs `build_panel.py`, `build_weather.py`, `analyze.py`, `make_figures.py`, `export_web.py`, `export_numbers.py` and `build_site.py`. No number on the site or in this README is typed by hand: `export_numbers.py` writes `site/numbers.json` and `build_site.py` fills the templates in `site/`. `scripts/lookup_regions.py` is the one-off helper that drafted the coordinates.

## Repo layout

| Path | Contents |
|---|---|
| `scripts/` | fetchers, panel and weather builders, models, figures, site builders |
| `data/` | `regions.csv` (frozen region list with coordinates and sources), `reviews_panel.csv.gz`, `weather_seasons.csv`, `region_normals.csv`; `data/raw/` is gitignored |
| `results/` | `models.json` (every model), `numbers.json`, region-vintage cells, per-region slopes, out-of-sample detail |
| `tables/` | coefficient table, region, vintage and taster summaries, elevation check, inclusion list |
| `figures/` | the five static figures |
| `index.html`, `assets/` | the interactive site |
| `overview/` | the write-up, built from `site/overview.fragment.html` by the shared overview builder |
| `docs/decisions.md` | data and modeling decisions |

## Limitations

- Tasters are not blind to vintage. A score can carry the vintage's reputation, so this measures what critics scored, not what a blind panel would.
- Wine Enthusiast reviews what producers submit. A weak vintage may be under-submitted, which would shrink measured differences.
- There is no review date, so the lag between vintage and tasting is unknown and differs by style.
- One reanalysis grid point stands in for each region's many vineyards and slopes.
- Scores sit in a narrow band (mean {{pointsMean}}, standard deviation {{pointsSd}}).
- Band assignment depends on one grid point per region: ERA5-Land puts Carneros ({{carnerosGst}} °C) and Russian River Valley ({{rrvGst}} °C) in the {{carnerosBand}} band, though both are usually called cool AVAs, and the Douro point (Alijó, {{douroPointElev}} m) sits above most Douro vineyards. The elevation check compared each point with its town's elevation, not vineyard elevation.
- Taster and region are close to confounded: in {{oneTaster90}} of the {{nRegions}} regions one taster wrote more than 90% of the reviews.

## Sources

- Ashenfelter, O., Ashmore, D. and Lalonde, R. (1995). Bordeaux wine vintage quality and the weather. *Chance* 8(4), 7-14.
- Jones, G. V., White, M. A., Cooper, O. R. and Storchmann, K. (2005). Climate change and global wine quality. *Climatic Change* 73, 319-343.
- Jones, G. V. (2006). Climate and terroir: impacts of climate variability and change on wine. In R. W. Macqueen and L. D. Meinert (eds), *Fine Wine and Terroir: The Geoscience Perspective*, Geoscience Canada Reprint Series 9. Geological Association of Canada.
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349-4383. Accessed through the [Open-Meteo](https://open-meteo.com/) historical weather API (CC BY 4.0).

## License

Code under the MIT License. Review data belongs to Wine Enthusiast (collected in the public Kaggle dataset); weather data is ERA5-Land (temperature) and ERA5 (precipitation) from the Copernicus Climate Change Service, served by Open-Meteo under CC BY 4.0.
