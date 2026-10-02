"""Write prediction/runs/index.json: the list of editions the site's Weekly Brief tab shows.

The Worker (worker/src/index.js, GET /brief) reads this file and each run's brief.md and PDF
straight from main on GitHub, so committing them in step 9 is all it takes to publish.
usage (from anywhere): python3 <pipeline>/site_index.py"""
import json, re
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
editions = []
for d in sorted(RUNS.iterdir(), reverse=True):   # newest first; folders are YYYY-MM-DD
    brief = d / "brief.md"
    if not (d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name) and brief.is_file()):
        continue
    week = json.loads((d / "week.json").read_text()).get("start") if (d / "week.json").is_file() else None
    title = next((l[2:].strip() for l in brief.read_text().splitlines() if l.startswith("# ")), f"Brief {d.name}")
    pdfs = sorted(p.name for p in d.glob("*.pdf"))
    editions.append({"run": d.name, "week": week, "title": title,
                     "brief": f"{d.name}/brief.md", "pdf": f"{d.name}/{pdfs[-1]}" if pdfs else None})
(RUNS / "index.json").write_text(json.dumps({"editions": editions}, indent=1) + "\n")
print(f"wrote {RUNS / 'index.json'}: {len(editions)} editions, latest {editions[0]['run'] if editions else 'none'}")
