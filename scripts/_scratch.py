import os, json, urllib.request, urllib.parse
# A plain BBC logo: TMDB companies named BBC and their logos.
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


res = []
for c in get("/search/company", query="BBC").get("results", [])[:12]:
    logos = [(l["file_path"], l["width"], l["height"]) for l in get(f"/company/{c['id']}/images").get("logos", [])]
    res.append({"id": c["id"], "name": c["name"], "logos": logos})
    print(c["id"], c["name"], logos)
json.dump(res, open(f"{OUT}/bbc.json", "w"), indent=1)
