"""Kids & Family sample: Saturday Morning; plus a sheet of Looney Tunes cover options and the pool's fanart."""
import io, os, sys, subprocess, urllib.request
sys.path.insert(0, "scripts"); sys.path.insert(0, "art_tools")
import kids_art as k
from PIL import Image, ImageDraw, ImageFont
os.makedirs("refs/kids", exist_ok=True)
F = ImageFont.truetype("spotlight/fonts/Montserrat-SemiBold.ttf", 14)
items = k.COVER_ALTS["Looney Tunes"] + [("tv", "Looney Tunes", 0)] + k.CARDS["Saturday Morning & Classic Cartoons"][4]
cw, ch, cols = 280, 170, 6
sheet = Image.new("RGB", (220 + cw * cols, ch * len(items)), (18, 18, 22))
d = ImageDraw.Draw(sheet)
for r, it in enumerate(items):
    tid, real = k.find(it[0], it[1], it[2] or None)
    urls = k.fanart(it[0], tid)
    d.text((6, r * ch + 70), f"{(real or it[1])[:26]}", font=F, fill=(255, 255, 255))
    d.text((6, r * ch + 90), f"{it[0]} {tid} · {len(urls)} fanart", font=F, fill=(160, 160, 170))
    for c, u in enumerate(urls[:cols]):
        try:
            im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u.replace("/fanart/", "/preview/"), headers={"User-Agent": "x"}), timeout=60).read())).convert("RGB")
            im.thumbnail((cw - 6, ch - 6)); sheet.paste(im, (220 + c * cw + 3, r * ch + 3))
            d.text((220 + c * cw + 6, r * ch + 4), str(c), font=F, fill=(255, 255, 0))
        except Exception:
            pass
sheet.save("refs/kids/survey.jpg", quality=78)
r = subprocess.run([sys.executable, "art_tools/kids_art.py", "refs/kids", "Saturday Morning & Classic Cartoons"], capture_output=True, text=True)
open("refs/kids/log.txt", "w").write(r.stdout + r.stderr[-3000:])
