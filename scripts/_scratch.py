"""Studios: TMDB company logos for the remaining studios."""
import os, sys, urllib.request
sys.path.insert(0, "scripts")
from spotlight import tmdb
os.makedirs("refs/st", exist_ok=True)
log = []
for name, q in [("a24", "A24"), ("blumhouse", "Blumhouse Productions"), ("neon", "NEON"), ("ghibli", "Studio Ghibli"),
                ("searchlight", "Searchlight Pictures"), ("foxsearchlight", "Fox Searchlight Pictures")]:
    r = (tmdb("/search/company", query=q) or {}).get("results", [])
    log.append(f"{name}: " + " | ".join(f"{x['id']} {x['name']}" for x in r[:4]))
    for x in r[:2]:
        im = tmdb(f"/company/{x['id']}/images") or {}
        for i, l in enumerate(im.get("logos", [])[:5]):
            u = "https://image.tmdb.org/t/p/original" + l["file_path"]
            try:
                open(f"refs/st/{name}_{x['id']}_{i}.png", "wb").write(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "x"}), timeout=60).read())
            except Exception as e:
                log.append(f"  err {e}")
for name, cid in [("wb", 174), ("universal", 33), ("20th", 127928)]:
    pass
open("refs/st/log.txt", "w").write("\n".join(log))
