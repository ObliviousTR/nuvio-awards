"""Awards & Festivals row. Look A is the row's (C was the alternative on trial):
  A "winners"     the award's mark (statuette / logo) up front; on hover it settles in the corner and the films and
                  shows that won it play behind (textless key art), the title and the prize written under them; the
                  card's gold light runs round once; the mark comes back. Combined cards relay their marks.
  C "trophy shelf" no pictures: the trophies on a dark plinth, a spotlight travels from one to the next and lights it,
                  its name under it.
Marks and statuettes are kept in nuvio-art art/logos/awards (TMDB award-show logos, Wikimedia Commons marks, rembg
cut-outs). Winners move on every month through each card's pool.
usage: python3 art_tools/awards_art.py OUT_DIR [folder titles...]   (AWARDS_LOOK=C for the shelf look)
"""
import datetime as dt, io, math, os, random, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from reletter import f as font, tracked, width

W, H = 1280, 720
OW, OH = 512, 288
N = 160
ART = os.environ.get("NUVIO_ART", "/home/claude/nuvio-art")
RAW = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/art/logos/awards/"
GOLD = [(0.0, (255, 240, 190)), (0.45, (232, 188, 98)), (0.75, (190, 138, 52)), (1.0, (120, 82, 30))]
GOLD_TXT = (226, 190, 120)

# folder -> marks (asset, name, prize) and, per mark, a pool of winners: (title, lookup year[, prize, kind, year shown]).
# One mark: three winners a month; two marks: two each; four marks: one each (a relay).
CARDS = {
    "The Oscars": {
        "marks": [("oscars-gold.png", "OSCARS", "BEST PICTURE")], "statue": "oscar-trophy.png",
        "trophy": [("oscar-trophy.png", "THE OSCAR", "ACADEMY AWARDS")],
        "pool": [[("The Godfather", 1972), ("Parasite", 2019), ("Oppenheimer", 2023),
                  ("The Lord of the Rings: The Return of the King", 2003), ("Schindler's List", 1993),
                  ("No Country for Old Men", 2007), ("The Silence of the Lambs", 1991), ("Gladiator", 2000),
                  ("Everything Everywhere All at Once", 2022), ("One Flew Over the Cuckoo's Nest", 1975)]],
    },
    "Golden Globes & BAFTA": {
        "marks": [("golden-globes.png", "GOLDEN GLOBES", "GOLDEN GLOBE · BEST DRAMA"), ("bafta.png", "BAFTA", "BAFTA · BEST FILM")],
        "pool": [[("The Social Network", 2010), ("Boyhood", 2014), ("Brokeback Mountain", 2005), ("Avatar", 2009),
                  ("Three Billboards Outside Ebbing, Missouri", 2017), ("The Power of the Dog", 2021),
                  ("The Revenant", 2015), ("The Brutalist", 2024)],
                 [("1917", 2019), ("La La Land", 2016), ("All Quiet on the Western Front", 2022), ("The King's Speech", 2010),
                  ("Slumdog Millionaire", 2008), ("Conclave", 2024), ("12 Years a Slave", 2013)]],
    },
    "Cannes, Venice & Sundance": {
        "marks": [("palme-mark.png", "CANNES", "PALME D'OR"), ("lion-mark.png", "VENICE", "GOLDEN LION"),
                  ("sundance-mark.png", "SUNDANCE", "GRAND JURY PRIZE"), ("bear-mark.png", "BERLIN", "GOLDEN BEAR")],
        "names": True,
        "trophy": [("palme-trophy.png", "PALME D'OR", "CANNES"), ("lion-mark.png", "GOLDEN LION", "VENICE"),
                   ("sundance-mark.png", "GRAND JURY PRIZE", "SUNDANCE"), ("bear-mark.png", "GOLDEN BEAR", "BERLIN")],
        "pool": [[("Parasite", 2019), ("Pulp Fiction", 1994), ("Anora", 2024), ("Taxi Driver", 1976), ("Apocalypse Now", 1979)],
                 [("Joker", 2019), ("Roma", 2018), ("Nomadland", 2020), ("The Shape of Water", 2017), ("Poor Things", 2023)],
                 [("Whiplash", 2014), ("CODA", 2021), ("Fruitvale Station", 2013), ("Minari", 2020), ("Me and Earl and the Dying Girl", 2015)],
                 [("Spirited Away", 2001), ("A Separation", 2011), ("Magnolia", 1999), ("The Thin Red Line", 1998), ("On Body and Soul", 2017)]],
    },
    "The Emmy Awards": {
        "marks": [("emmy-word", "EMMY AWARDS", "OUTSTANDING DRAMA SERIES")], "statue": "emmy-trophy.png",
        "pool": [[("Breaking Bad", 2008, "OUTSTANDING DRAMA SERIES", "tv", 2013), ("Succession", 2018, "OUTSTANDING DRAMA SERIES", "tv", 2020),
                  ("The Bear", 2022, "OUTSTANDING COMEDY SERIES", "tv", 2023), ("Game of Thrones", 2011, "OUTSTANDING DRAMA SERIES", "tv", 2015),
                  ("Shōgun", 2024, "OUTSTANDING DRAMA SERIES", "tv", 2024), ("Chernobyl", 2019, "OUTSTANDING LIMITED SERIES", "tv", 2019),
                  ("Fleabag", 2016, "OUTSTANDING COMEDY SERIES", "tv", 2019), ("The Sopranos", 1999, "OUTSTANDING DRAMA SERIES", "tv", 2004),
                  ("Mad Men", 2007, "OUTSTANDING DRAMA SERIES", "tv", 2008), ("Ted Lasso", 2020, "OUTSTANDING COMEDY SERIES", "tv", 2021),
                  ("The Crown", 2016, "OUTSTANDING DRAMA SERIES", "tv", 2021), ("Hacks", 2021, "OUTSTANDING COMEDY SERIES", "tv", 2024)]],
    },
    "Criterion Collection & Arthouse": {
        "marks": [("criterion-word", "THE CRITERION COLLECTION", "CRITERION")],
        "pool": [[("Seven Samurai", 1954, "CRITERION SPINE #2"), ("The Seventh Seal", 1957, "CRITERION SPINE #11"),
                  ("8½", 1963, "CRITERION SPINE #140"), ("In the Mood for Love", 2000, "CRITERION SPINE #147"),
                  ("Tokyo Story", 1953, "CRITERION SPINE #217"), ("Rashomon", 1950, "CRITERION SPINE #138"),
                  ("The 400 Blows", 1959, "CRITERION SPINE #5"), ("Grand Illusion", 1937, "CRITERION SPINE #1"),
                  ("Wild Strawberries", 1957, "CRITERION SPINE #139"), ("Ikiru", 1952, "CRITERION SPINE #221")]],
    },
}


# ---------------------------------------------------------------- helpers
def asset(name):
    p = os.path.join(ART, "art", "logos", "awards", name)
    if os.path.exists(p):
        return Image.open(p).convert("RGBA")
    b = urllib.request.urlopen(urllib.request.Request(RAW + name, headers={"User-Agent": "nuvio-awards"}), timeout=60).read()
    return Image.open(io.BytesIO(b)).convert("RGBA")


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def stops(h, st):
    ys = np.linspace(0, 1, h)
    out = np.zeros((h, 3))
    for c in range(3):
        out[:, c] = np.interp(ys, [s for s, _ in st], [col[c] for _, col in st])
    return out


def gilded(im, bevel=True):
    """A flat mark turned to gold: vertical gold ramp, lit from the top left like a cast medal."""
    from scipy import ndimage as ndi
    a = np.asarray(im.getchannel("A"), dtype=np.float32) / 255
    h, w = a.shape
    col = np.repeat(stops(h, GOLD)[:, None, :], w, 1)
    if bevel:
        b = ndi.gaussian_filter(a, max(2, min(w, h) / 60))
        gy, gx = np.gradient(b)
        shade = np.clip(0.55 + (-gx * 0.7 - gy * 0.7) * min(w, h) / 9, 0, 1.4)
        col = col * (0.62 + 0.5 * shade[..., None])
    out = np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def fit(im, w, h):
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def alpha_mul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def place(cv, im, cx, cy, a=1.0):
    cv.alpha_composite(alpha_mul(im, a), (round(cx - im.width / 2), round(cy - im.height / 2)))


def stage(seed=1):
    """Dark warm stage: a low golden glow, a little gold dust."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H * 0.55) / (H * 0.75)) ** 2)
    k = np.clip(1 - d, 0, 1) ** 1.6
    base = np.array([5, 4, 3], np.float32) + k[..., None] * np.array([42, 30, 14], np.float32)
    im = Image.fromarray(base.astype(np.uint8))
    rnd = random.Random(seed)
    dust = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dust)
    for _ in range(90):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.8, 2.4)
        dd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 214, 140, rnd.randint(20, 80)))
    im = im.convert("RGBA")
    im.alpha_composite(dust.filter(ImageFilter.GaussianBlur(0.8)))
    return im.convert("RGB")


def sweep(layer, p, wid=0.16, strength=0.9):
    """A diagonal shine passing over a layer (p 0..1)."""
    w, h = layer.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pos = (xx / w + 0.35 * yy / h) / 1.35
    c = -0.2 + 1.4 * p
    band = np.clip(1 - np.abs(pos - c) / wid, 0, 1) ** 2 * strength
    a = np.asarray(layer.getchannel("A"), dtype=np.float32) / 255
    rgb = np.asarray(layer.convert("RGB"), dtype=np.float32)
    rgb = rgb + (255 - rgb) * band[..., None]
    return Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), "RGBA")


def frame_path(q, m=5, r=22):
    """Points of the card's edge light from the top-left corner round to q (0..1) of the way."""
    per = 2 * (W + H - 4 * m)
    pts, run, tgt = [], 0.0, q * per
    corners = [(m, m), (W - m, m), (W - m, H - m), (m, H - m), (m, m)]
    pts.append(corners[0])
    for (x0, y0), (x1, y1) in zip(corners, corners[1:]):
        seg = abs(x1 - x0) + abs(y1 - y0)
        if run + seg >= tgt:
            t = (tgt - run) / seg
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            return pts
        pts.append((x1, y1))
        run += seg
    return pts


def edge_light(cv, q, a, col=(240, 196, 110)):
    fr = Image.new("L", (W, H), 0)
    pts = frame_path(q)
    if len(pts) > 1 and q > 0:
        ImageDraw.Draw(fr).line(pts, fill=255, width=4, joint="curve")
    gl = Image.new("RGBA", (W, H), col + (0,))
    gl.putalpha(fr.filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, round(v * 1.6 * a))))
    cv.alpha_composite(gl)
    ln = Image.new("RGBA", (W, H), col + (0,))
    ln.putalpha(fr.point(lambda v: round(v * a)))
    cv.alpha_composite(ln)


def word(text, fnt, sp, fill=(255, 255, 255, 255)):
    lay = Image.new("RGBA", (round(width(text, fnt, sp)) + 40, round(fnt.size * 1.6)), (0, 0, 0, 0))
    tracked(ImageDraw.Draw(lay), (10, 10), text, fnt, fill, sp)
    return lay.crop(lay.getchannel("A").getbbox())


def mark_of(asset_name, flat_gold=True):
    if asset_name == "emmy-word":  # the Emmy's name set in gold Cinzel, like the Oscars logotype
        import universe_motion as um
        big = gilded(word("EMMY", um.font("cinzel", 260, weight=600), 40), bevel=False)
        small = gilded(word("AWARDS", um.font("cinzel", 90, weight=600), 40), bevel=False)
        out = Image.new("RGBA", (max(big.width, small.width), big.height + 40 + small.height), (0, 0, 0, 0))
        out.alpha_composite(big, ((out.width - big.width) // 2, 0))
        out.alpha_composite(small, ((out.width - small.width) // 2, big.height + 40))
        return out
    if asset_name == "criterion-word":  # the C and the house's name, white
        c = asset("criterion-mark.png")
        a = c.getchannel("A")
        c = Image.new("RGBA", c.size, (255, 255, 255, 0)); c.putalpha(a)
        c = fit(c, 999, 300)
        w1 = word("THE CRITERION", font("SemiBold", 70), 12)
        w2 = word("COLLECTION", font("SemiBold", 70), 12)
        out = Image.new("RGBA", (c.width + 50 + max(w1.width, w2.width), 300), (0, 0, 0, 0))
        out.alpha_composite(c, (0, 0))
        out.alpha_composite(w1, (c.width + 50, 150 - w1.height - 14))
        out.alpha_composite(w2, (c.width + 50, 150 + 14))
        return out
    im = asset(asset_name)
    if asset_name == "sundance-mark.png":  # the institute disc: keep the sun, set our own word under it
        a = np.asarray(im, dtype=np.float32)
        sun = ((a[..., 0] > 180) & (a[..., 1] > 150) & (a[..., 2] < 120) & (a[..., 3] > 100)).astype(np.uint8) * 255
        from scipy import ndimage as ndi
        sun = ndi.binary_fill_holes(sun > 0).astype(np.uint8) * 255
        disc = Image.new("RGBA", im.size, (0, 0, 0, 0))
        disc.putalpha(Image.fromarray(sun))
        disc = disc.crop(disc.getchannel("A").getbbox())
        disc = gilded(disc.resize((600, round(600 * disc.height / disc.width))))
        wd = Image.new("RGBA", (1400, 260), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(wd), (0, 30), "SUNDANCE", font("ExtraBold", 150), (255, 255, 255, 255), 26)
        wd = gilded(wd.crop(wd.getchannel("A").getbbox()), bevel=False)
        wd = fit(wd, disc.width * 1.5, 999)
        out = Image.new("RGBA", (max(disc.width, wd.width), disc.height + 40 + wd.height), (0, 0, 0, 0))
        out.alpha_composite(disc, ((out.width - disc.width) // 2, 0))
        out.alpha_composite(wd, ((out.width - wd.width) // 2, disc.height + 40))
        return out
    if asset_name in ("lion-mark.png", "bear-mark.png"):
        return gilded(im)
    if asset_name == "palme-mark.png":
        return gilded(im, bevel=False)
    return im


# ---------------------------------------------------------------- films
def winners(card):
    """This month's winners per mark: (image, title, year shown, prize, mark index)."""
    import kids_art as K
    c = CARDS[card]
    m = dt.date.today().year * 12 + dt.date.today().month
    per = {1: 3, 2: 2}.get(len(c["marks"]), 1)
    out = []
    for mi, pool in enumerate(c["pool"]):
        start = (m * per) % len(pool)
        got = 0
        for it in pool[start:] + pool[:start]:
            t, y = it[:2]
            prize = it[2] if len(it) > 2 else c["marks"][mi][2]
            kind = it[3] if len(it) > 3 else "movie"
            shown = it[4] if len(it) > 4 else y
            a = (0, t, None) if os.environ.get("AWARDS_TEST") else K.art_of((kind, t, y))
            if a:
                out.append((a[2], t, shown, prize, mi))
                got += 1
            if got == per:
                break
    if per == 2:  # alternate the marks: A1 B1 A2 B2
        out = [x for pair in zip(out[:2], out[2:]) for x in pair]
    return out


def load(p):
    if p is None:  # local test: any mirrored still
        import glob
        fs = sorted(glob.glob(os.path.join(ART, "mirror", "files", "*", "*.jpg")))
        return Image.open(random.Random(len(fs)).choice(fs[:200])).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


def scene(img):
    from spotlight_art import graded
    im = graded(img, 0.92, 1.05, (W, H))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((-W * 0.3, -H * 0.6, W * 0.42, H * 0.5), fill=200)      # dark pool behind the corner mark
    ImageDraw.Draw(m).rectangle((0, H * 0.62, W, H), fill=0)
    m = m.filter(ImageFilter.GaussianBlur(W * 0.07))
    out = Image.composite(Image.new("RGB", (W, H), (5, 4, 3)), im, m)
    yy = np.linspace(0, 1, H)
    fall = np.clip((yy - 0.55) / 0.45, 0, 1) ** 1.4 * 0.85                             # fall to dark for the label
    f = Image.fromarray((np.repeat(fall[:, None], W, 1) * 255).astype(np.uint8))
    return Image.composite(Image.new("RGB", (W, H), (5, 4, 3)), out, f)


def label(title, prize, year):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    t = title.upper()
    fz = 50
    while width(t, font("ExtraBold", fz), 3) > W * 0.8 and fz > 26:
        fz -= 2
    tracked(d, (60, H - 128), t, font("ExtraBold", fz), (255, 255, 255, 255), 3)
    tracked(d, (62, H - 128 + fz + 14), f"{prize} · {year}", font("SemiBold", 22), GOLD_TXT + (255,), 7)
    return lay


# ---------------------------------------------------------------- look A: winners
def look_a(card):
    c = CARDS[card]
    marks = [mark_of(a) for a, _, _ in c["marks"]]
    films = winners(card)
    scenes = [scene(load(p)) for p, *_ in films]
    labels = [label(t, prize, y) for _, t, y, prize, _ in films]
    st = stage()
    statue = fit(asset(c["statue"]), 999, H * 0.78) if c.get("statue") else None
    # rest positions of the marks on the cover
    big = []
    if len(marks) == 1:
        mk = fit(marks[0], W * (0.46 if statue else 0.5), H * 0.3)
        cx = W * 0.37 if statue else W / 2
        big = [(mk, cx, H * 0.5)]
    else:
        n = len(marks)
        for k, mk in enumerate(marks):
            m2 = fit(mk, W * 0.17, H * 0.3) if n > 2 else fit(mk, W * 0.34, H * 0.3)
            big.append((m2, W * (k + 0.5) / n, H * 0.46 if n > 2 else H * 0.5))
    names = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if c.get("names"):
        dn = ImageDraw.Draw(names)
        for k, (_, nm, _) in enumerate(c["marks"]):
            fn = font("SemiBold", 22)
            tw = width(nm, fn, 8)
            tracked(dn, (W * (k + 0.5) / len(marks) - tw / 2, H * 0.72), nm, fn, GOLD_TXT + (255,), 8)

    def cover_at(a=1.0, shine=None, skip=None):
        cv = st.convert("RGBA")
        if statue is not None:
            # a column of light behind the statuette
            beam = Image.new("L", (W, H), 0)
            ImageDraw.Draw(beam).rectangle((W * 0.70, 0, W * 0.86, H), fill=110)
            beam = beam.filter(ImageFilter.GaussianBlur(50))
            gl = Image.new("RGBA", (W, H), (255, 214, 140, 0)); gl.putalpha(beam.point(lambda v: round(v * a)))
            cv.alpha_composite(gl)
            s = statue if shine is None else sweep(statue, shine)
            place(cv, s, W * 0.78, H * 0.55, a)
        for k, (mk, x, y) in enumerate(big):
            if k != skip:
                place(cv, mk if shine is None else sweep(mk, shine), x, y, a)
        if c.get("names"):
            cv.alpha_composite(alpha_mul(names, a))
        return cv

    cover = cover_at().convert("RGB")
    corner = [fit(mk, W * 0.2, H * 0.17) for mk in marks]
    T0, T1, TF0, TF1, TB = 4, 18, 18, 142, 158
    S = len(scenes)
    seg = (TF1 - TF0) / S
    frames = []
    for i in range(N):
        if i < T0:
            cv = cover_at(1.0, shine=i / T0 * 0.5).convert("RGB")
        elif i < T1 or i >= TF1:
            # into the films (marks shrink to the corner) / back to the cover
            u = ease((i - T0) / (T1 - T0)) if i < T1 else 1 - ease((i - TF1) / (TB - TF1))
            j = 0 if i < T1 else S - 1
            bg = Image.blend(st, scenes[j], u)
            cv = bg.convert("RGBA")
            mi = films[j][4]
            if u < 1:                                  # the rest of the cover fades; the travelling mark is drawn below
                cv.alpha_composite(alpha_mul(cover_at(skip=mi), 1 - u))
            mk, x, y = big[mi]
            cm = corner[mi]
            sc = 1 + (cm.width / mk.width - 1) * u
            L = mk.resize((max(1, round(mk.width * sc)), max(1, round(mk.height * sc))), Image.LANCZOS)
            tx, ty = 56 + cm.width / 2, 44 + cm.height / 2
            place(cv, L, x + (tx - x) * u, y + (ty - y) * u)
            cv.alpha_composite(alpha_mul(labels[j], max(0, u * 2 - 1)))
            cv = cv.convert("RGB")
        else:
            tt = i - TF0
            j = min(S - 1, int(tt // seg))
            loc = (tt - j * seg) / seg
            bg = scenes[j]
            from spotlight_art import zoomed
            bg = zoomed(bg, 0.015 + 0.05 * loc)
            nxt = None
            if loc > 0.84 and j < S - 1:
                nxt = (loc - 0.84) / 0.16
                bg = Image.blend(bg, zoomed(scenes[j + 1], 0.015), ease(nxt))
            cv = bg.convert("RGBA")
            mi = films[j][4]
            cm = corner[mi]
            if nxt is not None and films[j + 1][4] != mi:   # relay: the corner mark hands over
                cn = corner[films[j + 1][4]]
                place(cv, cm, 56 + cm.width / 2, 44 + cm.height / 2, 1 - ease(nxt))
                place(cv, cn, 56 + cn.width / 2, 44 + cn.height / 2, ease(nxt))
            else:
                place(cv, cm, 56 + cm.width / 2, 44 + cm.height / 2)
            la = 1.0 if nxt is None else 1 - ease(nxt)
            cv.alpha_composite(alpha_mul(labels[j], la))
            if nxt is not None:
                cv.alpha_composite(alpha_mul(labels[j + 1], ease(nxt)))
            edge_light(cv, (i - TF0) / (TF1 - TF0), 1.0)
            cv = cv.convert("RGB")
        frames.append(cv.resize((OW, OH), Image.LANCZOS))
    return cover, frames, [f"{t} ({y}, {p})" for _, t, y, p, _ in films]


# ---------------------------------------------------------------- look C: trophy shelf
def look_c(card):
    c = CARDS[card]
    items = []
    for a, name, sub in c["trophy"]:
        im = mark_of(a) if a.endswith("-mark.png") else asset(a)
        items.append((im, name, sub))
    n = len(items)
    st = stage(seed=4)
    # plinth: one long shelf (or a single block for one statuette)
    top_y = round(H * 0.7)
    plinth = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plinth)
    if n == 1:
        x0, x1 = W * 0.36, W * 0.64
    else:
        x0, x1 = W * 0.05, W * 0.95
    face = stops(int(H - top_y), [(0, (40, 34, 28)), (0.2, (22, 19, 16)), (1, (6, 5, 4))])
    for yy in range(int(top_y), H):
        pd.line((x0, yy, x1, yy), fill=tuple(int(v) for v in face[yy - int(top_y)]) + (255,))
    pd.rectangle((x0, top_y - 10, x1, top_y), fill=(70, 58, 44, 255))
    pd.line((x0, top_y - 10, x1, top_y - 10), fill=(150, 124, 86, 255), width=2)
    slots = []
    for k, (im, name, sub) in enumerate(items):
        cx = W / 2 if n == 1 else W * (k + 0.5) / n
        maxh = H * (0.6 if n == 1 else 0.36)
        maxw = W * (0.3 if n == 1 else 0.19)
        t = fit(im, maxw, maxh)
        slots.append((t, cx, top_y - 10 - t.height / 2, name, sub))
    # name plates
    plates = []
    for t, cx, cy, name, sub in slots:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        fn, fs = font("ExtraBold", 30 if n == 1 else 22), font("SemiBold", 18 if n == 1 else 15)
        tw = width(name, fn, 5)
        tracked(d, (cx - tw / 2, top_y + 34), name, fn, (240, 228, 205, 255), 5)
        sw = width(sub, fs, 7)
        tracked(d, (cx - sw / 2, top_y + 34 + (44 if n == 1 else 34)), sub, fs, GOLD_TXT + (255,), 7)
        plates.append(lay)

    def frame(light_x, light_a, lit_k, plate_a, shine):
        cv = st.copy().convert("RGBA")
        # the cone of light from above, aimed at light_x
        cone = Image.new("L", (W, H), 0)
        hw = W * (0.17 if n == 1 else 0.1)
        ImageDraw.Draw(cone).polygon([(light_x - W * 0.03, -20), (light_x + W * 0.03, -20), (light_x + hw, top_y), (light_x - hw, top_y)], fill=120)
        cone = cone.filter(ImageFilter.GaussianBlur(36))
        pool = Image.new("L", (W, H), 0)
        ImageDraw.Draw(pool).ellipse((light_x - hw * 1.2, top_y - 22, light_x + hw * 1.2, top_y + 30), fill=200)
        pool = pool.filter(ImageFilter.GaussianBlur(20))
        for m_, col in ((cone, (255, 226, 170)), (pool, (255, 214, 150))):
            gl = Image.new("RGBA", (W, H), col + (0,))
            gl.putalpha(m_.point(lambda v: round(v * light_a)))
            cv.alpha_composite(gl)
        cv.alpha_composite(plinth)
        for k, (t, cx, cy, _, _) in enumerate(slots):
            lit = math.exp(-((cx - light_x) / (W * (0.12 if n > 1 else 0.25))) ** 2) * light_a
            tt = ImageEnhance.Brightness(t).enhance(0.35 + 0.8 * lit)
            if shine is not None and k == lit_k:
                tt = sweep(tt, shine, 0.14, 0.7)
            place(cv, tt, cx, cy)
            # reflection on the shelf top
            ref = tt.transpose(Image.FLIP_TOP_BOTTOM).crop((0, 0, tt.width, min(tt.height, 40)))
            cv.alpha_composite(alpha_mul(ref, 0.12 * lit), (round(cx - tt.width / 2), round(top_y - 6)))
        for k, pl in enumerate(plates):
            a = plate_a[k]
            if a > 0:
                cv.alpha_composite(alpha_mul(pl, a))
        return cv.convert("RGB")

    frames = []
    if n == 1:
        cx = slots[0][1]
        cover = frame(cx, 1.0, 0, [1.0], None)
        for i in range(N):
            # light goes out, comes back in from the left, sweeps past and settles; a shine runs over the statuette
            if i < 20:
                lx, la = cx, 1 - ease(i / 20) * 0.85
            elif i < 70:
                u = ease((i - 20) / 50)
                lx, la = -W * 0.2 + (W * 1.05) * u, 0.15 + 0.85 * ease((i - 20) / 20)
            elif i < 110:
                u = ease((i - 70) / 40)
                lx, la = W * 0.85 + (cx - W * 0.85) * u, 1.0
            else:
                lx, la = cx, 1.0
            sh = (i - 100) / 40 if 100 <= i < 140 else None
            pa = 1.0 if i >= 110 else max(0.0, 1 - i / 12) if i < 20 else 0.0
            if 110 <= i < 124:
                pa = ease((i - 110) / 14)
            frames.append(frame(lx, la, 0, [pa], sh).resize((OW, OH), Image.LANCZOS))
    else:
        xs = [s[1] for s in slots]
        cover = frame(W / 2, 0.0, -1, [0.0] * n, None)
        # a soft overall light for the cover: each trophy half lit, all plates
        cv = st.copy().convert("RGBA")
        cv.alpha_composite(plinth)
        for t, cx, cy, _, _ in slots:
            place(cv, ImageEnhance.Brightness(t).enhance(0.9), cx, cy)
        for pl in plates:
            cv.alpha_composite(alpha_mul(pl, 0.85))
        cover = cv.convert("RGB")
        hold = 30
        for i in range(N):
            if i < 8:
                frames.append(Image.blend(cover, frame(xs[0], ease(i / 8), 0, [0.85 * (1 - i / 8)] * n, None), ease(i / 8)).resize((OW, OH), Image.LANCZOS))
                continue
            if i >= N - 10:
                u = ease((i - (N - 10)) / 10)
                frames.append(Image.blend(frame(xs[-1], 1.0, n - 1, [0, 0, 0, 1.0][-n:] if n == 4 else [1.0] * n, None), cover, u).resize((OW, OH), Image.LANCZOS))
                continue
            tt = (i - 8) / (N - 18) * n
            k = min(n - 1, int(tt))
            loc = tt - k
            if loc < 0.22 and k > 0:
                u = ease(loc / 0.22)
                lx = xs[k - 1] + (xs[k] - xs[k - 1]) * u
                pa = [0.0] * n
                pa[k - 1], pa[k] = 1 - u, u
            else:
                lx = xs[k]
                pa = [0.0] * n
                pa[k] = 1.0
            sh = (loc - 0.3) / 0.5 if 0.3 <= loc < 0.8 else None
            frames.append(frame(lx, 1.0, k, pa, sh).resize((OW, OH), Image.LANCZOS))
    return cover, frames, [s[3] for s in slots]


def slug_of(t):
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


def build(card, out, look="A"):
    cover, frames, info = (look_a if look == "A" else look_c)(card)
    d = os.path.join(out, slug_of(card) + ("" if look == "A" else "-" + look.lower()))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 10, 24, 50, 76, 102, 128, 150]):
        strip.paste(frames[min(idx, len(frames) - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return info


if __name__ == "__main__":
    out = sys.argv[1]
    look = os.environ.get("AWARDS_LOOK", "A")
    bad = False
    for card in sys.argv[2:] or CARDS:
        try:
            print("built", card, "·", ", ".join(map(str, build(card, out, look))), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", card, e)
            bad = True
    sys.exit(1 if bad else 0)
