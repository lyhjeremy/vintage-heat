# Data and modeling decisions

Choices the spec left open, recorded when they were made.

## Reviews

- The vintage parse is Project 16's: the first year in the title matching `19xx`, `200x` or `201x`. 125,322 reviews carry a vintage from 1950 to 2017 (the spec's draft said 125,336; the difference comes from that parse and range, and the code's number is the one used).
- Seven labels pass the count rule but span more than one climate, so they are dropped as regions: the state-wide labels California, Oregon, Washington and Virginia, the Central Coast super-AVA, Toscana IGT and Sicilia. The list is `CATCH_ALL` in `scripts/build_panel.py`; `tables/region_inclusion.csv` shows every label that passed the counts.
- Columbia Valley (WA) and Mendoza are large but kept. Both are one dry continental climate, with the vineyards concentrated near the chosen point.
- The three generic Bordeaux labels (Bordeaux, Bordeaux Blanc, Bordeaux Supérieur) are merged into one region, `France / Bordeaux / Bordeaux (generic)`. They cover the same area and would have taken the same grid point, so keeping them apart would have counted one weather series three times.
- Result: 60 regions, frozen in `data/regions.csv` before any weather was fetched. `build_panel.py` stops if the rule and the frozen list ever disagree.
- Varieties with fewer than 20 reviews in the panel share one "(other)" fixed effect. Reviews with no taster named keep their own taster category; a robustness run drops them.

## Coordinates and elevation

- Each point comes from the Wikipedia API (`scripts/lookup_regions.py`): the AVA's page where it carries coordinates, otherwise the main wine town of the appellation. The page is in the `coord_source` column.
- The source elevation is the Wikidata elevation of that page's item, or a vineyard elevation range quoted in the article. `elev_source_note` says which.
- Open-Meteo returns the elevation of its 90 m terrain model at the point and downscales the ERA5-Land temperatures to it, so that is the elevation compared. 57 of 60 points were checked; Blenheim (Marlborough), Santarém (Tejo) and Torres Vedras (Lisboa) have no elevation in their sources and are recorded as unchecked in `tables/elevation_check.csv`.
- One point was moved. Santa Barbara County's Wikipedia coordinates are the county centroid, which sits at 888 m in the San Rafael Mountains. It was moved to Los Alamos (174 m), between the Santa Maria and Santa Ynez valleys.

## Weather

- Temperatures are ERA5-Land through Open-Meteo (`models=era5_land`), daily Tmax and Tmin. The daily mean is (Tmax + Tmin) / 2, the convention behind Winkler degree days.
- Open-Meteo returns the precipitation field empty for `era5_land` (checked 2026-10-28: every value null), so harvest rain comes from ERA5 itself (`models=era5`, 0.25 degree grid), fetched for the two harvest months only by `scripts/fetch_rain.py`. ERA5 is the reanalysis that drives ERA5-Land, so the two sources agree in time; the rain grid cell is coarser.
- Only growing-season days are fetched, one request per hemisphere per vintage, because Open-Meteo weighs requests by days times variables and a full 30-year daily series for 60 points would have taken more than the free tier's daily allowance.
- Normals are the 1991 to 2020 means of each variable for each region.

## Models

- Headline split at 17 °C normal GST: the boundary between Jones's intermediate and warm groups. "Cool" in the headline means Jones's cool and intermediate groups (below 17 °C); "warm" means warm and hot. The four-band version is reported beside it.
- Harvest rain coefficients are per 100 mm.
- The variety version (anomaly by each variety's climate-maturity group) is cut, the spec's first cut line. Jones's variety groupings exist only as a figure (Jones 2006, Figure 2), and assigning 300 varieties to groups by reading a chart would have meant inventing most of the mapping.
