import os, json, urllib.request, urllib.parse
# Spotlight hover samples (Headliner, Brad Pitt): his portrait and the best textless stills of his best-known films.
OUT = "refs/spotlight"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]


def get(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}", timeout=60).read())


pid = 287
person = get(f"/person/{pid}")
imgs = get(f"/person/{pid}/images")["profiles"]
cred = get(f"/person/{pid}/movie_credits")["cast"]
lead = [c for c in cred if (c.get("order") or 9) <= 2 and c.get("vote_count", 0) > 3000 and c.get("backdrop_path")]
lead.sort(key=lambda c: -c["vote_count"])
films = []
for c in lead[:14]:
    im = get(f"/movie/{c['id']}/images", include_image_language="null")
    bs = sorted(im.get("backdrops", []), key=lambda b: (-b.get("vote_average", 0), -b.get("width", 0)))[:8]
    films.append({"id": c["id"], "title": c["title"], "year": (c.get("release_date") or "")[:4], "character": c.get("character"),
                  "votes": c["vote_count"], "backdrops": [b["file_path"] for b in bs]})
json.dump({"profile": person.get("profile_path"), "profiles": [p["file_path"] for p in imgs[:10]], "films": films},
          open(OUT + "/brad_pitt.json", "w"), indent=1)
print("ok", len(films))
