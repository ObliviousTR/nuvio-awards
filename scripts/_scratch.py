import os, json, urllib.request, urllib.parse
# Awards heroes: textless backdrops of the ceremonies on TMDB.
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


res = {}
ids = {"oscars": ("tv", 27023), "globes": ("tv", 71494), "bafta": ("tv", 26183)}
for q in ("Emmy Awards", "Primetime Emmy Awards", "Cannes", "Festival de Cannes", "Venice Film Festival", "Sundance",
          "Criterion", "Academy Awards"):
    for kind in ("tv", "movie"):
        for r in get(f"/search/{kind}", query=q).get("results", [])[:4]:
            ids[f"{q}|{kind}|{r.get('name') or r.get('title')}"] = (kind, r["id"])
for k, (kind, i) in ids.items():
    bd = get(f"/{kind}/{i}/images", include_image_language="null,en").get("backdrops", [])
    bd.sort(key=lambda b: (b.get("iso_639_1") is not None, -b.get("vote_count", 0)))
    res[k] = [(b["file_path"], b.get("iso_639_1"), b["width"]) for b in bd[:10]]
    print(k, kind, i, len(bd))
json.dump(res, open(f"{OUT}/awards.json", "w"), ensure_ascii=False, indent=1)
