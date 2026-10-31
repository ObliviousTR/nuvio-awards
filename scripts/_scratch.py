import os, json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
# People heroes, take 2: stills from films in which the person is tagged on TMDB (a scene of them, not a cut-out).
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
P = json.load(open("scripts/_scratch_in.json", encoding="utf-8"))      # name -> person id


def get(p, **q):
    q["api_key"] = K
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}",
                                                     timeout=60).read())
        except Exception as e:
            err = e
    print("ERR", p, err)
    return {}


def tagged(item):
    name, pid = item
    out = []
    for page in (1, 2, 3):
        r = get(f"/person/{pid}/tagged_images", page=page)
        for x in r.get("results", []):
            if x.get("image_type") != "backdrop" or x.get("width", 0) < 1280:
                continue
            m = x.get("media") or {}
            out.append({"path": x["file_path"], "w": x["width"], "h": x["height"], "lang": x.get("iso_639_1"),
                        "votes": x.get("vote_count", 0), "avg": x.get("vote_average", 0),
                        "title": m.get("title") or m.get("name"), "pop": m.get("popularity", 0),
                        "mvotes": m.get("vote_count", 0)})
        if page >= r.get("total_pages", 1):
            break
    return name, out


print("RAW", json.dumps(get("/person/1158/tagged_images"))[:600])
with ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(tagged, P.items()))
json.dump(res, open(f"{OUT}/tagged.json", "w"), ensure_ascii=False)
for n, v in res.items():
    print(n, len(v), sorted({x["title"] for x in v if x["title"]})[:6])
