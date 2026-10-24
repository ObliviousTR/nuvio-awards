import os, json, urllib.request
OUT = "refs/matrix"; os.makedirs(OUT + "/st", exist_ok=True); os.makedirs(OUT + "/logo", exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
log = []
for kind, i in [("movie", 603), ("movie", 604), ("movie", 605), ("movie", 624860), ("movie", 55931)]:
    try:
        im = json.loads(get(f"https://api.themoviedb.org/3/{kind}/{i}/images?api_key={K}"))
        bds = sorted([b for b in im["backdrops"] if not b.get("iso_639_1")], key=lambda x: -x["vote_count"])[:10]
        for j, b in enumerate(bds):
            open(f"{OUT}/st/{i}_{j}.jpg", "wb").write(get("https://image.tmdb.org/t/p/w1280" + b["file_path"]))
        for j, l in enumerate([l for l in im["logos"] if l.get("iso_639_1") in ("en", None)][:5]):
            open(f"{OUT}/logo/{i}_{j}.png", "wb").write(get("https://image.tmdb.org/t/p/original" + l["file_path"]))
            if l.get("file_type") == ".svg":
                open(f"{OUT}/logo/{i}_{j}.svg", "wb").write(get("https://image.tmdb.org/t/p/original" + os.path.splitext(l["file_path"])[0] + ".svg"))
        log.append(f"{i}: {len(bds)}")
    except Exception as e:
        log.append(f"{i}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
