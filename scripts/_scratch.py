"""Probe: official logos for the typeset universes."""
import os, sys, io
sys.path.insert(0, "scripts")
import universe_motion as um
from PIL import Image, ImageDraw
OUT = "refs/probe3"
os.makedirs(OUT, exist_ok=True)
log = open(f"{OUT}/log.txt", "w")
tiles = []
for mid in (324857, 569094, 911916, 245891, 385128, 399566, 823464, 76341, 786892, 268):
    try:
        im = um.tmdb(f"/movie/{mid}/images", include_image_language="en,null") or {}
        for x in [x for x in im.get("logos", []) if x["file_path"].endswith(".png")][:6]:
            tiles.append((f"{mid} {x['file_path']}", "https://image.tmdb.org/t/p/w500" + x["file_path"]))
    except Exception as e:
        log.write(f"{mid} {e}\n")
sheet = Image.new("RGB", (1200, 160 * ((len(tiles) + 3) // 4)), (60, 60, 60))
for j, (lab, u) in enumerate(tiles):
    try:
        p = um.fit(Image.open(io.BytesIO(um.get(u))).convert("RGBA"), 280, 120)
        sheet.paste(p, ((j % 4) * 300 + 10, (j // 4) * 160 + 30), p)
    except Exception as e:
        log.write(f"tile {lab} {e}\n")
    ImageDraw.Draw(sheet).text(((j % 4) * 300 + 4, (j // 4) * 160 + 3), f"{j} {lab}", fill=(255, 255, 0))
    log.write(f"{j} {lab}\n")
sheet.save(f"{OUT}/logos.jpg", quality=85)
log.close()
