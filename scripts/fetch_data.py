"""Download the Wine Enthusiast review dataset (about 130,000 reviews) to data/raw/.

Source: the public "winemag-data-130k-v2" Kaggle dataset, through the same GitHub
mirror Project 16 (wine-score-inflation) uses. data/raw/ is gitignored.
"""
import pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = ("https://raw.githubusercontent.com/viannaandreBR/My-Data-Science-Journey/"
       "master/18-Kaggle/_DataSets/winemag-data-130k-v2.csv")
OUT = ROOT / "data/raw/winemag-data-130k-v2.csv"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        print(f"already present: {OUT}")
        return
    print(f"downloading {URL}")
    urllib.request.urlretrieve(URL, OUT)
    print(f"saved {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
