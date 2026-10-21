import os, sys, json
sys.path.insert(0, "scripts")
import universe_motion as um
OUT = "refs/probe5"; os.makedirs(OUT, exist_ok=True)
log = open(f"{OUT}/log.txt", "w")
for nid in list(range(90, 100)) + [160, 173, 614, 1063, 2541, 98, 3, 57, 1068, 1112]:
    try:
        n = um.tmdb(f"/network/{nid}")
        if n: log.write(f"network {nid} {n.get('name')} {n.get('origin_country')}\n")
    except Exception as e:
        log.write(f"network {nid} err {e}\n")
for q in ("Emmy Awards", "Primetime Emmy Awards"):
    r = um.tmdb("/search/tv", query=q) or {}
    for x in r.get("results", [])[:5]:
        log.write(f"tv {x['id']} {x['name']} {x.get('backdrop_path')}\n")
        im = um.tmdb(f"/tv/{x['id']}/images", include_image_language="en,null") or {}
        log.write("   logos " + " ".join(l["file_path"] for l in im.get("logos", [])[:6]) + "\n")
        log.write("   backdrops " + " ".join(f"{b['file_path']}:{b.get('iso_639_1')}" for b in im.get("backdrops", [])[:8]) + "\n")
log.close()
