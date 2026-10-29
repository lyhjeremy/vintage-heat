# Vintage Heat: write-up

Jeremy Lee, October 2026. Corrected 29 October 2026: duplicate rows in the source file are now dropped and the vintage parse follows the spec; see the repo's `docs/decisions.md`. The web version with figures and the region explorer is at [lyhjeremy.github.io/vintage-heat/overview/](https://lyhjeremy.github.io/vintage-heat/overview/).

## Question

Do hot growing seasons make better wine, or only better wine in cool places? Ashenfelter, Ashmore and Lalonde (1995) showed that the prices of mature red Bordeaux can be predicted from growing-season weather. Jones, White, Cooper and Storchmann (2005) found vintage ratings in most European regions rising with growing-season temperature, and modeled an optimum growing-season temperature for some regions, beyond which warmer seasons scored lower. If that holds across regions, an extra degree should help cool places and do little or harm in hot ones.

## Answer

A growing season 1 °C warmer than a region's normal moved Wine Enthusiast scores by {{cool}} points in the {{nCool}} regions whose normal season is below {{split}} °C (95% interval {{coolCi}}, {{coolP}}) and by {{warm}} points in the {{nWarm}} regions at {{split}} °C and above ({{warmCi}}, {{warmP}}). The difference, {{diff}} points, is not statistically clear ({{diffP}}). No climate group shows a significant negative effect, though the warm band's estimate is {{band_warm}} and {{slopesNeg}} of the {{nRegions}} regions taken one at a time slope downward. It is small: a typical season is {{anomSd}} °C off normal, which moves a cool region's scores by about {{coolPerSd}} points on a scale with a standard deviation of {{pointsSd}}.

## Data

- {{nReviewsAll}} Wine Enthusiast reviews (`winemag-data-130k-v2`), of which {{nDupes}} are exact duplicate rows and are dropped. {{nVintage}} of the rest carry a vintage year in the title. Kept: vintages 2000 to 2016 in regions with at least 400 reviews and 10 vintages, after dropping {{nCatchAll}} catch-all labels such as "California" and "Toscana": {{nRegions}} regions, {{nPanel}} reviews, {{nTasters}} named tasters plus {{nNoTaster}} unsigned reviews, {{nVarieties}} varieties.
- One point per region from Wikipedia. The terrain elevation Open-Meteo uses at each point was compared with the elevation in the point's source: {{elevPass}} within 300 m, {{elevUnchecked}} with no source elevation, and one point (the Santa Barbara County centroid, at 888 m in the mountains) moved to Los Alamos.
- Daily ERA5-Land maximum and minimum temperature, and ERA5 precipitation (Open-Meteo returns no ERA5-Land rain), for the growing season of every vintage from 1991 to 2020. Growing season: April to October in the north, October to April in the south. Harvest rain: September and October, or March and April.
- Normal growing-season temperatures run from {{gstMin}} °C ({{gstMinRegion}}) to {{gstMax}} °C ({{gstMaxRegion}}). Seasons warmed by {{warmingDecade}} °C a decade on average over 1991 to 2020.

## Model

Points on the growing-season temperature anomaly (separately below and above {{split}} °C normal) and the harvest-rain anomaly, with fixed effects for region, vintage year, variety and taster, and standard errors clustered by region ({{nRegions}} clusters). The year effects absorb the common warming trend and anything else that moved all scores in a given year.

## Results

| Model | Below {{split}} °C | {{split}} °C and above |
|---|---|---|
| Main | {{cool}} ({{coolP}}) | {{warm}} ({{warmP}}) |
| Region linear trends instead of year effects | {{trendCool}} ({{trendCoolP}}) | {{trendWarm}} ({{trendWarmP}}) |
| Main, reviews with a price only | {{priceSampleCool}} ({{priceSampleCoolP}}) | {{priceSampleWarm}} ({{priceSampleWarmP}}) |
| Same reviews, adds log price | {{priceCool}} ({{priceCoolP}}) | {{priceWarm}} ({{priceWarmP}}) |
| Region-vintage means, weighted by reviews | {{cellWCool}} ({{cellWCoolP}}) | {{cellWWarm}} ({{cellWWarmP}}) |
| Region-vintage means, unweighted | {{cellUCool}} ({{cellUCoolP}}) | {{cellUWarm}} ({{cellUWarmP}}) |
| Named tasters only | {{namedCool}} ({{namedCoolP}}) | {{namedWarm}} ({{namedWarmP}}) |
| Northern hemisphere only | {{northCool}} ({{northCoolP}}) | {{northWarm}} ({{northWarmP}}) |
| Placebo: next year's season | {{plcCool}} ({{plcCoolP}}) | {{plcWarm}} ({{plcWarmP}}) |

Points per 1 °C. If price carried vintage reputation, controlling for it should shrink both estimates; on the same reviews the cool one {{priceCoolDir}} and the warm one {{priceWarmDir}}. Jones's four bands: cool {{band_cool}} ({{nBand_cool}} regions, a p-value from too few clusters to trust), intermediate {{band_intermediate}} ({{nBand_intermediate}}), warm {{band_warm}} ({{nBand_warm}}), hot {{band_hot}} ({{nBand_hot}}). A continuous interaction with normal GST gives {{intSlope}} points per degree of warmer normal ({{intSlopeP}}). Harvest rain: {{rain}} points per 100 mm ({{rainP}}). Degree days: {{gddCool}} and {{gddWarm}} points per 100. Days above 35 °C: {{heatCool}} and {{heatWarm}} per day.

Out of sample, leaving one vintage out at a time, adding the weather terms to region-variety means cuts the prediction error from {{rmseBase}} to {{rmseWeather}} points ({{oosImprove}}%), better in {{oosBetter}} of {{oosVintages}} vintages. Dropping one region at a time moves the cool-group estimate between {{looCoolMin}} and {{looCoolMax}}.

## Reading it

Across the {{nSpecsWord}} versions in the robustness figure the cool-region estimate is {{coolAllPositive}}, but its interval crosses zero under {{coolCrossList}}, and the placebo is about half its size. No group shows a significant negative effect. Warm seasons nudge critics' scores up a little, perhaps more in cool places. Within the seasons of 2000 to 2016 there is no significant evidence of heat lowering scores in warm regions.

## Limitations

- Tasters are not blind to vintage, so a score can carry the vintage's reputation.
- Wine Enthusiast reviews what producers submit; weak vintages may be under-submitted.
- No review dates, so the lag between vintage and tasting is unknown.
- One grid point per region; rain from a coarser grid than temperature. ERA5-Land puts Carneros and Russian River Valley in the {{carnerosBand}} band, though both are usually called cool AVAs, and the Douro point (Alijó, {{douroPointElev}} m) sits above most Douro vineyards. The elevation check used town elevations, not vineyard elevations.
- Scores are compressed: mean {{pointsMean}}, standard deviation {{pointsSd}}, nothing below 80.
- Taster and region are close to confounded ({{oneTaster90}} regions have one taster writing over 90% of reviews).
- Only {{nBand_cool}} regions are in Jones's cool band.
- The variety version (anomaly by grape climate-maturity group) was cut: Jones's grape groupings exist only as a chart.

## References

- Ashenfelter, O., Ashmore, D. and Lalonde, R. (1995). Bordeaux wine vintage quality and the weather. *Chance* 8(4), 7-14.
- Jones, G. V., White, M. A., Cooper, O. R. and Storchmann, K. (2005). Climate change and global wine quality. *Climatic Change* 73, 319-343.
- Jones, G. V. (2006). Climate and terroir: impacts of climate variability and change on wine. In *Fine Wine and Terroir: The Geoscience Perspective*, Geoscience Canada Reprint Series 9.
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349-4383.
