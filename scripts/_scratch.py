"""Universes: survey sheet per universe - each film's top fanart backgrounds."""
import io, os, sys, urllib.request
sys.path.insert(0, "scripts"); sys.path.insert(0, "art_tools")
import genre_art as g
from universe_keyart import KEYART
from PIL import Image, ImageDraw, ImageFont
os.makedirs("refs/uni", exist_ok=True)
F = ImageFont.truetype("spotlight/fonts/Montserrat-SemiBold.ttf", 14)
cw, ch, cols = 280, 170, 5


def prev(url):
    u = url.replace("/fanart/", "/preview/") if "fanart" in url else "https://image.tmdb.org/t/p/w300" + url
    try:
        return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "x"}), timeout=60).read())).convert("RGB")
    except Exception:
        return None


for uid, films in KEYART.items():
    sheet = Image.new("RGB", (200 + cw * cols, ch * len(films)), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    for r, (name, year) in enumerate(films):
        tid, real = g.find_movie(name, year)
        d.text((6, r * ch + 70), f"{(real or name)[:24]}", font=F, fill=(255, 255, 255))
        urls = g.fanart_backgrounds(tid) if tid else []
        d.text((6, r * ch + 90), f"{year} · {len(urls)} fanart", font=F, fill=(160, 160, 170))
        if not urls and tid:
            t = g.textless_backdrop("movie", tid)
            urls = [t] if t else []
        for c, u in enumerate(urls[:cols]):
            im = prev(u)
            if im:
                im.thumbnail((cw - 6, ch - 6))
                sheet.paste(im, (200 + c * cw + 3, r * ch + 3))
                d.text((200 + c * cw + 6, r * ch + 4), str(c), font=F, fill=(255, 255, 0))
    sheet.save(f"refs/uni/{uid}.jpg", quality=78)
