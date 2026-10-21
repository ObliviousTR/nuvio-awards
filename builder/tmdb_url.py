"""Print the TMDB discover URL Nuvio builds for a rail (mirrors buildDiscoverQuery in Nuvio's resolver).
usage: python3 tmdb_url.py collection.json "Row/Folder/Rail" [...]"""
import json, sys
from urllib.parse import urlencode

KEY = open("/home/claude/.tmdbkey").read().strip()
data = json.load(open(sys.argv[1]))
FIELDS = [("withCompanies", "with_companies"), ("withoutCompanies", "without_companies"),
          ("withNetworks", "with_networks"), ("withGenres", "with_genres"), ("withoutGenres", "without_genres"),
          ("voteCountGte", "vote_count.gte"), ("voteAverageGte", "vote_average.gte"),
          ("voteAverageLte", "vote_average.lte"), ("withOriginalLanguage", "with_original_language"),
          ("withOriginCountry", "with_origin_country"), ("withKeywords", "with_keywords"),
          ("withoutKeywords", "without_keywords")]
for path in sys.argv[2:]:
    r, f, t = path.split("/")
    s = next(s for c in data if c["title"] == r for fo in c["folders"] if fo["title"] == f
             for s in fo["sources"] if s["title"] == t)
    media = "tv" if s["mediaType"] == "TV" or s["tmdbSourceType"] == "NETWORK" else "movie"
    fl = s.get("filters") or {}
    q = {"api_key": KEY, "language": "en-US", "page": 1, "sort_by": s.get("sortBy") or "popularity.desc"}
    if s["tmdbSourceType"] == "COMPANY": q["with_companies"] = s["tmdbId"]
    if s["tmdbSourceType"] == "NETWORK": q["with_networks"] = s["tmdbId"]
    for a, b in FIELDS:
        if fl.get(a) not in (None, "") and b not in q:
            q[b] = fl[a]
    if fl.get("withWatchProviders"):
        q["with_watch_providers"] = fl["withWatchProviders"]
        q["watch_region"] = fl.get("watchRegion") or "US"
        q["with_watch_monetization_types"] = "flatrate|free|ads|rent|buy"
    pre = "primary_release_date" if media == "movie" else "first_air_date"
    if fl.get("releaseDateGte"): q[pre + ".gte"] = fl["releaseDateGte"]
    if fl.get("releaseDateLte"): q[pre + ".lte"] = fl["releaseDateLte"]
    print(f"https://api.themoviedb.org/3/discover/{media}?" + urlencode(q, safe="|,"))
