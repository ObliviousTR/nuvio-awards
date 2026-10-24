import os, json, urllib.request
OUT = "refs/mcu_logo"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
log = []
for cid in (420, 7505):
    im = json.loads(get(f"https://api.themoviedb.org/3/company/{cid}/images?api_key={K}"))
    for j, l in enumerate(im.get("logos", [])):
        if l.get("file_type") == ".svg":
            p = os.path.splitext(l["file_path"])[0] + ".svg"
            try:
                open(f"{OUT}/c{cid}_{j}.svg", "wb").write(get("https://image.tmdb.org/t/p/original" + p)); log.append(f"c{cid}_{j}.svg ok")
            except Exception as e:
                log.append(f"c{cid}_{j}.svg {e}")
open(OUT + "/log2.txt", "w").write("\n".join(log)); print("\n".join(log))
