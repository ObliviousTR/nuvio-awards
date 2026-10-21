import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
out = []
for q in ["Cloverfield", "Pink Panther", "Unbreakable", "Eastrail", "Glass", "Split", "AVP", "Alien vs Predator", "Before Sunrise"]:
    for r in (tmdb("/search/collection", query=q) or {}).get("results", [])[:6]:
        out.append(f"{q} | {r['id']} | {r['name']}")
open("refs/q/out.txt", "w").write("\n".join(out))
