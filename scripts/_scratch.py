import os, json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
# People heroes, option B: several textless backdrops from each person's best-known films (lead roles / directed).
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
P = json.load(open("scripts/_scratch_in.json", encoding="utf-8"))      # name -> [person id, dept]


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


def stills(item):
    name, (pid, dept) = item
    cr = get(f"/person/{pid}/movie_credits")
    if dept == "Directing":
        films = [f for f in cr.get("crew", []) if f.get("job") == "Director"]
    else:
        films = [f for f in cr.get("cast", []) if f.get("order", 99) <= 2] or cr.get("cast", [])
    films = sorted({f["id"]: f for f in films}.values(), key=lambda f: -f.get("vote_count", 0))[:5]
    out = []
    for f in films:
        bd = [b for b in get(f"/movie/{f['id']}/images", include_image_language="null").get("backdrops", [])
              if not b.get("iso_639_1") and b.get("width", 0) >= 1280]
        bd.sort(key=lambda b: (-b.get("vote_count", 0), -b.get("vote_average", 0)))
        out += [{"film": f["title"], "path": b["file_path"], "votes": b.get("vote_count", 0)} for b in bd[:8]]
    return name, out


with ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(stills, P.items()))
json.dump(res, open(f"{OUT}/stills.json", "w"), ensure_ascii=False)
for n, v in res.items():
    print(n, len(v))
