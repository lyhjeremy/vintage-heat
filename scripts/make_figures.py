"""Static figures in figures/. Reads results/ and data/; draws in the cellar palette.

The map needs Natural Earth's 1:110m land outlines, downloaded once to data/raw/.
"""
import json, os, pathlib, textwrap, urllib.request
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
RES = ROOT / "results"
PAPER, PANEL, INK, INK2, RULE, EDGE = "#F1ECE3", "#F7F3EC", "#24191B", "#5C4C4E", "#D3C8BC", "#7E7070"
CLARET, OLIVE = "#7A2335", "#6A5A1E"
TITLE_FAMILY = None
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"


def setup_fonts():
    """Use IBM Plex Sans if a TTF copy is available (VH_TTF dir), else the default sans."""
    ttf = pathlib.Path(os.environ.get("VH_TTF", pathlib.Path.home() / "data-cache/vintage-heat/ttf"))
    global TITLE_FAMILY
    fam = "sans-serif"
    if ttf.exists():
        for f in ttf.glob("*.ttf"):
            font_manager.fontManager.addfont(str(f))
        fam = "IBM Plex Sans"
        # the subset 600 file registers as its own family name
        TITLE_FAMILY = "IBM Plex Sans SemiBold"
    plt.rcParams.update({
        "font.family": fam, "font.size": 11, "axes.edgecolor": EDGE, "axes.labelcolor": INK,
        "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "figure.facecolor": PANEL,
        "axes.facecolor": PANEL, "savefig.facecolor": PANEL, "axes.spines.top": False,
        "axes.spines.right": False, "figure.dpi": 100, "savefig.dpi": 200,
    })


def title(ax, t, sub=None):
    """Title and subtitle at the figure's left edge, subtitle wrapped to the width."""
    fig = ax.figure
    style = {"family": TITLE_FAMILY, "fontweight": 600} if TITLE_FAMILY else {"fontweight": "bold"}
    fig.text(0.012, 0.975, t, ha="left", va="top", fontsize=14, color=INK, **style)
    if sub:
        width = int(fig.get_figwidth() * 11.5)
        fig.text(0.012, 0.915, textwrap.fill(sub, width), ha="left", va="top", fontsize=10.5, color=INK2,
                 linespacing=1.35)


def finish(fig, name, top=0.8):
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(FIG / name)
    plt.close(fig)


def anomaly_trend(M):
    s = pd.read_csv(ROOT / "data/weather_seasons.csv")
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for _, g in s.groupby("region"):
        ax.plot(g.vintage, g.gst_anom, color=RULE, lw=0.8)
    m = s.groupby("vintage").gst_anom.mean()
    ax.plot(m.index, m.values, color=CLARET, lw=2.4, label=f"Mean of {s.region.nunique()} regions")
    ax.axhline(0, color=EDGE, lw=0.8)
    ax.axvspan(1999.5, 2016.5, color=OLIVE, alpha=0.08, lw=0)
    ax.text(2008, ax.get_ylim()[1] * 0.92, "vintages analyzed", ha="center", color=OLIVE, fontsize=10)
    ax.set_xlabel("Vintage")
    ax.set_ylabel("Growing-season temperature\nminus the 1991-2020 normal (°C)")
    title(ax, "Growing seasons warmed over the record",
          f"Each gray line is one region. Fitted trend of the mean: {M['eda']['warming_per_decade_1991_2020']:+.2f} °C per decade.")
    ax.legend(frameon=False, loc="upper left")
    finish(fig, "01_anomaly_trend.png", 0.84)


def dot_rows(ax, rows, colors, offsets=None):
    """rows: list of (label, [(est, lo, hi), ...]) drawn top to bottom."""
    n = len(rows)
    for i, (lab, ests) in enumerate(rows):
        y = n - 1 - i
        for j, (b, lo, hi) in enumerate(ests):
            dy = 0 if offsets is None else offsets[j]
            ax.plot([lo, hi], [y + dy, y + dy], color=colors[j], lw=2)
            ax.plot([b], [y + dy], "o", color=colors[j], ms=7)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.axvline(0, color=EDGE, lw=0.9)
    ax.set_ylim(-0.7, n - 0.3)


def band_effects(M):
    two, four = M["models"]["two_group"]["coefs"], M["models"]["four_band"]["coefs"]
    bands = M["regions"]["by_band"]
    rows = [(f"Below 17 °C normal ({M['regions']['cool_group']} regions)", [two["gst_cool"]]),
            (f"17 °C and above ({M['regions']['warm_group']} regions)", [two["gst_warm"]])]
    lab = {"cool": "Cool, below 15 °C", "intermediate": "Intermediate, 15-17 °C",
           "warm": "Warm, 17-19 °C", "hot": "Hot, 19 °C and above"}
    for b in ("cool", "intermediate", "warm", "hot"):
        k = f"gst_b_{b}"
        if k in four:
            rows.append((f"{lab[b]} ({bands[b]})", [four[k]]))
    rows = [(l, [(e["b"], e["lo"], e["hi"]) for e in es]) for l, es in rows]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    dot_rows(ax, rows, [CLARET])
    ax.axhline(len(rows) - 2.5, color=RULE, lw=0.8)
    ax.set_xlabel("Change in score, points per 1 °C warmer season than the region's normal")
    title(ax, "Effect of a warmer season by climate group",
          "Dots are estimates, lines 95% intervals clustered by region. Top: the two-group model. Below: Jones's four bands.")
    finish(fig, "02_band_effects.png", 0.8)


def placebo(M):
    a, p = M["models"]["two_group"]["coefs"], M["models"]["placebo_next_only"]["coefs"]
    rows = [("Below 17 °C", [(a["gst_cool"]["b"], a["gst_cool"]["lo"], a["gst_cool"]["hi"]),
                              (p["gst_next_cool"]["b"], p["gst_next_cool"]["lo"], p["gst_next_cool"]["hi"])]),
            ("17 °C and above", [(a["gst_warm"]["b"], a["gst_warm"]["lo"], a["gst_warm"]["hi"]),
                                  (p["gst_next_warm"]["b"], p["gst_next_warm"]["lo"], p["gst_next_warm"]["hi"])]),
            ("Harvest rain, per 100 mm", [(a["rain"]["b"], a["rain"]["lo"], a["rain"]["hi"]),
                                          (p["rain_next"]["b"], p["rain_next"]["lo"], p["rain_next"]["hi"])])]
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    dot_rows(ax, rows, [CLARET, OLIVE], offsets=[0.13, -0.13])
    ax.plot([], [], "o-", color=CLARET, label="The vintage's own season")
    ax.plot([], [], "o-", color=OLIVE, label="The following year's season (placebo)")
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9.5)
    ax.set_xlabel("Change in score, points per 1 °C (or per 100 mm of harvest rain)")
    title(ax, "Placebo: next year's weather against this year's wine",
          "Same model, same fixed effects. Lines are 95% intervals clustered by region.")
    finish(fig, "03_placebo.png", 0.8)


def world_map():
    path = ROOT / "data/raw/ne_110m_land.geojson"
    if not path.exists():
        urllib.request.urlretrieve(NE_URL, path)
    land = json.loads(path.read_text())
    n = pd.read_csv(ROOT / "data/region_normals.csv")
    fig, ax = plt.subplots(figsize=(10, 5.0))
    for f in land["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            x, y = zip(*poly[0])
            ax.fill(x, y, color=RULE, lw=0)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("cellar", [OLIVE, "#C9B46A", "#B5717E", CLARET])
    sc = ax.scatter(n.lon, n.lat, c=n.gst_normal, cmap=cmap, s=34, edgecolor=INK, linewidth=0.5, zorder=3)
    ax.set_xlim(-130, 180); ax.set_ylim(-48, 58)
    ax.set_aspect("equal"); ax.axis("off")
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, aspect=40)
    cb.set_label("Normal growing-season temperature, 1991-2020 (°C)")
    cb.outline.set_edgecolor(EDGE)
    title(ax, f"The {len(n)} regions, colored by their normal growing season",
          f"One ERA5-Land point per region. California holds {n.region.str.startswith('US / California').sum()} of them, so its dots overlap.")
    finish(fig, "04_map.png", 0.86)


def robustness(M):
    mm = M["models"]
    specs = [("Main: vintage-year fixed effects", "two_group", "gst_cool", "gst_warm"),
             ("Region linear trends instead", "region_trends", "gst_cool", "gst_warm"),
             ("Adds log price", "with_price", "gst_cool", "gst_warm"),
             ("Region-vintage means, weighted", "cell_weighted", "gst_cool", "gst_warm"),
             ("Region-vintage means, unweighted", "cell_unweighted", "gst_cool", "gst_warm"),
             ("Named tasters only", "named_tasters", "gst_cool", "gst_warm"),
             ("Northern hemisphere only", "north_only", "gst_cool", "gst_warm"),
             ("Placebo: next year's season", "placebo_next_only", "gst_next_cool", "gst_next_warm")]
    rows = [(lab, [(mm[k]["coefs"][c]["b"], mm[k]["coefs"][c]["lo"], mm[k]["coefs"][c]["hi"]),
                   (mm[k]["coefs"][w]["b"], mm[k]["coefs"][w]["lo"], mm[k]["coefs"][w]["hi"])])
            for lab, k, c, w in specs]
    (RES / "robustness_specs.json").write_text(json.dumps(
        [{"label": lab, "model": k, "cool": [b for b in r[0]], "warm": [b for b in r[1]]}
         for (lab, k, _, _), (_, r) in zip(specs, rows)], indent=1))
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    dot_rows(ax, rows, [OLIVE, CLARET], offsets=[0.14, -0.14])
    ax.plot([], [], "o-", color=OLIVE, label="Regions below 17 °C")
    ax.plot([], [], "o-", color=CLARET, label="Regions at 17 °C and above")
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9.5)
    ax.set_xlabel("Points per 1 °C warmer season than normal")
    title(ax, "The estimate under each robustness check", "95% intervals clustered by region.")
    finish(fig, "05_robustness.png", 0.86)


def main():
    FIG.mkdir(exist_ok=True)
    setup_fonts()
    M = json.loads((RES / "models.json").read_text())
    anomaly_trend(M)
    band_effects(M)
    placebo(M)
    world_map()
    robustness(M)
    print("figures written")


if __name__ == "__main__":
    main()
