import os, json, urllib.request, urllib.parse
# Release dates of films that are in cinemas only (Ozzy: Clayface, The Odyssey), to set the "out at home" rule.
OUT = "refs/digital"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]


def get(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}", timeout=60).read())


out = {}
ids = [1698863] + [r["id"] for r in get("/search/movie", query="Clayface", year=2026)["results"][:1]]
for i in ids:
    out[i] = {"title": get(f"/movie/{i}")["title"], "dates": get(f"/movie/{i}/release_dates")["results"]}
json.dump(out, open(OUT + "/dates.json", "w"), indent=1)
print("ok", ids)
