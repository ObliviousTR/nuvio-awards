"""Temporary: Favourites cover samples (key art + logo, light grading) and GIF candidate sheets."""
import io, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageSequence

OUT = "refs/fav"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
W, H = art.W, art.H


def get(url):
    return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()))


def logo(kind, tid, lang="en"):
    ls = (tmdb(f"/{kind}/{tid}/images", include_image_language=f"{lang},null") or {}).get("logos", [])
    ls = [l for l in ls if l["file_path"].endswith(".png")]
    ls.sort(key=lambda l: (l.get("iso_639_1") != lang, -l.get("vote_average", 0)))
    return [art.fetch(l["file_path"], "w500") for l in ls[:3]]


def fade(base, start=0.5, top=170):
    shade = Image.new("RGB", (W, H), (0, 0, 0))
    m = Image.new("L", (1, H))
    for y in range(H):
        f = (y / H - start) / (1 - start)
        m.putpixel((0, y), 0 if f <= 0 else round(top * f ** 1.4))
    return Image.composite(shade, base, m.resize((W, H)))


def place(base, lg, where="center", maxw=560, maxh=210, bottom=58):
    lg = lg.convert("RGBA")
    r = min(maxw / lg.width, maxh / lg.height)
    lg = lg.resize((round(lg.width * r), round(lg.height * r)), Image.LANCZOS)
    x = (W - lg.width) // 2 if where == "center" else 72
    y = H - bottom - lg.height
    sh = Image.new("RGBA", (lg.width + 80, lg.height + 80), (0, 0, 0, 0))
    a = lg.getchannel("A").point(lambda v: v * 0.7)
    sh.paste(Image.new("RGBA", lg.size, (0, 0, 0, 255)), (40, 40), a)
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    base = base.convert("RGBA")
    base.alpha_composite(sh, (x - 40, y - 34))
    base.alpha_composite(lg, (x, y))
    return base.convert("RGB")


def wordmark(base, text, where="center", size=92, sub=None):
    d = ImageDraw.Draw(base)
    f = art.font("ExtraBold", size)
    w = d.textlength(text, font=f)
    x = (W - w) // 2 if where == "center" else 72
    y = H - 70 - size
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((x, y), text, font=f, fill=(0, 0, 0, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    base = base.convert("RGBA"); base.alpha_composite(glow); base = base.convert("RGB")
    d = ImageDraw.Draw(base)
    d.text((x, y), text, font=f, fill=(255, 255, 255))
    return base


def grade(im, b=0.92, c=1.05):
    im = art.cover_fit(im.convert("RGB"), W, H)
    return ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(b)).enhance(c)


def save(im, name):
    im.save(f"{OUT}/{name}.jpg", "JPEG", quality=88)


# Doctor Who: the user's own cover + the show's logo
dw = grade(get("https://i.pinimg.com/1200x/ce/6d/19/ce6d198219d333e44c15ec35bd18e1f9.jpg"))
lgs = [l for l in logo("tv", 57243) if l]
for i, lg in enumerate(lgs[:2]):
    save(place(fade(dw), lg, "center"), f"doctorwho-A{i}")
    save(place(fade(dw), lg, "left"), f"doctorwho-B{i}")

# One Pace: One Piece crew art + One Piece logo + "ONE PACE"
bd = get("https://image.tmdb.org/t/p/original/6fRwRD7GdCfg6owzmCT3VgQtowl.jpg")
op = grade(bd, 0.95)
oplogo = [l for l in logo("tv", 37854) if l]
if oplogo:
    im = place(fade(op, 0.45, 190), oplogo[0], "center", maxw=460, maxh=170, bottom=96)
    d = ImageDraw.Draw(im)
    f = art.font("ExtraBold", 30)
    t = "ONE PACE"
    x = (W - sum(d.textlength(ch, font=f) + 10 for ch in t)) // 2
    art.spaced(d, (x, H - 76), t, f, (255, 255, 255), 10)
    save(im, "onepace-A")
save(wordmark(fade(op, 0.45, 190), "ONE PACE"), "onepace-B")

# Live Sport: stadium, natural light, wordmark + LIVE pill
st = get("https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Germany_and_Argentina_face_off_in_the_final_of_the_World_Cup_2014_-2014-07-13_%285%29.jpg/1920px-Germany_and_Argentina_face_off_in_the_final_of_the_World_Cup_2014_-2014-07-13_%285%29.jpg")
ls = grade(st, 1.0, 1.08)
save(art.live_pill(wordmark(fade(ls, 0.5, 180), "LIVE SPORT")), "livesport-A")

# GIF candidate sheets
GIFS = {
 "onepiece": ["D0jGorbyCnZyE", "uvCxJCIdf1BcY", "dX1iTuEIj4yfwHDUCy", "Nm31pMDFs6k8DYRfhB", "3vIsKbCJgSRojGuUAY",
              "DSxKEQoQix9hC", "WeyqDp1shHe7u", "7BW9U2cJPQZ0s", "v8rbkCKtuZbRC", "q8ld8Sk7WWyY0"],
 "stadium": ["LaeEI5VSjjP3IFHLDd", "vvaDh9BKJy0mpElmh8", "LRImhef19evRyXDQnx", "DUeCanb3kaAuima0mq",
             "YtQqKLb4wYPJOOa05w", "zT6eLPuZsiIkvRoeBj", "3ohhwwyFYkqd68YoLu", "cmMzVX4LV157ubMD6V",
             "nPowS08L20SfJG7xPk", "HJtf633F5Mb9q23EKC", "hKdKx85h8bcGhErnMZ"],
}
info = {}
for group, ids in GIFS.items():
    rows = []
    for gid in ids:
        try:
            g = get(f"https://media.giphy.com/media/{gid}/giphy.gif")
        except Exception as e:
            print("fail", gid, e); continue
        fr = [f.copy().convert("RGB") for f in ImageSequence.Iterator(g)]
        info[gid] = {"size": g.size, "frames": len(fr), "ms": g.info.get("duration")}
        pick = [fr[int(i * (len(fr) - 1) / 4)] for i in range(5)]
        row = Image.new("RGB", (5 * 256 + 200, 150), (20, 20, 20))
        for i, p in enumerate(pick):
            p = art.cover_fit(p, 256, 144); row.paste(p, (200 + i * 256, 3))
        ImageDraw.Draw(row).text((6, 50), f"{gid}\n{g.size[0]}x{g.size[1]} {len(fr)}f", fill=(255, 255, 0))
        rows.append(row)
    sheet = Image.new("RGB", (rows[0].width, 150 * len(rows)))
    for i, r in enumerate(rows):
        sheet.paste(r, (0, i * 150))
    sheet.save(f"{OUT}/gifs-{group}.jpg", quality=80)
json.dump(info, open(f"{OUT}/gifs.json", "w"), indent=1)
