"""Discover row: the agreed folders + Hidden Gems.

Agreed: New Movies, New Series, Trending Movies, Trending Series, All-Time Top Rated (each: the general list,
an anime rail, then genre rails), Awards & Prestige (a short curated pick of the Awards row), plus Hidden Gems.
Kaptain's Top Movies / Top Series by streaming service are dropped (agreed: they repeat the Streaming row).

Rules carried over: general rails are English-language, no animation outside the Animation / Anime rails,
genres merged the same way as the Genres row. Nuvio's TMDB source has no "trending" endpoint, so the trending
charts come from AIOMetadata (TMDB trending day/week, Trakt trending) and the genre rails underneath are native
"popular right now" rails limited to recent releases.
"""
import sys
from common import (src, addon_src, span, load, save, row, placeholder_folder, NOISE, POP, TOP, NEW,
                    CURRENT_YEAR)
from build_discover_gems_data import GEMS
from build_awards import AWARDS_ADDON
from common import spot_src, art_folder

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
EN = {"withOriginalLanguage": "en"}
ANIME = {"withGenres": "16", "withOriginalLanguage": "ja"}
RECENT = {"releaseDateGte": f"{CURRENT_YEAR - 1}-01-01"}  # "right now": last year + this year

# (display, movie genres, series genres) — merged the same way as the Genres row; None = no rail
GENRES = [
    ("Action & Adventure", "28|12", "10759"),
    ("Comedy", "35", "35"),
    ("Crime", "80", "80"),
    ("Drama", "18", "18"),
    ("Sci-Fi & Fantasy", "878|14", "10765"),
    ("Mystery & Thriller", "9648|53", "9648"),
    ("Horror", "27", None),
    ("Romance", "10749", None),
    ("Family", "10751", "10751"),
    ("History & War", "36|10752", "10768"),
    ("Western", "37", "37"),
    ("Music", "10402", None),
    ("Documentary", "99", "99"),
    ("Reality", None, "10764"),
    ("Kids", None, "10762"),
]


def m(title, sort, vc, genres=None, toon=False, **f):
    no = None if toon else "16"
    g = {"withGenres": genres} if genres else {}
    return src(title, "MOVIE", sort, voteCountGte=vc, withoutGenres=no, **EN, **g, **f)


def s(title, sort, vc, genres=None, toon=False, **f):
    no = NOISE if toon else "16|" + NOISE
    g = {"withGenres": genres} if genres else {}
    return src(title, "TV", sort, voteCountGte=vc, withoutGenres=no, **EN, **g, **f)


def genre_rails(media, sort, vc, prefix, suffix, **f):
    out = []
    mk = m if media == "MOVIE" else s
    for name, mg, tg in GENRES:
        g = mg if media == "MOVIE" else tg
        if g is None or (name == "Kids" and media == "MOVIE"):
            continue
        toon = name == "Kids"  # kids TV is mostly animated; it's its own rail
        out.append(mk(f"{prefix}{name} {suffix}".strip(), sort, vc, g, toon=toon, **f))
        if name == "Comedy":  # Animation sits after Comedy, as in Kaptain's order
            out.append(mk(f"{prefix}Animation {suffix}".strip(), sort, vc, "16", toon=True, **f))
    return out


def genre_pairs(sort, vm, vt, prefix):
    """Movie / series pairs per genre (only the half that exists), Animation after Comedy."""
    out = []
    for name, mg, tg in GENRES:
        names = [name] + (["Animation"] if name == "Comedy" else [])
        for n in names:
            g_m, g_t = ("16", "16") if n == "Animation" else (mg, tg)
            toon = n in ("Animation", "Kids")
            if g_m and n != "Kids":
                out.append(m(f"{prefix}{n} Movies", sort, vm, g_m, toon=toon))
            if g_t:
                out.append(s(f"{prefix}{n} Series", sort, vt, g_t, toon=toon))
    return out


def aio(title, media, cid, genre="None"):
    a = addon_src(title, media, cid)
    a["genre"] = genre
    return a


def awards(title, media, cid):
    a = addon_src(title, media, cid, addon_id=AWARDS_ADDON)
    a["genre"] = None
    return a


FOLDERS = [
    ("New Movies", "New Movies", [
        m("New Movies", NEW["MOVIE"], 50),
        spot_src("New on Digital", "MOVIE", "spotlight-fresh-movies"),  # just out of theaters, rebuilt daily
        src("New Anime Movies", "MOVIE", NEW["MOVIE"], voteCountGte=10, **ANIME),
    ] + genre_rails("MOVIE", NEW["MOVIE"], 20, "New ", "Movies")),
    ("New Series", "New Series", [
        s("New Series", NEW["TV"], 20),
        src("New Anime Series", "TV", NEW["TV"], voteCountGte=5, **ANIME),
    ] + genre_rails("TV", NEW["TV"], 10, "New ", "Series")),
    ("Trending Movies", "Trending Movies", [
        aio("Trending Today", "MOVIE", "tmdb.trending", "Day"),
        aio("Trending This Week", "MOVIE", "tmdb.trending", "Week"),
        aio("Trending on Trakt", "MOVIE", "trakt.trending.movies"),
        src("Trending Anime Movies", "MOVIE", POP, voteCountGte=20, **ANIME, **RECENT),
    ] + genre_rails("MOVIE", POP, 50, "Trending ", "Movies", **RECENT)),
    ("Trending Series", "Trending TV", [
        aio("Trending Today", "TV", "tmdb.trending", "Day"),
        aio("Trending This Week", "TV", "tmdb.trending", "Week"),
        aio("Trending on Trakt", "TV", "trakt.trending.shows"),
        src("Trending Anime Series", "TV", POP, voteCountGte=10, **ANIME, **RECENT),   # was Simkl's anime catalog:
        # AIOMetadata serves it as type "anime", so the TV rail asked for it came back empty
    ] + genre_rails("TV", POP, 20, "Trending ", "Series", **RECENT)),
    ("All-Time Top Rated", "Top Movies", [
        src("Top Rated Movies", "MOVIE", TOP, voteCountGte=3000, withoutGenres="16|99", **EN),  # docs/kids have own rails
        src("Top Rated Series", "TV", TOP, voteCountGte=1000, withoutGenres="16|99|10762|" + NOISE, **EN),
        src("Top Rated Anime Movies", "MOVIE", TOP, voteCountGte=500, **ANIME),
        src("Top Rated Anime Series", "TV", TOP, voteCountGte=300, **ANIME),
        aio("IMDb Top 250", "MOVIE", "mdblist.205811"),
        aio("Letterboxd Top 500", "MOVIE", "mdblist.205902"),
    ] + genre_pairs(TOP, 1000, 300, "Top Rated ")),
    ("Awards & Prestige", "🏆", [
        awards("Latest Oscar Nominees", "MOVIE", "oscar-latest-nominees"),
        awards("Oscar Best Picture Winners", "MOVIE", "oscar-best-picture"),
        awards("Oscar Best Picture Nominees", "MOVIE", "oscar-best-picture-nominees"),
        awards("Best International Feature Winners", "MOVIE", "oscar-international"),
        awards("Palme d'Or Winners", "MOVIE", "cannes-palme"),
        awards("Venice Golden Lion Winners", "MOVIE", "venice-golden-lion"),
        awards("Emmy · Outstanding Drama Series", "TV", "emmy-drama-series"),
        awards("Emmy · Outstanding Comedy Series", "TV", "emmy-comedy-series"),
        aio("Criterion Collection · Essentials", "MOVIE", "mdblist.13676"),
        aio("Sight and Sound · Greatest Films", "MOVIE", "mdblist.207869"),
    ]),
    ("Hidden Gems", "💎", [addon_src(t, media, f"mdblist.{i}") for t, media, i in GEMS]),
]

data = load(SRC)
discover = row(data, "Discover")
kaptain = {f["title"]: f for f in discover["folders"]}
folders, report = [], []
for title, art, rails in FOLDERS:
    if art in kaptain:
        f = {k: v for k, v in kaptain[art].items() if k not in ("sources", "catalogSources")}
        f["title"] = title
    else:
        f = placeholder_folder(title, art)
    f["sources"], f["catalogSources"] = rails, []
    folders.append(f)
    report.append(f"## {title} ({len(rails)} rails)")
    report += [f"   {i+1:2}. {s_['title']}" for i, s_ in enumerate(rails)]
# Daily charts from our Spotlight addon (rebuilt every morning), with our covers
BOX_OFFICE = art_folder("folder-discover-boxoffice", "Box Office Champions", "boxoffice", [
    spot_src("Box Office · Last 12 Months", "MOVIE", "spotlight-boxoffice-movies"),
    spot_src("Box Office · All-Time Champions", "MOVIE", "spotlight-boxoffice-alltime")])
CERTIFIED = art_folder("folder-discover-certified", "Certified Fresh & Must-See", "certified", [
    spot_src("Must-See Movies", "MOVIE", "spotlight-certified-movies"),
    spot_src("Must-See Series", "TV", "spotlight-certified-series")])
order = [f["title"] for f in folders]
folders.insert(order.index("Trending Series") + 1, BOX_OFFICE)
folders.insert([f["title"] for f in folders].index("Awards & Prestige") + 1, CERTIFIED)
for f in (BOX_OFFICE, CERTIFIED):
    report.append(f"## {f['title']} ({len(f['sources'])} rails)")
    report += [f"   {i+1:2}. {s_['title']}" for i, s_ in enumerate(f["sources"])]
discover["folders"] = folders
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} folders -> {OUT}")
