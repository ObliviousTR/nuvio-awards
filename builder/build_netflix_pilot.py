"""Netflix pilot: original backup with ONLY the Netflix folder rebuilt on Nuvio's native TMDB sources.

IDs used (verified in mali-king/nuvio-collections build report or Nuvio source):
  Netflix watch providers 8|1796, Netflix network 213, stand-up keyword 9716,
  nature keywords 221355|9902, noise TV genres 10763|10767|10766 (news/talk/soap).
"""
import json, sys, copy

SRC, OUT = sys.argv[1], sys.argv[2]
NF = "8|1796"
NOISE = "10763|10767|10766"


def src(title, media, sort="popularity.desc", stype="DISCOVER", tmdb_id=None, **filters):
    # mediaType must be upper-case: the TV app parses it with Enum.valueOf(raw.uppercase()).
    return {
        "type": None, "genre": None, "title": title, "sortBy": sort, "tmdbId": tmdb_id,
        "addonId": None, "filters": {k: v for k, v in filters.items() if v is not None},
        "sortHow": None, "provider": "tmdb", "catalogId": None, "mediaType": media,
        "traktListId": None, "tmdbSourceType": stype,
    }


def us(title, media, sort="popularity.desc", vc=None, **f):
    """Rail limited to what Netflix US carries."""
    if media == "TV":
        f.setdefault("withoutGenres", NOISE)
    if vc is None:
        vc = 20 if media == "MOVIE" else 10
    return src(title, media, sort, withWatchProviders=NF, watchRegion="US", voteCountGte=vc, **f)


rails = [
    # Headline rails (Kaptain's "Top 10" has no TMDB equivalent; Popular is the closest live signal)
    us("Popular Movies", "MOVIE", vc=100),
    us("Popular Series", "TV", vc=50),
    src("Netflix Original Series", "TV", stype="NETWORK", tmdb_id=213,
        withoutGenres=NOISE, releaseDateGte="2012-01-01"),
    us("New Movies", "MOVIE", "primary_release_date.desc", vc=25),
    us("New Series", "TV", "first_air_date.desc", vc=15),
    us("Top Rated Movies", "MOVIE", "vote_average.desc", vc=1000),
    us("Top Rated Series", "TV", "vote_average.desc", vc=300),
    # Turkish picks
    src("Türk Dizileri · Netflix Original", "TV", stype="NETWORK", tmdb_id=213,
        withOriginCountry="TR", withoutGenres=NOISE),
    src("Türk Filmleri · Netflix TR", "MOVIE", withWatchProviders=NF, watchRegion="TR",
        withOriginCountry="TR", voteCountGte=5),
    # Genres (TMDB TV has no separate Horror/Romance/Thriller/History genres, so those are movie-only)
    us("Action Movies", "MOVIE", withGenres="28"),
    us("Action & Adventure Series", "TV", withGenres="10759"),
    us("Adventure Movies", "MOVIE", withGenres="12"),
    us("Animation Movies", "MOVIE", withGenres="16"),
    us("Animation Series", "TV", withGenres="16"),
    us("Anime Movies", "MOVIE", vc=10, withGenres="16", withOriginalLanguage="ja"),
    us("Anime Series", "TV", vc=5, withGenres="16", withOriginalLanguage="ja"),
    us("Comedy Movies", "MOVIE", withGenres="35"),
    us("Comedy Series", "TV", withGenres="35"),
    us("Romantic Comedy Movies", "MOVIE", withGenres="10749,35"),
    us("Crime Movies", "MOVIE", withGenres="80"),
    us("Crime Series", "TV", withGenres="80"),
    us("Documentary Movies", "MOVIE", vc=10, withGenres="99"),
    us("Documentary Series", "TV", vc=5, withGenres="99"),
    us("Nature Documentaries", "MOVIE", vc=5, withGenres="99", withKeywords="221355|9902"),
    us("Nature Docuseries", "TV", vc=3, withGenres="99", withKeywords="221355|9902"),
    us("Drama Movies", "MOVIE", withGenres="18"),
    us("Drama Series", "TV", withGenres="18"),
    us("Family Movies", "MOVIE", withGenres="10751"),
    us("Family Series", "TV", withGenres="10751"),
    us("Kids Series", "TV", vc=5, withGenres="10762"),
    us("Fantasy Movies", "MOVIE", withGenres="14"),
    us("Science Fiction Movies", "MOVIE", withGenres="878"),
    us("Sci-Fi & Fantasy Series", "TV", withGenres="10765"),
    us("History Movies", "MOVIE", vc=10, withGenres="36"),
    us("Horror Movies", "MOVIE", withGenres="27"),
    us("Mystery Movies", "MOVIE", withGenres="9648"),
    us("Mystery Series", "TV", withGenres="9648"),
    us("Reality Series", "TV", vc=3, withGenres="10764"),
    us("Romance Movies", "MOVIE", withGenres="10749"),
    us("Stand-Up Comedy Specials", "MOVIE", vc=5, withKeywords="9716"),
    us("Thriller Movies", "MOVIE", withGenres="53"),
    us("War Movies", "MOVIE", vc=10, withGenres="10752"),
    us("War & Politics Series", "TV", vc=5, withGenres="10768"),
    us("Western Movies", "MOVIE", vc=5, withGenres="37"),
]

data = json.load(open(SRC))
hit = 0
for c in data:
    if c["title"] != "Streaming Services":
        continue
    for f in c["folders"]:
        if f["title"] == "Netflix":
            f["sources"] = copy.deepcopy(rails)
            f["catalogSources"] = []  # drop BingeCat fallback so only TMDB rails resolve
            hit += 1
assert hit == 1, hit

# Mirror Nuvio's validateImportModel before writing.
cids = set()
for c in data:
    assert c["id"] and c["id"] not in cids and c["title"]; cids.add(c["id"])
    fids = set()
    for f in c["folders"]:
        assert f["id"] and f["id"] not in fids and f["title"]; fids.add(f["id"])
        for s in f["sources"]:
            if s["provider"] == "tmdb":
                assert s["tmdbSourceType"] and s["mediaType"] in ("MOVIE", "TV")
            else:
                assert s["addonId"] and s["type"] and s["catalogId"]

json.dump(data, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"ok: Netflix -> {len(rails)} TMDB rails; {len(data)} collections, "
      f"{sum(len(c['folders']) for c in data)} folders written to {OUT}")
