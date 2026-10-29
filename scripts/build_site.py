"""Fill the page, write-up and README templates from site/numbers.json.

site/index.template.html     -> index.html
site/README.template.md      -> README.md
site/writeup.template.md     -> writeup.md
site/overview.fragment.html  -> the shared overview builder's fragments folder
                                (_ai-projects-tooling/overview-pages/fragments/vintage-heat.html),
                                when that folder exists; build it with that builder.
Stops if a template names a number that numbers.json does not have.
"""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLING = ROOT.parent.parent / "_ai-projects-tooling/overview-pages/fragments/vintage-heat.html"


def fill(text, n, name):
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", text)) - set(n))
    if missing:
        raise SystemExit(f"numbers missing in {name}: {missing}")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(n[m.group(1)]), text)


def main():
    n = json.loads((ROOT / "site/numbers.json").read_text())
    for src, dst in [("site/index.template.html", ROOT / "index.html"),
                     ("site/README.template.md", ROOT / "README.md"),
                     ("site/writeup.template.md", ROOT / "writeup.md")]:
        dst.write_text(fill((ROOT / src).read_text(), n, src))
        print(f"wrote {dst.relative_to(ROOT)}")
    frag = fill((ROOT / "site/overview.fragment.html").read_text(), n, "overview fragment")
    if TOOLING.parent.exists():
        TOOLING.write_text(frag)
        print(f"wrote {TOOLING}")


if __name__ == "__main__":
    main()
