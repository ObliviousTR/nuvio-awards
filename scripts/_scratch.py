import os, json, urllib.request, urllib.parse
# Hero samples: textless backdrops and English logos for a few titles (TMDB paths only).
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}", timeout=60).read())
want = [("movie", 120467), ("tv", 66732), ("movie", 1891), ("movie", 11), ("tv", 57243), ("tv", 1399), ("movie", 9806)]
res = {}
for kind, i in want:
    im = get(f"/{kind}/{i}/images", include_image_language="en,null")
    bd = sorted([b for b in im.get("backdrops", []) if not b.get("iso_639_1") and b["width"] >= 1920],
                key=lambda b: (-b.get("vote_average", 0), -b.get("vote_count", 0)))[:8]
    lg = sorted([l for l in im.get("logos", []) if l.get("iso_639_1") == "en"],
                key=lambda l: (-l.get("vote_average", 0), -l.get("vote_count", 0)))[:4]
    res[f"{kind}/{i}"] = dict(backdrops=[(b["file_path"], b["width"], b.get("vote_average")) for b in bd],
                              logos=[(l["file_path"], l["width"], l["height"]) for l in lg])
json.dump(res, open(f"{OUT}/samples.json", "w"), indent=1)
print(json.dumps(res)[:3000])
