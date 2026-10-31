import os, json, urllib.request, urllib.parse
# Hand-picked titles for mood heroes: resolve to TMDB posters.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
SRC = json.load(open("scripts/_scratch_in.json", encoding="utf-8"))


def get(p, **q):
    q["api_key"] = K
    try:
        return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}",
                                                 timeout=60).read())
    except Exception as e:
        print("ERR", p, e)
        return {}


res = {}
for folder, titles in SRC.items():
    out = []
    for t in titles:
        kind = "tv" if t.startswith("tv:") else "movie"
        t = t[3:] if kind == "tv" else t
        name, _, year = t.partition("|")
        q = {"query": name}
        if year:
            q["year" if kind == "movie" else "first_air_date_year"] = year
        rs = get(f"/search/{kind}", **q).get("results", [])
        rs = [r for r in rs if r.get("poster_path")]
        if not rs:
            print("MISS", folder, t)
            continue
        exact = [r for r in rs if (r.get("title") or r.get("name") or "").lower() == name.lower()
                 or (r.get("original_title") or r.get("original_name") or "").lower() == name.lower()]
        r = max(exact or rs[:1], key=lambda r: r.get("vote_count", 0))
        out.append({"title": r.get("title") or r.get("name"), "poster": r["poster_path"], "votes": r.get("vote_count", 0)})
    res[folder] = out
    print(folder, [x["title"] for x in out])
json.dump(res, open(f"{OUT}/picked.json", "w"), ensure_ascii=False)
