"""Chosen Bond posters at original size -> refs/bondsel (same ordering as the previous fetch)."""
import json, os, urllib.parse, urllib.request
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/bondsel"; os.makedirs(OUT, exist_ok=True)
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
pick = {"connery": (657, 3), "lazenby": (668, 4), "moore": (699, 1), "dalton": (708, 0), "brosnan": (36643, 4), "craig": (37724, 4),
        "dalton_alt": (709, 1), "moore_alt": (707, 2), "connery_alt": (646, 0), "craig_alt": (10764, 1)}
for name, (mid, i) in pick.items():
    im = t(f"movie/{mid}/images", include_image_language="null,en")
    posters = [x for x in im.get("posters", []) if x.get("iso_639_1") in (None, "en")]
    posters = sorted(posters, key=lambda x: (x.get("iso_639_1") is not None, -x.get("vote_average", 0)))[:5]
    raw = urllib.request.urlopen("https://image.tmdb.org/t/p/original" + posters[i]["file_path"], timeout=90).read()
    open(os.path.join(OUT, name + ".jpg"), "wb").write(raw)
print("ok")
