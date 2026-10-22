"""Genres: for every film in every iconic pool, its top fanart.tv backgrounds (previews), one sheet per genre;
plus Action/Comedy samples with the most liked one."""
import io, os, subprocess, sys, urllib.request
sys.path.insert(0, "scripts"); sys.path.insert(0, "art_tools")
import genre_art as g
from PIL import Image, ImageDraw, ImageFont
os.makedirs("refs/gen", exist_ok=True)
F = ImageFont.truetype("spotlight/fonts/Montserrat-SemiBold.ttf", 14)
cw, ch, cols = 300, 190, 5


def prev(url):
    u = url.replace("/fanart/", "/preview/")
    try:
        return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "x"}), timeout=60).read())).convert("RGB")
    except Exception:
        return None


for t, pool in g.ICONIC.items():
    sheet = Image.new("RGB", (220 + cw * cols, ch * len(pool)), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    for r, (name, year) in enumerate(pool):
        tid, real = g.find_movie(name, year)
        d.text((8, r * ch + 80), (real or name)[:26], font=F, fill=(255, 255, 255))
        urls = g.fanart_backgrounds(tid) if tid else []
        d.text((8, r * ch + 100), f"{len(urls)} backgrounds", font=F, fill=(160, 160, 170))
        for c, u in enumerate(urls[:cols]):
            im = prev(u)
            if im:
                im.thumbnail((cw - 8, ch - 8))
                sheet.paste(im, (220 + c * cw + 4, r * ch + 4))
    sheet.save(f"refs/gen/fa_{g.slug_of(t)}.jpg", quality=80)
r = subprocess.run([sys.executable, "art_tools/genre_art.py", "refs/gen", "Action & Adventure", "Comedy"], capture_output=True, text=True)
open("refs/gen/log.txt", "w").write(r.stdout + "\n" + r.stderr[-4000:])
