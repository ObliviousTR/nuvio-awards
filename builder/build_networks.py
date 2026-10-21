"""Step 3: Networks row = the 24 channels from the Gemini master list (row 13), native TMDB sources.

Kaptain artwork is reused where the backup has the channel (some under a different folder name);
channels without Kaptain art get TMDB's network logo for now (design pass comes at the end).
Network IDs: TMDB network export (davecollections/tmdb-id-lookup), highest-title-count match.
"""
import json, sys

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
NOISE = "10763|10767|10766"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

# (agreed title, TMDB network ids, backup folder to take art from or None, TMDB logo path, small catalogue?)
NETWORKS = [
    ("HBO", [49], "HBO", None, False),
    ("FX", [88], "FX", None, True),
    ("AMC", [174], "AMC", None, True),
    ("Showtime", [67], "Showtime", None, False),
    ("BBC", [4, 332, 3, 100], "BBC One", None, False),          # BBC One/Two/Three/Four
    ("ITV", [9], "ITV", None, False),
    ("Channel 4", [26], "Channel 4", None, False),
    ("U&Dave", [388], "Dave", None, True),
    ("Sky Atlantic", [1063], "Sky Atlantic", None, True),
    ("TV Tokyo", [98], "TV Tokyo", None, True),
    ("Fuji TV / MBS", [1, 94], None, "/4x4GsmRmSLLL0RVNKsoqAVH43tz.png", True),
    ("Adult Swim", [80], "Adult Swim", None, True),
    ("Comedy Central", [47], "Comedy Central", None, False),
    ("Syfy", [77], "Syfy", None, False),
    ("Cartoon Network", [56], "Cartoon Network", None, False),
    ("Discovery Channel", [64], "Discovery", None, False),
    ("National Geographic", [43], "National Geographic", None, False),
    ("History Channel", [65], "History", None, False),
    ("Food Network", [143], "Food Network", None, False),
    ("USA Network", [30], "USA Network", None, False),
    ("NBC", [6], "NBC", None, False),
    ("FOX", [19], "FOX", None, False),
    ("ABC", [2], "ABC", None, False),
    ("CBS", [16], "CBS", None, False),
]


def src(title, sort, nets, vc):
    base = {
        "type": None, "genre": None, "title": title, "sortBy": sort, "addonId": None, "sortHow": None,
        "provider": "tmdb", "catalogId": None, "mediaType": "TV", "traktListId": None,
    }
    filters = {"withoutGenres": NOISE, "voteCountGte": vc}
    if len(nets) == 1:   # NETWORK type: Nuvio sends tmdbId as with_networks
        return {**base, "tmdbId": nets[0], "tmdbSourceType": "NETWORK", "filters": filters}
    # Nuvio's NETWORK type ignores extra ids, so several networks go through DISCOVER.
    return {**base, "tmdbId": None, "tmdbSourceType": "DISCOVER",
            "filters": {**filters, "withNetworks": "|".join(map(str, nets))}}


# Genre rails for the networks with a big, varied catalogue (agreed 2026-10-21). Sorted by vote count, so the
# channel's defining shows come first. Specialty channels (docs, food, cartoons, anime, comedy) keep the three rails.
VOTES = "vote_count.desc"
NATURE = "221355|9902"
EXTRA = {
    "HBO": [("Drama", {"withGenres": "18"}, 50), ("Comedy", {"withGenres": "35"}, 30),
            ("Crime & Mystery", {"withGenres": "80|9648"}, 30), ("Fantasy & Sci-Fi", {"withGenres": "10765"}, 30),
            ("War & History", {"withGenres": "10768"}, 10), ("Docuseries", {"withGenres": "99"}, 10)],
    "Showtime": [("Drama", {"withGenres": "18"}, 30), ("Comedy", {"withGenres": "35"}, 20),
                 ("Crime & Thriller", {"withGenres": "80|9648"}, 20), ("Docuseries", {"withGenres": "99"}, 5)],
    "FX": [("Drama", {"withGenres": "18"}, 20), ("Comedy", {"withGenres": "35"}, 20)],
    "USA Network": [("Drama", {"withGenres": "18"}, 20), ("Crime & Mystery", {"withGenres": "80|9648"}, 20),
                    ("Comedy", {"withGenres": "35", "withoutGenres": "16|" + NOISE}, 10)],
    "BBC": [("Drama", {"withGenres": "18"}, 50), ("Crime & Mystery", {"withGenres": "80|9648"}, 30),
            ("Sci-Fi & Fantasy", {"withGenres": "10765"}, 20), ("Period & War Drama", {"withGenres": "10768"}, 10),
            ("Comedy", {"withGenres": "35", "withoutGenres": "16|" + NOISE}, 30),
            ("Natural History", {"withGenres": "99", "withKeywords": NATURE}, 10),
            ("Documentaries", {"withGenres": "99"}, 20)],
    "ITV": [("Drama", {"withGenres": "18"}, 30), ("Crime & Mystery", {"withGenres": "80|9648"}, 20),
            ("Comedy", {"withGenres": "35", "withoutGenres": "16|" + NOISE}, 10),
            ("Classic ITV (before 1980)", {"releaseDateLte": "1979-12-31", "withoutGenres": "16|10762|" + NOISE}, 10)],
    "Channel 4": [("Drama", {"withGenres": "18"}, 20), ("Comedy", {"withGenres": "35", "withoutGenres": "16|" + NOISE}, 20),
                  ("Documentaries", {"withGenres": "99"}, 10)],
    "NBC": [("Drama", {"withGenres": "18"}, 50), ("Crime & Procedurals", {"withGenres": "80"}, 30),
            ("Sci-Fi & Mystery", {"withGenres": "10765|9648"}, 30),
            ("Classic TV (before 1980)", {"releaseDateLte": "1979-12-31", "withoutGenres": "16|10762|" + NOISE}, 10),
            ("Westerns", {"withGenres": "37"}, 5)],
    "ABC": [("Drama", {"withGenres": "18"}, 50), ("Crime & Procedurals", {"withGenres": "80"}, 30),
            ("Sci-Fi & Mystery", {"withGenres": "10765|9648"}, 30),
            ("Classic TV (before 1980)", {"releaseDateLte": "1979-12-31", "withoutGenres": "16|10762|" + NOISE}, 10),
            ("Westerns", {"withGenres": "37"}, 5)],
    "CBS": [("Drama", {"withGenres": "18"}, 50), ("Crime & Procedurals", {"withGenres": "80"}, 30),
            ("Sci-Fi & Mystery", {"withGenres": "10765|9648"}, 30),
            ("Classic TV (before 1980)", {"releaseDateLte": "1979-12-31", "withoutGenres": "16|10762|" + NOISE}, 10),
            ("Westerns", {"withGenres": "37"}, 5)],
    "FOX": [("Drama", {"withGenres": "18"}, 50), ("Crime & Procedurals", {"withGenres": "80"}, 30),
            ("Sci-Fi & Mystery", {"withGenres": "10765|9648"}, 30),
            ("Animation Domination", {"withGenres": "16", "withoutGenres": "10762|" + NOISE}, 30)],
}


def extra(title, nets, f, vc):
    s = src(title, VOTES, nets, vc)
    s["filters"] = {**s["filters"], **f}
    if s["tmdbSourceType"] == "NETWORK":  # extra filters need DISCOVER (NETWORK sends tmdbId only)
        s.update(tmdbSourceType="DISCOVER", tmdbId=None)
        s["filters"]["withNetworks"] = "|".join(map(str, nets))
    return s


def rails(nets, small):
    # Kaptain's three network rails, in the order the user asked for.
    return [
        src("Recent Series", "first_air_date.desc", nets, 1 if small else 3),
        src("Popular Series", "popularity.desc", nets, 3 if small else 10),
        src("Top Rated Series", "vote_average.desc", nets, 15 if small else 50),
    ]


data = json.load(open(SRC))
row = next(c for c in data if c["title"] == "Networks")
backup = {f["title"]: f for f in row["folders"]}
folders, report = [], []
for title, nets, art_from, logo, small in NETWORKS:
    if art_from:
        f = dict(backup[art_from])
        f["title"] = title
        art = f"Kaptain art from '{art_from}'"
    else:
        f = {
            "id": "folder-tmdb-net-" + "-".join(map(str, nets)), "title": title,
            "hideTitle": False, "tileShape": "POSTER",
            "coverImageUrl": TMDB_IMG + logo, "titleLogoUrl": TMDB_IMG + logo,
            "focusGifUrl": None, "focusGifEnabled": False, "heroBackdropUrl": None,
        }
        art = "TMDB logo (placeholder until design pass)"
    f["sources"], f["catalogSources"] = rails(nets, small) + [extra(t, nets, x, vc) for t, x, vc in EXTRA.get(title, [])], []
    folders.append(f)
    report.append(f"{title:22} networks={'|'.join(map(str, nets)):12} {art}")
row["folders"] = folders

# Mirror Nuvio's validateImportModel; TV app needs MOVIE/TV upper-case.
cids = set()
for c in data:
    assert c["id"] and c["id"] not in cids and c["title"]; cids.add(c["id"])
    fids = set()
    for f in c["folders"]:
        assert f["id"] and f["id"] not in fids and f["title"]; fids.add(f["id"])
        for s in f["sources"]:
            if s["provider"] == "tmdb":
                assert s["tmdbSourceType"] and s["mediaType"] in ("MOVIE", "TV"), s
            else:
                assert s["addonId"] and s["type"] and s["catalogId"]

json.dump(data, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} networks -> {OUT}")
