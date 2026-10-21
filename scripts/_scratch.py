"""Probe: frame sheets of the Giphy stickers and the TMDB English logos we may use for the universe marks."""
import os, sys, io, traceback
sys.path.insert(0, "scripts")
import universe_motion as um
from PIL import Image, ImageDraw

OUT = "refs/probe"
os.makedirs(OUT, exist_ok=True)
log = open(f"{OUT}/log.txt", "w")

STICKERS = {"mcu": "dC3uDJazzlM4z3lZJ5", "dc_shine": "ensd2k3UXTw2ErdEet", "dc_spin": "46zn5FmNndXaJVjgdG",
            "bat_fog": "erg5dWNomXlY8K4sxu", "bat_the": "st8Zsj32VefZ4mBlPZ", "bat_oval": "LoffmNN2wQYKc",
            "xmen97": "0sifJvGCjI0tXVcnhM", "mi": "Znclz38sX4JBsdUvX3", "jp": "3ohzdPbvIlusvgwaQw",
            "jp30": "FUy4jLKH9gTREgxOqD", "dune": "V5EflugpxzxrYL0MEE", "trek": "JtBbQlcLJHdCCeKM4O",
            "autobot": "mpvtRkRFx3z2HZE2uk"}
LOGOS = {"startrek": 13475, "indiana": 85, "matrix": 603, "avp": 395, "alien": 348, "predator": 106, "apes": 871,
         "apes_kingdom": 653346, "terminator": 218, "t2": 280, "transformers": 1858, "conjuring": 138843,
         "fast": 9799, "fastx": 385687, "madmax": 76341, "furiosa": 786892, "gxk": 823464, "godzilla": 124905,
         "dune": 438631, "jurassic": 329, "mi": 954, "batman": 414906, "xmen": 36657}


def checker(w, h):
    im = Image.new("RGB", (w, h), (60, 60, 60))
    d = ImageDraw.Draw(im)
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            if (x // 16 + y // 16) % 2:
                d.rectangle((x, y, x + 15, y + 15), fill=(90, 90, 90))
    return im


for k, gid in STICKERS.items():
    try:
        fr = um.sticker(gid)
        n = len(fr)
        idx = sorted(set(round(i * (n - 1) / 23) for i in range(24)))
        tw, th = 300, round(300 * fr[0].height / fr[0].width)
        sheet = Image.new("RGB", (tw * 6, (th + 18) * ((len(idx) + 5) // 6)), (20, 20, 20))
        for j, i in enumerate(idx):
            c = checker(tw, th)
            c.paste(fr[i].resize((tw, th)), (0, 0), fr[i].resize((tw, th)))
            sheet.paste(c, ((j % 6) * tw, (j // 6) * (th + 18) + 18))
            ImageDraw.Draw(sheet).text(((j % 6) * tw + 4, (j // 6) * (th + 18) + 3), f"{i}/{n}", fill=(255, 255, 0))
        sheet.save(f"{OUT}/st_{k}.jpg", quality=80)
        log.write(f"sticker {k}: {n} frames {fr[0].size}\n")
    except Exception as e:
        log.write(f"sticker {k} FAILED {e}\n")

for k, mid in LOGOS.items():
    try:
        im = um.tmdb(f"/movie/{mid}/images", include_image_language="en,null") or {}
        lg = sorted([x for x in im.get("logos", []) if x.get("iso_639_1") == "en"], key=lambda x: -x["vote_average"])[:8]
        tiles = []
        for x in lg:
            p = Image.open(io.BytesIO(um.get("https://image.tmdb.org/t/p/w500" + x["file_path"]))).convert("RGBA")
            p = um.fit(p, 280, 120)
            c = checker(300, 140)
            c.paste(p, ((300 - p.width) // 2, (140 - p.height) // 2), p)
            tiles.append((c, x["file_path"]))
        sheet = Image.new("RGB", (300 * 4, 160 * max(1, (len(tiles) + 3) // 4)), (20, 20, 20))
        for j, (c, fp) in enumerate(tiles):
            sheet.paste(c, ((j % 4) * 300, (j // 4) * 160 + 18))
            ImageDraw.Draw(sheet).text(((j % 4) * 300 + 4, (j // 4) * 160 + 3), f"{j} {fp}", fill=(255, 255, 0))
        sheet.save(f"{OUT}/lg_{k}.jpg", quality=80)
        log.write(f"logo {k}: " + " ".join(x["file_path"] for x in lg) + "\n")
    except Exception as e:
        log.write(f"logo {k} FAILED {e}\n{traceback.format_exc()}\n")
log.close()
