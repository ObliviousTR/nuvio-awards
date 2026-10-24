import os, json, urllib.request, io, zipfile
OUT = "refs/me"; os.makedirs(OUT + "/fonts", exist_ok=True); os.makedirs(OUT + "/img", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
log = []
for name, u in {"alcarin": "https://codeload.github.com/Tosche/Alcarin-Tengwar/zip/refs/heads/main",
                "alcarin_master": "https://codeload.github.com/Tosche/Alcarin-Tengwar/zip/refs/heads/master",
                "ringbearer": "https://dl.dafont.com/dl/?f=ringbearer", "aniron": "https://dl.dafont.com/dl/?f=aniron",
                "annatar": "https://dl.dafont.com/dl/?f=tengwar_annatar"}.items():
    try:
        z = zipfile.ZipFile(io.BytesIO(get(u)))
        for n in z.namelist():
            if n.lower().endswith((".ttf", ".otf")) or "licen" in n.lower() or "ofl" in n.lower() or n.lower().endswith(".txt"):
                if "/sources/" in n.lower(): continue
                open(f"{OUT}/fonts/{name}__{os.path.basename(n)}", "wb").write(z.read(n))
        log.append(f"{name}: ok {len(z.namelist())}")
    except Exception as e:
        log.append(f"{name}: {e}")
K = os.environ["TMDB_API_KEY"]
def tm(p):
    return json.loads(get(f"https://api.themoviedb.org/3{p}{'&' if '?' in p else '?'}api_key={K}"))
for kind, i in [("movie", 120), ("movie", 121), ("movie", 122), ("movie", 49051), ("movie", 57158), ("movie", 122917), ("tv", 84773), ("movie", 839033)]:
    try:
        im = tm(f"/{kind}/{i}/images?include_image_language=en,null")
        for j, b in enumerate(sorted(im["backdrops"], key=lambda x: -x["vote_count"])[:8]):
            if b.get("iso_639_1"): continue
            open(f"{OUT}/img/{kind}{i}_bd{j}.jpg", "wb").write(get("https://image.tmdb.org/t/p/w1280" + b["file_path"]))
        for j, b in enumerate([l for l in im["logos"] if l.get("iso_639_1") == "en"][:3]):
            open(f"{OUT}/img/{kind}{i}_logo{j}.png", "wb").write(get("https://image.tmdb.org/t/p/original" + b["file_path"]))
        log.append(f"{kind}{i}: ok")
    except Exception as e:
        log.append(f"{kind}{i}: {e}")
open(OUT + "/log.txt", "w").write("\n".join(log))
print("\n".join(log))
