"""Probe: Indiana Jones logos that are just the name."""
import os, sys, io, json, urllib.parse
sys.path.insert(0, "scripts")
import universe_motion as um
from PIL import Image, ImageDraw
OUT = "refs/probe2"
os.makedirs(OUT, exist_ok=True)
log = open(f"{OUT}/log.txt", "w")
tiles = []
for kind, mid in (("movie", 87), ("movie", 89), ("movie", 217), ("movie", 335977), ("tv", 1081), ("collection", 84)):
    try:
        im = um.tmdb(f"/{kind}/{mid}/images", include_image_language="en,null") or {}
        for x in [x for x in im.get("logos", []) if x["file_path"].endswith(".png")][:6]:
            tiles.append((f"{kind}{mid} {x['file_path']}", "https://image.tmdb.org/t/p/w500" + x["file_path"]))
    except Exception as e:
        log.write(f"{kind} {mid} {e}\n")
try:
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": "Indiana Jones logo", "srnamespace": 6, "format": "json", "srlimit": 12})
    d = json.loads(um.get("https://commons.wikimedia.org/w/api.php?" + q))
    for r in d["query"]["search"]:
        log.write("commons " + r["title"] + "\n")
        try:
            q2 = urllib.parse.urlencode({"action": "query", "titles": r["title"], "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 500, "format": "json"})
            info = next(iter(json.loads(um.get("https://commons.wikimedia.org/w/api.php?" + q2))["query"]["pages"].values()))["imageinfo"][0]
            tiles.append((r["title"][:40], info.get("thumburl") or info["url"]))
        except Exception as e:
            log.write(f"  {e}\n")
except Exception as e:
    log.write(f"commons {e}\n")
sheet = Image.new("RGB", (1200, 160 * ((len(tiles) + 3) // 4)), (60, 60, 60))
for j, (lab, u) in enumerate(tiles):
    try:
        p = um.fit(Image.open(io.BytesIO(um.get(u))).convert("RGBA"), 280, 120)
        sheet.paste(p, ((j % 4) * 300 + 10, (j // 4) * 160 + 30), p)
    except Exception as e:
        log.write(f"tile {lab} {e}\n")
    ImageDraw.Draw(sheet).text(((j % 4) * 300 + 4, (j // 4) * 160 + 3), f"{j} {lab}", fill=(255, 255, 0))
    log.write(f"{j} {lab} {u}\n")
sheet.save(f"{OUT}/indiana.jpg", quality=85)
log.close()
