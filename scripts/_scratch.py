"""Genres: sheet of every genre's iconic pool (the picture each film would show), plus Action/Comedy samples."""
import os, subprocess, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, "art_tools")
import genre_art as g
import spotlight_art as art
from PIL import Image, ImageDraw, ImageFont
os.makedirs("refs/gen", exist_ok=True)
F = ImageFont.truetype("spotlight/fonts/Montserrat-SemiBold.ttf", 15)
FB = ImageFont.truetype("spotlight/fonts/Montserrat-ExtraBold.ttf", 22)
cw, ch = 300, 190
rows = list(g.ICONIC)
sheet = Image.new("RGB", (190 + cw * 8, ch * len(rows)), (18, 18, 22))
d = ImageDraw.Draw(sheet)
for r, t in enumerate(rows):
    d.text((10, r * ch + 80), g.GENRES[t][0], font=FB, fill=(255, 255, 255))
    for c, (name, year) in enumerate(g.ICONIC[t]):
        x, y = 190 + c * cw, r * ch
        tid, real = g.find_movie(name, year)
        p = g.textless_backdrop("movie", tid) if tid else None
        if p:
            im = art.fetch(p, "w500").convert("RGB")
            im.thumbnail((cw - 8, ch - 30))
            sheet.paste(im, (x + 4, y + 4))
        d.text((x + 4, y + ch - 24), f"{real or name} ({year})"[:36], font=F, fill=(255, 214, 90) if p else (255, 80, 80))
sheet.save("refs/gen/pools.jpg", quality=82)
r = subprocess.run([sys.executable, "art_tools/genre_art.py", "refs/gen", "Action & Adventure", "Comedy"], capture_output=True, text=True)
open("refs/gen/log.txt", "w").write(r.stdout + "\n" + r.stderr[-4000:])
