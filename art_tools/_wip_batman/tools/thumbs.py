import json, glob, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
jobs = []; index = {}
for f in sorted(glob.glob(os.path.join(src, "tmdb_*.json"))):
    i = os.path.basename(f)[5:-5]
    b = sorted([x for x in json.load(open(f))["backdrops"] if not x.get("iso_639_1") and x["width"] >= 1920], key=lambda x: -x["vote_count"])[:48]
    for j, x in enumerate(b):
        name = f"{i}_t{j:02d}"; jobs.append((name, "https://image.tmdb.org/t/p/w300" + x["file_path"]))
        index[name] = "https://image.tmdb.org/t/p/original" + x["file_path"]
    fa = json.load(open(os.path.join(src, f"fanart_{i}.json")))
    for j, x in enumerate(fa.get("moviebackground", []) + fa.get("moviethumb", [])):
        name = f"{i}_f{j:02d}"; jobs.append((name, x["url"].replace("/fanart/", "/preview/")))
        index[name] = x["url"]
json.dump(index, open(os.path.join(out, "index.json"), "w"), indent=0)
def get(job):
    n, u = job
    p = os.path.join(out, n + ".jpg")
    if os.path.exists(p): return
    try:
        open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
    except Exception as e:
        print(n, e)
with ThreadPoolExecutor(16) as ex: list(ex.map(get, jobs))
print(len(jobs))
