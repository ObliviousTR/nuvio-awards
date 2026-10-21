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
GW, GH = 480, 270
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
    b = get("https://raw.githubusercontent.com/google/fonts/main/" + FONTS[name])
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


def tmdb_logo(movie_id=None, path=None):
    """A TMDB logo: a given file path, or the movie's best-voted English PNG (SVG logos are skipped)."""
    if not path:
        im = tmdb(f"/movie/{movie_id}/images", include_image_language="en") or {}
        lg = sorted([x for x in im.get("logos", []) if x.get("iso_639_1") == "en" and x["file_path"].endswith(".png")],
                    key=lambda x: -x["vote_average"])
        path = lg[0]["file_path"]
    return trim(Image.open(io.BytesIO(get("https://image.tmdb.org/t/p/original" + path))).convert("RGBA"))


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


def key_black(im, lo=40, hi=110):
    """Logos delivered on a black plate: brightness becomes transparency."""
    im = im.convert("RGBA")
    l = im.convert("L").point(lambda v: 0 if v < lo else (255 if v > hi else round(255 * (v - lo) / (hi - lo))))
    im.putalpha(ImageChops.multiply(im.getchannel("A"), l))
    return im


def blocks(im, gap=0.015, thr=10):
    """Vertical text blocks of a logo (rows of ink separated by empty rows): [(y0, y1), ...]."""
    a = im.getchannel("A").resize((1, im.height), Image.BOX)
    rows = [v > thr for v in a.getdata()]
    out, y, g = [], 0, max(2, int(im.height * gap))
    while y < len(rows):
        if rows[y]:
            y0 = y
            while y < len(rows) and (rows[y] or any(rows[y:y + g])):
                y += 1
            out.append((y0, y))
        y += 1
    return out


def line_of(im, which, thr=10):
    b = blocks(im, thr=thr)
    y0, y1 = b[which]
    return trim(im.crop((0, y0, im.width, y1)))


def fit(im, maxw, maxh):
    k = min(maxw / im.width, maxh / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def alpha(im, a):
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: round(v * max(0, min(1, a)))))
    return im


def comp(cv, im, x, y):
    """alpha_composite that accepts offsets partly or fully outside the canvas."""
    x, y = round(x), round(y)
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, cv.width - x), min(im.height, cv.height - y)
    if r <= l or b <= t:
        return
    cv.alpha_composite(im.crop((l, t, r, b)), (x + l, y + t))


def place(cv, im, cx, cy, a=1.0):
    if a <= 0:
        return
    comp(cv, alpha(im, a) if a < 1 else im, cx - im.width / 2, cy - im.height / 2)


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


class Mark2(Mark):
    """Second-batch base: self.i is the global frame index (set by render), finish() adds the sweep + tagline."""
    i = 0
    tag, tagcol, tag_y = "", (255, 255, 255), H / 2 + 200

    def finish(self, cv, t, h, sweep_strength=120):
        if h is not None and h < 0.5:
            sweep(cv, h * 2, strength=sweep_strength)
        if t > 0.85 and self.tag:
            tagline(cv, self.tag, self.tag_y, (t - 0.85) / 0.15, color=self.tagcol)
        return cv


def spider(size, col=(255, 255, 255, 255)):
    """Our spider emblem (body + eight bent legs), drawn at 4x and scaled down for smooth edges."""
    k = 4
    S = 220 * k
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    P = lambda x, y: (c + x * k, c + y * k)
    legs = [[(-9, -24), (-38, -52), (-46, -96)], [(-12, -15), (-56, -26), (-76, -64)],
            [(-12, -3), (-56, 10), (-74, 52)], [(-9, 8), (-40, 38), (-46, 92)]]
    for leg in legs:
        for sx in (1, -1):
            pts = [P(x * sx, y) for x, y in leg]
            d.line(pts[:2], fill=col, width=9 * k)
            d.ellipse((pts[1][0] - 4.5 * k, pts[1][1] - 4.5 * k, pts[1][0] + 4.5 * k, pts[1][1] + 4.5 * k), fill=col)
            # tapering lower leg ending in a point
            (x0, y0), (x1, y1) = pts[1], pts[2]
            L = math.hypot(x1 - x0, y1 - y0)
            nx, ny = -(y1 - y0) / L, (x1 - x0) / L
            w = 4.5 * k
            d.polygon([(x0 + nx * w, y0 + ny * w), (x1, y1), (x0 - nx * w, y0 - ny * w)], fill=col)
    d.ellipse((*P(-9, -46), *P(9, -30)), fill=col)                 # head
    d.ellipse((*P(-14, -36), *P(14, 2)), fill=col)                 # thorax
    d.polygon([P(-15, 6), P(15, 6), P(10, 46), P(0, 66), P(-10, 46)], fill=col)  # abdomen
    d.ellipse((*P(-16, -4), *P(16, 30)), fill=col)
    im = trim(im)
    return fit(im.resize((im.width // k, im.height // k), Image.LANCZOS), size, size)


def comic_word(text, size, fill, outline=(10, 10, 14), ow=7, dots=True):
    """Comic lettering: Bangers, a heavy dark outline, halftone dots fading down the letters."""
    f = font("bangers", size)
    base = text_layer(text, f, (255, 255, 255), 4)
    p = padded(base, ow + 4)
    a = p.getchannel("A")
    body = Image.new("RGBA", p.size, fill + (0,))
    body.putalpha(a)
    if dots:
        ht = Image.new("L", p.size, 0)
        dd = ImageDraw.Draw(ht)
        for y in range(0, p.height, 9):
            r = 3.2 * (y / p.height) ** 1.2
            for x in range((y // 9) % 2 * 4, p.width, 9):
                dd.ellipse((x - r, y - r, x + r, y + r), fill=110)
        shade = Image.new("RGBA", p.size, (0, 0, 0, 0))
        shade.putalpha(ImageChops.multiply(ht, a))
        body.alpha_composite(shade)
    edge = Image.new("RGBA", p.size, outline + (0,))
    edge.putalpha(a.filter(ImageFilter.MaxFilter(ow * 2 + 1)))
    edge.alpha_composite(body)
    return edge


class SpiderVerse(Mark2):
    """A spider drops in on its thread from the top of the card and twitches between universes; SPIDER-VERSE slams
    together out of red and blue misprints in comic lettering."""
    build, hold = 34, 30
    tag, tagcol = "EVERY SPIDER  ·  EVERY UNIVERSE", (255, 255, 255)

    def __init__(self):
        FONTS["bangers"] = "ofl/bangers/Bangers-Regular.ttf"
        self.face = comic_word("SPIDER-VERSE", 178, (232, 30, 44))
        self.red = comic_word("SPIDER-VERSE", 178, (255, 40, 80), outline=(255, 40, 80), dots=False)
        self.blue = comic_word("SPIDER-VERSE", 178, (30, 140, 255), outline=(30, 140, 255), dots=False)
        self.sp = spider(150)
        self.sp_r = tint(self.sp, (255, 30, 60), 1.0)
        self.sp_b = tint(self.sp, (30, 150, 255), 1.0)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wy = H / 2 + 60
        sy_end = wy - self.face.height / 2 - self.sp.height / 2 - 18
        # the drop: falls fast, overshoots, settles; a slow sway afterwards
        p = min(1, t / 0.4)
        y = -self.sp.height + (sy_end + self.sp.height) * (1 - (1 - p) ** 3) + (math.sin(p * math.pi * 2.2) * 26 * (1 - p) if p < 1 else 0)
        sway = math.sin(self.i * 0.35) * (6 if t < 0.6 else 3)
        sp = self.sp.rotate(sway, resample=Image.BICUBIC, expand=True)
        thread = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(thread).line((W / 2, 0, W / 2 + sway * 2, y - self.sp.height / 2 + 14), fill=(255, 255, 255, 190), width=2)
        cv.alpha_composite(thread)
        rnd = random.Random(self.i * 31)
        twitch = (h is not None and int(h * 40) % 9 == 0) or (0.42 < t < 0.5)
        if twitch:
            dx = rnd.choice((-1, 1)) * rnd.uniform(6, 14)
            place(cv, alpha(self.sp_b, 0.85), W / 2 + dx, y + 3)
            place(cv, alpha(self.sp_r, 0.85), W / 2 - dx, y - 3)
        place(cv, glow(padded(sp, 20), 10, (255, 255, 255), 0.5), W / 2, y)
        place(cv, sp, W / 2, y)
        # the word: misprints converge, then the inked face lands
        k = max(0, min(1, (t - 0.3) / 0.5))
        e = ease(k)
        off = 7 + (1 - e) * 120

        def put(layer, dx, dy, a):
            if a <= 0:
                return
            l = alpha(layer, a)
            if k < 1:
                sl = Image.new("RGBA", l.size, (0, 0, 0, 0))
                for yy in range(0, l.height, 14):
                    sl.paste(l.crop((0, yy, l.width, min(l.height, yy + 14))), (round(rnd.uniform(-1, 1) * 40 * (1 - e)), yy))
                l = sl
            place(cv, l, W / 2 + dx, wy + dy)
        a = min(1, max(0, (t - 0.25) / 0.2))
        if twitch and h is not None:
            off = 14
        put(self.blue, off, off * 0.15, a)
        put(self.red, -off, -off * 0.15, a)
        put(self.face, 0, 0, max(0, (t - 0.55) / 0.2) if t < 0.75 else 1)
        self.tag_y = wy + self.face.height / 2 + 30
        return self.finish(cv, t, h)


class MiddleEarth(Mark):
    """A gold ring glows up out of fire, then MIDDLE-EARTH burns in letter by letter like heated metal."""
    build, hold = 30, 26

    def __init__(self):
        f = font("cinzel", 112, weight=800)
        base = text_layer("MIDDLE-EARTH", f, (255, 255, 255), 14)
        self.word = gradient_fill(base, (255, 226, 150), (176, 120, 40))
        self.hot = gradient_fill(base, (255, 250, 220), (255, 150, 40))
        self.tag = "THE LORD OF THE RINGS  ·  THE HOBBIT"
        self.rings = [fit(trim(f), 230, 230) for f in sticker("jU8YU7i8WJFLMMDrEb")]

    def ring(self, spin, heat):
        """A thick gold band seen at an angle: filled ellipse minus the hole, lit from above, glowing hot."""
        s = 420
        squash = 0.42 + 0.12 * math.cos(spin)
        rx, ry = 170, 170 * squash
        th = 42  # band thickness
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
        idx = int((t * 30 if h is None else 30 + h * 26)) % len(self.rings)
        r0 = self.rings[idx]
        ring = Image.new("RGBA", (r0.width + 80, r0.height + 80), (0, 0, 0, 0))
        ring.alpha_composite(glow(padded(r0, 40), 24, (255, 120, 20), 1.4 * heat))
        ring.alpha_composite(r0, (40, 40))
        ry = H / 2 - 120 if t > 0.45 else H / 2 - 120 + (1 - ease(t / 0.45)) * 120
        place(cv, ring, W / 2, ry, min(1, t / 0.2))
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
        def solid(f):  # the sticker opens on a white placeholder card: a filled box, not a line drawing
            bb = f.getchannel("A").getbbox()
            if not bb:
                return True
            a = f.getchannel("A").crop(bb).resize((40, 40))
            return sum(1 for v in a.getdata() if v > 200) > 1000
        fr = [f for f in sticker("L2lkyiSIYFq6f4gAqq") if not solid(f)]
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
        self.logo = trim(key_black(commons("File:Star Wars Logo.svg")))
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
        self.main = fit(tmdb_logo(path="/77YSn1XL3KFDcmIQGWE0Y0Tj7jB.png"), 760, 210)
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
        place(cv, self.neon(self.top, self.cols[1], on_top), W / 2, H / 2 + 30 - self.main.height / 2 - 52)
        place(cv, self.neon(self.main, self.cols[0], on_main), W / 2, H / 2 + 30)
        return cv


# ---------------------------------------------------------------- shared helpers for the second batch
def clip(gid, a=0, b=None, maxw=640, maxh=300, keep=None):
    """Sticker frames a..b, cropped to one common box (so the motion inside the sticker is kept) and scaled."""
    fr = sticker(gid)[a:b]
    if keep:
        fr = [f for f in fr if keep(f)]
    bb = None
    for f in fr:
        x = f.getchannel("A").getbbox()
        if x:
            bb = x if bb is None else (min(bb[0], x[0]), min(bb[1], x[1]), max(bb[2], x[2]), max(bb[3], x[3]))
    fr = [f.crop(bb) for f in fr]
    k = min(maxw / fr[0].width, maxh / fr[0].height)
    return [f.resize((round(f.width * k), round(f.height * k)), Image.LANCZOS) for f in fr]


def stops_fill(layer, stops):
    w, h = layer.size
    g = Image.new("RGBA", (w, h))
    for y in range(h):
        f = y / max(1, h - 1)
        c = stops[-1][1]
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= f <= b:
                k = (f - a) / max(1e-6, b - a)
                c = tuple(round(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
                break
        g.paste(c + (255,), (0, y, w, y + 1))
    g.putalpha(layer.getchannel("A"))
    return g


CHROME = [(0, (255, 255, 255)), (0.44, (196, 200, 210)), (0.5, (72, 78, 90)), (0.64, (150, 156, 168)), (1, (238, 242, 248))]
STEEL = [(0, (246, 247, 250)), (0.5, (176, 180, 190)), (1, (110, 114, 124))]


def shear(layer, k=0.22):
    w, h = layer.size
    return layer.transform((w + round(k * h), h), Image.AFFINE, (1, k, -k * h, 0, 1, 0), resample=Image.BICUBIC)


def hblur(im, r):
    if r < 2:
        return im
    return im.resize((max(1, im.width // r), im.height), Image.BILINEAR).resize(im.size, Image.BILINEAR)


def tint(im, col, k):
    lay = Image.new("RGBA", im.size, col + (255,))
    out = Image.blend(im.convert("RGBA"), lay, k)
    out.putalpha(im.getchannel("A"))
    return out


def bright(im, k):
    out = ImageEnhance.Brightness(im.convert("RGB")).enhance(k).convert("RGBA")
    out.putalpha(im.getchannel("A"))
    return out


def noise(size, blur=0, seed=1):
    random.seed(seed)
    n = Image.effect_noise(size, 90)
    if blur:
        n = n.filter(ImageFilter.GaussianBlur(blur))
    from PIL import ImageOps
    return ImageOps.autocontrast(n)


def dissolve(layer, p, nz, soft=28):
    """Reveal a layer through a noise threshold (p 0..1)."""
    th = p * (255 + soft)
    m = nz.resize(layer.size).point(lambda v: max(0, min(255, round((th - v) / soft * 255))))
    out = layer.copy()
    out.putalpha(ImageChops.multiply(layer.getchannel("A"), m))
    return out


def vwipe(layer, p, soft=40, up=True):
    """Reveal bottom-to-top (up) or top-to-bottom."""
    w, h = layer.size
    m = Image.new("L", (1, h), 0)
    edge = -soft + p * (h + 2 * soft)
    for y in range(h):
        d = (h - y) if up else y
        m.putpixel((0, y), round(255 * max(0, min(1, (edge - d) / soft))))
    m = m.resize((w, h))
    out = layer.copy()
    out.putalpha(ImageChops.multiply(layer.getchannel("A"), m))
    return out


def flash(cv, a, col=(255, 255, 255)):
    if a > 0:
        cv.alpha_composite(Image.new("RGBA", (W, H), col + (round(255 * min(1, a)),)))


def cands(uid):
    meta = json.load(open(os.environ.get("CAND_META", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library", "art", "scene_candidates.json"))))
    return [b[1] for b in meta[uid]["backdrops"]]


class MCU(Mark2):
    """The Marvel Studios opening: flips through the saga's scenes washing red, then the logo lands."""
    build, hold = 36, 30
    dur_build = 85
    tag, tag_y = "THE INFINITY SAGA  ·  THE MULTIVERSE SAGA", H / 2 + 95

    def __init__(self):
        self.logo = clip("dC3uDJazzlM4z3lZJ5", maxw=780, maxh=200)
        self.flip = [ImageEnhance.Brightness(art.graded(art.fetch(p), 0.9, 1.05)).enhance(0.8) for p in cands("mcu")]
        self.red = Image.new("RGB", (W, H), (200, 18, 30))

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < 0.62:
            step = self.i // 3  # each page held for 3 frames
            rnd = random.Random(step)
            im = art.zoomed(self.flip[step % len(self.flip)], rnd.uniform(0.05, 0.3))
            red = min(0.75, t / 0.62 * 0.9)
            fr = Image.blend(im, self.red, red)
            cv.paste(fr.convert("RGBA"), (0, 0))
            cv.putalpha(round(255 * (1 - max(0, (t - 0.5) / 0.12))))
        if t > 0.5:
            k = ease((t - 0.5) / 0.2)
            idx = 0 if h is None else int(h * 24) % len(self.logo)
            lg = self.logo[idx]
            s = 1.35 - 0.35 * k
            lg = lg.resize((round(lg.width * s), round(lg.height * s)), Image.LANCZOS)
            place(cv, glow(padded(lg, 40), 30, (230, 30, 50), 0.9 * k), W / 2, H / 2 - 10, 1)
            place(cv, lg, W / 2, H / 2 - 10, k)
        return self.finish(cv, t, h, 90)


class DCU(Mark2):
    """The DC bullet spins in out of the dark, settles and catches the light."""
    build, hold = 30, 30
    tag, tagcol, tag_y = "SUPERMAN  ·  BATMAN  ·  WONDER WOMAN  ·  JUSTICE LEAGUE", (225, 235, 255), H / 2 + 215

    def __init__(self):
        self.spin = clip("46zn5FmNndXaJVjgdG", maxw=360, maxh=360)
        self.shine = clip("ensd2k3UXTw2ErdEet", maxw=360, maxh=360)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if h is None:
            n = len(self.spin)
            lg = self.spin[min(n - 1, int(ease(t / 0.9) * (n - 1)))] if t < 0.9 else self.spin[-1]
        else:
            lg = self.shine[min(len(self.shine) - 1, int(h / 0.6 * len(self.shine)))] if h < 0.6 else self.shine[-1]
        s = 0.55 + 0.45 * ease(t / 0.8)
        lg = lg.resize((round(lg.width * s), round(lg.height * s)), Image.LANCZOS)
        place(cv, glow(padded(lg, 50), 34, (0, 120, 255), 1.1), W / 2, H / 2 - 30, min(1, t / 0.2))
        place(cv, lg, W / 2, H / 2 - 30, min(1, t / 0.15))
        self.tag_y = H / 2 - 30 + 180 + 40
        if t > 0.85:
            tagline(cv, self.tag, self.tag_y, (t - 0.85) / 0.15, size=22, color=self.tagcol)
        if h is not None and h < 0.5:
            pass  # the sticker's own shine is the sweep
        return cv


class BatmanGotham(Mark2):
    """THE BATMAN title card (its own animated sticker) cuts in over a red bat-signal glow; lightning once."""
    build, hold = 34, 30
    tag, tagcol = "BATMAN  ·  GOTHAM  ·  JOKER  ·  THE PENGUIN", (235, 200, 200)

    def __init__(self):
        self.fr = clip("st8Zsj32VefZ4mBlPZ", maxw=860, maxh=320)
        self.fog = clip("erg5dWNomXlY8K4sxu", maxw=620, maxh=560)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, round(90 * (1 - ease(t / 0.4)))))
        fg = self.fog[0 if h is not None else self.i % len(self.fog)]
        place(cv, tint(fg, (200, 20, 20), 0.55), W / 2, H / 2 - 30, 0.32 * ease(t / 0.5))
        n = len(self.fr)
        lg = self.fr[min(n - 1, int(ease(min(1, t / 0.85)) * (n - 1)))]
        a = min(1, t / 0.12)
        place(cv, glow(padded(lg, 40), 30, (255, 20, 20), 0.8 * a), W / 2, H / 2 - 20, 1)
        place(cv, lg, W / 2, H / 2 - 20, a)
        flash(cv, 0.45 if 0.5 < t < 0.54 else 0, (230, 235, 255))
        self.tag_y = H / 2 - 20 + lg.height / 2 + 40
        return self.finish(cv, t, h, 100)


class XMen(Mark2):
    """The X-Men '97 opening logo, stopped before the '97: the X spins in and the name locks beside it."""
    build, hold = 34, 26
    tag, tag_y = "X-MEN  ·  WOLVERINE  ·  DEADPOOL", H / 2 + 175

    def __init__(self):
        self.fr = clip("0sifJvGCjI0tXVcnhM", 0, 36, maxw=900, maxh=420)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        n = len(self.fr)
        lg = self.fr[min(n - 1, int(t / 0.85 * (n - 1)))]
        place(cv, glow(padded(lg, 40), 26, (255, 150, 20), 0.7), W / 2, H / 2 - 20, 1)
        place(cv, lg, W / 2, H / 2 - 20, 1)
        return self.finish(cv, t, h)


class Dune(Mark2):
    """The DUNE glyphs ignite out of a sand blast (the film's own sticker), warmed to spice gold."""
    build, hold = 34, 26
    tag, tagcol, tag_y = "THE SPICE MUST FLOW", (240, 205, 150), H / 2 + 105

    def __init__(self):
        fr = clip("V5EflugpxzxrYL0MEE", 2, 52, maxw=820, maxh=200)
        self.fr = [bright(tint(f, (245, 200, 130), 0.45), 1.35) for f in fr]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        n = len(self.fr)
        lg = self.fr[min(n - 1, int(t / 0.9 * (n - 1)))]
        place(cv, glow(padded(lg, 40), 22, (255, 150, 60), 0.9), W / 2, H / 2, 1)
        place(cv, lg, W / 2, H / 2, 1)
        return self.finish(cv, t, h)


class StarTrek(Mark2):
    """Out of warp: star streaks snap to points, the Starfleet delta glints in, STAR TREK settles under it."""
    build, hold = 30, 30
    tag, tagcol = "TO BOLDLY GO", (200, 220, 255)

    def __init__(self):
        self.delta = clip("JtBbQlcLJHdCCeKM4O", maxw=200, maxh=250)
        self.logo = fit(tmdb_logo(path="/7uaXgLu3hkkS7ci0l0tc9SPHfER.png"), 640, 110)
        rnd = random.Random(11)
        self.stars = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(30, 900), rnd.uniform(0.4, 1)) for _ in range(220)]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, round(150 * (1 - min(1, t / 0.6)))))
        d = ImageDraw.Draw(cv)
        warp = max(0, 1 - t / 0.45)
        for a, r, s in self.stars:
            rr = r * (1 + 0.8 * (1 - warp))
            x, y = W / 2 + rr * math.cos(a), H / 2 + rr * 0.6 * math.sin(a)
            L = 220 * warp * s
            x0, y0 = W / 2 + (rr - L) * math.cos(a), H / 2 + (rr - L) * 0.6 * math.sin(a)
            d.line((x0, y0, x, y), fill=(220, 230, 255, round(220 * s * (0.6 + 0.4 * warp))), width=2 if warp > 0.1 else 1)
        k = ease((t - 0.35) / 0.3)
        if k > 0:
            dl = self.delta[self.i % len(self.delta)]
            place(cv, glow(padded(dl, 40), 22, (255, 190, 80), 0.8 * k), W / 2, H / 2 - 95, 1)
            place(cv, dl, W / 2, H / 2 - 95, k)
        p = max(0, (t - 0.55) / 0.35)
        if p > 0:
            lg = self.logo
            place(cv, wipe(lg, p, soft=120), W / 2, H / 2 + 105)
        self.tag_y = H / 2 + 105 + self.logo.height / 2 + 34
        return self.finish(cv, t, h)


class MissionImpossible(Mark2):
    """The fuse: a spark races in from the edge along a burning line and lights the M:I mark."""
    build, hold = 30, 30
    tag, tag_y = "MISSION: IMPOSSIBLE", H / 2 + 150

    def __init__(self):
        self.fr = clip("Znclz38sX4JBsdUvX3", maxw=720, maxh=300)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(cv)
        cy = H / 2 - 20
        p = min(1, t / 0.5)
        x = -40 + ease(p) * (W / 2 + 40)
        if t < 0.55:
            trail = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(trail).line((0, cy, x, cy), fill=(255, 140, 40, 230), width=4)
            cv.alpha_composite(glow(trail, 8, (255, 120, 30), 1.5))
            cv.alpha_composite(trail)
            rnd = random.Random(self.i)
            for _ in range(14):
                dx, dy = rnd.uniform(-30, 10), rnd.uniform(-22, 22)
                d.line((x, cy, x + dx, cy + dy), fill=(255, 230, 160, 230), width=2)
            d.ellipse((x - 9, cy - 9, x + 9, cy + 9), fill=(255, 250, 220, 255))
        k = ease((t - 0.45) / 0.2)
        if k > 0:
            lg = self.fr[self.i % len(self.fr)]
            place(cv, glow(padded(lg, 40), 26, (255, 60, 20), 0.8 * k), W / 2, cy, 1)
            place(cv, lg, W / 2, cy, k)
        flash(cv, max(0, 0.5 - abs(t - 0.5) * 6))
        return self.finish(cv, t, h)


class JurassicPark(Mark2):
    """Lightning over the gate: the logo comes out of the dark as a silhouette, warms to full colour, then shines."""
    build, hold = 30, 30
    tag, tagcol, tag_y = "JURASSIC PARK  ·  JURASSIC WORLD", (245, 225, 170), H / 2 + 215

    def __init__(self):
        self.fr = clip("3ohzdPbvIlusvgwaQw", maxw=520, maxh=360)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lg = self.fr[0] if h is None or h > 0.5 else self.fr[min(len(self.fr) - 1, int(h / 0.5 * len(self.fr)))]
        lit = ease((t - 0.2) / 0.6)
        im = bright(lg, 0.05 + 0.95 * lit)
        yy = H / 2 - 20 + (1 - ease(t / 0.7)) * 40
        place(cv, glow(padded(lg, 50), 30, (255, 170, 40), 0.9 * (1 - 0.4 * lit)), W / 2, yy, min(1, t / 0.15))
        place(cv, im, W / 2, yy, min(1, t / 0.15))
        flash(cv, (0.55 if 0.12 < t < 0.18 else 0) + (0.3 if 0.24 < t < 0.27 else 0), (225, 235, 255))
        if t > 0.85:
            tagline(cv, self.tag, self.tag_y, (t - 0.85) / 0.15, color=self.tagcol)
        return cv


class Transformers(Mark2):
    """The logo assembles itself: horizontal plates slide in from both sides and lock, then a metal glint."""
    build, hold = 30, 30
    tag, tagcol = "MORE THAN MEETS THE EYE", (255, 190, 90)

    def __init__(self):
        self.logo = fit(tmdb_logo(1858), 860, 220)
        n = 9
        h = self.logo.height
        self.plates = [(self.logo.crop((0, round(h * j / n), self.logo.width, round(h * (j + 1) / n))), round(h * j / n)) for j in range(n)]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay = Image.new("RGBA", self.logo.size, (0, 0, 0, 0))
        for j, (pl, y) in enumerate(self.plates):
            e = ease((t - j * 0.04) / 0.5)
            dx = (1 - e) * W * 0.7 * (1 if j % 2 else -1)
            comp(lay, alpha(pl, min(1, e * 3)), dx, y)
        place(cv, glow(padded(lay, 40), 26, (60, 140, 255), 0.7), W / 2, H / 2 - 20, 1)
        place(cv, lay, W / 2, H / 2 - 20)
        self.tag_y = H / 2 - 20 + self.logo.height / 2 + 44
        return self.finish(cv, t, h, 160)


class Matrix(Mark2):
    """Digital rain; the logo decodes column by column out of it, green first, then its own colour."""
    build, hold = 32, 28
    tag, tagcol = "FREE YOUR MIND", (140, 255, 160)
    CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789Z:."

    def __init__(self):
        FONTS["jp"] = "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
        f = font("jp", 22, weight=500)
        self.cw = 22
        self.glyph = {}
        for c in self.CHARS:
            g = Image.new("L", (26, 30), 0)
            ImageDraw.Draw(g).text((2, 0), c, font=f, fill=255)
            for lv in range(1, 9):
                for head in (0, 1):
                    lay = Image.new("RGBA", g.size, ((235, 255, 235) if head else (40, 255, 90)) + (0,))
                    lay.putalpha(g.point(lambda q, v=lv / 8: round(q * v)))
                    self.glyph[c, lv, head] = lay
        rnd = random.Random(5)
        self.cols = [(rnd.uniform(16, 34), rnd.uniform(0, 900), rnd.randint(8, 20)) for _ in range(W // self.cw + 1)]
        self.logo = fit(tmdb_logo(603), 760, 230)
        self.green = Image.new("RGBA", self.logo.size, (130, 255, 150, 0))
        self.green.putalpha(self.logo.getchannel("A"))
        self.delay = [rnd.uniform(0.25, 0.7) for _ in range(self.logo.width // 16 + 1)]

    def rain(self, a):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fi = self.i if self.i < self.build else self.i // 3 * 3  # the rain ticks slower once the logo is up
        rnd = random.Random(fi * 7)
        for c, (sp, off, L) in enumerate(self.cols):
            head = (off + sp * fi) % (H + L * 26 + 200) - 100
            for k in range(L):
                y = head - k * 26
                lv = round(8 * a * (1 - k / L) ** 1.3)
                if -30 < y < H and lv > 0:
                    comp(im, self.glyph[rnd.choice(self.CHARS), lv, int(k == 0)], c * self.cw, y)
        return im.transpose(Image.FLIP_LEFT_RIGHT)

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, round(120 * (1 - (h or 0) * 0.5))))
        r = self.rain(1.0 if h is None else 0.85 - 0.45 * h)
        cv.alpha_composite(glow(r, 6, (40, 255, 90), 0.6))
        cv.alpha_composite(r)
        m = Image.new("L", self.logo.size, 0)
        for j, dl in enumerate(self.delay):
            v = round(255 * max(0, min(1, (t - dl) / 0.1)))
            m.paste(v, (j * 16, 0, (j + 1) * 16, self.logo.height))
        g = self.green.copy()
        g.putalpha(ImageChops.multiply(g.getchannel("A"), m))
        place(cv, glow(padded(g, 40), 18, (60, 255, 110), 1.0), W / 2, H / 2 - 10)
        place(cv, g, W / 2, H / 2 - 10)
        k = ease((t - 0.75) / 0.25)
        if k > 0:
            place(cv, self.logo, W / 2, H / 2 - 10, k)
        self.tag_y = H / 2 - 10 + self.logo.height / 2 + 44
        return self.finish(cv, t, h, 100)


class Terminator(Mark2):
    """Terminator vision: the frame goes red, a scan line reads the logo in under a HUD, a last glitch, locked."""
    build, hold = 32, 28
    tag, tagcol = "I'LL BE BACK", (255, 90, 80)

    def __init__(self):
        self.logo = fit(tmdb_logo(path="/ipgDUr7fD8adbqHfCssloIultfN.png"), 820, 200)
        self.hud = font("orbitron", 17, weight=600)

    def __call__(self, t, h):
        red = 1 - ease((t - 0.7) / 0.3)
        cv = Image.new("RGBA", (W, H), (150, 0, 0, round(110 * red)))
        d = ImageDraw.Draw(cv)
        lw, lh = self.logo.size
        x0, y0, x1, y1 = W / 2 - lw / 2 - 30, H / 2 - 20 - lh / 2 - 26, W / 2 + lw / 2 + 30, H / 2 - 20 + lh / 2 + 26
        ba = round(230 * (0.35 + 0.65 * red))
        for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            d.line((x, y, x + 40 * sx, y), fill=(255, 60, 50, ba), width=3)
            d.line((x, y, x, y + 40 * sy), fill=(255, 60, 50, ba), width=3)
        if h is None:
            lines = ["SCAN MODE 43984", "ANALYSIS:", "MATCH  SKYNET", "THREAT ASSESSMENT", "PRIORITY  01"]
            for j, ln in enumerate(lines[:int(t * 8)]):
                d.text((70, 90 + j * 26), ln, font=self.hud, fill=(255, 80, 70, round(220 * red)))
        p = min(1, t / 0.6)
        sy = y0 + p * (y1 - y0)
        m = Image.new("L", self.logo.size, 0)
        if sy > H / 2 - 20 - lh / 2:
            ImageDraw.Draw(m).rectangle((0, 0, lw, sy - (H / 2 - 20 - lh / 2)), fill=255)
        lg = self.logo.copy()
        lg.putalpha(ImageChops.multiply(lg.getchannel("A"), m))
        if 0.6 < t < 0.78 and self.i % 2 == 0:
            r = Image.new("RGBA", lg.size, (255, 40, 40, 0)); r.putalpha(lg.getchannel("A"))
            place(cv, r, W / 2 - 12, H / 2 - 20, 0.7)
            place(cv, lg, W / 2 + 8, H / 2 - 20)
        else:
            place(cv, glow(padded(lg, 30), 14, (255, 40, 30), 0.7), W / 2, H / 2 - 20)
            place(cv, lg, W / 2, H / 2 - 20)
        if t < 0.62:
            sc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sc).line((x0 - 60, sy, x1 + 60, sy), fill=(255, 70, 60, 255), width=3)
            cv.alpha_composite(glow(sc, 10, (255, 40, 30), 2.0))
            cv.alpha_composite(sc)
        self.tag_y = y1 + 40
        return self.finish(cv, t, h)


class Conjuring(Mark2):
    """Candlelight in a dark room: the title flickers into being, then a camera flash burns it in."""
    build, hold = 30, 30
    tag, tagcol = "THE CONJURING UNIVERSE  ·  INSIDIOUS", (225, 215, 200)

    def __init__(self):
        self.logo = fit(tmdb_logo(path="/5qjvxFhRZtvm4mcV90X9QNYLZVj.png"), 760, 200)

    def __call__(self, t, h):
        dark = 1 - 0.6 * ease((t - 0.68) / 0.2)
        cv = Image.new("RGBA", (W, H), (0, 0, 0, round(170 * dark)))
        rnd = random.Random(self.i * 13)
        if t < 0.68:
            a = min(1, t / 0.6) * (0.35 + 0.65 * rnd.random()) * 0.6
        else:
            a = 1.0 if h is None else (0.86 + 0.14 * rnd.random())
        place(cv, glow(padded(self.logo, 40), 26, (255, 170, 80), 0.9 * a), W / 2, H / 2 - 20)
        place(cv, self.logo, W / 2, H / 2 - 20, a)
        flash(cv, 0.95 if abs(t - 0.7) < 0.02 else (0.5 if abs(t - 0.73) < 0.02 else (0.2 if abs(t - 0.77) < 0.02 else 0)))
        self.tag_y = H / 2 - 20 + self.logo.height / 2 + 44
        return self.finish(cv, t, h, 90)


class FastSaga(Mark2):
    """THE FAST SAGA in raked chrome, launched in from the right on speed streaks, braking hard into place."""
    build, hold = 26, 34
    tag, tagcol = "IT'S ALL ABOUT FAMILY", (230, 235, 245)

    def __init__(self):
        self.main = stops_fill(fit(line_of(tmdb_logo(path="/3qNMg9iQmg3V2UHpxJCRHjsMTMV.png"), -1), 960, 170), CHROME)
        rnd = random.Random(9)
        self.lines = [(rnd.uniform(0, H), rnd.uniform(200, 700), rnd.uniform(0.3, 1)) for _ in range(40)]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        e = ease(t / 0.55)
        speed = 1 - e
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        place(lay, self.main, W / 2, H / 2 + 20)
        lay = hblur(lay, round(1 + speed * 26))
        dx = round(speed * W * 0.9)
        comp(cv, glow(lay, 22, (60, 140, 255), 0.6), dx, 0)
        comp(cv, lay, dx, 0)
        d = ImageDraw.Draw(cv)
        for (y, L, s) in self.lines:
            a = round(200 * s * max(0, speed - 0.05))
            if a:
                x = ((self.i * 140 * s + y * 7) % (W + L)) - L
                d.line((W - x, y, W - x - L, y), fill=(255, 255, 255, a), width=2)
        self.tag_y = H / 2 + 20 + self.main.height / 2 + 40
        return self.finish(cv, t, h, 170)


class MadMaxSaga(Mark2):
    """A dust storm blows across and leaves MAD MAX burned into the frame in rusted, sun-cracked letters."""
    build, hold = 30, 30
    tag, tagcol = "FURY ROAD  ·  FURIOSA  ·  THE ROAD WARRIOR", (245, 210, 160)

    def __init__(self):
        small = font("bebas", 64)
        lg = tmdb_logo(path="/cBAO0i9fZCux5SqJnizRECS8qfU.png")
        for thr in (10, 30, 60, 90):  # stop once FURY ROAD has come off: MAD MAX alone is a wide line
            word = line_of(lg, 0, thr)
            if word.width / word.height > 3.6:
                break
        self.word = fit(word, 900, 230)
        self.saga = stops_fill(text_layer("S A G A", small, (255, 255, 255), 22), [(0, (250, 230, 200)), (1, (220, 170, 120))])
        self.nz = noise((240, 80), 3, 4)
        rnd = random.Random(2)
        self.dust = [(rnd.uniform(-W, W), rnd.uniform(0, H), rnd.uniform(1, 3.5), rnd.uniform(0.6, 1.4)) for _ in range(260)]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        storm = max(0, 1 - abs(t - 0.4) / 0.4) if h is None else 0
        cv.alpha_composite(Image.new("RGBA", (W, H), (200, 140, 80, round(110 * storm))))
        d = ImageDraw.Draw(cv)
        g = self.i
        for (x, y, r, s) in self.dust:
            xx = (x + g * 60 * s) % (W + 200) - 100
            a = round(200 * (0.25 + storm * 0.75))
            d.ellipse((xx - r, y - r, xx + r, y + r), fill=(235, 190, 130, a))
        p = max(0, (t - 0.25) / 0.6)
        if p > 0:
            w = dissolve(self.word, p, self.nz)
            place(cv, glow(padded(w, 40), 26, (255, 110, 30), 0.9), W / 2, H / 2 - 30)
            place(cv, w, W / 2, H / 2 - 30)
        k = ease((t - 0.7) / 0.25)
        if k > 0:
            place(cv, self.saga, W / 2, H / 2 - 30 + self.word.height / 2 + 46, k)
        self.tag_y = H / 2 - 30 + self.word.height / 2 + 112
        return self.finish(cv, t, h)


def first_line(im):
    """Keep the logo's top line ('INDIANA JONES'), dropping the film subtitle under it."""
    a = im.getchannel("A")
    rows = [sum(a.crop((0, y, im.width, y + 1)).getdata()) for y in range(im.height)]
    top = max(rows)
    cut = next((y for y in range(int(im.height * 0.3), im.height) if rows[y] < 0.12 * top), im.height)
    return trim(im.crop((0, 0, im.width, cut)))


class IndianaJones(Mark2):
    """Torchlight in a tomb: dust drifts through warm, flickering light and the name catches the gold."""
    build, hold = 30, 30
    tag, tagcol = "ADVENTURE HAS A NAME", (245, 215, 150)

    def __init__(self):
        self.logo = fit(trim(commons("File:Indiana Jones logo.svg", 2000)), 820, 220)
        rnd = random.Random(4)
        self.motes = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1, 2.6), rnd.uniform(-1, 1)) for _ in range(50)]

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rnd = random.Random(self.i // 2 * 3)
        torch = 0.75 + 0.25 * rnd.random() if h is None else 0.9  # flickers while it builds, steady after
        lightc = Image.new("L", (W, H), 0)
        ImageDraw.Draw(lightc).ellipse((W / 2 - 520, H / 2 - 330, W / 2 + 520, H / 2 + 300), fill=round(120 * torch * ease(t / 0.5)))
        lay = Image.new("RGBA", (W, H), (255, 150, 50, 0))
        lay.putalpha(lightc.filter(ImageFilter.GaussianBlur(120)))
        cv.alpha_composite(lay)
        d = ImageDraw.Draw(cv)
        for (x, y, r, dx) in (self.motes if h is None else ()):
            yy = (y - self.i * 2.5) % H
            d.ellipse((x + dx * self.i - r, yy - r, x + dx * self.i + r, yy + r), fill=(255, 225, 170, round(150 * torch)))
        k = ease((t - 0.25) / 0.5)
        if k > 0:
            s = 1.08 - 0.08 * k
            lg = self.logo.resize((round(self.logo.width * s), round(self.logo.height * s)), Image.LANCZOS)
            place(cv, glow(padded(lg, 40), 24, (255, 150, 40), 0.9 * torch), W / 2, H / 2 - 20, k)
            place(cv, lg, W / 2, H / 2 - 20, k)
        self.tag_y = H / 2 - 20 + self.logo.height / 2 + 42
        return self.finish(cv, t, h, 150)


class AlienPredator(Mark2):
    """ALIEN assembles out of thin slits as in the 1979 titles; a tri-laser sight crosses the frame and PREDATOR
    locks in under it."""
    build, hold = 34, 26
    tag, tagcol = "ALIEN  ·  PREDATOR  ·  ALIEN VS. PREDATOR", (200, 230, 210)

    def __init__(self):
        self.alien = fit(tmdb_logo(path="/riI33EA1vYQ1szTtMe0NR7TwV1p.png"), 700, 70)
        self.pred = fit(tmdb_logo(path="/6dPMPbU5em2sFzD1uxzQLcuKtLG.png"), 640, 140)
        self.amp = text_layer("&", font("cinzel", 52, weight=500), (220, 220, 220))
        a = self.alien.getchannel("A")
        cols = [a.crop((x, 0, x + 1, a.height)).getbbox() is not None for x in range(a.width)]
        self.letters, x = [], 0
        while x < len(cols):
            if cols[x]:
                s = x
                while x < len(cols) and cols[x]:
                    x += 1
                self.letters.append((s, x))
            x += 1

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ay = H / 2 - 120
        lay = Image.new("RGBA", self.alien.size, (0, 0, 0, 0))
        n = len(self.letters)
        for j, (s, e) in enumerate(self.letters):
            k = ease((t - j * 0.07) / 0.25)
            if k <= 0:
                continue
            seg = self.alien.crop((s, 0, e, self.alien.height))
            hh = max(1, round(seg.height * (0.08 + 0.92 * k)))
            seg = seg.crop((0, (seg.height - hh) // 2, seg.width, (seg.height + hh) // 2))
            lay.alpha_composite(seg, (s, (self.alien.height - hh) // 2))
        place(cv, glow(padded(lay, 30), 14, (160, 255, 190), 0.5), W / 2, ay)
        place(cv, lay, W / 2, ay)
        place(cv, self.amp, W / 2, ay + 72, ease((t - 0.35) / 0.2))
        py = ay + 72 + 100
        p = max(0, (t - 0.4) / 0.45)
        if p > 0:
            lw = self.pred.width
            lx = W / 2 - lw / 2 - 60 + p * (lw + 120)
            m = Image.new("L", self.pred.size, 0)
            if lx > W / 2 - lw / 2:
                ImageDraw.Draw(m).rectangle((0, 0, lx - (W / 2 - lw / 2), self.pred.height), fill=255)
            pr = self.pred.copy()
            pr.putalpha(ImageChops.multiply(pr.getchannel("A"), m.filter(ImageFilter.GaussianBlur(10))))
            place(cv, pr, W / 2, py)
            if p < 1:
                d = ImageDraw.Draw(cv)
                for (dx, dy) in ((0, -12), (-11, 8), (11, 8)):
                    d.ellipse((lx + dx - 5, py + dy - 5, lx + dx + 5, py + dy + 5), fill=(255, 30, 20, 255))
                dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(dots).ellipse((lx - 22, py - 22, lx + 22, py + 22), fill=(255, 40, 20, 200))
                cv.alpha_composite(glow(dots, 14, (255, 30, 20), 1.2))
        self.tag_y = py + self.pred.height / 2 + 44
        return self.finish(cv, t, h)


class GodzillaKong(Mark2):
    """Atomic breath charging: blue light climbs up through the official title, flares, and keeps a slow pulse."""
    build, hold = 30, 30
    tag, tagcol = "LONG LIVE THE KINGS", (170, 215, 255)

    def __init__(self):
        self.word = fit(tmdb_logo(path="/cq6cY20MvUgips57Lj7QY2Vavu2.png"), 560, 330)
        self.hot = gradient_fill(self.word, (210, 240, 255), (60, 160, 255))

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p = min(1, t / 0.6)
        rnd = random.Random(self.i)
        charge = (0.6 + 0.4 * rnd.random()) * ease(p) if h is None else 0.7 + 0.3 * math.sin(h * math.pi * 4)
        hot = vwipe(self.hot, p, soft=60)
        place(cv, glow(padded(self.word, 50), 34, (50, 150, 255), 1.4 * charge), W / 2, H / 2 - 10, min(1, t / 0.3))
        place(cv, self.word, W / 2, H / 2 - 10, ease((t - 0.45) / 0.35))
        place(cv, hot, W / 2, H / 2 - 10, 1 - ease((t - 0.6) / 0.4) * 0.7)
        self.tag_y = H / 2 - 10 + self.word.height / 2 + 44
        return self.finish(cv, t, h)


class PlanetOfTheApes(Mark2):
    """Sunrise over the Forbidden Zone: god rays fan out from behind the title as it rises into the light."""
    build, hold = 30, 30
    tag, tagcol = "APES TOGETHER STRONG", (245, 220, 175)

    def __init__(self):
        self.logo = fit(tmdb_logo(path="/5Jn7FPpVjA8ZxkAmqWMvrZvQJ5b.png"), 560, 280)

    def rays(self, rot, a):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        cx, cy = W / 2, H / 2 - 20
        for j in range(14):
            ang = rot + j * 2 * math.pi / 14
            w = 0.06
            d.polygon([(cx, cy), (cx + 1400 * math.cos(ang - w), cy + 1400 * math.sin(ang - w)),
                       (cx + 1400 * math.cos(ang + w), cy + 1400 * math.sin(ang + w))], fill=round(80 * a))
        m = m.filter(ImageFilter.GaussianBlur(34))
        v = Image.new("L", (W, H), 0)
        ImageDraw.Draw(v).ellipse((cx - 560, cy - 420, cx + 560, cy + 420), fill=255)
        m = ImageChops.multiply(m, v.filter(ImageFilter.GaussianBlur(140)))
        lay = Image.new("RGBA", (W, H), (255, 214, 150, 0))
        lay.putalpha(m)
        return lay

    def __call__(self, t, h):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g = min(self.i, self.build) / (self.build + self.hold)
        cv.alpha_composite(self.rays(g * 0.6, ease(t / 0.6) * (1 if h is None else 0.7)))
        k = ease((t - 0.25) / 0.5)
        if k > 0:
            yy = H / 2 - 20 + (1 - k) * 40
            place(cv, glow(padded(self.logo, 40), 30, (255, 200, 120), 0.8), W / 2, yy, k)
            place(cv, self.logo, W / 2, yy, k)
        self.tag_y = H / 2 - 20 + self.logo.height / 2 + 42
        return self.finish(cv, t, h)


MARKS = {
    "spiderman": (SpiderVerse, ["/jHxCeXnSchAuwHnmVatTgqMYdX8.jpg", "/ac0kRKTfiJ4GcoUfb0XIO5vgC8q.jpg",
                                "/uyrOU4BDm2kbVxFsMiDFIHDhc4d.jpg", "/1ntePsIqeklfmrQJqZPncCydsqY.jpg",
                                "/jbthbh0KzaUWFPYvkfmXAamjI8j.jpg"]),
}


def scene_paths(uid, picks):
    meta = json.load(open(os.environ.get("CAND_META", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library", "art", "scene_candidates.json"))))
    return [meta[uid]["backdrops"][i][1] for i in picks]


PICKS = {"middleearth": (MiddleEarth, [1, 7, 0, 2, 11]), "wizarding": (WizardingWorld, [14, 3, 17, 19]),
         "starwars": (StarWars, [1, 13, 17, 19, 5]), "johnwick": (WorldOfJohnWick, [1, 5, 7, 6]),
         "mcu": (MCU, [1, 2, 4, 7, 9]), "dc": (DCU, [1, 10, 13, 17, 15]), "batman": (BatmanGotham, [0, 9, 11, 13, 15]),
         "xmen": (XMen, [6, 11, 17, 20, 21]), "dune": (Dune, [1, 3, 4, 2, 5]), "startrek": (StarTrek, [2, 16, 24, 21, 13]),
         "mi": (MissionImpossible, [1, 5, 2, 11, 14]), "jurassic": (JurassicPark, [3, 2, 9, 11, 13]),
         "transformers": (Transformers, [1, 3, 9, 14, 10]), "matrix": (Matrix, [4, 7, 2, 6]),
         "terminator": (Terminator, [0, 3, 6, 8, 11]), "conjuring": (Conjuring, [0, 3, 8, 14, 26]),
         "fast": (FastSaga, [0, 12, 3, 6, 19]), "madmax": (MadMaxSaga, [0, 1, 2, 3, 6]),
         "indiana": (IndianaJones, [1, 3, 6, 9, 4]), "alienpredator": (AlienPredator, [1, 12, 27, 18, 24]),
         "godzillakong": (GodzillaKong, [0, 3, 24, 25, 20]), "apes": (PlanetOfTheApes, [1, 16, 13, 14, 11])}


def render(uid, out_dir):
    """Build over the first scene; during the hold the scenes change with short crossfades. Backgrounds stay still
    (no push-in) so GIF frames only carry what moves, which keeps the file light: Nuvio mobile plays every visible
    card's GIF at once."""
    if uid in MARKS:
        cls, paths = MARKS[uid]
    else:
        cls, picks = PICKS[uid]
        paths = scene_paths(uid, picks)
    mark = cls()
    sc = scenes(paths)
    still = [vignette(art.zoomed(x, 0.04)) for x in sc]
    B, HD = mark.build, mark.hold
    order = list(range(1, len(still))) + [0]
    per = 10
    seq = [(still[0], min(1, i / B), None, getattr(mark, "dur_build", 65)) for i in range(B)]
    k, total = 0, per * len(order)
    for j, s_ in enumerate(order):
        prev = still[order[j - 1]] if j else still[0]
        for f in range(per):
            h = k / total
            k += 1
            if f < 3:
                seq.append((Image.blend(prev, still[s_], (f + 1) / 4), 1.0, h, 70))
            else:
                seq.append((still[s_], 1.0, h, getattr(mark, "dur_hold", 120)))
    frames = []
    for i, (bg, t, h, _) in enumerate(seq):
        mark.i = i
        f = bg.convert("RGBA")
        f.alpha_composite(mark(t, h))
        frames.append(f.convert("RGB"))
    d = os.path.join(out_dir, uid)
    os.makedirs(d, exist_ok=True)
    cov = still[0].convert("RGBA")
    mark.i = round(B + 0.75 * HD)
    cov.alpha_composite(mark(1.0, 0.75))
    cov.convert("RGB").save(os.path.join(d, "cover.jpg"), quality=88)
    art.graded(art.fetch(paths[0]), 0.95, 1.03, (1920, 1080)).save(os.path.join(d, "backdrop.jpg"), quality=86)
    small = [f.resize((GW, GH), Image.LANCZOS) for f in frames]
    picks = [B // 3, B - 1] + [B + per * j + per - 1 for j in range(len(order))]
    pal = Image.new("RGB", (GW, GH * len(picks)))
    for j, idx in enumerate(picks):
        pal.paste(small[min(idx, len(small) - 1)], (0, GH * j))
    pal = pal.convert("P", palette=Image.ADAPTIVE, colors=112)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in small]
    q[0].save(os.path.join(d, "hover.gif"), save_all=True, append_images=q[1:],
              duration=[x[3] for x in seq], loop=0, optimize=True)
    strip = Image.new("RGB", (GW * 4, GH * 2))
    n = len(small)
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
