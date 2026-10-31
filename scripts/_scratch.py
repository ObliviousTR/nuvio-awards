import os, json, urllib.request, urllib.parse
# Genres heroes: each genre's best-known films and series (poster paths), most voted first.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]


def get(p, **q):
    q["api_key"] = K
    try:
        return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}",
                                                 timeout=60).read())
    except Exception as e:
        print("ERR", p, e)
        return {}


G = {  # genre: [(kind, discover params)]
    "Action & Adventure": [("movie", {"with_genres": "28"}), ("tv", {"with_genres": "10759"})],
    "Sci-Fi & Fantasy": [("movie", {"with_genres": "878|14"}), ("tv", {"with_genres": "10765"})],
    "Comedy": [("movie", {"with_genres": "35", "without_genres": "16"}), ("tv", {"with_genres": "35", "without_genres": "16"})],
    "Animation": [("movie", {"with_genres": "16"}), ("tv", {"with_genres": "16"})],
    "Drama": [("movie", {"with_genres": "18", "without_genres": "28,878,14,80,53"}), ("tv", {"with_genres": "18", "without_genres": "10765,10759,80"})],
    "Crime": [("movie", {"with_genres": "80"}), ("tv", {"with_genres": "80"})],
    "Horror": [("movie", {"with_genres": "27"}), ("tv", {"with_genres": "9648", "with_keywords": "315058|6152"})],
    "Mystery & Thriller": [("movie", {"with_genres": "9648|53", "without_genres": "27,28"}), ("tv", {"with_genres": "9648"})],
    "Romance & Rom-Com": [("movie", {"with_genres": "10749"}), ("tv", {"with_genres": "10749|18", "with_keywords": "9840"})],
    "Stand-Up Comedy": [("movie", {"with_keywords": "9716"}), ("tv", {"with_keywords": "9716"})],
    "Superhero": [("movie", {"with_keywords": "9715"}), ("tv", {"with_keywords": "9715"})],
    "Martial Arts": [("movie", {"with_keywords": "779"}), ("tv", {"with_keywords": "779"})],
    "History & War": [("movie", {"with_genres": "36|10752"}), ("tv", {"with_genres": "10768"})],
    "Western": [("movie", {"with_genres": "37"}), ("tv", {"with_genres": "37"})],
}
res = {}
for name, qs in G.items():
    items, seen = [], set()
    for kind, q in qs:
        for page in ((1, 2, 3) if kind == "movie" else (1,)):
            for r in get(f"/discover/{kind}", sort_by="vote_count.desc", page=page, **q).get("results", []):
                if r.get("poster_path") and (kind, r["id"]) not in seen:
                    seen.add((kind, r["id"]))
                    items.append({"kind": kind, "id": r["id"], "title": r.get("title") or r.get("name"),
                                  "poster": r["poster_path"], "votes": r.get("vote_count", 0)})
    items.sort(key=lambda x: -x["votes"])
    res[name] = items
    print(name, len(items), [i["title"] for i in items[:12]])
json.dump(res, open(f"{OUT}/genres.json", "w"), indent=1, ensure_ascii=False)
