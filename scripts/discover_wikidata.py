"""One-off: find the Wikidata item for each catalog and show its latest winners -> data/discovery.md"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikidata import search, winners

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, "data", "wikidata.json")))
lines = ["# Wikidata discovery", ""]
for cid, c in cfg.items():
    if cid.startswith("_"):
        continue
    lines.append(f"## {cid}  (search: {c['search']})")
    try:
        for qid, label, desc in search(c["search"]):
            w = sorted([x for x in winners(qid) if x["year"]], key=lambda x: -x["year"])
            latest = "; ".join(f"{x['year']} {x['title']} {x['imdb']}" for x in w[:4])
            lines.append(f"- {qid} | {label} | {desc} | {len(w)} dated winners | {latest}")
    except Exception as e:
        lines.append(f"- ERROR {e!r}")
    lines.append("")
open(os.path.join(ROOT, "data", "discovery.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
