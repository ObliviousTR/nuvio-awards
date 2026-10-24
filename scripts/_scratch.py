import os, json, urllib.request
OUT = "refs/mcu"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
IDS = [1726, 1724, 10138, 10195, 1771, 24428, 68721, 76338, 100402, 118340, 99861, 102899, 271110, 284052, 283995, 315635,
       284053, 284054, 299536, 363088, 299537, 299534, 429617, 497698, 566525, 524434, 634649, 453395, 616037, 505642,
       640146, 447365, 609681, 533535, 822119, 986056, 617126]
log = []
for i in IDS:
    try:
        im = json.loads(get(f"https://api.themoviedb.org/3/movie/{i}/images?include_image_language=null&api_key={K}"))
        bds = sorted([b for b in im["backdrops"] if not b.get("iso_639_1")], key=lambda x: -x["vote_average"] * 10 - x["vote_count"])[:3]
        for j, b in enumerate(bds):
            open(f"{OUT}/{i}_{j}.jpg", "wb").write(get("https://image.tmdb.org/t/p/w1280" + b["file_path"]))
        log.append(f"{i}: {len(bds)}")
    except Exception as e:
        log.append(f"{i}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
