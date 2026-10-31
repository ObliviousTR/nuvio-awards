"""Documentaries row: Kaptain's two-tone cards brought to life. On hover three documentaries of the card's kind play;
each comes up in the card's two tones and then blooms into its true colours (the row's common beat), and each card
adds the device of its kind of film:
  True Crime   an evidence board: a CASE FILE stamp; each film is pinned up as a polaroid, red string between them
  History      archive footage: grain, flicker, gate weave, a typed ARCHIVE label; the bloom colourises it
  (Investigative: redaction bars; Nature: a camera viewfinder; Science: a telescope readout; Sports: a photo
   finish; Music: a level meter; Trending: festival laurels)
The card's name sits like Kaptain's on the cover and tucks into a tag on hover. Films move on every month.
usage: python3 art_tools/docs_art.py OUT_DIR [folder titles...]     (DOCS_TEST=1: local stills)
"""
import datetime as dt, math, os, random, sys
import numpy as np
import hero_styles  # Nuvio TV hero (backdrop.jpg) and title logo (logo.png), Ozzy 31 Oct 2026
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import reality_art as R
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from reletter import f as font, tracked, width

W, H, OW, OH = R.W, R.H, R.OW, R.OH
ease, amul, zoomed, cover_fit = R.ease, R.amul, R.zoomed, R.cover_fit
TEST = bool(os.environ.get("DOCS_TEST"))

# folder -> (title, subtitle, (dark, light) two tones, device, pool of (kind, title, year[, era of the footage]))
CARDS = {
    "Trending & Award-Winning Docs": ("TRENDING DOCS", "AWARD WINNERS & MOST-WATCHED STORIES", ((40, 30, 14), (250, 216, 150)), "laurels", [
        ("movie", "Free Solo", 2018, "ACADEMY AWARD|WINNER"), ("movie", "My Octopus Teacher", 2020, "ACADEMY AWARD|WINNER"),
        ("movie", "Navalny", 2022, "ACADEMY AWARD|WINNER"), ("movie", "20 Days in Mariupol", 2023, "ACADEMY AWARD|WINNER"),
        ("movie", "No Other Land", 2024, "ACADEMY AWARD|WINNER"), ("movie", "Icarus", 2017, "ACADEMY AWARD|WINNER"),
        ("movie", "American Factory", 2019, "ACADEMY AWARD|WINNER"), ("movie", "Searching for Sugar Man", 2012, "ACADEMY AWARD|WINNER"),
        ("movie", "Honeyland", 2019, "ACADEMY AWARD|NOMINEE"), ("movie", "Won't You Be My Neighbor?", 2018, "OFFICIAL|SELECTION")]),
    "Investigative & Scandals": ("INVESTIGATIVE", "DEEP DIVES, EXPOSÉS & SCANDALS", ((42, 8, 32), (236, 140, 176)), "redacted", [
        ("tv", "Dirty Money", 2018), ("movie", "The Social Dilemma", 2020), ("movie", "Blackfish", 2013), ("movie", "Fyre", 2019),
        ("movie", "The Tinder Swindler", 2022), ("tv", "Wild Wild Country", 2018), ("movie", "Inside Job", 2010),
        ("movie", "Enron: The Smartest Guys in the Room", 2005), ("movie", "Citizenfour", 2014)]),
    "Nature, Wildlife & Earth": ("NATURE & WILDLIFE", "UNTAMED HABITATS & PLANETARY WONDERS", ((12, 36, 26), (232, 222, 128)), "viewfinder", [
        ("tv", "Planet Earth II", 2016), ("tv", "Blue Planet II", 2017), ("tv", "Our Planet", 2019), ("tv", "Planet Earth", 2006),
        ("tv", "Seven Worlds, One Planet", 2019), ("movie", "March of the Penguins", 2005), ("tv", "The Green Planet", 2022),
        ("tv", "Frozen Planet", 2011), ("tv", "Life", 2009)]),
    "Science, Tech & Cosmos": ("SCIENCE & COSMOS", "SPACE EXPLORATION & QUANTUM REALMS", ((4, 24, 40), (120, 230, 255)), "telescope", [
        ("tv", "Cosmos: A Spacetime Odyssey", 2014), ("movie", "The Farthest", 2017), ("movie", "Particle Fever", 2013),
        ("tv", "Cosmos: Possible Worlds", 2020), ("tv", "Our Universe", 2022), ("movie", "AlphaGo", 2017),
        ("tv", "Inside Bill's Brain: Decoding Bill Gates", 2019), ("movie", "Return to Space", 2022), ("tv", "The Universe", 2007)]),
    "Sports & Athletic Stories": ("SPORTS STORIES", "LEGENDARY ATHLETES & ICONIC MOMENTS", ((40, 18, 8), (246, 174, 112)), "photofinish", [
        ("tv", "The Last Dance", 2020), ("tv", "Formula 1: Drive to Survive", 2019), ("movie", "Senna", 2010),
        ("movie", "Hoop Dreams", 1994), ("tv", "Welcome to Wrexham", 2022), ("tv", "Sunderland 'Til I Die", 2018),
        ("movie", "14 Peaks: Nothing Is Impossible", 2021), ("movie", "The Dawn Wall", 2018), ("tv", "Quarterback", 2023)]),
    "Music & Concert Documentaries": ("MUSIC & CONCERTS", "STAGE LIGHTS, SOUNDTRACKS & ICONIC ARTISTS", ((40, 8, 50), (255, 152, 230)), "levels", [
        ("movie", "Summer of Soul (...Or, When the Revolution Could Not Be Televised)", 2021), ("movie", "Amy", 2015),
        ("tv", "The Beatles: Get Back", 2021), ("movie", "Taylor Swift: The Eras Tour", 2023), ("movie", "Stop Making Sense", 1984),
        ("movie", "Gimme Shelter", 1970), ("movie", "What Happened, Miss Simone?", 2015), ("movie", "20 Feet from Stardom", 2013),
        ("movie", "Homecoming: A Film by Beyoncé", 2019)]),
    "True Crime & Serial Killers": ("TRUE CRIME", "FORENSIC INVESTIGATIONS & SERIAL KILLERS", ((52, 8, 18), (255, 150, 150)), "evidence", [
        ("tv", "Making a Murderer", 2015), ("tv", "The Jinx: The Life and Deaths of Robert Durst", 2015),
        ("tv", "Don't F**k with Cats: Hunting an Internet Killer", 2019), ("tv", "The Staircase", 2004),
        ("tv", "Conversations with a Killer: The Ted Bundy Tapes", 2019), ("movie", "American Murder: The Family Next Door", 2020),
        ("tv", "I'll Be Gone in the Dark", 2020), ("tv", "The Keepers", 2017), ("tv", "Evil Genius", 2018),
        ("movie", "Abducted in Plain Sight", 2017)]),
    "History, War & Civilizations": ("HISTORY & CIVILIZATIONS", "EMPIRES, ARCHIVES & WAR CHRONICLES", ((28, 20, 10), (236, 206, 156)), "archive", [
        ("movie", "They Shall Not Grow Old", 2018, "1914–1918"), ("tv", "The Vietnam War", 2017, "1955–1975"),
        ("tv", "World War II in Colour", 2009, "1939–1945"), ("movie", "Apollo 11", 2019, "1969"),
        ("tv", "The World at War", 1973, "1939–1945"), ("tv", "The Civil War", 1990, "1861–1865"),
        ("tv", "Apocalypse: The Second World War", 2009, "1939–1945"),
        ("tv", "Turning Point: The Bomb and the Cold War", 2024, "1945–1991"), ("tv", "Cold War", 1998, "1945–1991")]),
}


# ---------------------------------------------------------------- films
def docs_of(folder, n=3):
    pool = CARDS[folder][4]
    if TEST:
        import glob
        fs = [f for f in sorted(glob.glob("/home/claude/nuvio-art/mirror/files/*/*.jpg")) if os.path.getsize(f) > 150000]
        rnd = random.Random(folder)
        out = []
        while len(out) < n:
            p = rnd.choice(fs)
            im = Image.open(p)
            if im.width >= 1200 and 1.6 < im.width / im.height < 1.9:
                k, t, y = pool[len(out)][:3]
                out.append((t, "DOCUSERIES" if k == "tv" else "DOCUMENTARY", "NETFLIX", y, p, pool[len(out)][3] if len(pool[len(out)]) > 3 else str(y)))
        return out
    import kids_art as K
    m = dt.date.today().year * 12 + dt.date.today().month
    start = (m * n) % len(pool)
    out = []
    for it in pool[start:] + pool[:start]:
        kind, t, y = it[:3]
        era = it[3] if len(it) > 3 else str(y)
        a = K.art_of((kind, t, y))
        if not a:
            continue
        det = K.tmdb(f"/{kind}/{a[0]}") or {}
        nets = [x["name"] for x in det.get("networks", [])] if kind == "tv" else []
        name = det.get("name") or det.get("title") or t
        out.append((name, "DOCUSERIES" if kind == "tv" else "DOCUMENTARY", (nets[0] if nets else "").upper(), y, a[2], era))
        if len(out) == n:
            break
    return out


def load(p):
    if TEST:
        return Image.open(p).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


def duotone(im, dark, light):
    g = np.asarray(ImageEnhance.Contrast(im.convert("L")).enhance(1.15), np.float32)[..., None] / 255
    return Image.fromarray(np.clip(np.array(dark, np.float32) * (1 - g) + np.array(light, np.float32) * g, 0, 255).astype(np.uint8))


def label(title, kind, net, year, accent, maxw=W - 140):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    t = title.upper().replace(" | ", ": ")
    fn = font("ExtraBold", 44)
    while width(t, fn, 3) > maxw and fn.size > 24:
        fn = font("ExtraBold", fn.size - 2)
    y = H - 132
    d.rectangle((46, y + 6, 52, y + fn.size + 42), fill=accent + (255,))
    tracked(d, (68 + 2, y + 2), t, fn, (0, 0, 0, 150), 3)
    tracked(d, (68, y), t, fn, (255, 255, 255, 255), 3)
    sub = " · ".join(x for x in (kind, net, str(year)) if x)
    tracked(d, (70, y + fn.size + 12), sub, font("SemiBold", 20), accent + (255,), 6)
    return lay


# ---------------------------------------------------------------- devices
def polaroid(img, w=250):
    """A polaroid of the frame: white border, thicker at the bottom."""
    h = round(w * 0.8)
    ph = cover_fit(img, w, h)
    card = Image.new("RGBA", (w + 24, h + 70), (244, 240, 230, 255))
    card.paste(ph, (12, 12))
    return card


def case_stamp(p, n):
    """CASE FILE #n, stamped top right."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if p <= 0:
        return lay
    fn = font("ExtraBold", 40)
    t1, t2 = "CASE FILE", f"No. {n:04d}"
    st = Image.new("RGBA", (360, 140), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    red = (210, 30, 40)
    d.rectangle((4, 4, 355, 135), outline=red + (255,), width=6)
    tracked(d, (24, 16), t1, fn, red + (255,), 6)
    tracked(d, (26, 74), t2, font("SemiBold", 34), red + (255,), 8)
    a = np.asarray(st, np.float32)
    a[..., 3] *= np.clip(np.random.default_rng(n).random(a.shape[:2]) * 1.6, 0.4, 1)
    st = Image.fromarray(a.astype(np.uint8)).rotate(8, expand=True, resample=Image.BICUBIC)
    e = ease(p)
    sc = 1.5 - 0.5 * e
    st = st.resize((round(st.width * sc * 0.8), round(st.height * sc * 0.8)), Image.LANCZOS)
    lay.alpha_composite(amul(st, min(1, e * 1.5)), (round(W - 230 - st.width / 2), round(130 - st.height / 2)))
    return lay


PIN_SPOTS = [(W - 150, 300), (W - 300, 420), (W - 140, 520)]


def board(pins, accent):
    """The evidence pinned so far (small polaroids along the right) and the red string between them."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(x, y - 60) for (_, x, y, _) in pins]
    if len(pts) > 1:
        d.line(pts, fill=(200, 20, 30, 255), width=4)
    for pol, x, y, ang in pins:
        r = pol.rotate(ang, expand=True, resample=Image.BICUBIC)
        sh = Image.new("RGBA", r.size, (0, 0, 0, 0))
        sh.putalpha(r.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: round(v * 0.6)))
        lay.alpha_composite(sh, (round(x - r.width / 2) + 6, round(y - r.height / 2) + 8))
        lay.alpha_composite(r, (round(x - r.width / 2), round(y - r.height / 2)))
    for x, y in pts:
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(220, 30, 40, 255), outline=(90, 0, 0, 255), width=2)
    if len(pts) > 1:
        d.line(pts, fill=(200, 20, 30, 230), width=3)
    return lay


GRAIN = [np.random.default_rng(s).normal(0, 1, (H // 2, W // 2)).astype(np.float32) for s in range(6)]


def archive(img, f, tone, a=1.0):
    """Archive footage in the card's sepia: grain, flicker, gate weave, dust; a = how much of the archive is left."""
    if a <= 0:
        return img
    arr = np.asarray(img, np.float32)
    g = np.repeat(np.repeat(GRAIN[(f // 2) % 6], 2, 0), 2, 1)
    arr = arr + g[..., None] * 14 * a
    arr *= 1 + (0.04 * math.sin(f * 2.3) + 0.02 * math.sin(f * 5.1)) * a
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    dx, dy = round(1.6 * math.sin(f * 1.7) * a), round(1.2 * math.sin(f * 2.9) * a)
    im = im.transform(im.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR)
    d = ImageDraw.Draw(im)
    r = random.Random(f // 2)
    if a > 0.3:
        for _ in range(r.randint(1, 4)):
            x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(1, 3)
            d.ellipse((x - s, y - s, x + s, y + s), fill=r.choice([(20, 15, 10), (240, 230, 210)]))
        if r.random() < 0.4:
            x = r.uniform(W * 0.2, W * 0.8)
            d.line((x, 0, x + r.uniform(-6, 6), H), fill=(230, 220, 200), width=1)
    return im


def archive_tag(year, a):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if a <= 0:
        return lay
    import universe_motion as um
    um.FONTS.setdefault("typewriter", "apache/specialelite/SpecialElite-Regular.ttf")
    d = ImageDraw.Draw(lay)
    t = f"ARCHIVE FOOTAGE · {year}"
    fo = um.font("typewriter", 30)
    d.rectangle((W - 60 - d.textlength(t, font=fo) - 30, 40, W - 40, 92), fill=(20, 15, 10, round(200 * a)))
    d.text((W - 60 - d.textlength(t, font=fo) - 12, 50), t, font=fo, fill=(236, 206, 156, round(255 * a)))
    return lay


def laurels(text, accent, p):
    """A pair of festival laurels with the honour between them, bottom right."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if p <= 0:
        return lay
    top, bot = (text.split("|") + [""])[:2]
    S_ = 470
    im = Image.new("RGBA", (S_, 210), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (250, 230, 190, 255)
    cx, cy, rx, ry = S_ / 2, 100, 206, 86

    def almond(bx, by, ux, uy, L, wd, mir):
        nx, ny = -uy, ux
        pts = []
        for t in [i / 10 for i in range(11)]:
            w_ = wd * math.sin(math.pi * t) ** 0.8
            pts.append((bx + ux * L * t + nx * w_, by + uy * L * t + ny * w_))
        for t in [i / 10 for i in range(10, -1, -1)]:
            w_ = wd * math.sin(math.pi * t) ** 0.8
            pts.append((bx + ux * L * t - nx * w_, by + uy * L * t - ny * w_))
        if mir:
            pts = [(S_ - x, y) for x, y in pts]
        d.polygon(pts, fill=col)

    N_ = 8
    ths = [math.radians(108 + j * 15) for j in range(N_)]   # bottom-centre up the left side; open at the top
    stem = [(cx + rx * math.cos(t), cy + ry * math.sin(t)) for t in ths]
    for mir in (False, True):
        d.line([((S_ - x) if mir else x, y) for x, y in stem], fill=col, width=3)
        for j, th in enumerate(ths):
            x, y = stem[j]
            gx, gy = -rx * math.sin(th), ry * math.cos(th)        # growth direction
            g = math.hypot(gx, gy); gx, gy = gx / g, gy / g
            L = 30 - j * 1.6
            for side in (-1, 1):                                 # a leaf out and a leaf in
                a_ = math.radians(38 * side)
                ux = gx * math.cos(a_) - gy * math.sin(a_)
                uy = gx * math.sin(a_) + gy * math.cos(a_)
                almond(x, y, ux, uy, L, L * 0.26, mir)
        x, y = stem[-1]
        th = ths[-1]
        gx, gy = -rx * math.sin(th), ry * math.cos(th)
        g = math.hypot(gx, gy)
        almond(x, y, gx / g, gy / g, 24, 6, mir)
    f1, f2 = font("ExtraBold", 24), font("SemiBold", 20)
    for t_, f_, y in ((top, f1, 70), (bot, f2, 106)):
        tw = width(t_, f_, 4)
        tracked(d, (S_ / 2 - tw / 2, y), t_, f_, col, 4)
    e = ease(p)
    sc = 0.6 + 0.4 * e
    im = im.resize((round(S_ * sc), round(210 * sc)), Image.LANCZOS)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: round(v * 0.7)))
    x0, y0 = round(W - 250 - im.width / 2), round(H - 118 - im.height / 2)   # bottom right, clear of faces
    lay.alpha_composite(amul(sh, e), (x0 + 2, y0 + 3))
    lay.alpha_composite(amul(im, e), (x0, y0))
    return lay


def redactions(k, q):
    """Black redaction bars over the picture; q 0..1 = how far they have been pulled away (one after another)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(k * 7 + 3)
    n = 6
    for j in range(n):
        y = 90 + j * 88 + rnd.uniform(-10, 10)
        x0 = rnd.uniform(40, 260)
        x1 = rnd.uniform(W * 0.55, W - 60)
        qq = ease(q * 1.6 - j * 0.12)
        x1q = x1 - (x1 - x0) * qq
        if x1q - x0 > 2:
            d.rectangle((x0, y, x1q, y + 54), fill=(6, 6, 8, 245))
            if x1q - x0 > 220:
                tracked(d, (x0 + 18, y + 14), "REDACTED", font("ExtraBold", 22), (60, 60, 64, 255), 6)
    return lay


def viewfinder(i, accent):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    m, L, t = 40, 70, 4
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.rectangle([min(x, x + sx * L), min(y, y + sy * t), max(x, x + sx * L), max(y, y + sy * t)], fill=(255, 255, 255, 220))
        d.rectangle([min(x, x + sx * t), min(y, y + sy * L), max(x, x + sx * t), max(y, y + sy * L)], fill=(255, 255, 255, 220))
    cx, cy = W / 2, H / 2
    d.rectangle((cx - 40, cy - 1, cx + 40, cy + 1), fill=(255, 255, 255, 150))
    d.rectangle((cx - 1, cy - 40, cx + 1, cy + 40), fill=(255, 255, 255, 150))
    fn = font("SemiBold", 22)
    if (i // 10) % 2 == 0:
        d.ellipse((W - 250, 76, W - 234, 92), fill=(230, 40, 40, 240))
    tracked(d, (W - 224, 70), "REC", fn, (255, 255, 255, 230), 4)
    tracked(d, (W - 224, 100), "4K · 60P", fn, (255, 255, 255, 200), 3)
    tracked(d, (W - 224, 130), "ƒ/5.6  ·  600MM", fn, (255, 255, 255, 180), 2)
    return lay


def telescope(i, open_, accent):
    """An eyepiece: dark outside a circle that opens up with the bloom; reticle and coordinates."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r = H * 0.42 + (W * 0.75 - H * 0.42) * ease(open_)
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=0)
    m = m.filter(ImageFilter.GaussianBlur(18))
    dark = Image.new("RGBA", (W, H), (2, 6, 12, 0))
    dark.putalpha(m.point(lambda v: round(v * 0.92)))
    lay.alpha_composite(dark)
    d = ImageDraw.Draw(lay)
    a = round(200 * (1 - ease(open_) * 0.6))
    d.ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), outline=accent + (a,), width=3)
    for k_ in range(0, 360, 10):
        rr = r - (14 if k_ % 30 == 0 else 7)
        x0, y0 = W / 2 + r * math.cos(math.radians(k_)), H / 2 + r * math.sin(math.radians(k_))
        x1, y1 = W / 2 + rr * math.cos(math.radians(k_)), H / 2 + rr * math.sin(math.radians(k_))
        d.line((x0, y0, x1, y1), fill=accent + (a,), width=2)
    d.line((W / 2 - 60, H / 2, W / 2 - 14, H / 2), fill=accent + (a,), width=2)
    d.line((W / 2 + 14, H / 2, W / 2 + 60, H / 2), fill=accent + (a,), width=2)
    d.line((W / 2, H / 2 - 60, W / 2, H / 2 - 14), fill=accent + (a,), width=2)
    d.line((W / 2, H / 2 + 14, W / 2, H / 2 + 60), fill=accent + (a,), width=2)
    fn = font("SemiBold", 20)
    ra = 5 + i * 0.013
    dec = -5.391 + i * 0.002
    tracked(d, (W - 300, 70), f"RA  {int(ra):02d}h {int(ra % 1 * 60):02d}m {(ra * 3600) % 60:04.1f}s", fn, accent + (230,), 2)
    tracked(d, (W - 300, 98), f"DEC {dec:+.3f}°", fn, accent + (230,), 2)
    tracked(d, (W - 300, 126), "MAG 4.2  ·  TRACKING", fn, accent + (200,), 2)
    return lay


def stopwatch(sec, fin, accent):
    """A running clock; at the end a finish line sweeps across and the clock stops."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x1, y0 = W - 48, 44
    box = (x1 - 290, y0, x1, y0 + 92)
    d.rounded_rectangle(box, radius=14, fill=(10, 10, 12, 220), outline=accent + (255,), width=3)
    s_ = f"{int(sec // 60):02d}:{sec % 60:05.2f}"
    tracked(d, (box[0] + 22, y0 + 14), s_, font("ExtraBold", 52), ((255, 70, 60) if fin > 0 else (255, 255, 255)) + (255,), 2)
    if fin > 0:
        x = W * (1.1 - 1.2 * ease(fin))
        d.rectangle((x - 3, 0, x + 3, H), fill=(255, 60, 50, 230))
        g = Image.new("RGBA", (W, H), (255, 60, 50, 0))
        gm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(gm).rectangle((x - 3, 0, x + 3, H), fill=255)
        g.putalpha(gm.filter(ImageFilter.GaussianBlur(10)))
        lay.alpha_composite(g)
        tracked(d, (box[0], y0 + 104), "PHOTO FINISH", font("ExtraBold", 22), (255, 70, 60, round(255 * min(1, fin * 3))), 5)
    return lay


def levels(i, accent):
    """Stage lights sweeping from above and a level meter jumping to the music, bottom right."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for j, col in enumerate(((255, 120, 220), (120, 160, 255), (255, 210, 120))):
        x = W * (0.2 + 0.3 * j) + 160 * math.sin(i * 0.12 + j * 2.1)
        cone = Image.new("L", (W, H), 0)
        ImageDraw.Draw(cone).polygon([(x - 20, -10), (x + 20, -10), (x + 220, H), (x - 220, H)], fill=70)
        cone = cone.filter(ImageFilter.GaussianBlur(30))
        g = Image.new("RGBA", (W, H), col + (0,))
        g.putalpha(cone)
        lay.alpha_composite(g)
    d = ImageDraw.Draw(lay)
    n, bw, gap = 22, 12, 6
    x0, yb = W - 48 - n * (bw + gap), 190
    for j in range(n):
        h = 20 + 90 * abs(math.sin(i * 0.45 + j * 0.7) * math.sin(i * 0.17 + j * 0.31))
        d.rounded_rectangle((x0 + j * (bw + gap), yb - h, x0 + j * (bw + gap) + bw, yb), radius=3, fill=accent + (235,))
    return lay


# ---------------------------------------------------------------- the card
def slug_of(t):
    return R.slug_of(t)


def build(folder, out):
    title, sub, (dark, light), device, _ = CARDS[folder]
    accent = tuple(min(255, int(v)) for v in light)
    docs = docs_of(folder)
    pics = [cover_fit(load(d_[4])) for d_ in docs]
    tones = [duotone(p, dark, light) for p in pics]
    fl = R.fall()
    tb = R.title_block(title, sub, accent)
    tg = R.tag(title, accent)
    labels = [label(t, k, nw, y, accent, W - 580 if device == "laurels" else W - 140) for t, k, nw, y, _, _ in docs]
    cv = tones[0].convert("RGBA")
    cv.alpha_composite(fl)
    cv.alpha_composite(tb)
    cover = cv.convert("RGB")
    HOLD, DOCK, SEG, BACK = 6, 12, 48, 14
    S = len(docs)
    T1 = HOLD + DOCK
    T2 = T1 + SEG * S
    N_ = T2 + BACK
    BLOOM0, BLOOM1, OUT0 = 16, 30, SEG - 10   # within a segment: two tones, bloom, colour, hand over
    pins = []
    pol_angles = [-6, 5, -3]
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < T1:
            u = (i - HOLD) / DOCK
            base = zoomed(tones[0], 0.01 * u)
            if device == "archive":
                base = archive(base, i, (dark, light), ease(u))
            c = base.convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(amul(tb, 1 - ease(u * 1.6)))
            c.alpha_composite(amul(tg, ease((u - 0.3) / 0.7)), (40, 34))
            if device == "evidence":
                c.alpha_composite(case_stamp(ease((u - 0.4) / 0.6), 1047))
            if device == "archive":
                c.alpha_composite(archive_tag(docs[0][5], ease((u - 0.4) / 0.6)))
            c.alpha_composite(amul(labels[0], ease((u - 0.5) / 0.5)))
        elif i < T2:
            k, t = divmod(i - T1, SEG)
            z = 0.01 + 0.05 * t / SEG
            bloom = ease((t - BLOOM0) / (BLOOM1 - BLOOM0))
            pic = Image.blend(zoomed(tones[k], z), zoomed(pics[k], z), bloom)
            if device == "viewfinder":   # the focus is pulled from soft to sharp
                rb = 9 * (1 - ease(t / 18))
                if rb > 0.3:
                    pic = pic.filter(ImageFilter.GaussianBlur(rb))
            if device == "archive":
                pic = archive(pic, i, (dark, light), 1 - bloom * 0.85)
            last = k == S - 1
            la = 1.0
            if k > 0 and t < 8:
                prev = zoomed(pics[k - 1], 0.06)
                if device == "archive":   # a splice: a flash, then the next reel
                    pic = Image.blend(prev, pic, ease(t / 8))
                    if t < 2:
                        pic = Image.blend(pic, Image.new("RGB", (W, H), (245, 235, 210)), 0.6 * (1 - t / 2))
                else:
                    pic = Image.blend(prev, pic, ease(t / 8))
                la = ease(t / 8)
            c = pic.convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(tg, (40, 34))
            if device == "laurels":
                c.alpha_composite(laurels(docs[k][5], accent, ease((t - 4) / 8) * (1 - ease((t - (SEG - 6)) / 6) if not last else 1)))
            elif device == "redacted":
                c.alpha_composite(redactions(k, (t - 2) / (BLOOM0 - 2)))
            elif device == "viewfinder":
                c.alpha_composite(viewfinder(i, accent))
            elif device == "telescope":
                c.alpha_composite(telescope(i, bloom, accent))
            elif device == "photofinish":
                fin = ease((t - OUT0) / (SEG - OUT0 - 2)) if t >= OUT0 else 0.0
                sec = (min(t, OUT0) / 20.0) * 7.3 + k * 3.1 + 9.4
                c.alpha_composite(stopwatch(sec, fin, accent))
            elif device == "levels":
                c.alpha_composite(levels(i, accent))
            if device == "evidence":
                stamp_p = 1.0 if k == 0 else ease((t - 4) / 6)
                c.alpha_composite(case_stamp(stamp_p, 1047 + 13 * k))
                cur = list(pins)
                if t >= OUT0 and not last:
                    # the film is pinned up: it shrinks into a polaroid and flies to the board
                    u = ease((t - OUT0) / (SEG - OUT0))
                    pol = polaroid(pics[k])
                    x1, y1 = PIN_SPOTS[len(pins)]
                    sc = 2.2 + (0.55 - 2.2) * u
                    pp = pol.resize((max(1, round(pol.width * sc)), max(1, round(pol.height * sc))), Image.LANCZOS)
                    x = W / 2 + (x1 - W / 2) * u
                    y = H / 2 + (y1 - H / 2) * u
                    r = pp.rotate(pol_angles[len(pins)] * u, expand=True, resample=Image.BICUBIC)
                    c.alpha_composite(board(cur, accent))
                    c.alpha_composite(amul(r, ease(u * 3)), (round(x - r.width / 2), round(y - r.height / 2)))
                    la = 1 - ease(u * 2)
                    if t == SEG - 1:
                        small = pol.resize((round(pol.width * 0.55), round(pol.height * 0.55)), Image.LANCZOS)
                        pins.append((small, x1, y1, pol_angles[len(pins)]))
                else:
                    c.alpha_composite(board(cur, accent))
            if device == "archive":
                c.alpha_composite(archive_tag(docs[k][5], 1 - bloom))
            if not (device == "evidence" and t >= OUT0 and not last):
                if t >= SEG - 6 and not last:
                    la = 1 - ease((t - (SEG - 6)) / 6)
            c.alpha_composite(amul(labels[k], la))
        else:
            u = ease((i - T2) / BACK)
            c = Image.blend(zoomed(pics[-1], 0.06), tones[0], u).convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(amul(tg, 1 - u), (40, 34))
            if device == "evidence":
                c.alpha_composite(amul(board(pins, accent), 1 - u))
                c.alpha_composite(amul(case_stamp(1, 1047 + 13 * (S - 1)), 1 - u))
            c.alpha_composite(amul(labels[-1], 1 - ease(u * 2)))
            c.alpha_composite(amul(tb, ease((u - 0.3) / 0.7)))
        frames.append(c.convert("RGB").resize((OW, OH), Image.LANCZOS))
    d = os.path.join(out, slug_of(folder))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    hero_styles.scene(tones[0]).save(os.path.join(d, "backdrop.jpg"), quality=86)
    tb.crop(tb.getchannel("A").getbbox()).save(os.path.join(d, "logo.png"))
    n = len(frames)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 16, 30, 45, 58, 80, 110, n - 6]):
        strip.paste(frames[min(idx, n - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return [f"{t} ({y})" for t, _, _, y, _, _ in docs]


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
