import os, json, urllib.request, urllib.parse
# Hero samples, round 2: collage posters, person portraits, award ceremony images (TMDB paths only).
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(p, **q):
    q["api_key"] = K
    try:
        return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}", timeout=60).read())
    except Exception as e:
        return {"error": str(e)}
res = {}
nf = []
for page in (1, 2):
    nf += get("/discover/tv", with_networks=213, sort_by="vote_count.desc", page=page).get("results", [])
res["netflix"] = [dict(id=r["id"], name=r["name"], poster=r.get("poster_path"), backdrop=r.get("backdrop_path")) for r in nf[:36]]
co = []
for page in (1, 2):
    co += get("/discover/movie", with_genres=35, without_genres=16, sort_by="vote_count.desc", page=page).get("results", [])
res["comedy"] = [dict(id=r["id"], name=r["title"], poster=r.get("poster_path"), backdrop=r.get("backdrop_path")) for r in co[:36]]
for name, pid in (("pacino", 1158), ("nolan", 525), ("streep", 5064)):
    im = get(f"/person/{pid}/images").get("profiles", [])
    im.sort(key=lambda x: (-x.get("vote_average", 0), -x.get("height", 0)))
    cr = get(f"/person/{pid}/combined_credits")
    pool = cr.get("crew", []) if name == "nolan" else cr.get("cast", [])
    pool = [c for c in pool if c.get("backdrop_path") and (name != "nolan" or c.get("job") == "Director")]
    pool.sort(key=lambda c: -c.get("vote_count", 0))
    res[name] = dict(profiles=[(x["file_path"], x["width"], x["height"], x.get("vote_average")) for x in im[:10]],
                     films=[(c.get("title") or c.get("name"), c.get("media_type"), c["id"], c["backdrop_path"]) for c in pool[:8]])
for q in ("The Oscars", "Academy Awards", "Golden Globe Awards", "BAFTA Film Awards", "Cannes"):
    r = get("/search/tv", query=q).get("results", [])[:3]
    for t in r:
        imgs = get(f"/tv/{t['id']}/images", include_image_language="null,en").get("backdrops", [])
        imgs.sort(key=lambda b: (-b.get("vote_average", 0), -b["width"]))
        res[f"award:{q}:{t['id']}:{t['name']}"] = [(b["file_path"], b["width"], b.get("iso_639_1")) for b in imgs[:10]]
json.dump(res, open(f"{OUT}/samples2.json", "w"), indent=1)
print({k: (len(v) if isinstance(v, list) else list(v)) for k, v in res.items()})
