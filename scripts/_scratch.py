import os, json, urllib.request, urllib.parse
# Spotlight people: their TMDB photos (paths only), best voted first.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}", timeout=60).read())
res = {}
for name in ("Brad Pitt", "Ari Aster", "Jack Nicholson", "Boris Karloff", "Haluk Bilginer"):
    pid = get("/search/person", query=name)["results"][0]["id"]
    im = get(f"/person/{pid}/images").get("profiles", [])
    im.sort(key=lambda x: (-x.get("vote_average", 0), -x.get("height", 0)))
    res[name] = [x["file_path"] for x in im[:8]]
json.dump(res, open(f"{OUT}/people.json", "w"), indent=1)
print(res)
