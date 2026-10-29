"""Run the pipeline after the downloads: panel, weather table, models, figures, numbers, site."""
import pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
STEPS = ["build_panel.py", "build_weather.py", "analyze.py", "make_figures.py",
         "export_web.py", "export_numbers.py", "build_site.py"]

for s in STEPS:
    print(f"== {s}", flush=True)
    subprocess.run([sys.executable, str(HERE / s)], check=True)
