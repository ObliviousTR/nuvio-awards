"""By Decade row: Kaptain's big decade numbers filled with a film. On hover the camera flies into the numbers until
the picture fills the card, and three films of the decade play the way that decade watched them:
  1950s  black and white, Academy ratio, grain, flicker, gate weave      (splices between films)
  1960s  Technicolor, scope letterbox, soft and saturated
  1970s  warm faded print, grain, scratches
  1980s  a VHS tape: pan & scan, chroma bleed, tracking noise, PLAY       (tracking glitch between films)
  1990s  a CRT television: 4:3 in a tube, scanlines, channel number       (static between channels)
  2000s  DVD: widescreen at last, a little MPEG blocking, chapter counter
  2010s  clean HD
  2020s  streaming: 4K HDR, a progress bar under the film
then flies back out into the numbers. The three films move on every month through each decade's pool (the first
one also fills the numbers on the cover). "Best of <year>" takes this year's most popular well-rated films.
usage: python3 art_tools/decade_art.py OUT_DIR [folder titles...]    (DECADE_TEST=1: local stills, no network)
"""
import datetime as dt, math, os, random, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from reletter import f as font, tracked, width

W, H = 1280, 720
OW, OH = 512, 288
TEST = bool(os.environ.get("DECADE_TEST"))
YEAR = dt.date.today().year if dt.date.today().month >= 3 else dt.date.today().year - 1   # Best of <year>: the new year from March (builder/new_year.py)

CARDS = {  # folder -> (numbers, era, accent, pool of (title, year))
    "1950s & Golden Age": ("50S", "50s", (230, 90, 80), [
        ("Rear Window", 1954), ("Singin' in the Rain", 1952), ("Vertigo", 1958), ("12 Angry Men", 1957),
        ("Sunset Boulevard", 1950), ("Some Like It Hot", 1959), ("Seven Samurai", 1954), ("North by Northwest", 1959),
        ("Ben-Hur", 1959), ("Rebel Without a Cause", 1955)]),
    "1960s": ("60S", "60s", (235, 235, 240), [
        ("2001: A Space Odyssey", 1968), ("Lawrence of Arabia", 1962), ("Psycho", 1960),
        ("The Good, the Bad and the Ugly", 1966), ("Breakfast at Tiffany's", 1961), ("Dr. Strangelove", 1964),
        ("The Sound of Music", 1965), ("Goldfinger", 1964), ("Planet of the Apes", 1968), ("West Side Story", 1961)]),
    "1970s": ("70S", "70s", (240, 190, 90), [
        ("Star Wars", 1977), ("The Godfather", 1972), ("Jaws", 1975), ("Taxi Driver", 1976), ("Alien", 1979),
        ("Apocalypse Now", 1979), ("Rocky", 1976), ("A Clockwork Orange", 1971), ("Close Encounters of the Third Kind", 1977),
        ("Saturday Night Fever", 1977)]),
    "1980s": ("80S", "80s", (255, 80, 190), [
        ("Back to the Future", 1985), ("E.T. the Extra-Terrestrial", 1982), ("Blade Runner", 1982),
        ("The Empire Strikes Back", 1980), ("Raiders of the Lost Ark", 1981), ("The Terminator", 1984),
        ("Ghostbusters", 1984), ("The Breakfast Club", 1985), ("Top Gun", 1986), ("The Shining", 1980)]),
    "1990s": ("90S", "90s", (200, 230, 90), [
        ("Jurassic Park", 1993), ("Pulp Fiction", 1994), ("The Matrix", 1999), ("Titanic", 1997), ("Forrest Gump", 1994),
        ("Terminator 2: Judgment Day", 1991), ("Fight Club", 1999), ("Home Alone", 1990), ("The Lion King", 1994),
        ("Goodfellas", 1990)]),
    "2000s": ("00S", "00s", (240, 180, 80), [
        ("The Dark Knight", 2008), ("The Lord of the Rings: The Fellowship of the Ring", 2001), ("Gladiator", 2000),
        ("Spirited Away", 2001), ("Pirates of the Caribbean: The Curse of the Black Pearl", 2003), ("Kill Bill: Vol. 1", 2003),
        ("Avatar", 2009), ("The Departed", 2006), ("Shrek", 2001), ("No Country for Old Men", 2007)]),
    "2010s": ("10S", "10s", (170, 215, 255), [
        ("Interstellar", 2014), ("Inception", 2010), ("Mad Max: Fury Road", 2015), ("Avengers: Endgame", 2019),
        ("Parasite", 2019), ("La La Land", 2016), ("Get Out", 2017), ("The Social Network", 2010), ("Joker", 2019),
        ("Django Unchained", 2012)]),
    "2020s": ("20S", "20s", (240, 200, 110), [
        ("Dune", 2021), ("Oppenheimer", 2023), ("Everything Everywhere All at Once", 2022), ("Top Gun: Maverick", 2022),
        ("Barbie", 2023), ("Spider-Man: Across the Spider-Verse", 2023), ("Dune: Part Two", 2024), ("Poor Things", 2023),
        ("The Batman", 2022), ("Furiosa: A Mad Max Saga", 2024)]),
    f"🏆 Best of {YEAR}": (str(YEAR), "20s", (240, 200, 110), None),
}


# ---------------------------------------------------------------- helpers
def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def arr(im):
    return np.asarray(im.convert("RGB"), dtype=np.float32)


def img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def cover_fit(im, w=W, h=H):
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def zoomed(im, z):
    w, h = im.size
    cw, ch = w / (1 + z), h / (1 + z)
    x, y = (w - cw) / 2, (h - ch) / 2
    return im.resize((w, h), Image.BILINEAR, box=(x, y, x + cw, y + ch))


def ufont(name, size, weight=None):
    import universe_motion as um
    um.FONTS.setdefault("montserrat", "ofl/montserrat/Montserrat%5Bwght%5D.ttf")
    um.FONTS.setdefault("vcr", "ofl/vt323/VT323-Regular.ttf")
    return um.font(name, size, weight)


def amul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def boxed(im, ratio, fill=(0, 0, 0)):
    """Letterbox (wider than 16:9) or pillarbox (narrower) the frame to a ratio."""
    out = Image.new("RGB", (W, H), fill)
    if ratio >= W / H:
        h = round(W / ratio)
        out.paste(cover_fit(im, W, h), (0, (H - h) // 2))
    else:
        w = round(H * ratio)
        out.paste(cover_fit(im, w, H), ((W - w) // 2, 0))
    return out


# ---------------------------------------------------------------- the eras: base(img) once per film, live(base, f) per frame
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = np.clip(np.sqrt(((XX - W / 2) / (W * 0.62)) ** 2 + ((YY - H / 2) / (H * 0.62)) ** 2) - 0.5, 0, 1)
RND = np.random.default_rng(1)
GRAIN = [RND.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]


def grain(f, amt):
    g = GRAIN[(f // 2) % len(GRAIN)]
    return np.repeat(np.repeat(g, 2, 0), 2, 1) * amt


def base_50s(im):
    a = arr(im).mean(2)
    a = np.clip((a - 128) * 1.25 + 128, 0, 255)
    return np.stack([a, a, a], 2)


def live_50s(b, f):
    a = b + grain(f, 13)[..., None]
    a *= 1 + 0.035 * math.sin(f * 2.3) + 0.02 * math.sin(f * 5.1)        # flicker
    a *= (1 - VIG * 0.8)[..., None]
    im = img(a)
    dx, dy = round(1.5 * math.sin(f * 1.7)), round(1.2 * math.sin(f * 2.9))   # gate weave
    im = im.transform(im.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR)
    d = ImageDraw.Draw(im)
    r = random.Random(f // 2)
    for _ in range(r.randint(1, 4)):                                       # dust
        x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(1, 3.5)
        d.ellipse((x - s, y - s, x + s, y + s), fill=(r.choice([10, 235]),) * 3)
    if r.random() < 0.35:
        x = r.uniform(W * 0.2, W * 0.8)
        d.line((x, 0, x + r.uniform(-8, 8), H), fill=(225, 225, 225), width=1)
    return boxed(im, 1.37)


def base_60s(im):
    im = ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.12)).enhance(1.45)
    a = arr(im) * np.array([1.04, 1.0, 0.93], np.float32)
    return arr(img(a).filter(ImageFilter.GaussianBlur(0.8)))


def live_60s(b, f):
    a = b + grain(f, 6)[..., None]
    a *= (1 - VIG * 0.45)[..., None]
    return boxed(img(a), 2.35)


def base_70s(im):
    a = arr(ImageEnhance.Color(im).enhance(0.8))
    a = a * np.array([1.08, 0.98, 0.78], np.float32) + np.array([18, 12, 4], np.float32)   # warm, faded, lifted blacks
    a = 20 + a * 0.9
    return a


def live_70s(b, f):
    a = b + grain(f, 11)[..., None]
    a *= (1 - VIG * 0.6)[..., None]
    im = img(a)
    d = ImageDraw.Draw(im)
    r = random.Random(f // 3 + 99)
    for _ in range(r.randint(0, 2)):                                       # scratches
        x = r.uniform(0, W)
        d.line((x, 0, x + r.uniform(-4, 4), H), fill=(235, 220, 190), width=1)
    return boxed(im, 1.85)


VCR_TIME = [0]


def base_80s(im):
    im = boxed(im, 4 / 3)                                                  # pan & scan
    a = arr(ImageEnhance.Color(im).enhance(0.9))
    a = arr(img(a).filter(ImageFilter.BoxBlur(1)))
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], 5, 1)                                 # chroma bleed
    out[..., 2] = np.roll(a[..., 2], -3, 1)
    out[1::3] *= 0.9                                                       # scanlines
    return out


def vcr_osd(im, f, t0=(1, 42, 17)):
    d = ImageDraw.Draw(im)
    fo = ufont("vcr", 46)
    if (f // 12) % 2 == 0 or f < 30:
        d.text((178, 40), "PLAY", font=fo, fill=(235, 235, 235))
        d.polygon([(290, 50), (290, 78), (314, 64)], fill=(235, 235, 235))
    secs = t0[0] * 3600 + t0[1] * 60 + t0[2] + f // 20
    d.text((W - 340, H - 92), f"{secs // 3600}:{secs // 60 % 60:02d}:{secs % 60:02d}", font=fo, fill=(235, 235, 235))
    d.text((W - 340, 40), "SP", font=fo, fill=(235, 235, 235))
    return im


def live_80s(b, f, glitch=0.0):
    a = b + grain(f, 7)[..., None]
    # the tracking band rolls down the picture
    yb = (f * 9) % (H + 120) - 60
    band = np.exp(-((YY[:, :1] - yb) / 14) ** 2)
    noise = RND.normal(0, 1, (H, 1)).astype(np.float32)
    a = a * (1 - 0.35 * band[..., None]) + band[..., None] * 60 * (noise[..., None] > 0.8)
    im = img(a)
    if glitch > 0:  # tracking lost: rows torn sideways, snow
        aa = np.asarray(im).copy()
        r = np.random.default_rng(f)
        for y0 in range(0, H, 8):
            aa[y0:y0 + 8] = np.roll(aa[y0:y0 + 8], int(r.normal(0, 40 * glitch)), 1)
        sn = r.random((H, W, 1)) * 255
        aa = (aa * (1 - 0.6 * glitch) + sn * 0.6 * glitch).astype(np.uint8)
        im = Image.fromarray(aa)
    return vcr_osd(im, f)


def base_90s(im):
    tv = boxed(im, 4 / 3)
    a = arr(ImageEnhance.Contrast(tv).enhance(1.05))
    a[::2] *= 0.86
    return a


TUBE = None


def tube_mask():
    global TUBE
    if TUBE is None:
        m = Image.new("L", (W, H), 0)
        w = round(H * 4 / 3) - 40
        ImageDraw.Draw(m).rounded_rectangle(((W - w) / 2, 20, (W + w) / 2, H - 20), radius=70, fill=255)
        TUBE = m.filter(ImageFilter.GaussianBlur(6))
    return TUBE


def live_90s(b, f, static=0.0, ch=3):
    a = b * (1 - VIG * 0.5)[..., None]
    im = img(a)
    if static > 0:
        r = np.random.default_rng(f)
        sn = (r.random((H // 2, W // 2)) * 255).astype(np.uint8)
        sn = Image.fromarray(sn).resize((W, H), Image.NEAREST).convert("RGB")
        im = Image.blend(im, sn, static)
    glow = im.filter(ImageFilter.GaussianBlur(5))
    im = Image.blend(im, glow, 0.25)
    out = Image.new("RGB", (W, H), (8, 8, 9))
    out.paste(im, (0, 0), tube_mask())
    d = ImageDraw.Draw(out)
    d.text((W / 2 + H * 2 / 3 - 190, 50), f"CH {ch:02d}", font=ufont("vcr", 54), fill=(80, 255, 90))
    return out


def base_00s(im):
    q = im.resize((854, 480), Image.BILINEAR)                               # a DVD's worth of pixels, MPEG-ish blocking
    import io
    bio = io.BytesIO()
    q.save(bio, "JPEG", quality=38)
    q = Image.open(bio).convert("RGB").resize((W, H), Image.BICUBIC)
    return arr(boxed(q, 1.85))


def live_00s(b, f, chapter=1):
    im = img(b)
    if f % 60 < 40:
        d = ImageDraw.Draw(im)
        fo = font("SemiBold", 24)
        tracked(d, (60, 44), f"CHAPTER {chapter}", fo, (230, 230, 230), 6)
    return im


def base_10s(im):
    im = ImageEnhance.Sharpness(ImageEnhance.Contrast(im).enhance(1.06)).enhance(1.4)
    a = arr(im)
    lum = a.mean(2, keepdims=True) / 255
    a = a + (np.array([12, 2, -10], np.float32) * lum + np.array([-6, 2, 8], np.float32) * (1 - lum))   # teal & orange
    return a


def live_10s(b, f):
    im = img(b)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((W - 130, 40, W - 50, 82), radius=8, outline=(240, 240, 240), width=3)
    tracked(d, (W - 116, 46), "HD", font("ExtraBold", 26), (240, 240, 240), 3)
    return im


def base_20s(im):
    return arr(ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.05)).enhance(1.08))


def live_20s(b, f, n=170):
    im = img(b).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    p = 0.38 + 0.25 * f / n
    x0, x1, y = 60, W - 60, H - 46
    d.rounded_rectangle((x0, y - 3, x1, y + 3), radius=3, fill=(255, 255, 255, 90))
    d.rounded_rectangle((x0, y - 3, x0 + (x1 - x0) * p, y + 3), radius=3, fill=(229, 9, 20, 255))
    cx = x0 + (x1 - x0) * p
    d.ellipse((cx - 10, y - 10, cx + 10, y + 10), fill=(229, 9, 20, 255))
    fo = font("SemiBold", 22)
    tot = 2 * 3600 + 28 * 60 + 31
    cur = int(tot * p)
    tracked(d, (x1 - 210, y - 44), f"{cur // 3600}:{cur // 60 % 60:02d}:{cur % 60:02d} / 2:28:31", fo, (235, 235, 235, 255), 1)
    d.rounded_rectangle((W - 220, 40, W - 50, 80), radius=8, fill=(0, 0, 0, 120))
    tracked(d, (W - 204, 47), "4K · HDR", font("ExtraBold", 22), (240, 240, 240, 255), 3)
    im.alpha_composite(ov)
    return im.convert("RGB")


ERAS = {"50s": (base_50s, live_50s, "splice"), "60s": (base_60s, live_60s, "splice"), "70s": (base_70s, live_70s, "splice"),
        "80s": (base_80s, live_80s, "vhs"), "90s": (base_90s, live_90s, "static"), "00s": (base_00s, live_00s, "dissolve"),
        "10s": (base_10s, live_10s, "dissolve"), "20s": (base_20s, live_20s, "dissolve")}


# ---------------------------------------------------------------- pictures
def films_of(folder, n=3):
    text, era, accent, pool = CARDS[folder]
    if TEST:
        import glob
        fs = [f for f in sorted(glob.glob("/home/claude/nuvio-art/mirror/files/*/*.jpg")) if os.path.getsize(f) > 150000]
        rnd = random.Random(folder)
        out = []
        while len(out) < n:
            p = rnd.choice(fs)
            im = Image.open(p)
            if im.width >= 1200 and 1.6 < im.width / im.height < 1.9:
                out.append((f"Test {len(out)}", 1980 + len(out), p))
        return out
    import kids_art as K
    if pool is None:  # Best of this year: the year's most popular films that are also well rated
        r = (K.tmdb("/discover/movie", primary_release_year=YEAR, sort_by="popularity.desc",
                    **{"vote_count.gte": 300, "vote_average.gte": 6.8}) or {}).get("results", [])
        pool = [(x["title"], YEAR) for x in r]
        if len(pool) < 2 * n:   # early in the year few films qualify yet: last year's best fill the card meanwhile
            r = (K.tmdb("/discover/movie", primary_release_year=YEAR - 1, sort_by="popularity.desc",
                        **{"vote_count.gte": 300, "vote_average.gte": 6.8}) or {}).get("results", [])
            pool += [(x["title"], YEAR - 1) for x in r]
        start = 0
    else:
        m = dt.date.today().year * 12 + dt.date.today().month
        start = (m * n) % len(pool)
    out = []
    for t, y in pool[start:] + pool[:start]:
        # a real scene suits a film "on its own format" better than designed key art: TMDB's best textless still
        tid, _ = K.g.find_movie(t, y)
        p = K.g.textless_backdrop("movie", tid) if tid else None
        if not p:
            a = K.art_of(("movie", t, y))
            p = a[2] if a else None
        if p:
            out.append((t, y, p))
        if len(out) == n:
            break
    return out


def load(p):
    if TEST:
        return Image.open(p).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


# ---------------------------------------------------------------- lettering
def numbers(text):
    """Kaptain's numbers: black Montserrat, tight, centred on the card; returns the mask on a card-sized canvas."""
    import universe_motion as um
    L = um.text_layer(text, ufont("montserrat", 620, 900), (255, 255, 255), -8)
    L = um.fit(L, W * 0.9, H * 0.66)
    m = Image.new("L", (W, H), 0)
    m.paste(L.getchannel("A"), ((W - L.width) // 2, (H - L.height) // 2))
    return m


def anchor_of(mask):
    """The deepest point of the strokes near the middle: the camera flies in there."""
    from scipy import ndimage as ndi
    a = np.asarray(mask, np.float32) > 128
    dist = ndi.distance_transform_edt(a)
    score = dist - 0.05 * np.sqrt((XX - W / 2) ** 2 + (YY - H / 2) ** 2)
    y, x = np.unravel_index(np.argmax(score), score.shape)
    return float(x), float(y), float(dist[y, x])


def scaled(mask, s, ax, ay):
    if s <= 1.0001:
        return mask
    return mask.transform((W, H), Image.AFFINE, (1 / s, 0, ax - ax / s, 0, 1 / s, ay - ay / s), resample=Image.BILINEAR)


def ring_of(mask, wpx=5):
    from PIL import ImageChops
    return ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(wpx * 2 + 1)), mask.filter(ImageFilter.MinFilter(3)))


def label(title, year, accent):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    t = title.upper()
    fz = 44
    while width(t, font("ExtraBold", fz), 3) > W - 160 and fz > 24:
        fz -= 2
    y = H - 140
    tracked(d, (60, y), t, font("ExtraBold", fz), (255, 255, 255, 255), 3)
    tracked(d, (62, y + fz + 10), str(year), font("SemiBold", 22), accent + (255,), 8)
    return lay


def fall():
    f = np.clip((np.linspace(0, 1, H, dtype=np.float32) - 0.55) / 0.45, 0, 1) ** 1.3 * 0.8
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.putalpha(Image.fromarray((np.repeat(f[:, None], W, 1) * 255).astype(np.uint8)))
    return lay


# ---------------------------------------------------------------- the card
def build(folder, out):
    text, era, accent, _ = CARDS[folder]
    base_f, live_f, trans = ERAS[era]
    films = films_of(folder)
    reals = [cover_fit(load(p)) for _, _, p in films]
    bases = [base_f(r) for r in reals]
    mask = numbers(text)
    ax, ay, depth = anchor_of(mask)
    smax = max(40.0, min(W, H) / max(depth, 4) * 1.6)
    fill0 = ImageEnhance.Brightness(ImageEnhance.Contrast(reals[0]).enhance(1.08)).enhance(1.1)
    back = ImageEnhance.Brightness(reals[0].filter(ImageFilter.GaussianBlur(10))).enhance(0.3)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(18)).point(lambda v: round(v * 0.9)))
    labels = [label(t, y, accent) for t, y, _ in films]
    fl = fall()

    def numbers_frame(content, s, ring_a=1.0, glow_a=1.0):
        m = scaled(mask, s, ax, ay)
        cv = back.convert("RGBA")
        if glow_a > 0:
            sh = shadow if s <= 1.0001 else scaled(shadow.getchannel("A"), s, ax, ay)
            if s > 1.0001:
                tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); tmp.putalpha(sh); sh = tmp
            cv.alpha_composite(amul(sh, glow_a))
        c = content.convert("RGBA")
        c.putalpha(m)
        cv.alpha_composite(c)
        if ring_a > 0:
            r = ring_of(m)
            rl = Image.new("RGBA", (W, H), (255, 255, 255, 0))
            rl.putalpha(r.point(lambda v: round(v * 0.92 * ring_a)))
            cv.alpha_composite(rl)
            gl = Image.new("RGBA", (W, H), accent + (0,))
            gl.putalpha(r.filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, round(v * 1.4 * ring_a))))
            cv.alpha_composite(gl)
        return cv.convert("RGB")

    cover = numbers_frame(fill0, 1.0)
    HOLD, IN, SEG, OUT = 6, 20, 44, 20
    S = len(films)
    F0 = HOLD + IN
    N_ = F0 + SEG * S + OUT

    def era_live(b, f, k):
        if era == "00s":
            return live_f(b, f, chapter=3 + 4 * k)
        if era == "20s":
            return live_f(b, f, n=N_)
        if era == "90s":
            return live_f(b, f, ch=3 + k)
        return live_f(b, f)

    frames = []
    for i in range(N_):
        if i < HOLD:
            fr = cover
        elif i < F0:
            # fly into the numbers; the picture inside turns into the decade's format
            u = (i - HOLD) / IN
            s = math.exp(math.log(smax) * (u ** 2.2))
            era_pic = era_live(bases[0], i - HOLD, 0)
            content = Image.blend(fill0, era_pic, ease(u * 1.4))
            fr = numbers_frame(content, s, ring_a=1 - ease(u * 1.6), glow_a=1 - ease(u * 2))
        elif i < F0 + SEG * S:
            k, t = divmod(i - F0, SEG)
            f = i - HOLD
            z = 0.02 * t / SEG
            b = bases[k] if z <= 0 else arr(zoomed(img(bases[k]), z))
            if era == "80s":
                gl = 0.0
                if k > 0 and t < 6:
                    gl = 1 - t / 6
                elif k < S - 1 and t >= SEG - 4:
                    gl = (t - (SEG - 4)) / 4
                fr = live_f(b, f, glitch=gl)
            elif era == "90s":
                st = 0.0
                if k > 0 and t < 5:
                    st = 1 - t / 5
                elif k < S - 1 and t >= SEG - 3:
                    st = (t - (SEG - 3)) / 3
                fr = live_f(b, f, static=st, ch=3 + k)
            elif era == "00s":
                fr = live_f(b, f, chapter=3 + 4 * k)
            elif era == "20s":
                fr = live_f(b, f, n=N_)
            else:
                fr = live_f(b, f)
            if trans in ("dissolve", "splice") and k > 0 and t < 7:
                prev = era_live(bases[k - 1], f, k - 1)
                fr = Image.blend(prev, fr, ease(t / 7))
                if trans == "splice" and t < 2:
                    fr = Image.blend(fr, Image.new("RGB", (W, H), (245, 240, 230)), 0.55 * (1 - t / 2))
            c = fr.convert("RGBA")
            c.alpha_composite(fl)
            la = ease((t - 2) / 6) if t < 8 else (1 - ease((t - (SEG - 5)) / 5) if t >= SEG - 5 else 1.0)
            c.alpha_composite(amul(labels[k], la))
            fr = c.convert("RGB")
        else:
            # fly back out: the decade's picture becomes the cover's film again inside the numbers
            u = (i - (F0 + SEG * S)) / OUT
            s = math.exp(math.log(smax) * ((1 - u) ** 2.2))
            last = era_live(bases[-1], i - HOLD, S - 1)
            content = Image.blend(last, fill0, ease(u * 1.3))
            fr = numbers_frame(content, s, ring_a=ease((u - 0.4) / 0.6), glow_a=ease((u - 0.5) / 0.5))
        frames.append(fr.resize((OW, OH), Image.LANCZOS))
    d = os.path.join(out, slug_of(folder))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 12, 20, 40, 70, 100, 140, 162]):
        strip.paste(frames[min(idx, len(frames) - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return [f"{t} ({y})" for t, y, _ in films]


def slug_of(t):
    t = t.replace("🏆", "").strip()
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


if __name__ == "__main__":
    out = sys.argv[1]
    bad = False
    for fo in sys.argv[2:] or CARDS:
        try:
            print("built", fo, "·", ", ".join(build(fo, out)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", fo, e)
            bad = True
    sys.exit(1 if bad else 0)
