"""Genres (14, merged where TMDB content overlaps) and By Decade (9).

Genre rail order (user spec):
  New M/S -> Popular M/S -> Top All Time M/S -> Top of the Year M/S -> International Hits M/S ->
  Popular Anime M/S -> Top Rated Anime M/S
All year rails use release-date windows (span), never TMDB's `year` filter (matches re-releases).
Main rails become English-only in apply_language_policy.py; anime rails are pinned to Japanese.
"""
import sys
from common import src, span, load, save, row, add, placeholder_folder, NOISE, CURRENT_YEAR, INTL_LANGS, TOP, NEW

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
HORROR_TV = "315058|9853|162846|3358|295907"  # verified: Supernatural, AHS, Stranger Things, Ghosts
ROMANCE_TV = "9840"                           # verified: Bridgerton, Outlander, This Is Us
JA = {"withOriginalLanguage": "ja"}

# (title, backup art, movie filters, series filters, small?, anime movie filters, anime series filters)
GENRES = [
    ("Action & Adventure", "Action", {"withGenres": "28|12"}, {"withGenres": "10759"}, False,
     {"withGenres": "16,28"}, {"withGenres": "16,10759"}),
    ("Sci-Fi & Fantasy", "Science Fiction", {"withGenres": "878|14"}, {"withGenres": "10765"}, False,
     {"withGenres": "16,14"}, {"withGenres": "16,10765"}),
    ("Superhero", "Superhero", {"withKeywords": "9715"}, {"withKeywords": "9715"}, True,
     None, {"withGenres": "16", "withKeywords": "9715"}),
    ("Martial Arts", "Martial Arts", {"withKeywords": "779|780|184656"}, {"withKeywords": "779|780|184656"}, True,
     None, None),
    ("Horror", "Horror", {"withGenres": "27"},
     {"withKeywords": HORROR_TV, "withoutGenres": "16|99|" + NOISE}, False,
     {"withGenres": "16,27"}, {"withGenres": "16", "withKeywords": HORROR_TV}),
    ("Mystery & Thriller", "Thriller", {"withGenres": "9648|53"}, {"withGenres": "9648"}, False,
     {"withGenres": "16,9648"}, {"withGenres": "16,9648"}),
    ("Crime", "Crime", {"withGenres": "80"}, {"withGenres": "80"}, False,
     None, {"withGenres": "16,80"}),
    ("Comedy", "Comedy", {"withGenres": "35"}, {"withGenres": "35"}, False,
     {"withGenres": "16,35"}, {"withGenres": "16,35"}),
    ("Stand-Up Comedy", "Stand-Up Comedy", {"withKeywords": "9716"}, {"withKeywords": "9716"}, True,
     None, None),
    ("Romance & Rom-Com", "Romance", {"withGenres": "10749"},
     {"withKeywords": ROMANCE_TV, "withoutGenres": "16|" + NOISE}, False,
     {"withGenres": "16,10749"}, {"withGenres": "16", "withKeywords": ROMANCE_TV}),
    ("Drama", "Drama", {"withGenres": "18"}, {"withGenres": "18"}, False,
     {"withGenres": "16,18"}, {"withGenres": "16,18"}),
    ("History & War", "War", {"withGenres": "36|10752"}, {"withGenres": "10768"}, False,
     None, None),
    ("Western", "Western", {"withGenres": "37"}, {"withGenres": "37"}, True,
     None, None),
]

# ---- Animation and Anime: own folders, same main flow, then sub-genre rails in movie / series pairs.
# Sub-genres kept only where TMDB has enough titles (checked live: anime action series 907, action
# films 348, mystery series 201, isekai 143, romance series 500; adult animated comedy series 138).
ANIM = {"withGenres": "16"}                                   # language policy makes these English-only
ANIME = {"withGenres": "16", "withOriginalLanguage": "ja"}
ANIMATION_SUB = [  # (rail prefix, movie filters, series filters)
    ("Action & Adventure", {"withGenres": "16,28"}, {"withGenres": "16,10759"}),
    ("Sci-Fi & Fantasy", {"withGenres": "16,14"}, {"withGenres": "16,10765"}),
    ("Comedy", {"withGenres": "16,35"}, None),
    ("Adult Animated Comedy", None, {"withGenres": "16,35", "withoutGenres": "10751|10762|" + NOISE}),
    ("Family", {"withGenres": "16,10751"}, {"withGenres": "16,10751"}),
    ("Superhero", {"withGenres": "16", "withKeywords": "9715"}, {"withGenres": "16", "withKeywords": "9715"}),
    ("Kids", None, {"withGenres": "16,10762"}),
]
ANIME_SUB = [
    ("Action & Adventure", {"withGenres": "16,28"}, {"withGenres": "16,10759"}),
    ("Sci-Fi & Fantasy", {"withGenres": "16,14"}, {"withGenres": "16,10765"}),
    ("Isekai", None, {"withGenres": "16", "withKeywords": "237451"}),
    ("Mystery & Thriller", {"withGenres": "16,9648"}, {"withGenres": "16,9648"}),
    ("Romance", {"withGenres": "16,10749"}, {"withGenres": "16", "withKeywords": ROMANCE_TV}),
    ("Comedy", {"withGenres": "16,35"}, {"withGenres": "16,35"}),
    ("Drama", {"withGenres": "16,18"}, {"withGenres": "16,18"}),
    ("Horror", {"withGenres": "16,27"}, {"withGenres": "16", "withKeywords": HORROR_TV}),
]


def toon_rails(base, subs, anime):
    """Main flow (New / Popular / Top All Time / Top of the Year, movie-series pairs) + sub-genres."""
    lang = {"withOriginalLanguage": "ja"} if anime else {}
    vc = dict(new=(10, 5), pop=(50, 30), top=(300, 150), yr=(15, 8), sub=(30, 20))
    yr = span(CURRENT_YEAR)
    r = []
    for label, sort, key, extra in (("New", NEW, "new", {}), ("Popular", None, "pop", {}),
                                    ("Top All Time", TOP, "top", {}), ("Top of the Year", TOP, "yr", yr)):
        sm = sort["MOVIE"] if isinstance(sort, dict) else (sort or "popularity.desc")
        st = sort["TV"] if isinstance(sort, dict) else (sort or "popularity.desc")
        r.append(src(f"{label} Movies", "MOVIE", sm, voteCountGte=vc[key][0], **add(base, **extra)))
        r.append(src(f"{label} Series", "TV", st, voteCountGte=vc[key][1], **add(base, **extra)))
    if not anime:  # non-English, non-Japanese animation (Flow, Persepolis, European features)
        r.append(src("International Animation", "MOVIE", voteCountGte=500, withGenres="16",
                     withOriginalLanguage=INTL_LANGS.replace("|ja", "")))
    for prefix, mf, tf in subs:
        if mf: r.append(src(f"{prefix} Movies", "MOVIE", voteCountGte=vc["sub"][0], **add(mf, **lang)))
        if tf: r.append(src(f"{prefix} Series", "TV", voteCountGte=vc["sub"][1], **add(tf, **lang)))
    return r


def genre_rails(title, mf, tf, small, am, at):
    fl = dict(new_m=10, new_t=5, pop_m=30, pop_t=10, top_m=300, top_t=50, yr_m=15, yr_t=8, im=400, it=150) \
        if small else dict(new_m=20, new_t=10, pop_m=100, pop_t=50, top_m=1000, top_t=300, yr_m=60, yr_t=25, im=1500, it=800)
    yr = span(CURRENT_YEAR)
    pairs = [
        ("New", NEW, "new"), ("Popular", None, "pop"), ("Top All Time", TOP, "top"), ("Top of the Year", TOP, "yr"),
    ]
    mf = add(mf, withoutGenres="16")  # animation and anime have their own folders
    tf = add(tf, withoutGenres="16|" + NOISE)
    r = []
    for label, sort, key in pairs:
        extra = yr if key == "yr" else {}
        sm = sort["MOVIE"] if isinstance(sort, dict) else (sort or "popularity.desc")
        st = sort["TV"] if isinstance(sort, dict) else (sort or "popularity.desc")
        r.append(src(f"{label} Movies", "MOVIE", sm, voteCountGte=fl[key + "_m"], **add(mf, **extra)))
        r.append(src(f"{label} Series", "TV", st, voteCountGte=fl[key + "_t"], **add(tf, **extra)))
    if True:  # intl hits exclude animation
        r.append(src("International Hits Movies", "MOVIE", voteCountGte=fl["im"],
                     **add(mf, withOriginalLanguage=INTL_LANGS, withoutGenres="16")))
        r.append(src("International Hits Series", "TV", voteCountGte=fl["it"],
                     **add(tf, withOriginalLanguage=INTL_LANGS, withoutGenres="16|" + NOISE)))
    if am or at:
        if am: r.append(src("Popular Anime Movies", "MOVIE", voteCountGte=20, **add(am, **JA)))
        if at: r.append(src("Popular Anime Series", "TV", voteCountGte=20, **add(at, **JA)))
        if am: r.append(src("Top Rated Anime Movies", "MOVIE", TOP, voteCountGte=200, **add(am, **JA)))
        if at: r.append(src("Top Rated Anime Series", "TV", TOP, voteCountGte=100, **add(at, **JA)))
    return r


# ---------------------------------------------------------------- By Decade (Kaptain rail names)
def decade_rails(label, start, end, last_year, intl_tv_floor=None):
    d = span(start, end)
    r = [
        src(f"Popular {label} Movies", "MOVIE", voteCountGte=100, **d),
        src(f"Popular {label} TV Shows", "TV", voteCountGte=30, **d),
        src(f"Top Rated {label} Movies", "MOVIE", TOP, voteCountGte=500, **d),
        src(f"Top Rated {label} TV Shows", "TV", TOP, voteCountGte=100, **d),
        src(f"International Hits of the {label} · Movies", "MOVIE", voteCountGte=1000,
            withOriginalLanguage=INTL_LANGS, withoutGenres="16", **d),
    ]
    if intl_tv_floor:
        r.append(src(f"International Hits of the {label} · TV Shows", "TV", voteCountGte=intl_tv_floor,
                     withOriginalLanguage=INTL_LANGS, withoutGenres="16|" + NOISE, **d))
    r += [src(f"Most Popular of the Year {y}", "MOVIE", voteCountGte=50, **span(y)) for y in range(start, last_year + 1)]
    return r


yr = span(CURRENT_YEAR)
DECADES = [  # (title, backup art folder or None, rails)
    (f"🏆 Best of {CURRENT_YEAR}", None, [
        src("Top Rated Movies", "MOVIE", TOP, voteCountGte=60, **yr),
        src("Top Rated Series", "TV", TOP, voteCountGte=25, **yr),
        src("Popular Movies", "MOVIE", voteCountGte=40, **yr),
        src("Popular Series", "TV", voteCountGte=15, **yr),
        src("International Hits Movies", "MOVIE", voteCountGte=150, withOriginalLanguage=INTL_LANGS,
            withoutGenres="16", **yr),
        src("International Hits Series", "TV", voteCountGte=60, withOriginalLanguage=INTL_LANGS,
            withoutGenres="16|" + NOISE, **yr),
    ]),
    ("2020s", "2020s Movies", decade_rails("2020s", 2020, 2029, CURRENT_YEAR, 500)),
    ("2010s", "10s Movies", decade_rails("2010s", 2010, 2019, 2019, 800)),
    ("2000s", "00s Movies", decade_rails("2000s", 2000, 2009, 2009, 500)),
    ("1990s", "90s Movies", decade_rails("1990s", 1990, 1999, 1999, 150)),
    ("1980s", "80s Movies", decade_rails("1980s", 1980, 1989, 1989, 100)),
    ("1970s", "70s Movies", decade_rails("1970s", 1970, 1979, 1979)),
    ("1960s", "60s Movies", decade_rails("1960s", 1960, 1969, 1969)),
    ("1950s & Golden Age", "50s Movies", decade_rails("1950s", 1950, 1959, 1959) + [
        src("Golden Age Classics (1930–1949)", "MOVIE", voteCountGte=100, **span(1930, 1949)),
        src("Top Rated Golden Age", "MOVIE", TOP, voteCountGte=300, **span(1930, 1949)),
    ]),
]

data = load(SRC)
report = []


def rebuild(row_title, specs, emoji="🏆"):
    r_ = row(data, row_title)
    backup = {f["title"]: f for f in r_["folders"]}
    out = []
    for title, art, rails in specs:
        f = dict(backup[art]) if art else placeholder_folder(title, emoji)
        f["title"], f["sources"], f["catalogSources"] = title, rails, []
        out.append(f)
        report.append(f"{row_title} / {title}: " + " | ".join(s["title"] for s in rails))
    r_["folders"] = out


rebuild("Genres", [(t, art, genre_rails(t, mf, tf, small, am, at)) for t, art, mf, tf, small, am, at in GENRES]
        + [("Animation", "Animation", toon_rails(ANIM, ANIMATION_SUB, anime=False)),
           ("Anime", "Anime", toon_rails(ANIME, ANIME_SUB, anime=True))])
rebuild("By Decade", DECADES)
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok -> {OUT}")
