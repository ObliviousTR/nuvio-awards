import os, json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
# People heroes: each actor's / director's TMDB photos and a textless still from their best-known film.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
SRC = json.load(open("scripts/_scratch_in.json", encoding="utf-8"))


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


def person(job):
    row, name = job
    dept = "Directing" if row == "Legendary Directors" else "Acting"
    rs = get("/search/person", query=name).get("results", [])
    rs = [r for r in rs if r.get("known_for_department") == dept] or rs
    if not rs:
        return name, None
    p = max(rs[:3], key=lambda r: r.get("popularity", 0))
    ims = get(f"/person/{p['id']}/images").get("profiles", [])
    ims.sort(key=lambda x: (-x.get("vote_average", 0), -x.get("height", 0)))
    cr = get(f"/person/{p['id']}/movie_credits")
    films = cr.get("crew", []) if dept == "Directing" else cr.get("cast", [])
    if dept == "Directing":
        films = [f for f in films if f.get("job") == "Director"]
    films = sorted({f["id"]: f for f in films}.values(), key=lambda f: -f.get("vote_count", 0))
    still, film = None, None
    for f in films[:4]:
        bd = [b for b in get(f"/movie/{f['id']}/images", include_image_language="null").get("backdrops", [])
              if not b.get("iso_639_1")]
        bd.sort(key=lambda b: (-b.get("vote_count", 0), -b.get("width", 0)))
        if bd:
            still, film = bd[0]["file_path"], f["title"]
            break
    return name, {"id": p["id"], "photos": [x["file_path"] for x in ims[:8]], "still": still, "film": film,
                  "films": [f["title"] for f in films[:5]]}


jobs = [(row, n) for row, ns in SRC.items() for n in ns]
with ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(person, jobs))
json.dump(res, open(f"{OUT}/people_all.json", "w"), ensure_ascii=False, indent=1)
for n, v in res.items():
    print(n, v and (len(v["photos"]), v["film"]))
