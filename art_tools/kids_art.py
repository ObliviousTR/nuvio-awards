"""Kids & Family row: Kaptain's cards (one picture, accent bar, bold title, tracked subtitle) rebuilt so they move
like the Genres and Moods rows: the type rises in, bar and subtitle fill with the card colour, the bar counts the
pictures (one segment each) while three iconic pictures for the card play behind it, name and year top right.
Pictures are the films' / shows' own textless key art (fanart.tv backgrounds, TMDB textless backdrop as fallback).
Each card has a fixed cover and a pool; the trio moves on every month (.github/workflows/kids-art.yml -> kids-art).
Discover Family is the exception: its cover and trio are this month's most popular family films.
usage: python3 art_tools/kids_art.py OUT_DIR [titles...]
"""
import datetime as dt, io, json, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import genre_art as g
import hero_styles, tv_logos
from spotlight import tmdb
from PIL import Image

# title: card title, subtitle, accent, cover item, pool; items are (kind, title, year[, which fanart background])
CARDS = {
    "Discover Family": ("DISCOVER FAMILY", "CURATED PICKS FOR EVERY AGE", (245, 139, 95), None, None),
    "Family Movie Night": ("MOVIE NIGHT", "FILMS THE WHOLE FAMILY CAN SHARE", (6, 215, 160), ("movie", "The Incredibles", 2004),
                           [("movie", "Home Alone", 1990), ("movie", "Jumanji", 1995), ("movie", "Paddington 2", 2017),
                            ("movie", "The Goonies", 1985), ("movie", "E.T. the Extra-Terrestrial", 1982), ("movie", "Hook", 1991),
                            ("movie", "Night at the Museum", 2006), ("movie", "Matilda", 1996)]),
    "Saturday Morning & Classic Cartoons": ("SATURDAY MORNING", "NOSTALGIC CARTOONS & CLASSICS", (16, 138, 177),
                                            ("tv", "Looney Tunes", 0, 2),
                                            [("tv", "Scooby-Doo, Where Are You!", 1969), ("tv", "Batman: The Animated Series", 1992, 3),
                                             ("tv", "Teenage Mutant Ninja Turtles", 1987), ("tv", "DuckTales", 1987),
                                             ("tv", "Dexter's Laboratory", 1996, 3), ("tv", "The Powerpuff Girls", 1998, 1),
                                             ("tv", "SpongeBob SquarePants", 1999)]),
    "Disney & Pixar Magic": ("DISNEY & PIXAR", "BELOVED CLASSICS & MODERN FAVOURITES", (120, 170, 255), ("movie", "Coco", 2017),
                             [("movie", "Toy Story", 1995), ("movie", "Finding Nemo", 2003), ("movie", "Moana", 2016),
                              ("movie", "Aladdin", 1992), ("movie", "Ratatouille", 2007), ("movie", "Zootopia", 2016),
                              ("movie", "Monsters, Inc.", 2001), ("movie", "Beauty and the Beast", 1991)]),
    "DreamWorks & Illumination": ("DREAMWORKS & MINIONS", "SHREK, KUNG FU PANDA, DESPICABLE ME & MORE", (150, 200, 70),
                                  ("movie", "Shrek", 2001),
                                  [("movie", "Kung Fu Panda", 2008), ("movie", "How to Train Your Dragon", 2010),
                                   ("movie", "Despicable Me", 2010), ("movie", "Madagascar", 2005),
                                   ("movie", "Puss in Boots: The Last Wish", 2022), ("movie", "The Super Mario Bros. Movie", 2023),
                                   ("movie", "Sing", 2016)]),
    "Studio Spotlight": ("STUDIO SPOTLIGHT", "LAIKA, AARDMAN & STOP-MOTION GEMS", (254, 209, 103), ("movie", "Coraline", 2009),
                         [("movie", "Wallace & Gromit: The Curse of the Were-Rabbit", 2005), ("movie", "Chicken Run", 2000),
                          ("movie", "Kubo and the Two Strings", 2016), ("movie", "ParaNorman", 2012), ("movie", "Song of the Sea", 2014),
                          ("movie", "Wolfwalkers", 2020), ("movie", "Fantastic Mr. Fox", 2009)]),
}
def fanart(kind, tid):
    key = os.environ.get("FANART_API_KEY")
    if not key or not tid:
        return []
    try:
        if kind == "tv":
            tvdb = (tmdb(f"/tv/{tid}/external_ids") or {}).get("tvdb_id")
            if not tvdb:
                return []
            url, keys = f"https://webservice.fanart.tv/v3/tv/{tvdb}?api_key={key}", ("showbackground",)
        else:
            url, keys = f"https://webservice.fanart.tv/v3/movies/{tid}?api_key={key}", ("moviebackground", "movie4kbackground")
        d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}), timeout=60).read())
    except Exception:
        return []
    bg = [x for k in keys for x in d.get(k, [])]
    return [x["url"] for x in sorted(bg, key=lambda x: -int(x.get("likes", 0) or 0))]


def find(kind, title, year):
    if kind == "movie":
        return g.find_movie(title, year)
    r = (tmdb("/search/tv", query=title) or {}).get("results", [])
    yr = lambda x: int((x.get("first_air_date") or "0")[:4] or 0) if (x.get("first_air_date") or "0")[:4].isdigit() else 0
    near = [x for x in r if not year or abs(yr(x) - year) <= 1]
    exact = [x for x in near if x.get("name", "").lower() == title.lower()]
    pick = (exact or near or r or [None])[0]
    return (pick["id"], pick["name"]) if pick else (None, None)


KIND = {}   # (tmdb id, name) -> "movie" / "tv" of the pictures picked, for the labels
LABEL = {}  # (tmdb id, name) -> (name, year) as the pool writes it (TMDB may file a classic under a later reboot)
SINCE = {"Looney Tunes": 1930}   # pool items searched without a year


def art_of(item):
    kind, title, year = item[:3]
    tid, real = find(kind, title, year)
    KIND[(tid, real)] = kind
    LABEL[(tid, real)] = (title, year or SINCE.get(title, ""))
    if not tid:
        return None
    fa = fanart(kind, tid)
    if fa:
        return tid, real, fa[min(item[3] if len(item) > 3 else 0, len(fa) - 1)]
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null") or {}
    bd = sorted([b for b in im.get("backdrops", []) if not b.get("iso_639_1")], key=lambda b: (-b["vote_count"], -b["vote_average"]))
    return (tid, real, bd[0]["file_path"]) if bd else None


USED_COLL = set()   # film series already on a card this month: no two films of one series play at once


def series_free(it, a):
    """True if a (picked from pool item it) is not from a series already showing; claims its series if so."""
    if it[0] != "movie":
        return True
    c = g.collection_of(a[0])
    if c and c in USED_COLL:
        return False
    if c:
        USED_COLL.add(c)
    return True


def trio(pool, n=3, avoid=()):
    m = dt.date.today().year * 12 + dt.date.today().month
    start = (m * n) % len(pool)
    out = []
    for it in pool[start:] + pool[:start]:
        a = art_of(it)
        if a and a[0] not in avoid and series_free(it, a):
            out.append(a)
        if len(out) == n:
            break
    return out


def popular_family(n=4):
    since = (dt.date.today() - dt.timedelta(days=3 * 365)).isoformat()
    r = (tmdb("/discover/movie", with_genres="10751", sort_by="popularity.desc", with_original_language="en",
              **{"vote_count.gte": 150, "primary_release_date.gte": since}) or {}).get("results", [])
    out = []
    for x in r:
        a = art_of(("movie", x["title"], int((x.get("release_date") or "0")[:4] or 0)))
        if a:
            out.append(a)
        if len(out) == n:
            break
    return out


def build(t, out):
    title, sub, accent, cover, pool = CARDS[t]
    if cover is None:
        seq = popular_family(4)
    else:
        first = art_of(cover)
        if first:
            series_free(cover, first)
        seq = ([first] if first else []) + trio(pool, 3, avoid={first[0]} if first else set())
    imgs = [g.load_img(p) for _, _, p in seq]
    labels = [LABEL.get((x[0], x[1])) or g.labels_of([x], KIND.get((x[0], x[1]), "movie"))[0] for x in seq]
    frame = g.make(title, sub, accent, imgs, labels=labels)
    dd = os.path.join(out, g.slug_of(t))
    os.makedirs(dd, exist_ok=True)
    n = frame.n
    frames = [frame(i, n).resize((g.OW, g.OH), Image.LANCZOS) for i in range(n)]
    frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * n, loop=0,
                   quality=80, method=4, kmin=0, kmax=1)
    frame.cover().save(os.path.join(dd, "cover.jpg"), quality=90)
    # Nuvio TV's hero and title logo: the cover's picture laid out for the TV, the cover's own type as the logo
    if imgs:
        hero_styles.scene(imgs[0].convert("RGB")).save(os.path.join(dd, "backdrop.jpg"), quality=86)
    tv_logos.kids_logo(title, accent, seed=2 * list(CARDS).index(t)).save(os.path.join(dd, "logo.png"))   # bouncy letters
    strip = Image.new("RGB", (g.OW * 3, g.OH * 2))
    for jj, idx in enumerate([0, n // 6, n // 3, n // 2, 2 * n // 3, n - 1]):
        strip.paste(frames[idx], ((jj % 3) * g.OW, (jj // 3) * g.OH))
    strip.save(os.path.join(dd, "frames.jpg"), quality=80)
    return [x[1] for x in seq]


if __name__ == "__main__":
    out = sys.argv[1]
    failed = False
    for t in sys.argv[2:] or CARDS:
        try:
            print("built", t, "·", ", ".join(map(str, build(t, out))))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", t, e)
            failed = True
    sys.exit(1 if failed else 0)
