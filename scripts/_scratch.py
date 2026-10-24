import os, json, urllib.request
# Batman card, round 2: dump the full TMDB and fanart.tv image lists (paths only) so stills can be picked by eye.
OUT = "refs/batman2"; os.makedirs(OUT, exist_ok=True)
K, F = os.environ["TMDB_API_KEY"], os.environ["FANART_API_KEY"]


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()


log = []
for i in (2661, 268, 364, 14919, 414, 415, 272, 155, 49026, 209112, 141052, 791373, 414906):
    try:
        open(f"{OUT}/tmdb_{i}.json", "wb").write(get(f"https://api.themoviedb.org/3/movie/{i}/images?api_key={K}"))
        log.append(f"tmdb {i} ok")
    except Exception as e:
        log.append(f"tmdb {i}: {e}")
    try:
        open(f"{OUT}/fanart_{i}.json", "wb").write(get(f"https://webservice.fanart.tv/v3/movies/{i}?api_key={F}"))
        log.append(f"fanart {i} ok")
    except Exception as e:
        log.append(f"fanart {i}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
