"""Tidy the AIOMetadata catalog setup for Nuvio's Discover menu.

AIOMetadata can't keep a catalog out of Discover while a folder uses it: a catalog is either served (and listed in
Discover) or disabled. So: every catalog a folder of the collection uses stays on, renamed into groups that read well
in the Discover menu ("Top 10 · ...", "Hidden Gems · ...", "Awards · ..."); a few personal / forward-looking ones stay
for Discover; everything else is switched off (import never deletes, so they go in with enabled: false).
usage: python3 aio/tidy.py IN.json COLLECTION.json OUT.json   (import OUT in AIOMetadata: Catalogs > Import Setup > Replace)
"""
import json, sys, datetime

src, coll, dst = sys.argv[1:4]
cfg = json.load(open(src))
data = json.load(open(coll))
used = set()
for r in data:
    for f in r.get("folders", []):
        for s in f["sources"]:
            if s.get("addonId") == "aio-metadata":
                used.add((s["catalogId"], s["type"]))
TYPES = {"movie": "Movies", "series": "Series", "all": "Movies & Series", "anime": "Anime"}
PLAT = {"netflix": "Netflix", "hbo-max": "HBO Max", "amazon-prime": "Prime Video", "disney": "Disney+", "hulu": "Hulu",
        "paramount": "Paramount+", "apple-tv": "Apple TV+", "crunchyroll": "Crunchyroll", "discovery-plus": "Discovery+",
        "shudder": "Shudder"}
REGION = {"us": "US", "tr": "Türkiye", "global": "Global"}
NAMES = {
    "mdblist.228941": "Hidden Gems · Underrated & Cult Films", "mdblist.164980": "Hidden Gems · Comedies",
    "mdblist.164919": "Hidden Gems · Sci-Fi", "mdblist.198591": "Hidden Gems · Series",
    "mdblist.148283": "Hidden Gems · Under-the-Radar Series", "mdblist.230335": "Hidden Gems · Anime",
    "mdblist.122821": "Awards · Emmy Winners", "mdblist.34134": "Awards · Emmy Nominees",
    "mdblist.146624": "Awards · Cannes Winners", "mdblist.146622": "Awards · Venice Winners",
    "mdblist.146625": "Awards · Sundance Winners", "mdblist.146627": "Awards · Golden Globe Winners",
    "mdblist.32972": "Awards · Golden Globe Nominees", "mdblist.32970": "Awards · BAFTA Nominees",
    "mdblist.13676": "Criterion · Essentials", "mdblist.13675": "Criterion · Popular", "mdblist.13674": "Criterion · New Additions",
    "mdblist.132014": "Criterion · Arthouse & Independent",
    "mdblist.205902": "Best Of · Letterboxd Top 500", "mdblist.207869": "Best Of · Sight and Sound Greatest Films",
    "mdblist.205811": "Best Of · IMDb Top 250",
    ("tmdb.trending", "movie"): "Trending · Movies (TMDB)", ("tmdb.trending", "series"): "Trending · Series (TMDB)",
    "trakt.trending.movies": "Trending · Movies (Trakt)", "trakt.trending.shows": "Trending · Series (Trakt)",
    "trakt.anticipated.movies": "Coming Soon · Most Anticipated Movies", "trakt.anticipated.shows": "Coming Soon · Most Anticipated Series",
    "mal.airing": "Anime · Airing Now", "mal.season_top": "Anime · Top This Week", "mal.upcoming": "Anime · Upcoming Season",
    "mal.top_anime": "Anime · All-Time Top", "mal.most_favorites": "Anime · Most Favorited", "mal.most_popular": "Anime · Most Popular",
    "simkl.trending.anime": "Anime · Trending (Simkl)",
    "simkl.upnext": "My Simkl · Up Next", "simkl.watchlist.shows.watching": "My Simkl · Watching",
    "simkl.watchlist.movies.plantowatch": "My Simkl · Plan to Watch Movies", "simkl.watchlist.shows.plantowatch": "My Simkl · Plan to Watch Series",
    "simkl.watchlist.anime.watching": "My Simkl · Watching Anime", "simkl.watchlist.anime.plantowatch": "My Simkl · Plan to Watch Anime",
}
KEEP_FOR_DISCOVER = {"trakt.anticipated.movies", "trakt.anticipated.shows", "simkl.watchlist.anime.watching",
                     "simkl.watchlist.anime.plantowatch"}
GROUP = ["Trending", "Coming Soon", "Hidden Gems", "Best Of", "Top 10", "Awards", "Criterion", "Anime", "My Simkl"]
on, off = [], []
for c in cfg["catalogs"]:
    key = (c["id"], c["type"])
    c = dict(c)
    is_used = key in used or (c["id"] == "simkl.trending.anime")
    if is_used or c["id"] in KEEP_FOR_DISCOVER:
        if c["id"].startswith("flixpatrol."):
            _, plat, reg, _ = c["id"].split(".")
            c["name"] = f"Top 10 · {PLAT.get(plat, plat)} {TYPES[c['type']]} ({REGION.get(reg, reg)})"
        else:
            c["name"] = NAMES.get(key) or NAMES.get(c["id"]) or c["name"]
        c["enabled"] = True
        on.append(c)
    else:
        c["enabled"] = False
        off.append(c)
rank = lambda c: (next((i for i, g in enumerate(GROUP) if c["name"].startswith(g)), 99), c["name"])
on.sort(key=rank)
missing = sorted(used - {(c["id"], c["type"]) for c in on})
out = {"version": cfg.get("version", 1), "exportedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
       "catalogs": on + off}
json.dump(out, open(dst, "w"), indent=2, ensure_ascii=False)
print(f"on {len(on)}, off {len(off)}; used by folders but not in the setup: {missing}")
for c in on:
    print("  ", c["name"])
