"""Streaming Services: the 11 agreed platforms, native TMDB rails + FlixPatrol Top 10 via AIOMetadata.

Rail order per folder (user spec):
  Top 10 Movies / Series (FlixPatrol, AIOMetadata) -> <Service> Originals -> New Movies / Series ->
  Popular Movies / Series -> Top Rated Movies / Series -> (Netflix only: Turkish rails) ->
  genre rails: every movie genre in canonical order, then every series genre in the same order.
A genre appears only if Kaptain had it for that service. Genres TMDB lumps together are merged
under one name in both movies and series (Action & Adventure, Sci-Fi & Fantasy, History & War,
Mystery & Thriller).

IDs: providers / networks verified via mali-king/nuvio-collections report, Kometa defaults and the
TMDB network export. Horror / romance series keywords verified against the TMDB API.
"""
import sys
from common import src, addon_src, load, save, row, NOISE, NEW, TOP, placeholder_folder

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]

FLOORS = {
    "global": dict(pop_m=100, pop_t=50, new_m=25, new_t=15, top_m=1000, top_t=300, g_m=20, g_t=10),
    "mid": dict(pop_m=30, pop_t=20, new_m=10, new_t=5, top_m=200, top_t=80, g_m=10, g_t=5),
}

# title -> (watch providers, region, originals networks, floor)
SERVICES = {
    "Netflix":     ("8|1796", "US", [213], "global"),
    "HBO Max":     ("1899", "US", [49, 3186, 8304], "global"),
    "Apple TV+":   ("350", "US", [2552], "global"),
    "Prime Video": ("9|2100", "US", [1024], "global"),
    "Disney+":     ("337", "US", [2739], "global"),
    "Hulu":        ("15", "US", [453], "global"),
    "Paramount+":  ("2303|2616|531|1770", "US", [4330], "global"),
    "Mubi":        ("11", "US", None, "mid"),
    "Crunchyroll": ("283", "US", [1112], "mid"),
    "Shudder":     ("99", "US", [2949], "mid"),
    "Discovery+":  ("510", "US", [4353], "mid"),
}

# FlixPatrol Top 10 catalogs exactly as they appear in the user's AIOMetadata manifest (checked live).
# Netflix / Apple TV+ use the Global chart (same catalogue worldwide); the rest use the US chart.
# Services that publish one combined chart come through as type "all".
TOP10 = {
    "Netflix":     [("Top 10 Movies", "MOVIE", "flixpatrol.netflix.global.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.netflix.global.series"),
                    ("Top 10 Movies · Türkiye", "MOVIE", "flixpatrol.netflix.tr.movie"),
                    ("Top 10 Series · Türkiye", "TV", "flixpatrol.netflix.tr.series")],
    "HBO Max":     [("Top 10 Movies", "MOVIE", "flixpatrol.hbo-max.us.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.hbo-max.us.series"),
                    ("Top 10 Movies · Türkiye", "MOVIE", "flixpatrol.hbo-max.tr.movie")],
    "Apple TV+":   [("Top 10 Movies", "MOVIE", "flixpatrol.apple-tv.global.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.apple-tv.global.series")],
    "Prime Video": [("Top 10 Movies", "MOVIE", "flixpatrol.amazon-prime.us.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.amazon-prime.us.series"),
                    ("Top 10 Movies · Türkiye", "MOVIE", "flixpatrol.amazon-prime.tr.movie"),
                    ("Top 10 Series · Türkiye", "TV", "flixpatrol.amazon-prime.tr.series")],
    "Disney+":     [("Top 10 Movies", "MOVIE", "flixpatrol.disney.us.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.disney.us.series"),
                    ("Top 10 Movies · Türkiye", "MOVIE", "flixpatrol.disney.tr.movie"),
                    ("Top 10 Series · Türkiye", "TV", "flixpatrol.disney.tr.series")],
    "Hulu":        [("Top 10 Movies", "MOVIE", "flixpatrol.hulu.us.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.hulu.us.series")],
    "Paramount+":  [("Top 10 Movies", "MOVIE", "flixpatrol.paramount.us.movie"),
                    ("Top 10 Series", "TV", "flixpatrol.paramount.us.series")],
    "Crunchyroll": [("Top 10", "ALL", "flixpatrol.crunchyroll.us.all")],
    "Shudder":     [("Top 10", "ALL", "flixpatrol.shudder.us.all")],
    "Discovery+":  [("Top 10", "ALL", "flixpatrol.discovery-plus.us.all")],
}
AGREED = list(SERVICES)

# Turkish platforms (agreed 2026-10-21): their own originals by TMDB network, no US provider filter.
# BluTV became Max / HBO Max Türkiye in 2025, so its archive sits in the HBO Max folder instead.
# tabii is TRT's platform: its originals plus the TRT 1 archive it streams. TOD left out on purpose.
SITCOM_SERVICES = {"Netflix", "HBO Max", "Disney+", "Prime Video", "Hulu", "Paramount+"}
TR_LOGO = "https://image.tmdb.org/t/p/w500"
TR_SERVICES = {
    "Exxen": (4405, "/4zfhGWmcU1iZzBXam02RWix54FY.png", ["Comedy"]),
    "GAİN":  (4409, "/jl6MlpZG9y0dHB0FBuzcy3QldvO.png", ["Comedy", "Drama", "Crime & Mystery"]),
    "tabii": (6854, "/fgz7CR1S4zMhND86zVwgKCOhCj4.png", []),
}
TR_GENRES = {"Comedy": "35", "Drama": "18", "Crime & Mystery": "80|9648"}


def tr_rails(name, net):
    n = dict(withNetworks=str(net))
    r = [src(f"Popular {name} Originals", "TV", **n),
         src(f"New on {name}", "TV", NEW["TV"], **n),
         src(f"Top Rated {name} Originals", "TV", TOP, voteCountGte=3, **n)]
    r += [src(f"{g} Series", "TV", withGenres=TR_GENRES[g], **n) for g in TR_SERVICES[name][2]]
    if name == "tabii":  # TRT 1 archive streams on tabii
        r += [src("Popular TRT Series", "TV", withNetworks="869"),
              src("Top Rated TRT Series", "TV", TOP, withNetworks="869", voteCountGte=5)]
    return r

HORROR_TV = "315058|9853|162846|3358|295907"  # horror, paranormal, ghost, haunted house, psychological horror
ROMANCE_TV = "9840"
NATURE = "221355|9902"
STANDUP = "9716"
ANIME = {"withGenres": "16", "withOriginalLanguage": "ja"}

# Canonical genre order: (display name, Kaptain words that map here, movie filters, series filters)
GENRES = [
    ("Action & Adventure", {"Action", "Adventure"}, {"withGenres": "28|12"}, {"withGenres": "10759"}),
    # English-language animation only, so Japanese anime stays in the Anime rails (as in the Genres row)
    ("Animation", {"Animation"}, {"withGenres": "16", "withOriginalLanguage": "en"},
     {"withGenres": "16", "withOriginalLanguage": "en"}),
    ("Anime", {"Anime"}, ANIME, ANIME),
    ("Comedy", {"Comedy"}, {"withGenres": "35"}, {"withGenres": "35"}),
    ("Romantic Comedy", {"Romantic Comedy"}, {"withGenres": "10749,35"}, {"withGenres": "35", "withKeywords": ROMANCE_TV}),
    ("Crime", {"Crime"}, {"withGenres": "80"}, {"withGenres": "80"}),
    ("Drama", {"Drama"}, {"withGenres": "18"}, {"withGenres": "18"}),
    # Live-action family; animated family titles live in the Animation rails right above.
    ("Family", {"Family"}, {"withGenres": "10751", "withoutGenres": "16"},
     {"withGenres": "10751", "withoutGenres": "16|" + NOISE}),
    ("Sci-Fi & Fantasy", {"Science Fiction", "Fantasy"}, {"withGenres": "878|14"}, {"withGenres": "10765"}),
    ("History & War", {"History", "War"}, {"withGenres": "36|10752"}, {"withGenres": "10768"}),
    ("Horror", {"Horror"}, {"withGenres": "27"}, {"withKeywords": HORROR_TV, "withoutGenres": "16|99|" + NOISE}),
    ("Mystery & Thriller", {"Mystery", "Thriller"}, {"withGenres": "9648|53"}, {"withGenres": "9648"}),
    ("Romance", {"Romance"}, {"withGenres": "10749"}, {"withKeywords": ROMANCE_TV, "withoutGenres": "16|" + NOISE}),
    ("Documentary", {"Documentary"}, {"withGenres": "99"}, {"withGenres": "99"}),
    ("Nature Documentary", {"Nature Documentary"}, {"withGenres": "99", "withKeywords": NATURE},
     {"withGenres": "99", "withKeywords": NATURE}),
    ("Reality", {"Reality"}, None, {"withGenres": "10764"}),
    ("Stand-Up Comedy", {"Stand-Up Comedy"}, {"withKeywords": STANDUP}, {"withKeywords": STANDUP}),
    ("Western", {"Western"}, {"withGenres": "37"}, {"withGenres": "37"}),
]
SERIES_NAME = {"Nature Documentary": "Nature Docuseries", "Documentary": "Docuseries"}


def provider_rail(title, media, sort, vc, svc, **f):
    prov, region = svc[0], svc[1]
    return src(title, media, sort, withWatchProviders=prov, watchRegion=region, voteCountGte=vc, **f)


def originals(svc, name):
    nets = svc[2]
    if len(nets) == 1:  # NETWORK type sends tmdbId only
        return src(f"{name} Originals", "TV", stype="NETWORK", tmdb_id=nets[0], releaseDateGte="2000-01-01")
    return src(f"{name} Originals", "TV", withNetworks="|".join(map(str, nets)), releaseDateGte="2000-01-01")


def kaptain_genres(folder):
    """Which (genre, media) pairs Kaptain had for this service."""
    have = set()
    for s in folder["sources"]:
        t = s.get("title") or ""
        for suffix, media in ((" Movies", "MOVIE"), (" Series", "TV")):
            if t.endswith(suffix):
                have.add((t[: -len(suffix)], media))
    return have


def build(folder, name, svc):
    fl = FLOORS[svc[3]]
    have = kaptain_genres(folder)
    # Kaptain gave Mubi a "Top 10 Series" chart rail; chart rails don't mean the service has series.
    has_m = any(m == "MOVIE" and g != "Top 10" for g, m in have)
    has_t = any(m == "TV" and g != "Top 10" for g, m in have)
    r = []
    r += [addon_src(title, media, cid) for title, media, cid in TOP10.get(name, [])]
    if svc[2]:
        r.append(originals(svc, name))
    for kind, sort_m, sort_t, km, kt in (("New", "primary_release_date.desc", "first_air_date.desc", "new_m", "new_t"),
                                        ("Popular", "popularity.desc", "popularity.desc", "pop_m", "pop_t"),
                                        ("Top Rated", "vote_average.desc", "vote_average.desc", "top_m", "top_t")):
        if has_m:
            r.append(provider_rail(f"{kind} Movies", "MOVIE", sort_m, fl[km], svc))
        if has_t:
            r.append(provider_rail(f"{kind} Series", "TV", sort_t, fl[kt], svc))
    if name == "Netflix":  # Turkish picks: originals by network, films from the Turkish catalogue
        r.append(src("Türk Filmleri · Netflix TR", "MOVIE", withWatchProviders="8|1796", watchRegion="TR",
                     withOriginCountry="TR", voteCountGte=5))
        r.append(src("Türk Dizileri · Netflix Original", "TV", stype="NETWORK", tmdb_id=213, withOriginCountry="TR"))
    if name == "HBO Max":  # Turkish originals: BluTV archive + Max / HBO Max Türkiye; Turkish films on HBO Max TR
        r.append(src("Türk Dizileri · HBO Max & BluTV", "TV", withNetworks="1747|6783|8304", withOriginCountry="TR"))
        r.append(src("Türk Filmleri · HBO Max TR", "MOVIE", withWatchProviders="1899", watchRegion="TR",
                     withOriginCountry="TR", voteCountGte=5))
    # Genre rails in movie / series pairs: Action & Adventure Movies, Action & Adventure Series, ...
    for disp, words, mf, tf in GENRES:
        for media in ("MOVIE", "TV"):
            f = mf if media == "MOVIE" else tf
            if f is None or not any((w, media) in have for w in words):
                continue
            title = f"{disp} Movies" if media == "MOVIE" else f"{SERIES_NAME.get(disp, disp + ' Series')}"
            vc = fl["g_m"] if media == "MOVIE" else fl["g_t"]
            r.append(provider_rail(title, media, "popularity.desc", vc, svc, **f))
            if title == "Comedy Series" and name in SITCOM_SERVICES:  # classic sitcoms first (agreed 2026-10-21)
                r.append(provider_rail("Sitcoms", "TV", "vote_count.desc", vc, svc, withKeywords="193171",
                                       withoutGenres="16|" + NOISE))
    return r


data = load(SRC)
streaming = row(data, "Streaming Services")
by_name = {f["title"]: f for f in streaming["folders"]}
streaming["folders"] = [by_name[t] for t in AGREED]
report = []
for f in streaming["folders"]:
    rails = build(f, f["title"], SERVICES[f["title"]])
    f["sources"], f["catalogSources"] = rails, []
    report.append(f"## {f['title']} ({len(rails)} rails)")
    report += [f"   {i+1:2}. {s['title']}" for i, s in enumerate(rails)]
for name, (net, logo, _) in TR_SERVICES.items():
    f = placeholder_folder(name, "📺")
    f.update(tileShape="LANDSCAPE", coverImageUrl=TR_LOGO + logo, titleLogoUrl=TR_LOGO + logo, coverEmoji=None)
    f["sources"], f["catalogSources"] = tr_rails(name, net), []
    streaming["folders"].append(f)
    rails = f["sources"]
    report.append(f"## {f['title']} ({len(rails)} rails)")
    report += [f"   {i+1:2}. {s['title']}" for i, s in enumerate(rails)]
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(AGREED)} + {len(TR_SERVICES)} Turkish services -> {OUT}")
