"""Temporary: Favourites cover samples v2 (official logos for Doctor Who / One Pace, our logos for the rest)."""
import io, json, os, sys, traceback, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

OUT = "refs/fav2"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
W, H = art.W, art.H
LOG = open(f"{OUT}/log.txt", "w")


def get(url):
    return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()))


def wiki_logo(page):
    api = "https://en.wikipedia.org/w/api.php?"
    q = {"action": "query", "titles": page, "prop": "pageimages|images", "piprop": "original", "format": "json"}
    d = json.loads(urllib.request.urlopen(urllib.request.Request(api + urllib.parse.urlencode(q), headers=UA)).read())
    pg = next(iter(d["query"]["pages"].values()))
    LOG.write(json.dumps(pg, indent=1) + "\n")
    files = [i["title"] for i in pg.get("images", []) if "logo" in i["title"].lower() or "whoniverse" in i["title"].lower()]
    for f in files:
        q = {"action": "query", "titles": f, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "1600", "format": "json"}
        d = json.loads(urllib.request.urlopen(urllib.request.Request(api + urllib.parse.urlencode(q), headers=UA)).read())
        ii = next(iter(d["query"]["pages"].values())).get("imageinfo", [{}])[0]
        LOG.write(f"{f}: {ii}\n")
        url = ii.get("thumburl") or ii.get("url")
        if url:
            im = get(url)
            im.save(f"{OUT}/logo-{len(os.listdir(OUT))}.png")
            return im
    return None


def fade(base, start=0.5, top=170):
    shade = Image.new("RGB", (W, H), (0, 0, 0))
    m = Image.new("L", (1, H))
    for y in range(H):
        f = (y / H - start) / (1 - start)
        m.putpixel((0, y), 0 if f <= 0 else round(top * f ** 1.4))
    return Image.composite(shade, base, m.resize((W, H)))


def place(base, lg, maxw=560, maxh=200, bottom=58):
    lg = lg.convert("RGBA")
    r = min(maxw / lg.width, maxh / lg.height)
    lg = lg.resize((round(lg.width * r), round(lg.height * r)), Image.LANCZOS)
    x, y = (W - lg.width) // 2, H - bottom - lg.height
    sh = Image.new("RGBA", (lg.width + 80, lg.height + 80), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", lg.size, (0, 0, 0, 255)), (40, 40), lg.getchannel("A").point(lambda v: v * 0.75))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    base = base.convert("RGBA")
    base.alpha_composite(sh, (x - 40, y - 34))
    base.alpha_composite(lg, (x, y))
    return base.convert("RGB")


def grade(im, b=0.92, c=1.05):
    im = art.cover_fit(im.convert("RGB"), W, H)
    return ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(b)).enhance(c)


def save(im, name):
    im.save(f"{OUT}/{name}.jpg", "JPEG", quality=88)


def step(name, fn):
    try:
        fn()
    except Exception:
        LOG.write(f"{name}\n{traceback.format_exc()}\n")


def doctor_who():
    dw = grade(get("https://i.pinimg.com/1200x/ce/6d/19/ce6d198219d333e44c15ec35bd18e1f9.jpg"))
    lg = wiki_logo("Whoniverse")
    if lg is not None:
        lg.convert("RGBA").save("spotlight/logos/whoniverse.png")
        save(place(fade(dw), lg, maxw=600, maxh=190), "doctorwho")


def one_pace():
    op = grade(get("https://image.tmdb.org/t/p/original/6fRwRD7GdCfg6owzmCT3VgQtowl.jpg"), 0.95)
    lg = get("https://onepace.net/_next/static/media/logo.3b-t7f20tomve.png")
    lg.convert("RGBA").save("spotlight/logos/onepace.png")
    LOG.write(f"onepace logo {lg.size} {lg.mode}\n")
    save(place(fade(op, 0.45, 190), lg, maxw=520, maxh=200), "onepace")


def live_sport():
    from favourites_art import commons, COMMONS
    st = grade(commons(COMMONS)[0], 1.0, 1.08)
    for v in ("a", "b"):
        save(place(fade(st, 0.5, 180), Image.open(f"spotlight/logos/livesport-{v}.png"), maxw=620, maxh=150), f"livesport-{v}")


def my_simkl():
    posters = []
    for path in ("/trending/movie/week", "/trending/tv/week"):
        posters += [r["poster_path"] for r in (tmdb(path) or {}).get("results", []) if r.get("poster_path")]
    wall = poster_wall_natural(posters[:40])
    for v in ("a", "b"):
        save(place(fade(wall, 0.4, 200), Image.open(f"spotlight/logos/mysimkl-{v}.png"), maxw=600, maxh=150), f"mysimkl-{v}")


def poster_wall_natural(posters, angle=-12):
    pw, ph, gap = 170, 255, 16
    cols, rows = 11, 5
    wall = Image.new("RGB", (cols * (pw + gap), rows * (ph + gap)), (12, 12, 16))
    imgs = [im for im in (art.fetch(p, "w342") for p in posters) if im]
    for i in range(cols * (rows + 1)):
        im = imgs[i % len(imgs)].convert("RGB").resize((pw, ph), Image.LANCZOS)
        c, r = i % cols, i // cols
        wall.paste(im, (c * (pw + gap), r * (ph + gap) - (ph // 2 if c % 2 else 0)))
    wall = wall.rotate(angle, resample=Image.BICUBIC, fillcolor=(12, 12, 16))
    x, y = (wall.width - W) // 2, (wall.height - H) // 2
    return ImageEnhance.Brightness(wall.crop((x, y, x + W, y + H))).enhance(0.8)


for n, f in (("doctor_who", doctor_who), ("one_pace", one_pace), ("live_sport", live_sport), ("my_simkl", my_simkl)):
    step(n, f)
LOG.close()
