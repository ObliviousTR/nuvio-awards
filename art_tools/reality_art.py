"""Reality TV row, "on air": every card plays three shows of its kind under a reality-TV graphics package - a lower
third with the show and its channel - and its own game element that carries one show to the next:
  Cooking      a kitchen countdown; at 0:00 TIME'S UP and the next kitchen
  Makeover     a before / after slider sweeping one show away for the next
  (Trending: ranking bars, Strategy: countdown + ELIMINATED, Panel & Quiz: a scoreboard, Dating: a heart meter)
The card's name sits like Kaptain's (big, lower left) on the cover and tucks into a tag top left on hover.
The trio moves on every month through each card's pool; pictures are fanart.tv / TMDB show art.
usage: python3 art_tools/reality_art.py OUT_DIR [folder titles...]     (REALITY_TEST=1: local stills)
"""
import datetime as dt, math, os, random, sys
import numpy as np
import hero_logos
import hero_styles  # Nuvio TV hero (backdrop.jpg) and title logo (logo.png), Ozzy 31 Oct 2026
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from reletter import f as font, tracked, width

W, H = 1280, 720
OW, OH = 512, 288
TEST = bool(os.environ.get("REALITY_TEST"))

# folder -> (title, subtitle, accent, game, pool of (show, first-air year))
CARDS = {
    "Trending & New Reality": ("TRENDING REALITY", "THE SHOWS EVERYONE IS WATCHING", (255, 170, 40), "rank", None),
    "Strategy, Mind Games & Survival": ("STRATEGY & SURVIVAL", "ISLANDS, MIND GAMES & BETRAYAL", (240, 196, 60), "eliminated", [
        ("Survivor", 2000), ("The Traitors", 2022), ("Squid Game: The Challenge", 2023), ("Alone", 2015),
        ("The Amazing Race", 2001), ("Physical: 100", 2023), ("The Devil's Plan", 2023), ("Big Brother", 2000),
        ("Outlast", 2023)]),
    "British Panel, Quiz & Comedy Shows": ("PANEL & QUIZ SHOWS", "BRITISH PANEL GAMES, QUIZZES & COMEDY", (60, 170, 255), "score", [
        ("Taskmaster", 2015), ("QI", 2003), ("Would I Lie to You?", 2007), ("8 Out of 10 Cats Does Countdown", 2012),
        ("Have I Got News for You", 1990), ("The Chase", 2009), ("Pointless", 2009), ("Only Connect", 2008),
        ("Never Mind the Buzzcocks", 1996)]),
    "Dating, Social Experiment & Drama": ("DATING & DRAMA", "LOVE, LIES & SOCIAL EXPERIMENTS", (255, 80, 150), "heart", [
        ("Love Is Blind", 2020), ("Love Island", 2015), ("Too Hot to Handle", 2020), ("Single's Inferno", 2021),
        ("The Bachelor", 2002), ("Married at First Sight", 2015), ("The Ultimatum: Marry or Move On", 2022),
        ("Temptation Island", 2019), ("The Real Housewives of Beverly Hills", 2010)]),
    "Culinary & Cooking Battles": ("COOKING BATTLES", "CHEFS, BAKERS & KITCHEN HEAT", (235, 70, 50), "timer", [
        ("Hell's Kitchen", 2005), ("The Great British Bake Off", 2010), ("MasterChef", 2010), ("Nailed It!", 2018),
        ("Top Chef", 2006), ("Kitchen Nightmares", 2007), ("Culinary Class Wars", 2024), ("Chopped", 2009),
        ("MasterChef Australia", 2009)]),
    "Makeover, Motors & Craft Battles": ("MAKEOVER & MOTORS", "HOMES, CARS, CRAFTS & FRESH STARTS", (160, 110, 255), "slider", [
        ("Queer Eye", 2018), ("Top Gear", 2002), ("The Repair Shop", 2017), ("Fixer Upper", 2013), ("Blown Away", 2019),
        ("Pimp My Ride", 2004), ("Making It", 2018), ("Wheeler Dealers", 2003), ("Selling Sunset", 2019)]),
}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def amul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def cover_fit(im, w=W, h=H):
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 3
    return im.crop((x, y, x + w, y + h))


def zoomed(im, z):
    w, h = im.size
    cw, ch = w / (1 + z), h / (1 + z)
    x, y = (w - cw) / 2, (h - ch) / 2
    return im.resize((w, h), Image.BILINEAR, box=(x, y, x + cw, y + ch))


# ---------------------------------------------------------------- shows
def shows_of(folder, n=3):
    pool = CARDS[folder][4]
    if TEST:
        pool = pool or [("Show A", 0), ("Show B", 0), ("Show C", 0)]
        import glob
        fs = [f for f in sorted(glob.glob("/home/claude/nuvio-art/mirror/files/*/*.jpg")) if os.path.getsize(f) > 150000]
        rnd = random.Random(folder)
        out = []
        while len(out) < n:
            p = rnd.choice(fs)
            im = Image.open(p)
            if im.width >= 1200 and 1.6 < im.width / im.height < 1.9:
                out.append((pool[len(out)][0], "NETWORK", p))
        return out
    import kids_art as K
    if pool is None:  # this month's most popular reality shows (counted down #3, #2, #1)
        r = (K.tmdb("/discover/tv", with_genres="10764", sort_by="popularity.desc", with_original_language="en",
                    **{"vote_count.gte": 30, "first_air_date.gte": f"{dt.date.today().year - 8}-01-01"}) or {}).get("results", [])
        pool = [(x["name"], int((x.get("first_air_date") or "0")[:4] or 0)) for x in r]
        start = 0
    else:
        m = dt.date.today().year * 12 + dt.date.today().month
        start = (m * n) % len(pool)
    out = []
    for t, y in pool[start:] + pool[:start]:
        a = K.art_of(("tv", t, y))
        if not a:
            continue
        det = K.tmdb(f"/tv/{a[0]}") or {}
        nets = [x["name"] for x in det.get("networks", [])]
        out.append((det.get("name") or t, (nets[0] if nets else "").upper(), a[2]))
        if len(out) == n:
            break
    return out


def load(p):
    if TEST:
        return Image.open(p).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


# ---------------------------------------------------------------- the package
def fall(top=0.5, a=0.85):
    f = np.clip((np.linspace(0, 1, H, dtype=np.float32) - top) / (1 - top), 0, 1) ** 1.3 * a
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.putalpha(Image.fromarray((np.repeat(f[:, None], W, 1) * 255).astype(np.uint8)))
    return lay


def title_block(title, sub, accent):
    """Kaptain's card lettering: accent bar, big title, tracked subtitle (lower left)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    fn = font("ExtraBold", 74)
    while width(title, fn, 3) > W * 0.86 and fn.size > 40:
        fn = font("ExtraBold", fn.size - 2)
    y = H - 168
    d.rectangle((46, y + 8, 52, y + fn.size + 46), fill=accent + (255,))
    tracked(d, (68 + 3, y + 3), title, fn, (0, 0, 0, 150), 3)
    tracked(d, (68, y), title, fn, (255, 255, 255, 255), 3)
    tracked(d, (70, y + fn.size + 14), sub, font("SemiBold", 22), (230, 230, 235, 255), 6)
    return lay


def tag(title, accent):
    """The card's name tucked into a tag, top left."""
    fn = font("ExtraBold", 24)
    tw = width(title, fn, 4)
    lay = Image.new("RGBA", (round(tw) + 70, 52), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, lay.width - 1, 51), radius=10, fill=(12, 12, 14, 215))
    d.ellipse((18, 19, 32, 33), fill=accent + (255,))
    tracked(d, (44, 13), title, fn, (255, 255, 255, 255), 4)
    return lay


def lower_third(show, net, accent, p):
    """Reality-TV lower third: an accent block and a white bar slide in from the left (p 0..1), the show's name on it."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if p <= 0:
        return lay
    d = ImageDraw.Draw(lay)
    fn = font("ExtraBold", 40)
    t = show.upper()
    while width(t, fn, 2) > W * 0.62 and fn.size > 24:
        fn = font("ExtraBold", fn.size - 2)
    tw = width(t, fn, 2)
    x0, y0 = 48, H - 150
    e1, e2 = ease(p / 0.6), ease((p - 0.25) / 0.75)
    bar_w = (tw + 64) * e2
    d.rectangle((x0, y0, x0 + 16 * e1, y0 + 66), fill=accent + (255,))
    if bar_w > 2:
        d.rectangle((x0 + 16, y0, x0 + 16 + bar_w, y0 + 66), fill=(250, 250, 250, 245))
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(txt), (x0 + 40, y0 + 10), t, fn, (18, 18, 20, 255), 2)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle((x0 + 16, y0, x0 + 16 + bar_w, y0 + 66), fill=255)
        txt.putalpha(Image.composite(txt.getchannel("A"), Image.new("L", (W, H), 0), m))
        lay.alpha_composite(txt)
    if net and e2 > 0.5:
        sf = font("SemiBold", 20)
        nw = width(net, sf, 6)
        d.rectangle((x0 + 16, y0 + 66, x0 + 16 + nw + 48, y0 + 100), fill=accent + (round(255 * ease((e2 - 0.5) * 2)),))
        tracked(d, (x0 + 40, y0 + 72), net, sf, (255, 255, 255, round(255 * ease((e2 - 0.5) * 2))), 6)
    return lay


# ---------------------------------------------------------------- game elements
def timer(sec, accent, flash=0.0):
    """A kitchen countdown, top right; red in the last seconds; TIME'S UP at zero."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x1, y0 = W - 48, 44
    box = (x1 - 250, y0, x1, y0 + 96)
    d.rounded_rectangle(box, radius=18, fill=(12, 12, 14, 225), outline=accent + (255,), width=4)
    # a little stopwatch crown
    d.rounded_rectangle((box[0] + 30, y0 - 14, box[0] + 54, y0 + 2), radius=4, fill=accent + (255,))
    if sec > 0:
        s = f"0:{int(math.ceil(sec)):02d}"
        col = (255, 70, 60) if sec <= 5 else (255, 255, 255)
        fn = font("ExtraBold", 62)
        tw = width(s, fn, 2)
        tracked(d, ((box[0] + box[2]) / 2 - tw / 2, y0 + 10), s, fn, col + (255,), 2)
    else:
        fn = font("ExtraBold", 34)
        s = "TIME'S UP!"
        tw = width(s, fn, 2)
        tracked(d, ((box[0] + box[2]) / 2 - tw / 2, y0 + 28), s, fn, (255, 70, 60, 255), 2)
    if flash > 0:
        g = Image.new("RGBA", (W, H), (255, 255, 255, round(110 * flash)))
        lay.alpha_composite(g)
    return lay


def rank_panel(names, k, accent, p=1.0):
    """The trending chart, right: three rows #1..#3; the show on screen lit (shows run #3, #2, #1)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x1, y0, rw, rh = W - 44, 44, 400, 58
    x0 = x1 - rw
    d.rounded_rectangle((x0 - 14, y0 - 46, x1 + 2, y0 + 3 * (rh + 8) + 6), radius=14, fill=(10, 10, 12, round(205 * p)))
    tracked(d, (x0 + 4, y0 - 36), "TRENDING NOW", font("ExtraBold", 20), accent + (round(255 * p),), 5)
    order = list(reversed(names))  # names come #3, #2, #1
    cur = len(names) - 1 - k       # row index (0 = #1) of the show on screen
    for r, nm in enumerate(order):
        y = y0 + r * (rh + 8)
        on = r == cur
        d.rounded_rectangle((x0, y, x1 - 10, y + rh), radius=8, fill=(accent + (round(235 * p),)) if on else (255, 255, 255, round(30 * p)))
        fn = font("ExtraBold", 30)
        tracked(d, (x0 + 16, y + 11), f"#{r + 1}", fn, ((18, 18, 20) if on else (255, 255, 255)) + (round(255 * p),), 1)
        t = nm.upper()
        f2 = font("SemiBold", 20)
        while width(t, f2, 2) > rw - 110 and len(t) > 4:
            t = t[:-2].rstrip() + "…"
        tracked(d, (x0 + 84, y + 18), t, f2, ((18, 18, 20) if on else (235, 235, 240)) + (round(255 * p),), 2)
    return lay


def stamp(p, a=1.0):
    """ELIMINATED, slammed onto the screen (p 0..1: from big and faint to its place)."""
    if p <= 0:
        return Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fn = font("ExtraBold", 92)
    t = "ELIMINATED"
    tw = width(t, fn, 6)
    st = Image.new("RGBA", (round(tw) + 90, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    red = (226, 30, 40)
    d.rectangle((6, 6, st.width - 7, st.height - 7), outline=red + (255,), width=10)
    tracked(d, (45, 30), t, fn, red + (255,), 6)
    arr_ = np.asarray(st, np.float32)
    arr_[..., 3] *= np.clip(np.random.default_rng(4).random(arr_.shape[:2]) * 1.5, 0.45, 1)   # worn ink
    st = Image.fromarray(arr_.astype(np.uint8)).rotate(-11, expand=True, resample=Image.BICUBIC)
    e = ease(p)
    sc = 1.6 - 0.6 * e
    st = st.resize((round(st.width * sc * 0.8), round(st.height * sc * 0.8)), Image.LANCZOS)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.alpha_composite(amul(st, min(1.0, e * 1.5) * a), (round(W / 2 - st.width / 2), round(H * 0.42 - st.height / 2)))
    return lay


def vote_timer(sec, accent):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x1, y0 = W - 48, 44
    box = (x1 - 300, y0, x1, y0 + 110)
    d.rounded_rectangle(box, radius=16, fill=(10, 10, 12, 220), outline=accent + (255,), width=3)
    tracked(d, (box[0] + 22, y0 + 12), "VOTE CLOSES IN", font("ExtraBold", 18), accent + (255,), 4)
    s_ = f"00:{max(0, int(math.ceil(sec))):02d}"
    col = (255, 70, 60) if sec <= 5 else (255, 255, 255)
    tracked(d, (box[0] + 22, y0 + 38), s_, font("ExtraBold", 56), col + (255,), 3)
    return lay


def scoreboard(score, buzz, accent):
    """A quiz scoreboard top right; the buzzer ring flashes as a show hands over."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x1, y0 = W - 48, 44
    box = (x1 - 330, y0, x1, y0 + 110)
    d.rounded_rectangle(box, radius=16, fill=(8, 14, 30, 225), outline=accent + (255,), width=3)
    tracked(d, (box[0] + 22, y0 + 12), "SCORE", font("ExtraBold", 18), accent + (255,), 6)
    tracked(d, (box[0] + 22, y0 + 38), f"{int(score):03d}", font("ExtraBold", 56), (255, 255, 255, 255), 6)
    cx, cy = box[2] - 58, y0 + 55
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=(200, 20, 30, 255), outline=(255, 255, 255, 255), width=4)
    if buzz > 0:
        for r in (60, 110, 170):
            rr = r * (0.6 + 0.4 * (1 - buzz))
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 60, 60, round(200 * buzz)), width=6)
        tracked(d, (box[0] - 10, y0 + 130), "BZZT!", font("ExtraBold", 40), (255, 60, 60, round(255 * buzz)), 4)
    return lay


def heart_meter(fill, accent, pop=0.0):
    """A heart that fills from the bottom; at full IT'S A MATCH! pops."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    S_ = 120
    hm = Image.new("L", (S_ * 2, S_ * 2), 0)
    pts = []
    for k in range(200):
        t = 2 * math.pi * k / 200
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((S_ + x * S_ / 18, S_ - y * S_ / 18))
    ImageDraw.Draw(hm).polygon(pts, fill=255)
    sc = 1 + 0.25 * math.sin(math.pi * pop)
    hm = hm.resize((round(hm.width * sc * 0.6), round(hm.height * sc * 0.6)), Image.LANCZOS)
    w_, h_ = hm.size
    level = Image.new("L", (w_, h_), 0)
    top = round(h_ * (1 - fill))
    ImageDraw.Draw(level).rectangle((0, top, w_, h_), fill=255)
    from PIL import ImageChops
    filled = ImageChops.multiply(hm, level)
    ring = ImageChops.subtract(hm.filter(ImageFilter.MaxFilter(7)), hm)
    cx, cy = W - 140, 130
    x0, y0 = round(cx - w_ / 2), round(cy - h_ / 2)
    back = Image.new("RGBA", (w_, h_), (10, 10, 12, 0))
    back.putalpha(hm.point(lambda v: round(v * 0.6)))
    lay.alpha_composite(back, (x0, y0))
    f = Image.new("RGBA", (w_, h_), accent + (0,))
    f.putalpha(filled)
    lay.alpha_composite(f, (x0, y0))
    r_ = Image.new("RGBA", (w_, h_), (255, 255, 255, 0))
    r_.putalpha(ring)
    lay.alpha_composite(r_, (x0, y0))
    if pop > 0:
        d = ImageDraw.Draw(lay)
        fn = font("ExtraBold", 46)
        t = "IT'S A MATCH!"
        tw = width(t, fn, 3)
        cx = min(cx, W - 40 - tw / 2)
        a = round(255 * min(1, pop * 2))
        tracked(d, (cx - tw / 2 + 3, cy + h_ / 2 + 14 + 3), t, fn, (0, 0, 0, a // 2), 3)
        tracked(d, (cx - tw / 2, cy + h_ / 2 + 14), t, fn, accent + (a,), 3)
    return lay


def whip(a, b, u):
    """A whip pan: a slides out left, b comes in from the right, both smeared."""
    e = ease(u)
    off = round(W * e)
    out = Image.new("RGB", (W, H))
    out.paste(a, (-off, 0))
    out.paste(b, (W - off, 0))
    blur = math.sin(math.pi * u)
    if blur > 0.05:
        smear = out.resize((W // 10, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        out = Image.blend(out, smear, 0.85 * blur)
    return out


def slider(a, b, u, accent):
    """Before / after: the handle sweeps right to left; to its left the old show (BEFORE), to its right the new one."""
    x = round(W * (1 - ease(u)))
    out = a.copy()
    out.paste(b.crop((x, 0, W, H)), (x, 0))
    cv = out.convert("RGBA")
    d = ImageDraw.Draw(cv)
    if 0 < x < W:
        d.rectangle((x - 3, 0, x + 3, H), fill=(255, 255, 255, 255))
        cy = H * 0.45
        d.ellipse((x - 34, cy - 34, x + 34, cy + 34), fill=(255, 255, 255, 255))
        d.polygon([(x - 8, cy - 12), (x - 22, cy), (x - 8, cy + 12)], fill=accent + (255,))
        d.polygon([(x + 8, cy - 12), (x + 22, cy), (x + 8, cy + 12)], fill=accent + (255,))
        fn = font("ExtraBold", 22)
        if x > 200:
            tw = width("BEFORE", fn, 5)
            d.rounded_rectangle((x - tw - 70, 120, x - 24, 162), radius=8, fill=(12, 12, 14, 210))
            tracked(d, (x - tw - 48, 129), "BEFORE", fn, (255, 255, 255, 255), 5)
        if x < W - 200:
            d.rounded_rectangle((x + 24, 120, x + 24 + width("AFTER", fn, 5) + 46, 162), radius=8, fill=accent + (235,))
            tracked(d, (x + 46, 129), "AFTER", fn, (255, 255, 255, 255), 5)
    return cv.convert("RGB")


# ---------------------------------------------------------------- the card
def slug_of(t):
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


def build(folder, out):
    title, sub, accent, game, _ = CARDS[folder]
    shows = shows_of(folder)
    if game == "rank":  # count down: #3, #2, then #1
        shows = shows[::-1]
    pics = [cover_fit(load(p)) for _, _, p in shows]
    fl = fall()
    tb = title_block(title, sub, accent)
    tg = tag(title, accent)
    cv = pics[0].convert("RGBA")
    cv.alpha_composite(fl)
    cv.alpha_composite(tb)
    cover = cv.convert("RGB")
    HOLD, DOCK, SEG, BACK = 6, 12, 46, 14
    S = len(shows)
    T1 = HOLD + DOCK
    T2 = T1 + SEG * S
    N_ = T2 + BACK
    TR = 8                                   # the hand-over between shows (last frames of a segment)
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < T1:      # the big title gives way to the tag and the lower third
            u = (i - HOLD) / DOCK
            c = zoomed(pics[0], 0.01 * u).convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(amul(tb, 1 - ease(u * 1.6)))
            c.alpha_composite(amul(tg, ease((u - 0.3) / 0.7)), (40, 34))
            c.alpha_composite(lower_third(shows[0][0], shows[0][1], accent, (u - 0.4) / 0.6))
            if game == "timer":
                c.alpha_composite(amul(timer(30, accent), ease((u - 0.3) / 0.7)))
        elif i < T2:
            k, t = divmod(i - T1, SEG)
            z = 0.01 + 0.04 * t / SEG
            pic = zoomed(pics[k], z)
            last = k == S - 1
            lt = 1.0
            game_lay = None
            if game == "timer":
                sec = 30 * (1 - t / (SEG - TR))
                flash = 0.0
                if t >= SEG - TR:
                    sec = 0
                    flash = max(0.0, 1 - (t - (SEG - TR)) / 3)
                    if not last:   # time's up: whip to the next kitchen
                        pic = whip(pic, zoomed(pics[k + 1], 0.01), (t - (SEG - TR) - 2) / (TR - 2)) if t - (SEG - TR) >= 2 else pic
                game_lay = timer(sec, accent, flash)
                lt = 1 - ease((t - (SEG - TR)) / 3) if t >= SEG - TR else ease(t / 6) if k > 0 else 1.0
            elif game == "rank":
                if t >= SEG - TR and not last:
                    u = (t - (SEG - TR)) / TR
                    pic = Image.blend(pic, zoomed(pics[k + 1], 0.01), ease(u))
                    lt = 1 - ease(u * 2)
                elif k > 0:
                    lt = ease(t / 6)
                game_lay = rank_panel([x[0] for x in shows], k if t < SEG - TR // 2 or last else k + 1, accent)
            elif game == "eliminated":
                sec = 15 * (1 - t / (SEG - 12))
                game_lay = vote_timer(sec, accent)
                if t >= SEG - 12 and not last:
                    u = (t - (SEG - 12)) / 12
                    game_lay.alpha_composite(stamp(min(1, u * 3), 1 - ease((u - 0.6) / 0.4)))
                    if u > 0.55:
                        pic = whip(pic, zoomed(pics[k + 1], 0.01), (u - 0.55) / 0.45)
                    lt = 1 - ease(u * 2)
                elif k > 0:
                    lt = ease(t / 6)
            elif game == "score":
                score = 10 * (k * 5 + int(t / SEG * 5))
                buzz = 0.0
                if t >= SEG - TR and not last:
                    u = (t - (SEG - TR)) / TR
                    buzz = 1 - u
                    pic = Image.blend(pic, zoomed(pics[k + 1], 0.01), ease((u - 0.3) / 0.7))
                    lt = 1 - ease(u * 2)
                elif k > 0:
                    lt = ease(t / 6)
                game_lay = scoreboard(score, buzz, accent)
            elif game == "heart":
                fill_ = min(1.0, t / (SEG - 14))
                pop = 0.0
                if t >= SEG - 14:
                    pop = min(1.0, (t - (SEG - 14)) / 6)
                    if t >= SEG - 8 and not last:
                        u = (t - (SEG - 8)) / 8
                        pic = Image.blend(pic, zoomed(pics[k + 1], 0.01), ease(u))
                        lt = 1 - ease(u * 2)
                        fill_ = 1 - ease(u)
                        pop = 1 - ease(u)
                elif k > 0:
                    lt = ease(t / 6)
                game_lay = heart_meter(fill_, accent, pop)
            elif game == "slider":
                if t >= SEG - 14 and not last:
                    u = (t - (SEG - 14)) / 14
                    pic = slider(pic, zoomed(pics[k + 1], 0.01), u, accent)
                    lt = 1 - ease(u * 2)
                elif k > 0:
                    lt = ease(t / 8)
            c = pic.convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(tg, (40, 34))
            c.alpha_composite(lower_third(shows[k][0], shows[k][1], accent, lt))
            if game_lay is not None:
                c.alpha_composite(game_lay)
        else:           # back to the card
            u = ease((i - T2) / BACK)
            c = Image.blend(zoomed(pics[-1], 0.05), pics[0], u).convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(amul(tg, 1 - u), (40, 34))
            c.alpha_composite(lower_third(shows[-1][0], shows[-1][1], accent, 1 - u * 1.4))
            if game == "timer":
                c.alpha_composite(amul(timer(0, accent), 1 - u))
            c.alpha_composite(amul(tb, ease((u - 0.3) / 0.7)))
        frames.append(c.convert("RGB").resize((OW, OH), Image.LANCZOS))
    d = os.path.join(out, slug_of(folder))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    hero_styles.scene(pics[0]).save(os.path.join(d, "backdrop.jpg"), quality=86)
    hero_logos.bar_logo(title, sub, accent).save(os.path.join(d, "logo.png"))   # the cover's bar, title, subtitle
    n = len(frames)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 14, 40, 58, 62, 90, 108, n - 6]):
        strip.paste(frames[min(idx, n - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return [f"{s} ({nw})" for s, nw, _ in shows]


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
