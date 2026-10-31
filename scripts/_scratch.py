import os, json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
# Hero walls for many rows at once: run each folder's own TMDB discover/network sources, best known first.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
SRC = json.load(open("scripts/_scratch_in.json", encoding="utf-8"))


def get(p, **q):
    q["api_key"] = K
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(
                f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}", timeout=60).read())
        except Exception as e:
            err = e
    print("ERR", p, q.get("with_genres"), err)
    return {}


def params(s):
    kind = "tv" if s["mediaType"] == "TV" else "movie"
    f = s.get("filters") or {}
    q = {}
    m = {"voteCountGte": "vote_count.gte", "voteAverageGte": "vote_average.gte", "withGenres": "with_genres",
         "withoutGenres": "without_genres", "withKeywords": "with_keywords", "withoutKeywords": "without_keywords",
         "withCompanies": "with_companies", "withoutCompanies": "without_companies", "withNetworks": "with_networks",
         "withOriginCountry": "with_origin_country", "withOriginalLanguage": "with_original_language",
         "withWatchProviders": "with_watch_providers", "watchRegion": "watch_region"}
    for k, v in f.items():
        if v in (None, ""):
            continue
        if k in m:
            q[m[k]] = v
        elif k == "releaseDateGte":
            q["primary_release_date.gte" if kind == "movie" else "first_air_date.gte"] = v
        elif k == "releaseDateLte":
            q["primary_release_date.lte" if kind == "movie" else "first_air_date.lte"] = v
    sb = s.get("sortBy") or "popularity.desc"
    q["sort_by"] = "popularity.desc" if sb.startswith(("popularity", "primary_release", "first_air", "release")) \
        else "vote_count.desc"
    return kind, q


def run(s):
    if s["tmdbSourceType"] == "DISCOVER":
        kind, q = params(s)
    elif s["tmdbSourceType"] == "NETWORK":
        kind, q = "tv", {"with_networks": s["tmdbId"], "sort_by": "vote_count.desc"}
    else:
        return []
    rs = get(f"/discover/{kind}", **q).get("results", [])
    return [{"kind": kind, "id": r["id"], "title": r.get("title") or r.get("name"), "poster": r["poster_path"],
             "votes": r.get("vote_count", 0)} for r in rs if r.get("poster_path")]


res = {}
jobs = [(row, folder, i, s) for row, fs in SRC.items() for folder, ss in fs.items() for i, s in enumerate(ss)]
with ThreadPoolExecutor(8) as ex:
    outs = list(ex.map(lambda j: run(j[3]), jobs))
for (row, folder, i, s), items in zip(jobs, outs):
    res.setdefault(row, {}).setdefault(folder, []).append({"source": s["title"], "items": items})
json.dump(res, open(f"{OUT}/rows_extra.json", "w"), ensure_ascii=False)
for row, fs in res.items():
    for folder, lists in fs.items():
        print(row, "/", folder, [len(l["items"]) for l in lists])
