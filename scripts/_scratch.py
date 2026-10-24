import os, json, urllib.request, urllib.parse
OUT = "refs/dc"; os.makedirs(OUT + "/logo", exist_ok=True); os.makedirs(OUT + "/st", exist_ok=True)
K = os.environ["TMDB_API_KEY"]
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
def tm(p):
    return json.loads(get(f"https://api.themoviedb.org/3{p}{'&' if '?' in p else '?'}api_key={K}"))
log = []
for q in ("DC Studios", "DC Films", "DC Entertainment", "DC Comics"):
    for c in tm("/search/company?query=" + urllib.parse.quote(q))["results"][:4]:
        try:
            for j, l in enumerate(tm(f"/company/{c['id']}/images").get("logos", [])):
                base = os.path.splitext(l["file_path"])[0]
                open(f"{OUT}/logo/c{c['id']}_{j}.png", "wb").write(get("https://image.tmdb.org/t/p/original" + l["file_path"]))
                if l.get("file_type") == ".svg":
                    open(f"{OUT}/logo/c{c['id']}_{j}.svg", "wb").write(get("https://image.tmdb.org/t/p/original" + base + ".svg"))
                log.append(f"c{c['id']}_{j} {c['name']} {l.get('file_type')} {l.get('width')}x{l.get('height')}")
        except Exception as e:
            log.append(f"{c['id']}: {e}")
ITEMS = [("movie", i) for i in (1924, 268, 364, 1452, 272, 155, 13183, 49521, 209112, 297761, 297762, 141052, 297802, 287947,
                                475557, 495764, 464052, 791373, 436969, 414906, 436270, 594767, 298618, 565770, 572802,
                                889737, 1061474)] + [("tv", 110492), ("tv", 194764)]
for kind, i in ITEMS:
    try:
        im = tm(f"/{kind}/{i}/images?include_image_language=null")
        bds = sorted([b for b in im["backdrops"] if not b.get("iso_639_1")], key=lambda x: -x["vote_average"] * 10 - x["vote_count"])[:3]
        for j, b in enumerate(bds):
            open(f"{OUT}/st/{kind}{i}_{j}.jpg", "wb").write(get("https://image.tmdb.org/t/p/w1280" + b["file_path"]))
        log.append(f"{kind}{i}: {len(bds)}")
    except Exception as e:
        log.append(f"{kind}{i}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
