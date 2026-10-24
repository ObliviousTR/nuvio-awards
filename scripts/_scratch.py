import os, json, urllib.request
OUT = "refs/xmen"; os.makedirs(OUT + "/p", exist_ok=True); os.makedirs(OUT + "/logo", exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
log = []
for i in (36657, 36658, 36668, 2080, 49538, 76170, 127585, 246655, 263115, 320288, 340102, 293660, 383498, 533535):
    try:
        im = json.loads(get(f"https://api.themoviedb.org/3/movie/{i}/images?api_key={K}"))
        ps = sorted(im["posters"], key=lambda x: -x["vote_count"])[:40]
        for j, p in enumerate(ps):
            open(f"{OUT}/p/{i}_{j}.jpg", "wb").write(get("https://image.tmdb.org/t/p/w342" + p["file_path"]))
        json.dump([p["file_path"] for p in ps], open(f"{OUT}/p/{i}.json", "w"))
        for j, l in enumerate([l for l in im["logos"] if l.get("iso_639_1") == "en"][:3]):
            open(f"{OUT}/logo/{i}_{j}.png", "wb").write(get("https://image.tmdb.org/t/p/original" + l["file_path"]))
            if l.get("file_type") == ".svg":
                open(f"{OUT}/logo/{i}_{j}.svg", "wb").write(get("https://image.tmdb.org/t/p/original" + os.path.splitext(l["file_path"])[0] + ".svg"))
        log.append(f"{i}: {len(ps)} posters")
    except Exception as e:
        log.append(f"{i}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
