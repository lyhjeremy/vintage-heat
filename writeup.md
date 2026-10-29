# Vintage Heat: write-up

Jeremy Lee, October 2026. Corrected 29 October 2026: duplicate rows in the source file are now dropped and the vintage parse follows the spec; see the repo's `docs/decisions.md`. The web version with figures and the region explorer is at [lyhjeremy.github.io/vintage-heat/overview/](https://lyhjeremy.github.io/vintage-heat/overview/).

## Question

Do hot growing seasons make better wine, or only better wine in cool places? Ashenfelter, Ashmore and Lalonde (1995) showed that the prices of mature red Bordeaux can be predicted from growing-season weather. Jones, White, Cooper and Storchmann (2005) found vintage ratings in most European regions rising with growing-season temperature, and modeled an optimum growing-season temperature for some regions, beyond which warmer seasons scored lower. If that holds across regions, an extra degree should help cool places and do little or harm in hot ones.

## Answer

A growing season 1 °C warmer than a region's normal moved Wine Enthusiast scores by +0.24 points in the 16 regions whose normal season is below 17 °C (95% interval 0.02 to 0.47, p = 0.035) and by +0.08 points in the 39 regions at 17 °C and above (−0.07 to 0.23, p = 0.29). The difference, −0.16 points, is not statistically clear (p = 0.16). No climate group shows a significant negative effect, though the warm band's estimate is 0.00 and 29 of the 55 regions taken one at a time slope downward. It is small: a typical season is 0.60 °C off normal, which moves a cool region's scores by about +0.15 points on a scale with a standard deviation of 3.1.

## Data

- 129,971 Wine Enthusiast reviews (`winemag-data-130k-v2`), of which 9,983 are exact duplicate rows and are dropped. 115,694 of the rest carry a vintage year in the title. Kept: vintages 2000 to 2016 in regions with at least 400 reviews and 10 vintages, after dropping 5 catch-all labels such as "California" and "Toscana": 55 regions, 55,597 reviews, 14 named tasters plus 11,842 unsigned reviews, 302 varieties.
- One point per region from Wikipedia. The terrain elevation Open-Meteo uses at each point was compared with the elevation in the point's source: 52 within 300 m, 3 with no source elevation, and one point (the Santa Barbara County centroid, at 888 m in the mountains) moved to Los Alamos.
- Daily ERA5-Land maximum and minimum temperature, and ERA5 precipitation (Open-Meteo returns no ERA5-Land rain), for the growing season of every vintage from 1991 to 2020. Growing season: April to October in the north, October to April in the south. Harvest rain: September and October, or March and April.
- Normal growing-season temperatures run from 14.6 °C (Dundee Hills) to 21.0 °C (Santa Lucia Highlands). Seasons warmed by 0.40 °C a decade on average over 1991 to 2020.

## Model

Points on the growing-season temperature anomaly (separately below and above 17 °C normal) and the harvest-rain anomaly, with fixed effects for region, vintage year, variety and taster, and standard errors clustered by region (55 clusters). The year effects absorb the common warming trend and anything else that moved all scores in a given year.

## Results

| Model | Below 17 °C | 17 °C and above |
|---|---|---|
| Main | +0.24 (p = 0.035) | +0.08 (p = 0.29) |
| Region linear trends instead of year effects | +0.09 (p = 0.28) | +0.03 (p = 0.74) |
| Main, reviews with a price only | +0.28 (p = 0.016) | +0.09 (p = 0.25) |
| Same reviews, adds log price | +0.25 (p = 0.002) | +0.14 (p = 0.041) |
| Region-vintage means, weighted by reviews | +0.30 (p < 0.001) | +0.16 (p = 0.20) |
| Region-vintage means, unweighted | +0.20 (p = 0.15) | +0.21 (p = 0.064) |
| Named tasters only | +0.26 (p = 0.032) | +0.07 (p = 0.27) |
| Northern hemisphere only | +0.26 (p = 0.033) | +0.10 (p = 0.27) |
| Placebo: next year's season | +0.13 (p = 0.28) | +0.05 (p = 0.38) |

Points per 1 °C. If price carried vintage reputation, controlling for it should shrink both estimates; on the same reviews the cool one falls and the warm one rises. Jones's four bands: cool +0.24 (3 regions, a p-value from too few clusters to trust), intermediate +0.25 (13), warm 0.00 (20), hot +0.18 (19). A continuous interaction with normal GST gives −0.02 points per degree of warmer normal (p = 0.64). Harvest rain: −0.04 points per 100 mm (p = 0.55). Degree days: +0.14 and +0.04 points per 100. Days above 35 °C: −0.023 and −0.001 per day.

Out of sample, leaving one vintage out at a time, adding the weather terms to region-variety means cuts the prediction error from 1.313 to 1.293 points (1.5%), better in 11 of 17 vintages. Dropping one region at a time moves the cool-group estimate between +0.13 and +0.28.

## Reading it

Across the eight versions in the robustness figure the cool-region estimate is positive in all of them, but its interval crosses zero under region trends, unweighted cell means and the placebo, and the placebo is about half its size. No group shows a significant negative effect. Warm seasons nudge critics' scores up a little, perhaps more in cool places. Within the seasons of 2000 to 2016 there is no significant evidence of heat lowering scores in warm regions.

## Limitations

- Tasters are not blind to vintage, so a score can carry the vintage's reputation.
- Wine Enthusiast reviews what producers submit; weak vintages may be under-submitted.
- No review dates, so the lag between vintage and tasting is unknown.
- One grid point per region; rain from a coarser grid than temperature. ERA5-Land puts Carneros and Russian River Valley in the hot band, though both are usually called cool AVAs, and the Douro point (Alijó, 609 m) sits above most Douro vineyards. The elevation check used town elevations, not vineyard elevations.
- Scores are compressed: mean 88.8, standard deviation 3.1, nothing below 80.
- Taster and region are close to confounded (22 regions have one taster writing over 90% of reviews).
- Only 3 regions are in Jones's cool band.
- The variety version (anomaly by grape climate-maturity group) was cut: Jones's grape groupings exist only as a chart.

## References

- Ashenfelter, O., Ashmore, D. and Lalonde, R. (1995). Bordeaux wine vintage quality and the weather. *Chance* 8(4), 7-14.
- Jones, G. V., White, M. A., Cooper, O. R. and Storchmann, K. (2005). Climate change and global wine quality. *Climatic Change* 73, 319-343.
- Jones, G. V. (2006). Climate and terroir: impacts of climate variability and change on wine. In *Fine Wine and Terroir: The Geoscience Perspective*, Geoscience Canada Reprint Series 9.
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349-4383.
