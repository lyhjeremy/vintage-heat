"""One-off helper that drafted data/regions.csv.

For every region that passes the inclusion rule it asks the Wikipedia API for the
coordinates of the page named in PAGES (the appellation's page where it carries
coordinates, otherwise the main wine town's page) and pulls any sentence in that page
that states a vineyard elevation. The output, data/regions_lookup.csv, was then checked
by hand and frozen as data/regions.csv. Rerunning it does not touch regions.csv.
"""
import json, pathlib, re, time
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "vintage-heat/0.1 (https://github.com/lyhjeremy/vintage-heat; lyhjeremy@gmail.com)"}

# region label -> Wikipedia page titles to try in order
PAGES = {
    "US / California / Napa Valley": ["Napa Valley AVA", "Napa, California"],
    "US / Washington / Columbia Valley (WA)": ["Columbia Valley AVA"],
    "US / California / Russian River Valley": ["Russian River Valley AVA"],
    "US / California / Paso Robles": ["Paso Robles AVA", "Paso Robles, California"],
    "Argentina / Mendoza Province / Mendoza": ["Luján de Cuyo"],
    "US / Oregon / Willamette Valley": ["Willamette Valley AVA"],
    "France / Alsace / Alsace": ["Colmar"],
    "Italy / Piedmont / Barolo": ["Barolo, Piedmont"],
    "US / New York / Finger Lakes": ["Finger Lakes AVA"],
    "US / California / Sonoma Coast": ["Sonoma Coast AVA"],
    "Spain / Northern Spain / Rioja": ["Haro, La Rioja", "Logroño"],
    "Italy / Tuscany / Brunello di Montalcino": ["Montalcino"],
    "Portugal / Douro": ["Pinhão", "Alijó"],
    "US / California / Sonoma County": ["Healdsburg, California"],
    "US / Washington / Walla Walla Valley (WA)": ["Walla Walla Valley AVA"],
    "Germany / Mosel": ["Bernkastel-Kues"],
    "Italy / Tuscany / Chianti Classico": ["Greve in Chianti"],
    "US / California / Santa Barbara County": ["Santa Barbara County, California"],
    "US / California / Sta. Rita Hills": ["Sta. Rita Hills AVA", "Lompoc, California"],
    "US / Washington / Yakima Valley": ["Yakima Valley AVA"],
    "US / California / Carneros": ["Los Carneros AVA"],
    "Portugal / Alentejano": ["Évora"],
    "US / California / Dry Creek Valley": ["Dry Creek Valley AVA"],
    "France / Provence / Côtes de Provence": ["Brignoles"],
    "Chile / Colchagua Valley": ["Santa Cruz, Chile"],
    "US / California / Santa Ynez Valley": ["Santa Ynez Valley AVA", "Santa Ynez, California"],
    "US / California / Santa Lucia Highlands": ["Santa Lucia Highlands AVA", "Gonzales, California"],
    "New Zealand / Marlborough": ["Blenheim, New Zealand"],
    "Italy / Piedmont / Barbaresco": ["Barbaresco, Piedmont"],
    "US / California / Lodi": ["Lodi AVA", "Lodi, California"],
    "US / California / Alexander Valley": ["Alexander Valley AVA"],
    "Spain / Northern Spain / Ribera del Duero": ["Aranda de Duero"],
    "US / Washington / Red Mountain": ["Red Mountain AVA"],
    "US / California / Santa Maria Valley": ["Santa Maria Valley AVA", "Santa Maria, California"],
    "Italy / Northeastern Italy / Alto Adige": ["Bolzano"],
    "Portugal / Tejo": ["Santarém, Portugal"],
    "Austria / Burgenland": ["Neusiedl am See"],
    "US / California / Anderson Valley": ["Anderson Valley AVA", "Philo, California"],
    "US / California / Sonoma Valley": ["Sonoma Valley AVA", "Sonoma, California"],
    "Chile / Maipo Valley": ["Maipo Valley", "Buin, Chile"],
    "Austria / Niederösterreich": ["Krems an der Donau"],
    "Chile / Casablanca Valley": ["Casablanca, Chile"],
    "France / Bordeaux / Saint-Émilion": ["Saint-Émilion"],
    "US / Washington / Horse Heaven Hills": ["Horse Heaven Hills AVA", "Paterson, Washington"],
    "France / Burgundy / Chablis": ["Chablis"],
    "US / New York / North Fork of Long Island": ["North Fork of Long Island AVA", "Cutchogue, New York"],
    "US / Oregon / Dundee Hills": ["Dundee Hills AVA", "Dundee, Oregon"],
    "France / Loire Valley / Sancerre": ["Sancerre"],
    "US / California / Santa Cruz Mountains": ["Santa Cruz Mountains AVA"],
    "France / Bordeaux / Bordeaux (generic)": ["Bordeaux"],
    "Portugal / Lisboa": ["Torres Vedras"],
    "France / Southwest France / Cahors": ["Cahors"],
    "Chile / Maule Valley": ["Talca"],
    "France / Champagne / Champagne": ["Épernay"],
    "US / California / Livermore Valley": ["Livermore Valley AVA", "Livermore, California"],
    "South Africa / Stellenbosch": ["Stellenbosch"],
    "Italy / Veneto / Amarone della Valpolicella Classico": ["Negrar di Valpolicella", "Negrar"],
    "Austria / Kamptal": ["Langenlois"],
    "US / California / Edna Valley": ["Edna Valley AVA"],
    "US / California / Rutherford": ["Rutherford AVA", "Rutherford, California"],
}

ELEV = re.compile(r"[^.]*\b(?:elevation|altitude|metres|meters|feet|ft|above sea level)\b[^.]*\.", re.I)


def query(title):
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=30, params={
        "action": "query", "format": "json", "redirects": 1, "titles": title,
        "prop": "coordinates|extracts|info", "inprop": "url", "explaintext": 1, "coprimary": "all"})
    r.raise_for_status()
    page = next(iter(r.json()["query"]["pages"].values()))
    return page


def main():
    rows = []
    for region, titles in PAGES.items():
        hit = None
        for t in titles:
            p = query(t)
            time.sleep(0.5)
            if "coordinates" in p:
                hit = p
                break
        if hit is None:
            rows.append({"region": region, "wiki_title": "", "lat": "", "lon": "", "url": "", "elev_text": ""})
            print("NO COORDS", region)
            continue
        c = hit["coordinates"][0]
        sents = [s.strip() for s in ELEV.findall(hit.get("extract", "")) if re.search(r"\d", s)]
        sents = [s for s in sents if re.search(r"(m|metres|meters|feet|ft)\b", s)][:4]
        rows.append({"region": region, "wiki_title": hit["title"], "lat": round(c["lat"], 4),
                     "lon": round(c["lon"], 4), "url": hit.get("fullurl", ""),
                     "elev_text": " | ".join(sents)[:900]})
        print(f"{region:55s} {hit['title']:35s} {c['lat']:.3f} {c['lon']:.3f}")
    import csv
    with open(ROOT / "data/regions_lookup.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
