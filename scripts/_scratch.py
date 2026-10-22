"""Fetch raw material for the Streaming row work into refs/st (logos, posters) for local design."""
import os, sys, io, json
sys.path.insert(0, "scripts")
import universe_motion as um
import spotlight_art as art
from spotlight import tmdb
from PIL import Image
O = "refs/st"
os.makedirs(O + "/posters", exist_ok=True)
log = open(O + "/log.txt", "w")
for name, title, w in (("exxen", "File:Exxen.png", 1600), ("gain", "File:GAİN LOGO.jpg", 1600),
                       ("tabii", "File:Trt-tabii-logo.png", 1600), ("tabii_svg", "File:Tabii logo.svg", 1600),
                       ("tabii_icon", "File:Tabii - TRT Logo.png", 1200)):
    try:
        um.commons(title, w).save(f"{O}/{name}.png")
    except Exception as e:
        log.write(f"{name} {e}\n")
for nid in (3186, 8304):
    im = tmdb(f"/network/{nid}/images") or {}
    for j, x in enumerate(im.get("logos", [])[:4]):
        try:
            Image.open(io.BytesIO(um.get("https://image.tmdb.org/t/p/original" + x["file_path"]))).save(f"{O}/hbomax_{nid}_{j}.png")
        except Exception as e:
            log.write(f"hbomax {e}\n")
idx = {}
for key, nets in (("exxen", "4405"), ("gain", "4409"), ("tabii", "6854"), ("hbomax", "3186|49")):
    ps = []
    for page in (1, 2):
        r = tmdb("/discover/tv", with_networks=nets, sort_by="popularity.desc", page=page) or {}
        ps += [x["poster_path"] for x in r.get("results", []) if x.get("poster_path")]
    idx[key] = ps[:36]
    for p in ps[:36]:
        if not os.path.exists(O + "/posters" + p):
            im = art.fetch(p, "w342")
            if im:
                im.convert("RGB").save(O + "/posters" + p, quality=85)
json.dump(idx, open(O + "/posters.json", "w"), indent=1)
log.write(json.dumps({k: len(v) for k, v in idx.items()}))
log.close()
