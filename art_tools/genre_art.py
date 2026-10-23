"""Genres row: Kaptain's genre cards (photo, accent bar, bold title, tracked subtitle; on hover the subtitle turns to
the genre colour, the bar to white and a coloured frame lights up), rebuilt by us so they can move:
  cover   the genre's iconic film (the one on Kaptain's card), plain state
  hover   starts and ends exactly on the cover (seamless loop). The genre's films play behind the title, 1.7 s each,
          their name and year top right; the accent bar splits into one segment per film and each fills with the
          genre colour while its film plays (the subtitle fills too); then everything drains back to the cover.
Popular films are refreshed monthly (.github/workflows/genre-art.yml -> genre-art branch, fixed URLs); a film stays
while it is still in the genre's top 6, so the art only changes when the genre's line-up really moves.
usage: python3 art_tools/genre_art.py OUT_DIR [--prev picks.json] [titles...]
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1280, 720
OW, OH = 512, 288
FONTS = os.path.join(ROOT, "spotlight", "fonts")

# title on the card, subtitle, accent (Kaptain's frame colour), iconic film (TMDB id), filters for "popular now"
GENRES = {
    "Action & Adventure": ("ACTION", "HIGH-OCTANE THRILLS & BLOCKBUSTERS", (221, 109, 105), 76341, {"with_genres": "28"}),
    "Sci-Fi & Fantasy": ("SCI-FI", "FUTURISTIC WORLDS & COSMIC SAGAS", (63, 180, 223), 157336, {"with_genres": "878|14"}),
    "Comedy": ("COMEDY", "LAUGH-OUT-LOUD FAVORITES & SATIRE", (244, 194, 81), 120467, {"with_genres": "35"}),
    "Animation": ("ANIMATION", "TIMELESS CLASSICS & MODERN MASTERPIECES", (59, 187, 136), 862, {"with_genres": "16"}),
    "Drama": ("DRAMA", "POWERHOUSE PERFORMANCES & HUMAN STORIES", (155, 73, 96), 278, {"with_genres": "18"}),
    "Crime": ("CRIME", "GRITTY HEISTS, MOBSTERS & DETECTIVES", (188, 159, 125), 238, {"with_genres": "80"}),
    "Horror": ("HORROR", "CHILLING TERROR & SUPERNATURAL DREAD", (145, 39, 191), 694, {"with_genres": "27"}),
    "Mystery & Thriller": ("THRILLER", "TENSION THAT NEVER LETS GO", (182, 61, 78), 6977, {"with_genres": "53|9648"}),
    "Romance & Rom-Com": ("ROMANCE", "LOVE STORIES WORTH FALLING FOR", (216, 91, 123), 4348, {"with_genres": "10749"}),
    "Stand-Up Comedy": ("STAND-UP", "COMICS, SPECIALS & LIVE WIRE SETS", (234, 160, 39), None, {"with_keywords": "9716"}),
    "Superhero": ("SUPERHERO", "CAPES, POWERS & COMIC-BOOK MYTH", (39, 91, 174), 155, {"with_keywords": "9715"}),
    "Martial Arts": ("MARTIAL ARTS", "DISCIPLINE, HONOR & FIGHTING GRACE", (199, 116, 100), 146, {"with_keywords": "779"}),
    "History & War": ("WAR", "BATTLEFIELDS, BROTHERHOOD & COST", (147, 154, 121), 857, {"with_genres": "10752"}),
    "Western": ("WESTERN", "DUST, GUNSMOKE & FRONTIER JUSTICE", (172, 124, 75), 429, {"with_genres": "37"}),
}


# Behind each genre card: iconic films whose one picture says the genre and the film at once (Kill Bill's yellow
# suit, the Grand Budapest's pink hotel) - not whatever is popular this month. Three of them play at a time; the
# trio moves on every month through the list, so the card changes while always staying on-message.
ICONIC = {
    "Action & Adventure": [("Kill Bill: Vol. 1", 2003), ("John Wick", 2014), ("Die Hard", 1988), ("Gladiator", 2000),
                           ("Raiders of the Lost Ark", 1981), ("Top Gun: Maverick", 2022),
                           ("Mission: Impossible - Fallout", 2018), ("Terminator 2: Judgment Day", 1991)],
    "Sci-Fi & Fantasy": [("Dune: Part Two", 2024), ("Blade Runner 2049", 2017), ("The Matrix", 1999),
                         ("Star Wars", 1977), ("The Lord of the Rings: The Fellowship of the Ring", 2001),
                         ("2001: A Space Odyssey", 1968), ("Avatar", 2009), ("Back to the Future", 1985)],
    "Comedy": [("The Big Lebowski", 1998), ("Home Alone", 1990), ("Superbad", 2007), ("Ferris Bueller's Day Off", 1986),
               ("The Hangover", 2009), ("Barbie", 2023), ("Dumb and Dumber", 1994), ("Anchorman: The Legend of Ron Burgundy", 2004)],
    "Animation": [("Shrek", 2001), ("The Lion King", 1994), ("Up", 2009), ("Spider-Man: Into the Spider-Verse", 2018),
                  ("Coco", 2017), ("WALL·E", 2008), ("Inside Out", 2015), ("Frozen", 2013)],
    "Drama": [("Forrest Gump", 1994), ("Fight Club", 1999), ("Whiplash", 2014), ("Good Will Hunting", 1997),
              ("Oppenheimer", 2023), ("The Green Mile", 1999), ("American Beauty", 1999), ("Moonlight", 2016)],
    "Crime": [("Pulp Fiction", 1994), ("Goodfellas", 1990), ("Heat", 1995), ("Scarface", 1983), ("The Departed", 2006),
              ("Reservoir Dogs", 1992), ("Joker", 2019), ("Taxi Driver", 1976)],
    "Horror": [("It", 2017), ("The Exorcist", 1973), ("Halloween", 1978), ("Get Out", 2017), ("Scream", 1996),
               ("Hereditary", 2018), ("A Nightmare on Elm Street", 1984), ("The Conjuring", 2013)],
    "Mystery & Thriller": [("Se7en", 1995), ("The Silence of the Lambs", 1991), ("Psycho", 1960), ("Gone Girl", 2014),
                           ("Shutter Island", 2010), ("Prisoners", 2013), ("Zodiac", 2007), ("Rear Window", 1954)],
    "Romance & Rom-Com": [("Titanic", 1997), ("The Notebook", 2004), ("La La Land", 2016), ("Before Sunrise", 1995),
                          ("Notting Hill", 1999), ("Pretty Woman", 1990), ("Dirty Dancing", 1987), ("Casablanca", 1942)],
    "Stand-Up Comedy": [("Eddie Murphy: Delirious", 1983), ("Eddie Murphy Raw", 1987), ("Bo Burnham: Inside", 2021),
                        ("Dave Chappelle: Sticks & Stones", 2019), ("John Mulaney: Kid Gorgeous at Radio City", 2018),
                        ("Hannah Gadsby: Nanette", 2018), ("Chris Rock: Bring the Pain", 1996), ("George Carlin: It's Bad for Ya", 2008)],
    "Superhero": [("Avengers: Endgame", 2019), ("Spider-Man", 2002), ("Iron Man", 2008), ("Black Panther", 2018),
                  ("Logan", 2017), ("Superman", 1978), ("The Avengers", 2012), ("Wonder Woman", 2017)],
    "Martial Arts": [("Enter the Dragon", 1973), ("Ip Man", 2008), ("The Raid", 2011), ("Hero", 2002),
                     ("Kung Fu Hustle", 2004), ("Drunken Master", 1978), ("Ong-Bak", 2003), ("The Karate Kid", 1984)],
    "History & War": [("Apocalypse Now", 1979), ("Full Metal Jacket", 1987), ("1917", 2019), ("Dunkirk", 2017),
                      ("Hacksaw Ridge", 2016), ("Platoon", 1986), ("Inglourious Basterds", 2009), ("Black Hawk Down", 2001)],
    "Western": [("Once Upon a Time in the West", 1968), ("Django Unchained", 2012), ("Unforgiven", 1992),
                ("True Grit", 2010), ("The Magnificent Seven", 1960), ("Tombstone", 1993), ("The Hateful Eight", 2015),
                ("Butch Cassidy and the Sundance Kid", 1969)],
}


KNOWN = {"The Raid": 94329}   # titles TMDB search gets wrong


def find_movie(title, year):
    """TMDB id for a title: the result released within a year of `year` (exact title first), else the top hit."""
    if title in KNOWN:
        return KNOWN[title], title
    r = (tmdb("/search/movie", query=title) or {}).get("results", [])
    yr = lambda x: int((x.get("release_date") or "0")[:4] or 0) if (x.get("release_date") or "0")[:4].isdigit() else 0
    near = [x for x in r if abs(yr(x) - year) <= 1]
    exact = [x for x in near if x.get("title", "").lower() == title.lower()]
    pick = (exact or near or r or [None])[0]
    return (pick["id"], pick["title"]) if pick else (None, None)


def fanart_backgrounds(tid):
    """fanart.tv's textless movie backgrounds for a film, most liked first (hand-picked key art by its community)."""
    import urllib.request
    key = os.environ.get("FANART_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(f"https://webservice.fanart.tv/v3/movies/{tid}?api_key={key}",
                                     headers={"User-Agent": "nuvio-awards"})
        d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception:
        return []
    bg = d.get("moviebackground", []) + d.get("movie4kbackground", [])
    return [x["url"] for x in sorted(bg, key=lambda x: -int(x.get("likes", 0) or 0))]


def load_img(p):
    """A TMDB file path or a full (fanart.tv) URL -> RGB image."""
    if not p.startswith("http"):
        return art.fetch(p).convert("RGB")
    import io, urllib.request
    for _ in range(3):
        try:
            data = urllib.request.urlopen(urllib.request.Request(p, headers={"User-Agent": "nuvio-awards"}), timeout=60).read()
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            continue
    raise RuntimeError("could not fetch " + p)


# film -> which fanart background to use when the most liked one isn't the film's best-known picture
PICK = {"Joker": 1, "Get Out": 1, "Gone Girl": 1, "Psycho": 2, "Full Metal Jacket": 2, "Django Unchained": 2,
        "Unforgiven": 1, "Home Alone": 2}


def best_art(tid, name=None):
    """The film's picture: its most liked fanart.tv background (textless key art), else TMDB's best textless one."""
    fa = fanart_backgrounds(tid)
    if fa:
        return fa[min(PICK.get(name, 0), len(fa) - 1)]
    return textless_backdrop("movie", tid)


_COLL = {}


def collection_of(tid):
    """TMDB collection (franchise) id of a film, or None."""
    if tid not in _COLL:
        c = (tmdb(f"/movie/{tid}") or {}).get("belongs_to_collection") or {}
        _COLL[tid] = c.get("id")
    return _COLL[tid]


def iconic(title, n=3, avoid=(), month=None, avoid_coll=None):
    """This month's trio from the genre's iconic list, each with its best-voted textless backdrop.
    avoid_coll: franchises already showing on another card; a film from one is skipped, and the films picked here add
    theirs (so two films of one series never play at the same time, on one card or two)."""
    import datetime as dt
    pool = ICONIC.get(title, [])
    if not pool:
        return []
    m = month if month is not None else (dt.date.today().year * 12 + dt.date.today().month)
    start = (m * n) % len(pool)
    order = pool[start:] + pool[:start]
    out = []
    for name, year in order:
        tid, real = find_movie(name, year)
        if not tid or tid in avoid:
            continue
        coll = collection_of(tid) if avoid_coll is not None else None
        if coll and coll in avoid_coll:
            continue
        path = best_art(tid, name)
        if path:
            out.append((tid, real, path))
            if coll:
                avoid_coll.add(coll)
        if len(out) == n:
            break
    return out


# genres a film must NOT carry to stand for a genre (a comedy with explosions reads as action, not comedy)
EXCLUDE = {"Action & Adventure": "35|27|10749", "Sci-Fi & Fantasy": "35|27", "Comedy": "28|878|27|53|80|10752|14",
           "Animation": "27", "Drama": "28|35|27|878|14", "Crime": "35|878|14", "Horror": "35|10751",
           "Mystery & Thriller": "35|10751|27", "Romance & Rom-Com": "28|27|878|53|80", "History & War": "35",
           "Western": "35"}


def font(w, s):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat-{w}.ttf"), s)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- material
def textless_backdrop(kind, tid):
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null") or {}
    bd = sorted([b for b in im.get("backdrops", []) if not b.get("iso_639_1") and b["width"] >= 1280],
                key=lambda b: (-b["vote_count"], -b["vote_average"]))
    return bd[0]["file_path"] if bd else None


def key_art(tid):
    """The film's landscape key art: the best-voted English titled backdrop (the studio's own 'cover' for the film),
    else the best textless one."""
    im = tmdb(f"/movie/{tid}/images", include_image_language="en,null") or {}
    bds = [b for b in im.get("backdrops", []) if b["width"] >= 1280]
    rank = lambda b: (-b["vote_count"], -b["vote_average"])
    titled = sorted([b for b in bds if b.get("iso_639_1") == "en"], key=rank)
    plain = sorted([b for b in bds if not b.get("iso_639_1")], key=rank)
    return (titled or plain or [{}])[0].get("file_path")


def popular(title, filters, n=3, keep=(), avoid=()):
    """The genre's popular films right now: TMDB popularity, English, a vote floor, released in the last 4 years
    (wider when the genre is thin). The genre has to lead the film's genre list and clashing genres are left out, so
    every film on the card reads as that genre."""
    import datetime as dt
    small = title == "Stand-Up Comedy"  # specials: a small genre, so a wider window and a lower vote floor
    lead = filters.get("with_genres", "").split("|") if "with_genres" in filters else None
    r = []
    for years in ((10,) if small else (4, 8, 15)):
        since = (dt.date.today() - dt.timedelta(days=years * 365)).isoformat()
        p = dict(filters, sort_by="popularity.desc", with_original_language="en",
                 **{"vote_count.gte": 25 if small else 300, "primary_release_date.gte": since})
        excl = ([] if title == "Animation" else ["16"]) + ([] if small else ["99"]) + EXCLUDE.get(title, "").split("|")
        p["without_genres"] = "|".join(x for x in excl if x)
        r = []
        for page in (1, 2):
            r += (tmdb("/discover/movie", page=page, **p) or {}).get("results", [])
        r = [x for x in r if x["id"] not in avoid and (not lead or (x.get("genre_ids") and str(x["genre_ids"][0]) in lead))]
        if len(r) >= n + 2:
            break
    kept = [x for x in r[:6] if x["id"] in keep]
    order = kept + [x for x in r if x not in kept]
    out = []
    for x in order:
        path = key_art(x["id"])
        if path:
            out.append((x["id"], x.get("title"), path))
        if len(out) == n:
            break
    rank = {x["id"]: i for i, x in enumerate(r)}
    return sorted(out, key=lambda x: rank.get(x[0], 99))


# ---------------------------------------------------------------- drawing
_PATH = {}


def frame_path(p, w=W, h=H, m=5, r=22):
    """The rounded card outline from the top centre clockwise, cut at fraction p of its length (constant speed)."""
    if (w, h) not in _PATH:
        x0, y0, x1, y1 = m, m, w - m, h - m
        pts = []

        def line(ax, ay, bx, by):
            k = max(2, int(math.hypot(bx - ax, by - ay) / 2))
            pts.extend((ax + (bx - ax) * i / k, ay + (by - ay) * i / k) for i in range(k))

        def arc(cx, cy, a0, a1):
            k = max(2, int(r * math.radians(abs(a1 - a0)) / 2))
            pts.extend((cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / k)),
                        cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / k))) for i in range(k))
        line(w / 2, y0, x1 - r, y0); arc(x1 - r, y0 + r, -90, 0)
        line(x1, y0 + r, x1, y1 - r); arc(x1 - r, y1 - r, 0, 90)
        line(x1 - r, y1, x0 + r, y1); arc(x0 + r, y1 - r, 90, 180)
        line(x0, y1 - r, x0, y0 + r); arc(x0 + r, y0 + r, 180, 270)
        line(x0 + r, y0, w / 2, y0)
        pts.append((w / 2, y0))
        cum = [0.0]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.hypot(bx - ax, by - ay))
        _PATH[(w, h)] = (pts, cum)
    pts, cum = _PATH[(w, h)]
    target = cum[-1] * max(0.0, min(1.0, p))
    out = [pts[0]]
    for k in range(1, len(pts)):
        if cum[k] <= target:
            out.append(pts[k])
        else:
            f = (target - cum[k - 1]) / max(1e-9, cum[k] - cum[k - 1])
            out.append((pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f))
            break
    return out


def tracked(d, xy, text, fnt, fill, sp):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + sp


def scene(img):
    """Kaptain's grade: the still, a dark gradient rising from the bottom and from the left behind the type."""
    im = art.graded(img, 0.95, 1.06, (W, H))
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for y in range(H):
        f = max(0.0, (y / H - 0.42) / 0.58)
        d.line((0, y, W, y), fill=round(238 * f ** 1.15))
    side = Image.new("L", (W, 1))
    for x in range(W):
        side.putpixel((x, 0), round(175 * max(0.0, 1 - x / (W * 0.62)) ** 1.5))
    m = ImageChops.lighter(m, ImageChops.multiply(side.resize((W, H)), Image.linear_gradient("L").resize((W, H))))
    pool = Image.new("L", (W, H), 0)   # a soft dark pool under the type, so a bright poster can't wash it out
    ImageDraw.Draw(pool).ellipse((-W * 0.25, H * 0.58, W * 0.62, H * 1.12), fill=205)
    m = ImageChops.lighter(m, pool.filter(ImageFilter.GaussianBlur(W * 0.07)))
    return Image.composite(Image.new("RGB", (W, H), (6, 6, 10)), im, m)


def make(title, sub, accent, imgs, labels=None, style=None):
    """labels: (name, year) per picture, written top right while it plays. style (or env GENRE_STYLE) of what
    marks time now the lap round the card is gone: A nothing (the colour fill only), B the bar split into one segment
    per film that fills as it plays, C a light sweeping over the title at every change of film."""
    style = style or os.environ.get("GENRE_STYLE", "B")
    k = W / 1920
    tf, sf = font("ExtraBold", round(124 * k)), font("SemiBold", round(42 * k))
    sp_t, sp_s = round(3 * k), round(5 * k)
    x0 = round(106 * k)
    bars = [scene(i) for i in imgs]
    S = len(bars)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    # the type block: title caps + gap + subtitle caps; the bar runs exactly alongside it (same height, centred)
    tb, sb = tf.getbbox("ACTION"), sf.getbbox("ACTION")
    cap_t, cap_s = tb[3] - tb[1], sb[3] - sb[1]
    gap = round(cap_t * 0.42)
    block = cap_t + gap + cap_s
    pad = round(cap_s * 0.35)
    bottom = round(H * 0.875)
    top = bottom - block
    title_y = top - tb[1]
    sub_y = top + cap_t + gap - sb[1]
    bar = (x0 - round(28 * k), top - pad, x0 - round(21 * k), bottom + pad)
    grey = (214, 220, 232)
    L0, L1 = 5 / 120, 105 / 120

    def mix(a, b, f):
        return tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3))

    # the title as separate letter layers (each slides up and fades in on its own), the subtitle as one layer
    letters, x = [], x0
    for ch in title:
        adv = probe.textlength(ch, font=tf) + sp_t
        if ch != " ":
            bb = tf.getbbox(ch)
            lay = Image.new("RGBA", (bb[2] + 20, bb[3] + 20), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((0, 0), ch, font=tf, fill=(255, 255, 255, 255))
            letters.append((x, lay))
        x += adv
    sw = round(sum(probe.textlength(ch, font=sf) + sp_s for ch in sub)) + 20
    sub_h = sf.getbbox("Ag")[3] + 10

    def sub_layer(col):
        lay = Image.new("RGBA", (sw, sub_h), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(lay), (0, 0), sub, sf, col + (255,), sp_s)
        return lay

    def put(cv, lay, x, y, a):
        if a <= 0:
            return
        if a < 1:
            lay = lay.copy()
            lay.putalpha(lay.getchannel("A").point(lambda v: round(v * a)))
        cv.alpha_composite(lay, (round(x), round(y)))

    sub_grey, sub_acc = sub_layer(grey), sub_layer(accent)

    def fill_amount(t):
        """Genre colour flows in after the type has arrived, and drains again before the loop ends."""
        return ease((t - 0.12) / 0.16) if t < 0.9 else 1 - ease((t - 0.9) / 0.06)

    def type_in(cv, t, out, c):
        """Bar grows up and letters rise in one by one, the subtitle slides in from the left (all neutral); then the
        genre colour fills the bar from the bottom up and the subtitle from left to right; at the loop end it drains
        and the type fades."""
        d = ImageDraw.Draw(cv)
        g = ease(t / 0.06)
        f = fill_amount(t)
        if g > 0 and out > 0:
            btop = bar[3] - (bar[3] - bar[1]) * g
            d.rectangle((bar[0], btop, bar[2], bar[3]), fill=grey + (round(255 * out),))
            if f > 0:
                ftop = bar[3] - (bar[3] - bar[1]) * f
                d.rectangle((bar[0], ftop, bar[2], bar[3]), fill=accent + (round(255 * out),))
        for k_, (lx, lay) in enumerate(letters):
            p_ = ease((t - 0.02 - k_ * 0.012) / 0.07)
            put(cv, lay, lx, title_y + (1 - p_) * 26, p_ * out)
        p_ = ease((t - 0.06) / 0.09)
        sx = x0 + 2 - (1 - p_) * 60
        lay = sub_grey
        if f > 0:
            m = Image.new("L", lay.size, 0)
            ImageDraw.Draw(m).rectangle((0, 0, round(sw * f), sub_h), fill=255)
            lay = Image.composite(sub_acc, sub_grey, m)
        put(cv, lay, sx, sub_y, p_ * out)

    def cover():
        cv = bars[0].copy().convert("RGBA")
        d = ImageDraw.Draw(cv)
        d.rectangle(bar, fill=grey + (255,))
        tracked(d, (x0, title_y), title, tf, (255, 255, 255, 255), sp_t)
        tracked(d, (x0 + 2, sub_y), sub, sf, grey + (255,), sp_s)
        return cv.convert("RGB")

    # the title as one layer (it stays put now: the hover starts and ends exactly on the cover)
    title_lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tracked(ImageDraw.Draw(title_lay), (x0, title_y), title, tf, (255, 255, 255, 255), sp_t)
    title_a = title_lay.getchannel("A")
    tx0, tx1 = x0, x0 + round(sum(probe.textlength(ch, font=tf) + sp_t for ch in title))

    lab_f = font("ExtraBold", 38)
    yr_f = font("SemiBold", 23)
    yr_col = tuple(min(255, round(v * 0.55 + 115)) for v in accent)

    def label_layer(name, year):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        tt = name.upper()
        f_ = lab_f
        while probe.textlength(tt, font=f_) + 2 * len(tt) > W * 0.5 and f_.size > 20:
            f_ = font("ExtraBold", f_.size - 2)
        tw = sum(probe.textlength(ch, font=f_) + 2 for ch in tt) - 2
        xr = W - 54
        tracked(d, (xr - tw, 44), tt, f_, (255, 255, 255, 255), 2)
        ys = str(year)
        yw = sum(probe.textlength(ch, font=yr_f) + 7 for ch in ys) - 7
        tracked(d, (xr - yw, 44 + f_.size + 12), ys, yr_f, yr_col + (255,), 7)
        return lay

    labs = [label_layer(n_, y_) for n_, y_ in labels] if labels else []
    shade = Image.new("L", (W, H), 0)   # a soft dark corner behind the label, only while one is up
    ImageDraw.Draw(shade).ellipse((W * 0.52, -H * 0.42, W * 1.25, H * 0.42), fill=170)
    shade = shade.filter(ImageFilter.GaussianBlur(70))

    def seg_bar(cv, t, q, out):
        """B: the bar as one segment per film, bottom up; each fills while its film plays."""
        d = ImageDraw.Draw(cv)
        e_ = ease(t / 0.05) * out
        gap = round(12 * e_)
        x2 = bar[2] + round(5 * e_)       # a little wider while it counts, so the segments read at card size
        h_ = (bar[3] - bar[1] - gap * (S - 1)) / S
        for s_ in range(S):
            y1 = bar[3] - s_ * (h_ + gap)
            y0 = y1 - h_
            d.rectangle((bar[0], round(y0), x2, round(y1)), fill=grey + (255,))
            p_ = min(1.0, max(0.0, q * S - s_)) * out
            if p_ > 0:
                d.rectangle((bar[0], round(y1 - h_ * p_), x2, round(y1)), fill=accent + (255,))

    def frame(i, n):
        t = i / n
        L0, L1 = 4 / n, (n - 16) / n
        q = min(1.0, max(0.0, (t - L0) / (L1 - L0)))
        seg = q * S
        j = min(S - 1, int(seg))
        loc = seg - j
        nxt, fade = (j + 1) % S, ((loc - 0.86) / 0.14 if loc > 0.86 and j < S - 1 else 0.0)
        if t > L1:
            j, nxt, loc, fade = S - 1, 0, 1.0, ease((t - L1) / (1 - L1 - 2 / n))
        bg = art.zoomed(bars[j], 0.06 * min(1, loc))
        if fade > 0:
            bg = Image.blend(bg, art.zoomed(bars[nxt], 0.0), min(1.0, fade))
        cv = bg.convert("RGBA")
        f = ease((t - L0) / 0.1) if t < L1 else 1 - ease((t - L1) / ((1 - L1) * 0.8))
        # the label of the film on screen, top right
        if labs and t <= L1:
            la = ease((loc - 0.06) / 0.1) * (1 - ease((loc - 0.84) / 0.12)) if j < S - 1 else ease((loc - 0.06) / 0.1) * (1 - ease((loc - 0.9) / 0.1))
            if la > 0:
                dark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                dark.putalpha(shade.point(lambda v: round(v * la)))
                cv.alpha_composite(dark)
                lay = labs[j].copy()
                lay.putalpha(lay.getchannel("A").point(lambda v: round(v * la)))
                cv.alpha_composite(lay, (0, round((1 - la) * -8)))
        d = ImageDraw.Draw(cv)
        # bar
        if style == "B":
            seg_bar(cv, t, q if t <= L1 else 1.0, f if t > L1 else 1.0)
        else:
            d.rectangle(bar, fill=grey + (255,))
            if f > 0:
                d.rectangle((bar[0], bar[3] - (bar[3] - bar[1]) * f, bar[2], bar[3]), fill=accent + (255,))
        # title
        cv.alpha_composite(title_lay)
        if style == "C" and t <= L1:   # a light sweeps over the title as each film comes in
            u = (loc - 0.02) / 0.55 if not (j == 0 and seg < 0.05) else -1
            if 0 < u < 1:
                cx = tx0 - 160 + (tx1 - tx0 + 320) * ease(u)
                xs = Image.linear_gradient("L").rotate(90).resize((W, H))
                import numpy as _np
                xx = _np.arange(W, dtype=_np.float32)[None, :] + (_np.arange(H, dtype=_np.float32)[:, None] - title_y) * 0.35
                band = _np.clip(1 - _np.abs(xx - cx) / 90, 0, 1) ** 1.5
                m = (_np.asarray(title_a, _np.float32) * band).astype(_np.uint8)
                mi = Image.fromarray(m)
                glow = Image.new("RGBA", (W, H), accent + (0,))
                glow.putalpha(mi.filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, v * 2)))
                cv.alpha_composite(glow)
                tint = Image.new("RGBA", (W, H), tuple(min(255, round(v * 0.6 + 100)) for v in accent) + (0,))
                tint.putalpha(mi)
                cv.alpha_composite(tint)
        # subtitle, filling with the colour left to right
        lay = sub_grey
        if f > 0:
            m = Image.new("L", lay.size, 0)
            ImageDraw.Draw(m).rectangle((0, 0, round(sw * f), sub_h), fill=255)
            lay = Image.composite(sub_acc, sub_grey, m)
        cv.alpha_composite(lay, (x0 + 2, sub_y))
        return cv.convert("RGB")

    frame.n = 26 + 34 * S   # 4 frames on the cover, 1.7 s a film, 0.8 s back to the cover
    frame.cover = cover
    return frame


def slug_of(t):
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


def labels_of(seq, kind="movie"):
    """(name, year) for each (tmdb id, name, path) - the card writes them while the picture plays."""
    out = []
    for tid, name, _ in seq:
        info = tmdb(f"/{kind}/{tid}") or {}
        d = info.get("release_date") or info.get("first_air_date") or ""
        out.append((info.get("title") or info.get("name") or name or "", d[:4]))
    return out


def build_one(job):
    t, picks, out = job
    title, sub, accent, icon, filters = GENRES[t]
    try:
        first = []
        if icon:
            p = textless_backdrop("movie", icon)
            info = tmdb(f"/movie/{icon}") or {}
            first = [(icon, info.get("title"), p)] if p else []
        seq = first + picks
        if not seq:
            raise RuntimeError("no films")
        imgs = [load_img(p) for _, _, p in seq]
        frame = make(title, sub, accent, imgs, labels=labels_of(seq))
        dd = os.path.join(out, slug_of(t))
        os.makedirs(dd, exist_ok=True)
        n = frame.n
        frames = [frame(i, n).resize((OW, OH), Image.LANCZOS) for i in range(n)]
        frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * n,
                       loop=0, quality=80, method=4, kmin=0, kmax=1)  # every frame a keyframe: desktop Nuvio decodes frames one by one
        frame.cover().save(os.path.join(dd, "cover.jpg"), quality=90)
        strip = Image.new("RGB", (OW * 3, OH * 2))
        for jj, idx in enumerate([0, n // 6, n // 3, n // 2, 2 * n // 3, n - 1]):
            strip.paste(frames[idx], ((jj % 3) * OW, (jj // 3) * OH))
        strip.save(os.path.join(dd, "frames.jpg"), quality=80)
        return t, [(x[0], x[1]) for x in picks], None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return t, [], str(e)


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    prev = {}
    if "--prev" in args:
        i = args.index("--prev")
        try:
            prev = json.load(open(args[i + 1])).get("picks", {})
        except Exception:
            prev = {}
        del args[i:i + 2]
    only = set(args)
    # pick first, one genre after another, so no film is on two genre cards at once (then render in parallel)
    used = {g[3] for g in GENRES.values() if g[3]}
    used_coll = {c for c in (collection_of(i) for i in used) if c}
    jobs = []
    for t in GENRES:
        if only and t not in only:
            continue
        keep = [p[0] for p in prev.get(t, [])]
        try:
            pk = iconic(t, 3, avoid=used, avoid_coll=used_coll)
        except Exception as e:
            print("pick failed", t, e)
            pk = []
        used |= {x[0] for x in pk}
        jobs.append((t, pk, out))
    from multiprocessing import Pool
    with Pool(4) as pool:
        res = pool.map(build_one, jobs)
    picks, failed = dict(prev), []
    for t, pk, err in res:
        if err:
            failed.append(t)
            print("FAILED", t, err)
        else:
            picks[t] = pk
            print("built", t, "·", ", ".join(str(x[1]) for x in pk))
    import datetime as dt
    os.makedirs(out, exist_ok=True)
    json.dump({"date": dt.date.today().isoformat(), "picks": picks}, open(os.path.join(out, "picks.json"), "w"),
              indent=1, ensure_ascii=False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
