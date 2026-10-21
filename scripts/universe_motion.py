"""Universes & Franchises art, motion version: per folder a hover GIF (the universe's mark builds over clean,
textless scenes from across the franchise), a cover (the settled frame) and a clean hero backdrop.

Marks are either the official logo (TMDB / Wikimedia Commons / an official Giphy sticker) animated in the
franchise's own idiom, or, where no single logo covers the folder, an original wordmark of ours in the same spirit
(Spider-Verse, Middle-earth...). Shared pieces: scene crossfade with slow push-in, soft vignette, light sweep,
tagline. Everything renders at 1280x720; the GIF is 512x288 and kept around 3 MB.
usage: python3 scripts/universe_motion.py OUT_DIR [ids...]
"""
import io, json, math, os, random, sys, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageSequence

W, H = 1280, 720
GW, GH = 512, 288
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36 nuvio-awards"}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
FONTS = {  # Google Fonts (OFL), fetched once
    "anton": "ofl/anton/Anton-Regular.ttf",
    "cinzel": "ofl/cinzel/Cinzel%5Bwght%5D.ttf",
    "bebas": "ofl/bebasneue/BebasNeue-Regular.ttf",
    "orbitron": "ofl/orbitron/Orbitron%5Bwght%5D.ttf",
}


def get(url):
    import time
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, urllib.parse.quote(url, safe="")[-150:])
    if not os.path.exists(p):
        # Wikimedia asks for a descriptive agent with a contact; others get a browser-like one
        ua = {"User-Agent": "nuvio-awards/1.0 (https://github.com/ObliviousTR/nuvio-awards)"} if "wiki" in url else UA
        for k in range(5):
            try:
                open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=90).read())
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or k == 4:
                    raise
                time.sleep(5 * (k + 1))
    return open(p, "rb").read()


def font(name, size, weight=None):
    b = get("https://github.com/google/fonts/raw/main/" + FONTS[name])
    f = ImageFont.truetype(io.BytesIO(b), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def commons(title, width=1600):
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url",
                                "iiurlwidth": width, "format": "json"})
    d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    info = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
    return Image.open(io.BytesIO(get(info.get("thumburl") or info["url"]))).convert("RGBA")


def tmdb_logo(movie_id):
    im = tmdb(f"/movie/{movie_id}/images", include_image_language="en") or {}
    lg = sorted([x for x in im.get("logos", []) if x.get("iso_639_1") == "en"], key=lambda x: -x["vote_average"])
    return Image.open(io.BytesIO(get("https://image.tmdb.org/t/p/original" + lg[0]["file_path"]))).convert("RGBA")


def sticker(gid):
    g = Image.open(io.BytesIO(get(f"https://media.giphy.com/media/{gid}/giphy.gif")))
    return [f.convert("RGBA").copy() for f in ImageSequence.Iterator(g)]


def trim(im):
    bb = im.getchannel("A").getbbox()
    return im.crop(bb) if bb else im


def whiten_dark(im, lim=90):
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and max(r, g, b) < lim:
                px[x, y] = (255, 255, 255, a)
    return im


def fit(im, maxw, maxh):
    k = min(maxw / im.width, maxh / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def alpha(im, a):
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: round(v * max(0, min(1, a)))))
    return im


def place(cv, im, cx, cy, a=1.0):
    cv.alpha_composite(alpha(im, a), (round(cx - im.width / 2), round(cy - im.height / 2)))


def text_layer(text, fnt, color=(255, 255, 255), tracking=0):
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    w = sum(probe.textlength(c, font=fnt) + tracking for c in text) - tracking
    asc, desc = fnt.getmetrics()
    m = Image.new("L", (round(w) + 40, asc + desc + 40), 0)
    art.spaced(ImageDraw.Draw(m), (20, 20), text, fnt, 255, tracking)
    m = m.crop(m.getbbox())
    lay = Image.new("RGBA", m.size, color + (0,))
    lay.putalpha(m)
    return lay


def gradient_fill(mask_layer, top, bottom):
    w, h = mask_layer.size
    g = Image.new("RGBA", (w, h))
    for y in range(h):
        f = y / max(1, h - 1)
        g.paste(tuple(round(top[i] + (bottom[i] - top[i]) * f) for i in range(3)) + (255,), (0, y, w, y + 1))
    g.putalpha(mask_layer.getchannel("A"))
    return g


def glow(layer, radius, color, strength=1.0):
    g = Image.new("RGBA", layer.size, color + (0,))
    g.putalpha(layer.getchannel("A").filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, round(v * strength))))
    return g


def padded(im, pad):
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(im, (pad, pad))
    return out


def sweep(cv, s, width=90, strength=150):
    """Diagonal light band across whatever is drawn on cv (s 0..1)."""
    band = Image.new("L", (W, H), 0)
    bx = -300 + s * (W + 600)
    ImageDraw.Draw(band).polygon([(bx, 0), (bx + width, 0), (bx - 110, H), (bx - 110 - width, H)], fill=strength)
    band = band.filter(ImageFilter.GaussianBlur(30))
    m = ImageChops.multiply(band, cv.getchannel("A"))
    lay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    lay.putalpha(m)
    cv.alpha_composite(lay)


def tagline(cv, text, y, a=1.0, size=26, color=(255, 255, 255)):
    f = art.font("SemiBold", size)
    lay = text_layer(text, f, color, tracking=8)
    place(cv, lay, W / 2, y, a)


def wipe(layer, p, soft=60, direction="lr"):
    """Reveal a layer left-to-right with a soft edge (p 0..1)."""
    w, h = layer.size
    m = Image.new("L", (w + 2 * soft, 1), 0)
    edge = -soft + p * (w + 2 * soft)
    for x in range(w + 2 * soft):
        v = (edge - (x - soft)) / soft
        m.putpixel((x, 0), round(255 * max(0, min(1, v))))
    m = m.crop((soft, 0, soft + w, 1)).resize((w, h))
    out = layer.copy()
    out.putalpha(ImageChops.multiply(layer.getchannel("A"), m))
    return out


def ease(x):
    x = max(0, min(1, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- scenes
def scenes(paths, b=0.62):
    out = []
    for p in paths:
        im = art.fetch(p)
        out.append(ImageEnhance.Brightness(art.graded(im, 0.92, 1.05)).enhance(b))
    return out


def vignette(im, strength=1.0):
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse((-W * 0.2, -H * 0.3, W * 1.2, H * 1.3), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(120)).point(lambda x: round(255 - (255 - x) * strength))
    return Image.composite(im, Image.new("RGB", (W, H), (0, 0, 0)), v)


def background(sc, g):
    seg = min(len(sc) - 1, int(g * len(sc)))
    loc = g * len(sc) - seg
    bg = art.zoomed(sc[seg], 0.02 + 0.06 * loc)
    if loc > 0.78:
        bg = Image.blend(bg, art.zoomed(sc[(seg + 1) % len(sc)], 0.02), (loc - 0.78) / 0.22)
    return vignette(bg)


# ---------------------------------------------------------------- marks
class Mark:
    """mark(t, h): t = build progress 0..1, h = hold progress 0..1 (or None while building). Returns RGBA WxH."""
    build, hold = 26, 34


class SpiderVerse(Mark):
    def __init__(self):
        f = font("anton", 170)
        self.face = text_layer("SPIDER-VERSE", f, (255, 255, 255), 3)
        self.red = text_layer("SPIDER-VERSE", f, (230, 36, 41), 3)
        self.blue = text_layer("SPIDER-VERSE", f, (40, 120, 255), 3)

    def web(self, s, p):
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c, n = s / 2, 12
        for i in range(n):
            a = i * 2 * math.pi / n - math.pi / 2
            r = c * min(1, p * 1.6)
            d.line((c, c, c + r * math.cos(a), c + r * math.sin(a)), fill=(255, 255, 255, 70), width=2)
        rings = max(0, (p - 0.25) / 0.75)
        for j in range(1, 6):
            if rings * 5 < j - 0.999:
                break
            rr = c * j / 5.4
            pts = [(c + rr * math.cos(i * 2 * math.pi / n - math.pi / 2), c + rr * math.sin(i * 2 * math.pi / n - math.pi / 2)) for i in range(n)]
            for i in range(n):
                p0, p1 = pts[i], pts[(i + 1) % n]
                mx, my = c + ((p0[0] + p1[0]) / 2 - c) * 0.92, c + ((p0[1] + p1[1]) / 2 - c) * 0.92
                d.line((p0, (mx, my), p1), fill=(255, 255, 255, 55), width=2)
        return im

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wb = self.web(620, min(1, t / 0.55))
        place(cv, wb if t < 0.85 else alpha(wb, 0.55), W / 2, H / 2 - 10)
        cy = H / 2
        k = max(0, min(1, (t - 0.25) / 0.6))
        e = ease(k)
        off = 7 + (1 - e) * 120
        rnd = random.Random(int(t * 1000))

        def put(layer, dx, dy, a):
            if a <= 0:
                return
            l = alpha(layer, a)
            if k < 1:
                sl = Image.new("RGBA", l.size, (0, 0, 0, 0))
                for y in range(0, l.height, 14):
                    sl.paste(l.crop((0, y, l.width, min(l.height, y + 14))), (round(rnd.uniform(-1, 1) * 40 * (1 - e)), y))
                l = sl
            place(cv, l, W / 2 + dx, cy + dy)
        a = min(1, t / 0.3)
        put(self.blue, off, -off * 0.15, a)
        put(self.red, -off, off * 0.15, a)
        put(self.face, 0, 0, max(0, (t - 0.45) / 0.3) if t < 0.75 else 1)
        if h is not None and h < 0.5:
            sweep(cv, h * 2)
        if t > 0.8:
            tagline(cv, "EVERY SPIDER  ·  EVERY UNIVERSE", cy + self.face.height / 2 + 46, (t - 0.8) / 0.2)
        return cv


class MiddleEarth(Mark):
    """A gold ring glows up out of fire, then MIDDLE-EARTH burns in letter by letter like heated metal."""
    build, hold = 30, 32

    def __init__(self):
        f = font("cinzel", 112, weight=800)
        base = text_layer("MIDDLE-EARTH", f, (255, 255, 255), 14)
        self.word = gradient_fill(base, (255, 226, 150), (176, 120, 40))
        self.hot = gradient_fill(base, (255, 250, 220), (255, 150, 40))
        self.tag = "THE LORD OF THE RINGS  ·  THE HOBBIT"

    def ring(self, spin, heat):
        """A thick gold band seen at an angle: filled ellipse minus the hole, lit from above, glowing hot."""
        s = 420
        squash = 0.34 + 0.12 * math.cos(spin)
        rx, ry = 170, 170 * squash
        th = 30  # band thickness
        band = Image.new("L", (s, s), 0)
        d = ImageDraw.Draw(band)
        d.ellipse((s / 2 - rx, s / 2 - ry, s / 2 + rx, s / 2 + ry + th * 0.6), fill=255)
        d.ellipse((s / 2 - rx + th, s / 2 - ry + th * squash * 1.4, s / 2 + rx - th, s / 2 + ry - th * squash * 0.4), fill=0)
        gold = Image.new("RGBA", (s, s))
        for y in range(s):
            f = (y - (s / 2 - ry)) / max(1, 2 * ry + th)
            f = max(0, min(1, f))
            # bright crown, deep amber belly, a second highlight near the lower rim
            v = 0.55 + 0.45 * math.cos(f * math.pi * 1.6) ** 2
            gold.paste((round(255 * v), round(196 * v), round(70 * v * 0.8), 255), (0, y, s, y + 1))
        gold.putalpha(band)
        hl = Image.new("L", (s, s), 0)
        ImageDraw.Draw(hl).arc((s / 2 - rx + 8, s / 2 - ry + 4, s / 2 + rx - 8, s / 2 + ry - 4), 200, 330, fill=200, width=5)
        hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(2)), band)
        shine = Image.new("RGBA", (s, s), (255, 250, 225, 0))
        shine.putalpha(hl)
        out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        out.alpha_composite(glow(gold, 26, (255, 120, 20), 1.5 * heat))
        out.alpha_composite(gold)
        out.alpha_composite(shine)
        return out.rotate(-8 + 6 * math.sin(spin), resample=Image.BICUBIC)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        spin = (t * 2.2 if h is None else 2.2 + h * 1.2) * math.pi
        heat = 1.0 if t < 0.6 else 1.0 - 0.6 * min(1, (t - 0.6) / 0.4)
        ring = self.ring(spin, heat)
        ry = H / 2 - 120 if t > 0.45 else H / 2 - 120 + (1 - ease(t / 0.45)) * 120
        place(cv, fit(ring, 300, 300), W / 2, ry, min(1, t / 0.2))
        p = max(0, (t - 0.4) / 0.55)
        if p > 0:
            hot = wipe(self.hot, p, soft=80)
            cool = wipe(self.word, max(0, p - 0.18) / 0.82, soft=120)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            place(lay, glow(padded(hot, 40), 18, (255, 120, 20), 1.4), W / 2, H / 2 + 70)
            place(lay, hot, W / 2, H / 2 + 70)
            place(lay, cool, W / 2, H / 2 + 70)
            cv.alpha_composite(lay)
        if h is not None and h < 0.5:
            sweep(cv, h * 2, strength=110)
        if t > 0.85:
            tagline(cv, self.tag, H / 2 + 70 + self.word.height / 2 + 44, (t - 0.85) / 0.15, color=(240, 220, 170))
        return cv


class WizardingWorld(Mark):
    """The Deathly Hallows sigil draws itself (Wizarding World's own Giphy sticker), then the official
    Wizarding World logo shimmers in out of drifting sparks."""
    build, hold = 34, 30

    def __init__(self):
        fr = [f for f in sticker("L2lkyiSIYFq6f4gAqq")
              if sum(1 for v in f.getchannel("A").resize((40, 27)).getdata() if v > 200) < 300]
        self.sig = [fit(trim(f), 330, 330) for f in fr if f.getchannel("A").getbbox()]
        self.logo = fit(trim(whiten_dark(commons("File:Wizarding World logo.svg"))), 660, 230)
        rnd = random.Random(7)
        self.sparks = [(rnd.uniform(0.3, 0.7) * W, rnd.uniform(0.35, 0.8) * H, rnd.uniform(-1, 1), rnd.uniform(0.5, 1)) for _ in range(70)]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        n = len(self.sig)
        i = min(n - 1, round(min(1, t / 0.55) * (n - 1)))
        sig = self.sig[i] if t < 0.6 else self.sig[-1]
        sa = 1.0 if t < 0.55 else 1 - 0.75 * min(1, (t - 0.55) / 0.3)
        place(cv, glow(padded(sig, 30), 14, (190, 210, 255), 1.2), W / 2, H / 2, sa * 0.8)
        place(cv, sig, W / 2, H / 2, sa)
        p = max(0, (t - 0.5) / 0.45)
        if p > 0:
            d = ImageDraw.Draw(cv)
            for (x, y, dx, s) in self.sparks:
                age = p if h is None else 1 + (h or 0)
                yy = y - age * 120 * s
                a = max(0, 1 - abs(age - 0.6) * 1.4) if h is None else max(0, 0.5 - (h or 0))
                r = 2 + 2 * s
                d.ellipse((x + dx * 40 * age - r, yy - r, x + dx * 40 * age + r, yy + r), fill=(255, 240, 200, round(220 * a)))
            lg = self.logo
            place(cv, glow(padded(lg, 40), 20, (255, 225, 170), 0.9 * ease(p)), W / 2, H / 2, 1)
            place(cv, lg, W / 2, H / 2, ease(p))
        if h is not None and h < 0.5:
            sweep(cv, h * 2, strength=120)
        if t > 0.88:
            tagline(cv, "HARRY POTTER  ·  FANTASTIC BEASTS", H / 2 + self.logo.height / 2 + 40, (t - 0.88) / 0.12)
        return cv


class StarWars(Mark):
    """The opening's move in reverse: a starfield, the logo arrives from far away and settles mid-screen."""
    build, hold = 30, 30

    def __init__(self):
        self.logo = trim(commons("File:Star Wars Logo.svg"))
        rnd = random.Random(3)
        self.stars = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.4, 1.0)) for _ in range(260)]

    def starfield(self, a):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for x, y, s in self.stars:
            d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, round(255 * s * a)))
        return im

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, round(255 * (1 - min(1, t / 0.9)) * 0.9)))
        cv.alpha_composite(self.starfield(1.0 if t < 0.9 else 0.6))
        s = 0.08 + 0.92 * ease(t / 0.8)  # grows toward the viewer, then rests
        lg = fit(self.logo, 620 * s, 330 * s)
        place(cv, lg, W / 2, H / 2 - 10, min(1, t / 0.15))
        if h is not None and h < 0.5:
            sweep(cv, h * 2, strength=120)
        if t > 0.85:
            tagline(cv, "A GALAXY FAR, FAR AWAY", H / 2 - 10 + 330 / 2 + 40, (t - 0.85) / 0.15, color=(255, 232, 31))
        return cv


class WorldOfJohnWick(Mark):
    """A neon sign stuttering on in the rain: THE WORLD OF / JOHN WICK."""
    build, hold = 28, 34

    def __init__(self):
        big = font("bebas", 190)
        small = font("bebas", 54)
        self.main = text_layer("JOHN WICK", big, (255, 255, 255), 10)
        self.top = text_layer("THE WORLD OF", small, (255, 255, 255), 16)
        self.cols = ((255, 60, 170), (90, 160, 255))

    def neon(self, layer, col, on):
        tube = Image.new("RGBA", layer.size, (255, 255, 255, 0))
        tube.putalpha(layer.getchannel("A"))
        p = padded(tube, 60)
        out = Image.new("RGBA", p.size, (0, 0, 0, 0))
        out.alpha_composite(glow(p, 26, col, 1.3 * on))
        out.alpha_composite(glow(p, 8, col, 1.8 * on))
        core = Image.new("RGBA", p.size, (255, 255, 255, 0))
        core.putalpha(p.getchannel("A").point(lambda v: round(v * (0.25 + 0.75 * on))))
        tint = Image.new("RGBA", p.size, tuple(round(c * 0.4 + 255 * 0.6) for c in col) + (0,))
        tint.putalpha(core.getchannel("A"))
        out.alpha_composite(tint)
        return out

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rnd = random.Random(int(t * 997))
        flick = lambda start: 0 if t < start else (1 if t > start + 0.3 else (1 if rnd.random() < (t - start) / 0.3 else 0.08))
        on_top, on_main = flick(0.05), flick(0.35)
        if h is not None:
            on_main = 0.88 if (int(h * 34) % 17 == 9) else 1.0  # one buzz in the hold
        place(cv, self.neon(self.top, self.cols[1], on_top), W / 2, H / 2 - 120)
        place(cv, self.neon(self.main, self.cols[0], on_main), W / 2, H / 2 + 30)
        return cv


MARKS = {
    "spiderman": (SpiderVerse, ["/jHxCeXnSchAuwHnmVatTgqMYdX8.jpg", "/ac0kRKTfiJ4GcoUfb0XIO5vgC8q.jpg",
                                "/uyrOU4BDm2kbVxFsMiDFIHDhc4d.jpg", "/1ntePsIqeklfmrQJqZPncCydsqY.jpg",
                                "/jbthbh0KzaUWFPYvkfmXAamjI8j.jpg"]),
}


def scene_paths(uid, picks):
    meta = json.load(open(os.environ.get("CAND_META", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library", "art", "scene_candidates.json"))))
    return [meta[uid]["backdrops"][i][1] for i in picks]


PICKS = {"middleearth": (MiddleEarth, [1, 7, 0, 2, 11]), "wizarding": (WizardingWorld, [14, 3, 17, 19]),
         "starwars": (StarWars, [1, 13, 17, 19, 5]), "johnwick": (WorldOfJohnWick, [1, 5, 7, 6])}


def render(uid, out_dir):
    if uid in MARKS:
        cls, paths = MARKS[uid]
    else:
        cls, picks = PICKS[uid]
        paths = scene_paths(uid, picks)
    mark = cls()
    sc = scenes(paths)
    n = mark.build + mark.hold
    frames = []
    for i in range(n):
        t = min(1, i / mark.build)
        h = (i - mark.build) / mark.hold if i >= mark.build else None
        bg = background(sc, i / n).convert("RGBA")
        bg.alpha_composite(mark(t, h))
        frames.append(bg.convert("RGB"))
    d = os.path.join(out_dir, uid)
    os.makedirs(d, exist_ok=True)
    cov = vignette(art.zoomed(sc[0], 0.04)).convert("RGBA")
    cov.alpha_composite(mark(1.0, 0.75))
    cov.convert("RGB").save(os.path.join(d, "cover.jpg"), quality=90)
    art.graded(art.fetch(paths[0]), 0.95, 1.03, (1920, 1080)).save(os.path.join(d, "backdrop.jpg"), quality=88)
    small = [f.resize((GW, GH), Image.LANCZOS) for f in frames]
    pal = Image.new("RGB", (GW, GH * 4))
    for j, idx in enumerate((n // 5, mark.build, mark.build + mark.hold // 2, n - 1)):
        pal.paste(small[idx], (0, GH * j))
    pal = pal.convert("P", palette=Image.ADAPTIVE, colors=128)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in small]
    q[0].save(os.path.join(d, "hover.gif"), save_all=True, append_images=q[1:],
              duration=[60] * mark.build + [95] * mark.hold, loop=0, optimize=True)
    strip = Image.new("RGB", (GW * 4, GH * 2))
    for j, idx in enumerate([round(k * (n - 1) / 7) for k in range(8)]):
        strip.paste(small[idx], ((j % 4) * GW, (j // 4) * GH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return d, os.path.getsize(os.path.join(d, "hover.gif")) // 1024


if __name__ == "__main__":
    out = sys.argv[1]
    for uid in sys.argv[2:] or list(MARKS) + list(PICKS):
        try:
            print("built", *render(uid, out), "KB")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", uid, e)
