import os, json, urllib.request
OUT = "refs/mcu_logo"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
log = []
for cid in (420, 7505, 19551):           # Marvel Studios, Marvel Entertainment, Marvel Studios (alt)
    try:
        im = json.loads(get(f"https://api.themoviedb.org/3/company/{cid}/images?api_key={K}"))
        for j, l in enumerate(im.get("logos", [])):
            ext = os.path.splitext(l["file_path"])[1]
            open(f"{OUT}/c{cid}_{j}{ext}", "wb").write(get("https://image.tmdb.org/t/p/original" + l["file_path"]))
            log.append(f"c{cid}_{j}{ext} {l.get('width')}x{l.get('height')} {l.get('file_type')}")
        info = json.loads(get(f"https://api.themoviedb.org/3/company/{cid}?api_key={K}"))
        log.append(f"{cid}: {info.get('name')} logo_path={info.get('logo_path')}")
    except Exception as e:
        log.append(f"{cid}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
