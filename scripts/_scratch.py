"""Studios: fetch TMDB company logos (all variants) for the pilot cards."""
import json, os, sys, urllib.request
sys.path.insert(0, "scripts")
from spotlight import tmdb
os.makedirs("refs/st", exist_ok=True)
log = []
for name, cid in [("paramount", 4), ("wda", 6125), ("pixar", 3), ("disney", 2), ("wb", 174), ("universal", 33), ("20th", 127928)]:
    im = tmdb(f"/company/{cid}/images") or {}
    for i, l in enumerate(im.get("logos", [])[:6]):
        ext = l["file_path"].rsplit(".", 1)[-1]
        for size in ("original",):
            u = "https://image.tmdb.org/t/p/original" + l["file_path"]
            try:
                open(f"refs/st/{name}_{i}.{ext}", "wb").write(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "x"}), timeout=60).read())
            except Exception as e:
                log.append(f"{name} {i} {e}")
        log.append(f"{name} {i} {l['file_path']} {l.get('width')}x{l.get('height')} {l.get('file_type')}")
open("refs/st/log.txt", "w").write("\n".join(log))
