import os, json, urllib.request, urllib.parse
# Universe title logos: English/neutral logos of each franchise's collection, key film or studio.
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
for u, qs in SRC.items():
    cands = []
    for kind, q in qs:
        name, _, year = q.partition("|")
        p = {"query": name}
        if year:
            p["year"] = year
        rs = get(f"/search/{kind}", **p).get("results", [])
        if not rs:
            print("MISS", u, kind, q)
            continue
        exact = [r for r in rs if (r.get("name") or r.get("title") or "").lower() == name.lower()]
        r = (exact or rs)[0]
        if kind == "company":
            ls = get(f"/company/{r['id']}/images").get("logos", [])
        else:
            ls = get(f"/{kind}/{r['id']}/images", include_image_language="en,null").get("logos", [])
            ls = [l for l in ls if l.get("iso_639_1") in ("en", None)]
        ls.sort(key=lambda l: (-l.get("vote_average", 0), -l.get("vote_count", 0)))
        for l in ls[:4]:
            cands.append({"src": f"{kind}:{r.get('name') or r.get('title')}", "path": l["file_path"],
                          "w": l["width"], "h": l["height"], "lang": l.get("iso_639_1")})
    res[u] = cands
    print(u, len(cands))
json.dump(res, open(f"{OUT}/univ_logos.json", "w"), ensure_ascii=False, indent=1)
