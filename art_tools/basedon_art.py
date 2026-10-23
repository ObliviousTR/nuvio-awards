"""Based On row, "from source to screen": three adaptations play on each card, and each one first appears in the
language of what it was adapted from, then turns into the film itself:
  Comics       an inked, halftoned comic panel; the film shows through growing halftone dots
  Video Games  a 16-colour pixel screen with a HUD; the resolution steps up until it is the film
  Books        a printed title page (title, author); the page turns and the film is underneath
  True Stories an old sepia print on a table; it straightens, fills the card and takes on colour
  Mythology    a black-figure vase painting with a meander band; it flakes away into the film
Under the card's name: the film and its source. Pictures: fanart.tv / TMDB textless art. The trio moves on every
month through each card's pool (.github/workflows/basedon-art.yml -> basedon-art); the cover stays.
usage: python3 art_tools/basedon_art.py OUT_DIR [folder titles...]     (BASEDON_TEST=1: local stills, no network)
"""
import datetime as dt, math, os, random, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from reletter import f as font, tracked, width

W, H = 1280, 720
OW, OH = 512, 288
TEST = bool(os.environ.get("BASEDON_TEST"))

# folder -> (word on the emblem, look, pool); items: (kind, title, year, source line[, extra])
#   extra: books -> the book's title when it differs; true stories -> the year stamped on the print
CARDS = {
    "Comics & Graphic Novels": ("COMICS", "comic", [
        ("movie", "The Dark Knight", 2008, "DC COMICS"), ("movie", "Spider-Man: Into the Spider-Verse", 2018, "MARVEL COMICS"),
        ("movie", "Watchmen", 2009, "ALAN MOORE & DAVE GIBBONS"), ("movie", "Sin City", 2005, "FRANK MILLER"),
        ("movie", "V for Vendetta", 2005, "ALAN MOORE & DAVID LLOYD"), ("movie", "Joker", 2019, "DC COMICS"),
        ("tv", "The Boys", 2019, "GARTH ENNIS & DARICK ROBERTSON"), ("movie", "Scott Pilgrim vs. the World", 2010, "BRYAN LEE O'MALLEY"),
        ("movie", "Oldboy", 2003, "THE MANGA BY GARON TSUCHIYA"), ("movie", "Logan", 2017, "MARVEL COMICS")]),
    "Video Games": ("VIDEO GAMES", "game", [
        ("tv", "Arcane", 2021, "LEAGUE OF LEGENDS"), ("tv", "Fallout", 2024, "THE FALLOUT GAMES"),
        ("movie", "The Super Mario Bros. Movie", 2023, "NINTENDO'S SUPER MARIO"), ("movie", "Sonic the Hedgehog", 2020, "SEGA'S SONIC"),
        ("movie", "Detective Pikachu", 2019, "POKÉMON"), ("tv", "Castlevania", 2017, "KONAMI'S CASTLEVANIA"),
        ("movie", "Uncharted", 2022, "NAUGHTY DOG'S UNCHARTED"), ("tv", "The Last of Us", 2023, "NAUGHTY DOG'S THE LAST OF US"),
        ("movie", "Silent Hill", 2006, "KONAMI'S SILENT HILL")]),
    "Books & Literature": ("BOOKS", "book", [
        ("movie", "The Godfather", 1972, "MARIO PUZO"), ("movie", "Dune", 2021, "FRANK HERBERT"),
        ("movie", "The Lord of the Rings: The Fellowship of the Ring", 2001, "J.R.R. TOLKIEN", "The Fellowship of the Ring"),
        ("movie", "Gone Girl", 2014, "GILLIAN FLYNN"), ("movie", "The Silence of the Lambs", 1991, "THOMAS HARRIS"),
        ("movie", "Fight Club", 1999, "CHUCK PALAHNIUK"), ("movie", "No Country for Old Men", 2007, "CORMAC McCARTHY"),
        ("movie", "Pride & Prejudice", 2005, "JANE AUSTEN", "Pride and Prejudice"),
        ("movie", "The Shawshank Redemption", 1994, "STEPHEN KING", "Rita Hayworth and Shawshank Redemption")]),
    "True Stories & Biographies": ("TRUE STORIES", "true", [
        ("movie", "Schindler's List", 1993, "THE LIFE OF OSKAR SCHINDLER"), ("movie", "Apollo 13", 1995, "THE APOLLO 13 MISSION", "1970"),
        ("movie", "The Social Network", 2010, "THE FOUNDING OF FACEBOOK", "2004"), ("movie", "Catch Me If You Can", 2002, "THE LIFE OF FRANK ABAGNALE JR."),
        ("tv", "Chernobyl", 2019, "THE CHERNOBYL DISASTER", "1986"), ("movie", "Ford v Ferrari", 2019, "THE 1966 LE MANS RACE", "1966"),
        ("movie", "Rush", 2013, "THE HUNT–LAUDA RIVALRY", "1976"), ("movie", "Bohemian Rhapsody", 2018, "THE STORY OF QUEEN", "1985"),
        ("movie", "Oppenheimer", 2023, "THE LIFE OF J. ROBERT OPPENHEIMER", "1945")]),
    "Mythology & Folklore": ("MYTHOLOGY", "myth", [
        ("movie", "Troy", 2004, "HOMER'S ILIAD"), ("movie", "O Brother, Where Art Thou?", 2000, "HOMER'S ODYSSEY"),
        ("movie", "The Northman", 2022, "THE LEGEND OF AMLETH"), ("movie", "The Green Knight", 2021, "ARTHURIAN LEGEND"),
        ("movie", "Thor", 2011, "NORSE MYTHOLOGY"), ("movie", "Moana", 2016, "POLYNESIAN MYTHOLOGY"),
        ("movie", "Clash of the Titans", 1981, "GREEK MYTHOLOGY"), ("movie", "Jason and the Argonauts", 1963, "GREEK MYTHOLOGY"),
        ("movie", "Beowulf", 2007, "THE OLD ENGLISH EPIC"), ("movie", "300", 2007, "THE LEGEND OF THERMOPYLAE")]),
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
    return um.font(name, size, weight)


# ---------------------------------------------------------------- source looks
def comic(real):
    import cv2
    a = np.asarray(real.convert("RGB"))
    sm = a
    for _ in range(2):
        sm = cv2.bilateralFilter(sm, 9, 70, 70)
    # flat colours (k-means on a small copy)
    small = cv2.resize(sm, (320, 180)).reshape(-1, 3).astype(np.float32)
    _, lab, cent = cv2.kmeans(small, 9, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    d = ((sm.reshape(-1, 1, 3).astype(np.float32) - cent[None]) ** 2).sum(2)
    flat = cent[d.argmin(1)].reshape(sm.shape)
    hsv = cv2.cvtColor(flat.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] * 1.08 + 8, 0, 255)
    flat = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    # ink: adaptive threshold on the smoothed grey + strong edges
    g = cv2.medianBlur(cv2.cvtColor(sm, cv2.COLOR_RGB2GRAY), 7)
    ink = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 5).astype(np.float32) / 255
    ed = cv2.Canny(g, 60, 140)
    ed = cv2.dilate(ed, np.ones((2, 2), np.uint8))
    ink = np.minimum(ink, 1 - ed.astype(np.float32) / 255)
    # halftone: dots on a 45-degree grid, bigger in the shadows
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sp = 9.0
    u, v = (xx + yy) / math.sqrt(2) / sp, (xx - yy) / math.sqrt(2) / sp
    du, dv = u - np.round(u), v - np.round(v)
    dist = np.sqrt(du * du + dv * dv)
    lum = g.astype(np.float32) / 255
    r = np.clip((0.75 - lum) * 0.75, 0, 0.62)
    dots = np.clip((r - dist) * 6, 0, 1)
    out = flat * (1 - 0.45 * dots[..., None]) * ink[..., None]
    paper = np.array([246, 239, 222], np.float32)
    out = out * 0.92 + paper * 0.08
    page = Image.new("RGB", (W, H), tuple(int(v) for v in paper))
    m = 26
    panel = img(out).resize((W - 2 * m, H - 2 * m), Image.LANCZOS)
    page.paste(panel, (m, m))
    ImageDraw.Draw(page).rectangle((m - 1, m - 1, W - m, H - m), outline=(10, 10, 10), width=7)
    return page


def comic_to_real(src, real, u):
    """The film shows through halftone dots that grow until they close up."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sp = 22.0
    du = (xx / sp) - np.round(xx / sp)
    dv = (yy / sp) - np.round(yy / sp)
    dist = np.sqrt(du * du + dv * dv)
    # dots start from the middle of the card and spread out
    cx = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    r = np.clip(u * 1.9 - cx * 1.2, 0, 0.75)
    m = np.clip((r - dist) * 10, 0, 1)[..., None]
    return img(arr(src) * (1 - m) + arr(real) * m)


PICO = [(0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81), (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
        (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54), (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170)]


def pixels(real, block, pal=1.0):
    sw, sh = max(1, W // block), max(1, H // block)
    sm = real.resize((sw, sh), Image.BOX)
    if pal > 0:
        p = Image.new("P", (1, 1))
        p.putpalette([c for col in PICO for c in col] + [0] * (768 - 48))
        q = ImageEnhance.Color(ImageEnhance.Contrast(sm).enhance(1.2)).enhance(1.3).quantize(palette=p, dither=Image.Dither.NONE).convert("RGB")
        sm = Image.blend(sm, q, pal)
    return sm.resize((W, H), Image.NEAREST)


def hud(level=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    f = ufont("pixel", 22)
    a = round(255 * level)
    for (x, y, t) in ((W // 2 - 300, 34, "1UP 004200"), (W // 2 + 20, 34, "STAGE 1-1"), (W - 300, 74, "HI 099990")):
        d.text((x + 3, y + 3), t, font=f, fill=(0, 0, 0, a))
        d.text((x, y), t, font=f, fill=(255, 255, 255, a))
    for k in range(3):  # hearts
        x, y = W - 300 + k * 34, 112
        d.polygon([(x, y + 6), (x + 6, y), (x + 12, y + 4), (x + 18, y), (x + 24, y + 6), (x + 12, y + 20)], fill=(255, 0, 77, a))
    return lay


def scanlines(im, k=0.82):
    a = arr(im)
    a[::4] *= k
    a[1::4] *= (k + 1) / 2
    return img(a)


def game(real):
    out = scanlines(pixels(real, 16)).convert("RGBA")
    out.alpha_composite(hud())
    return out.convert("RGB")


STEPS = [16, 12, 9, 6, 4, 3, 2, 1]


def game_to_real(src, real, u):
    if u <= 0:
        return src
    k = min(len(STEPS) - 1, int(u * len(STEPS)))
    b = STEPS[k]
    im = pixels(real, b, pal=max(0.0, 1 - u * 1.6)) if b > 1 else real
    if b > 1:
        im = scanlines(im, 0.82 + 0.18 * u)
    out = im.convert("RGBA")
    if u < 0.5:
        out.alpha_composite(hud(1 - u * 2))
    return out.convert("RGB")


def paper(seed=3):
    rnd = np.random.default_rng(seed)
    base = np.ones((H, W, 3), np.float32) * np.array([236, 226, 202], np.float32)
    n = rnd.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    fine = rnd.normal(0, 4, (H, W)).astype(np.float32)
    base += ((n - 0.5) * 14 + fine)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    base *= (1 - np.clip(v - 0.55, 0, 1) * 0.35)[..., None]
    sp = np.clip(1 - np.abs(xx - 0) / 60, 0, 1) ** 2  # spine shadow at the left edge
    base *= (1 - 0.35 * sp)[..., None]
    return img(base)


def wrap(text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


def book(real, title, author):
    pg = paper()
    d = ImageDraw.Draw(pg)
    ink = (48, 36, 24)
    cx = W * 0.56
    fz = 66
    tf = ufont("garamond", fz, 500)
    lines = wrap(title, tf, W * 0.62)
    while len(lines) > 3 and fz > 40:
        fz -= 6
        tf = ufont("garamond", fz, 500)
        lines = wrap(title, tf, W * 0.62)
    lh = fz * 1.15
    total = lh * len(lines)
    y = H * 0.38 - total / 2
    sf = ufont("garamond", 22, 500)
    t0 = "A NOVEL"
    tw = width(t0, sf, 8)
    tracked(d, (cx - tw / 2, y - 64), t0, sf, ink, 8)
    for l in lines:
        lw = d.textlength(l, font=tf)
        d.text((cx - lw / 2, y), l, font=tf, fill=ink)
        y += lh
    d.line((cx - 60, y + 26, cx + 60, y + 26), fill=ink, width=2)
    af = ufont("garamond", 30, 500)
    aw = width(author, af, 6)
    tracked(d, (cx - aw / 2, y + 52), author, af, ink, 6)
    return pg


def book_to_real(src, real, u):
    """The page turns from the right edge over to the spine; the film is underneath."""
    if u <= 0:
        return src
    if u >= 1:
        return real
    e = ease(u)
    out = real.copy()
    pw = max(1, round(W * (1 - e)))
    page = src.resize((pw, H), Image.LANCZOS)
    # the lifting side darkens as it turns
    g = np.linspace(1, 0.55 + 0.45 * (1 - e), pw, dtype=np.float32)
    pa = arr(page) * g[None, :, None]
    out.paste(img(pa), (0, 0))
    # shadow the page casts on the film
    sh = np.ones((H, W), np.float32)
    xs = np.arange(W, dtype=np.float32)
    sh *= 1 - 0.55 * np.clip(1 - (xs - pw) / (W * 0.12), 0, 1)[None, :] * (xs >= pw)[None, :] * math.sin(math.pi * e)
    return img(arr(out) * sh[..., None])


def sepia(real):
    g = arr(real).mean(2)
    g = np.clip((g - 128) * 1.15 + 128, 0, 255)
    rnd = np.random.default_rng(5)
    g = g + rnd.normal(0, 9, g.shape)
    s = np.stack([g * 1.0 + 18, g * 0.86 + 10, g * 0.66], 2)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    s *= (1 - np.clip(v - 0.5, 0, 1) * 0.7)[..., None]
    return img(s).filter(ImageFilter.GaussianBlur(0.8))


def print_on_table(photo, stamp, scale, angle, border_a=1.0):
    """The photo as a print (aged white border, the year typed under it) lying on a dark table."""
    table = Image.new("RGB", (W, H), (16, 13, 11))
    bw = 30
    pw, ph = round(W * scale), round(H * scale)
    pr = Image.new("RGB", (pw + 2 * bw, ph + 2 * bw + (30 if stamp else 0)), (232, 224, 204))
    pr.paste(photo.resize((pw, ph), Image.LANCZOS), (bw, bw))
    if stamp:
        f = ufont("typewriter", 26)
        ImageDraw.Draw(pr).text((bw, ph + bw + 8), stamp, font=f, fill=(90, 70, 50))
    pr = pr.convert("RGBA")
    if border_a < 1:
        full = photo.resize((pw + 2 * bw, pr.height), Image.LANCZOS).convert("RGBA")
        pr = Image.blend(full, pr, border_a)
    rot = pr.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", rot.size, (0, 0, 0, 0))
    sh.putalpha(rot.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: round(v * 0.7)))
    out = table.convert("RGBA")
    x, y = (W - rot.width) // 2, (H - rot.height) // 2
    out.alpha_composite(sh, (x + 10, y + 16))
    out.alpha_composite(rot, (x, y))
    return out.convert("RGB")


def true_look(real, stamp):
    return print_on_table(sepia(real), stamp, 0.66, -4)


def true_to_real(src, real, u, stamp=None):
    if u <= 0:
        return src
    e = ease(u)
    photo = Image.blend(sepia(real), real, ease((u - 0.35) / 0.65))
    sc = 0.66 + (1 + 0.1 - 0.66) * e   # grows past the card so the border leaves the frame
    out = print_on_table(photo, stamp if e < 0.5 else None, sc, -4 * (1 - e), border_a=1 - ease((u - 0.5) / 0.5))
    return out if u < 1 else real


TERRA = np.array([196, 102, 52], np.float32)


def meander(lay, y0, h, col=(18, 12, 8)):
    """A Greek key band between two rules."""
    W = lay.width
    d = ImageDraw.Draw(lay)
    d.rectangle((0, y0, W, y0 + 5), fill=col)
    d.rectangle((0, y0 + h - 5, W, y0 + h), fill=col)
    s = (h - 18) / 4
    x = 0.0
    lw = max(3, round(s * 0.55))
    top = y0 + 9
    while x < W:
        p = [(x, top + 4 * s), (x, top), (x + 3 * s, top), (x + 3 * s, top + 3 * s), (x + s, top + 3 * s), (x + s, top + s),
             (x + 2 * s, top + s), (x + 2 * s, top + 2 * s)]
        d.line(p, fill=col, width=lw, joint="curve")
        d.line([(x, top + 4 * s), (x + 4 * s, top + 4 * s)], fill=col, width=lw)
        x += 4 * s


def myth(real):
    import cv2
    a = np.asarray(real.convert("RGB"))
    g = cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), (0, 0), 3).astype(np.float32)
    t = np.percentile(g, 52)
    fig = (g < t).astype(np.uint8)
    fig = cv2.morphologyEx(fig, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    fig = cv2.morphologyEx(fig, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32)
    fig = cv2.GaussianBlur(fig, (0, 0), 1.2)
    # incised detail: edges inside the black figures scratched back to the clay
    ed = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), (0, 0), 1.5), 50, 120).astype(np.float32) / 255
    inc = ed * (fig > 0.6)
    rnd = np.random.default_rng(7)
    clay = TERRA[None, None] * (1 + rnd.normal(0, 0.035, (H, W, 1)).astype(np.float32))
    blk = np.array([22, 14, 10], np.float32)
    out = clay * (1 - fig[..., None]) + blk * fig[..., None]
    out = out * (1 - inc[..., None] * 0.85) + clay * inc[..., None] * 0.85
    im = img(out).convert("RGBA")
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.rectangle((0, 0, W, 70), fill=tuple(int(v) for v in TERRA) + (255,))
    bd.rectangle((0, H - 70, W, H), fill=tuple(int(v) for v in TERRA) + (255,))
    meander(band, 8, 56)
    meander(band, H - 64, 56)
    im.alpha_composite(band)
    return im.convert("RGB")


_NOISE = {}


def myth_to_real(src, real, u):
    """The paint flakes off in patches and the film is underneath."""
    if "n" not in _NOISE:
        rnd = np.random.default_rng(11)
        n = rnd.random((H // 24, W // 24)).astype(np.float32)
        _NOISE["n"] = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    n = _NOISE["n"]
    m = np.clip((u * 1.3 - n) * 8, 0, 1)[..., None]
    return img(arr(src) * (1 - m) + arr(real) * m)


LOOKS = {"comic": (comic, comic_to_real), "game": (game, game_to_real), "book": (book, book_to_real),
         "true": (true_look, true_to_real), "myth": (myth, myth_to_real)}


# ---------------------------------------------------------------- pictures
def art_of(item):
    if TEST:
        import glob
        fs = [f for f in sorted(glob.glob("/home/claude/nuvio-art/mirror/files/*/*.jpg")) if os.path.getsize(f) > 150000]
        rnd = random.Random(item[1])
        for _ in range(50):
            p = rnd.choice(fs)
            im = Image.open(p)
            if im.width >= 1200 and 1.6 < im.width / im.height < 1.9:
                return p
        return fs[0]
    import kids_art as K
    a = K.art_of(item[:3])
    return a[2] if a else None


def load(p):
    if TEST:
        return Image.open(p).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


def trio(pool, n=3, avoid=None):
    m = dt.date.today().year * 12 + dt.date.today().month
    start = (m * n) % len(pool)
    out = []
    for it in pool[start:] + pool[:start]:
        if avoid and it[1] == avoid:
            continue
        p = art_of(it)
        if p:
            out.append((it, p))
        if len(out) == n:
            break
    return out


# ---------------------------------------------------------------- lettering
def fall():
    yy = np.linspace(0, 1, H, dtype=np.float32)
    f = np.clip((yy - 0.55) / 0.45, 0, 1) ** 1.3 * 0.86
    m = Image.fromarray((np.repeat(f[:, None], W, 1) * 255).astype(np.uint8))
    lay = Image.new("RGBA", (W, H), (6, 5, 5, 0))
    lay.putalpha(m)
    return lay


def sub_layer(title, source):
    """Under the films: the title, and what it was adapted from."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    t = title.upper()
    fz = 46
    while width(t, font("ExtraBold", fz), 3) > W - 140 and fz > 26:
        fz -= 2
    tracked(d, (58, H - 118), t, font("ExtraBold", fz), (255, 255, 255, 255), 3)
    src = "BASED ON " + source
    fn = font("SemiBold", 21)
    while width(src, fn, 6) > W - 140 and fn.size > 14:
        fn = font("SemiBold", fn.size - 1)
    tracked(d, (61, H - 118 + fz + 12), src, fn, (226, 196, 140, 255), 6)
    return lay


def amul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


# ---------------------------------------------------------------- emblems: the card's name in its source's own language
def trim(im):
    bb = im.getchannel("A").getbbox()
    return im.crop(bb) if bb else im


def text_img(text, fnt, fill, stroke=0, stroke_fill=(0, 0, 0, 255), sp=0, shadow=None):
    w_ = round(width(text, fnt, sp)) + 4 * stroke + 60
    h_ = round(fnt.size * 1.6) + 4 * stroke + 60
    lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x, y = 2 * stroke + 20, 2 * stroke + 10
    if shadow:
        dx, dy, col = shadow
        xx = x + dx
        for ch in text:
            d.text((xx, y + dy), ch, font=fnt, fill=col, stroke_width=stroke, stroke_fill=col)
            xx += d.textlength(ch, font=fnt) + sp
    xx = x
    for ch in text:
        d.text((xx, y), ch, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        xx += d.textlength(ch, font=fnt) + sp
    return trim(lay)


def stack(parts, gap=18):
    w_ = max(p.width for p in parts)
    h_ = sum(p.height for p in parts) + gap * (len(parts) - 1)
    out = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    y = 0
    for p in parts:
        out.alpha_composite(p, ((w_ - p.width) // 2, y))
        y += p.height + gap
    return out


def emblem(look, word):
    if look == "comic":
        big = text_img(word, ufont("bangers", 190), (255, 214, 10, 255), stroke=9, sp=6, shadow=(12, 12, (0, 0, 0, 255)))
        top = text_img("BASED ON", ufont("bangers", 60), (255, 255, 255, 255), stroke=5, sp=4)
        inner = stack([top, big], 6)
        bw, bh = inner.width * 1.5, inner.height * 1.75
        burst = Image.new("RGBA", (round(bw) + 40, round(bh) + 40), (0, 0, 0, 0))
        cx, cy = burst.width / 2, burst.height / 2
        pts = []
        n = 22
        rnd = random.Random(4)
        for k in range(n * 2):
            ang = math.pi * k / n
            r = (1.0 if k % 2 == 0 else 0.74 + rnd.uniform(-0.04, 0.04))
            pts.append((cx + math.cos(ang) * bw / 2 * r, cy + math.sin(ang) * bh / 2 * r))
        d = ImageDraw.Draw(burst)
        d.polygon([(x + 10, y + 12) for x, y in pts], fill=(0, 0, 0, 255))
        d.polygon(pts, fill=(228, 36, 44, 255), outline=(0, 0, 0, 255), width=10)
        burst.alpha_composite(inner, (round(cx - inner.width / 2), round(cy - inner.height / 2)))
        return trim(burst)
    if look == "game":
        f = ufont("pixel", 84)
        words = word.split()
        rows = [text_img(w_, f, (255, 255, 255, 255), sp=6, shadow=(8, 8, (255, 0, 77, 255))) for w_ in words]
        top = text_img("BASED ON", ufont("pixel", 30), (0, 228, 54, 255), sp=6, shadow=(4, 4, (0, 0, 0, 255)))
        ps = text_img("PRESS START", ufont("pixel", 30), (255, 236, 39, 255), sp=6, shadow=(4, 4, (0, 0, 0, 255)))
        return stack([top] + rows + [ps], 28)
    if look == "book":  # a leather-bound cover with gold tooling (the pages come with the films)
        bw_, bh_ = 760, 1000
        rnd = np.random.default_rng(12)
        g = rnd.normal(0, 1, (bh_ // 3, bw_ // 3)).astype(np.float32)
        g = np.asarray(Image.fromarray(((g - g.min()) / (g.max() - g.min()) * 255).astype(np.uint8)).resize((bw_, bh_), Image.BICUBIC), np.float32) / 255
        base = np.array([96, 30, 32], np.float32) * (0.82 + 0.3 * g[..., None]) + rnd.normal(0, 3, (bh_, bw_, 1)).astype(np.float32)
        xs = np.arange(bw_, dtype=np.float32)
        spine = 1 - 0.45 * np.clip(1 - xs / 90, 0, 1) ** 1.5
        ridges = 1 - 0.18 * ((np.abs(xs - 52) < 5) | (np.abs(xs - 72) < 5))
        yy, xx = np.mgrid[0:bh_, 0:bw_].astype(np.float32)
        v = np.sqrt(((xx - bw_ * 0.55) / (bw_ * 0.7)) ** 2 + ((yy - bh_ / 2) / (bh_ * 0.7)) ** 2)
        base *= (spine * ridges)[None, :, None] * (1 - np.clip(v - 0.5, 0, 1) * 0.6)[..., None]
        cov = img(base).convert("RGBA")
        foil = Image.new("RGBA", (bw_, bh_), (0, 0, 0, 0))
        fd = ImageDraw.Draw(foil)
        gold = (255, 255, 255, 255)
        fd.rectangle((130, 60, bw_ - 60, bh_ - 60), outline=gold, width=6)
        fd.rectangle((146, 76, bw_ - 76, bh_ - 76), outline=gold, width=2)
        for (cx_, cy_) in ((146, 76), (bw_ - 76, 76), (146, bh_ - 76), (bw_ - 76, bh_ - 76)):
            fd.regular_polygon((cx_, cy_, 16), 4, rotation=45, fill=gold)
        top = text_img("BASED ON THE", ufont("garamond", 44, 600), gold, sp=12)
        big = text_img(word, ufont("garamond", 150, 600), gold, sp=14)
        rule = Image.new("RGBA", (round(big.width * 0.42), 4), gold)
        orn = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        ImageDraw.Draw(orn).regular_polygon((20, 20, 16), 4, rotation=45, fill=gold)
        inner = stack([top, rule, big, rule, orn], 30)
        k = min(1.0, (bw_ - 300) / inner.width)
        inner = inner.resize((round(inner.width * k), round(inner.height * k)), Image.LANCZOS)
        foil.alpha_composite(inner, (130 + (bw_ - 190 - inner.width) // 2, (bh_ - inner.height) // 2))
        # gold: a warm ramp, a little shine; pressed into the leather (dark edge below)
        ramp = np.repeat(np.linspace(0, 1, bh_)[:, None], bw_, 1)
        col = np.stack([238 - 40 * ramp, 196 - 60 * ramp, 110 - 50 * ramp], 2)
        fa = np.asarray(foil.getchannel("A"), np.float32)
        press = Image.new("RGBA", (bw_, bh_), (20, 6, 6, 0))
        press.putalpha(Image.fromarray(fa.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)).point(lambda v: round(v * 0.7)))
        cov.alpha_composite(press, (0, 3))
        cov.alpha_composite(Image.fromarray(np.dstack([col, fa]).astype(np.uint8), "RGBA"))
        return cov
    if look == "true":
        tf = ufont("typewriter", 64)
        ink = (40, 34, 30, 255)
        l1 = text_img("BASED ON A", ufont("typewriter", 44), ink, sp=8)
        l2 = text_img("TRUE STORY", ufont("typewriter", 112), ink, sp=10)
        inner = stack([l1, l2], 20)
        card = Image.new("RGBA", (inner.width + 160, inner.height + 170), (226, 205, 160, 255))
        noise = np.random.default_rng(2).normal(0, 6, (card.height, card.width, 1)).astype(np.float32)
        card = Image.fromarray(np.clip(np.asarray(card, np.float32) + np.concatenate([noise] * 3 + [np.zeros_like(noise)], 2), 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(card)
        d.line((60, card.height - 62, card.width - 60, card.height - 62), fill=(150, 120, 90, 255), width=2)
        card.alpha_composite(inner, ((card.width - inner.width) // 2, 52))
        # the archive stamp
        st = text_img("BIOGRAPHIES", ufont("typewriter", 50), (200, 40, 40, 255), sp=8)
        box = Image.new("RGBA", (st.width + 60, st.height + 44), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rectangle((2, 2, box.width - 3, box.height - 3), outline=(200, 40, 40, 255), width=6)
        bd.rectangle((12, 12, box.width - 13, box.height - 13), outline=(200, 40, 40, 255), width=2)
        box.alpha_composite(st, (30, 22))
        a_ = np.asarray(box, np.float32)
        a_[..., 3] *= np.clip(np.random.default_rng(3).random(a_.shape[:2]) * 1.6, 0.35, 1)  # worn ink
        box = Image.fromarray(a_.astype(np.uint8)).rotate(-9, expand=True, resample=Image.BICUBIC)
        out = Image.new("RGBA", (card.width + 60, card.height + box.height // 2 + 20), (0, 0, 0, 0))
        out.alpha_composite(card, (0, 0))
        out.alpha_composite(box, (card.width - box.width + 50, card.height - box.height // 2 - 10))
        return out
    if look == "myth":  # a terracotta plaque between two Greek key bands, the name painted in black
        blk = (22, 14, 10, 255)
        top = text_img("BASED ON", ufont("cinzel", 40, 600), blk, sp=12)
        big = text_img(word, ufont("cinzel", 150, 700), blk, sp=8)
        inner = stack([top, big], 18)
        pw, ph = inner.width + 160, inner.height + 2 * 90 + 70
        rnd = np.random.default_rng(8)
        clay = np.ones((ph, pw, 3), np.float32) * TERRA * (1 + rnd.normal(0, 0.03, (ph, pw, 1)).astype(np.float32))
        plaque = img(clay).convert("RGBA")
        meander(plaque, 14, 62, col=blk)
        meander(plaque, ph - 76, 62, col=blk)
        plaque.alpha_composite(inner, ((pw - inner.width) // 2, (ph - inner.height) // 2))
        ImageDraw.Draw(plaque).rectangle((0, 0, pw - 1, ph - 1), outline=blk, width=6)
        return plaque
    raise KeyError(look)


def fit(im, w, h):
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def place(cv, im, cx, cy, a=1.0):
    cv.alpha_composite(amul(im, a), (round(cx - im.width / 2), round(cy - im.height / 2)))


# ---------------------------------------------------------------- the card
def build(folder, out):
    word, look, pool = CARDS[folder]
    make, turn = LOOKS[look]
    films = trio(pool, 3)
    reals = [cover_fit(load(p)) for _, p in films]
    srcs = []
    for (it, _), r in zip(films, reals):
        if look == "book":
            srcs.append(make(r, it[4] if len(it) > 4 else it[1], it[3]))
        elif look == "true":
            srcs.append(make(r, it[4] if len(it) > 4 else None))
        else:
            srcs.append(make(r))
    fl = fall()
    subs = [sub_layer(it[1], ("THE BOOK BY " if look == "book" else "") + it[3]) for it, _ in films]
    em = emblem(look, word)
    big = fit(em, W * 0.62, H * (0.8 if look == "book" else 0.62))
    small = fit(em, W * 0.2, H * 0.2)
    corner = (44 + small.width / 2, 36 + small.height / 2)
    # cover: the emblem on the first film's source look, held down in the dark
    # (the book card sits on the film itself: its title page would be too like the leather cover's paper)
    back = ImageEnhance.Brightness((reals[0] if look == "book" else srcs[0]).filter(ImageFilter.GaussianBlur(3))).enhance(0.32)
    cv = back.convert("RGBA")
    place(cv, big, W / 2, H / 2)
    cover = cv.convert("RGB")

    def emb(cv, m, a=1.0):  # m 0 = centre, 1 = corner
        sc = 1 + (small.width / big.width - 1) * m
        L = big.resize((max(1, round(big.width * sc)), max(1, round(big.height * sc))), Image.LANCZOS) if 0 < m < 1 else (big if m <= 0 else small)
        place(cv, L, W / 2 + (corner[0] - W / 2) * m, H / 2 + (corner[1] - H / 2) * m, a)

    HOLD, MOVE, SEG, BACK = 6, 14, 46, 14
    F0 = HOLD
    N_ = HOLD + SEG * len(films) + BACK
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        c = None
        if i < F0 + SEG * len(films):
            k, t = divmod(i - F0, SEG)
            z = 0.01 + 0.05 * t / SEG
            src, real = zoomed(srcs[k], z), zoomed(reals[k], z)
            stamp = films[k][0][4] if look == "true" and len(films[k][0]) > 4 else None
            if t < 18:
                pic = src
            elif t < 34:
                u = (t - 18) / 16
                pic = turn(src, real, u, stamp) if look == "true" else turn(src, real, u)
            else:
                pic = real
            if k == 0 and t < MOVE:   # the dimmed backdrop lights up while the emblem leaves
                pic = Image.blend(zoomed(back, z), pic, ease(t / MOVE))
            elif k > 0 and t < 8:     # in from the previous film
                pic = Image.blend(zoomed(reals[k - 1], 0.06), pic, ease(t / 8))
            c = pic.convert("RGBA")
            c.alpha_composite(fl)
            m = ease(t / MOVE) if k == 0 and t < MOVE else 1.0
            emb(c, m)
            sa = ease((t - 4) / 6) if t < 10 else (1 - ease((t - (SEG - 6)) / 6) if (t >= SEG - 6 and k == len(films) - 1) else 1.0)
            if k > 0 and t < 8:
                c.alpha_composite(amul(subs[k - 1], 1 - ease(t / 6)))
            c.alpha_composite(amul(subs[k], sa))
        else:
            # back to the cover: the last film sinks into the dark backdrop, the emblem returns to the middle
            u = ease((i - (F0 + SEG * len(films))) / BACK)
            pic = Image.blend(zoomed(reals[-1], 0.06), back, u)
            c = pic.convert("RGBA")
            c.alpha_composite(amul(fl, 1 - u))
            emb(c, 1 - u)
        frames.append(c.convert("RGB").resize((OW, OH), Image.LANCZOS))
    d = os.path.join(out, slug_of(folder))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 12, 30, 44, 70, 100, 140, 152]):
        strip.paste(frames[min(idx, len(frames) - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return [it[1] for it, _ in films]


def slug_of(t):
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
