"""Moods: find the textless source image behind each of Kaptain's mood covers (TMDB backdrops + fanart.tv
backgrounds of candidate films, best grey-level correlation on the part of the card above the type)."""
import io, json, os, sys, urllib.request
import numpy as np
sys.path.insert(0, "scripts"); sys.path.insert(0, "art_tools")
from spotlight import tmdb
import genre_art as g
from PIL import Image
os.makedirs("refs/moods", exist_ok=True)
M = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/mirror/files/"
COV = {"Feel-Good": ("45/45720700a11bc407.jpg", [("La La Land", 2016)]),
       "Cozy & Comforting": ("5e/5ee512bfb04bc7b2.jpg", [("Amélie", 2001)]),
       "Adrenaline Rush": ("9f/9f64f57574827abd.jpg", [("Top Gun: Maverick", 2022)]),
       "Epic & Sweeping": ("d2/d224e5f5a179c038.jpg", [("Lawrence of Arabia", 1962), ("Kingdom of Heaven", 2005),
                           ("Dune: Part Two", 2024), ("Exodus: Gods and Kings", 2014), ("The Message", 1976),
                           ("Dune", 2021), ("Gladiator II", 2024), ("Napoleon", 2023), ("Mad Max: Fury Road", 2015)]),
       "Mind-Bending": ("b4/b4ee6d73ada0c7f8.jpg", [("Inception", 2010)]),
       "Slow Burn": ("bd/bdd80b9bd68167c3.jpg", [("There Will Be Blood", 2007)]),
       "Dark & Gritty": ("ec/ecf2ae62f61e7f67.jpg", [("The Batman", 2022)]),
       "Spooky & Creepy": ("70/705342b6a61cfc62.jpg", [("Alien: Romulus", 2024), ("Alien", 1979), ("Alien: Covenant", 2017),
                           ("Prometheus", 2012), ("Aliens", 1986)]),
       "Tearjerkers": ("90/9059e4f14e5e82ce.jpg", [("Manchester by the Sea", 2016)]),
       "80s & 90s Vibes": ("72/7262c18ca103862b.jpg", [("Pulp Fiction", 1994)])}


def get(u):
    return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "x"}), timeout=60).read()))


def sig(im):
    a = np.asarray(im.convert("L").resize((96, 54), Image.BILINEAR), dtype=np.float32)[:34]   # above the type
    a = a - a.mean()
    return a / (np.linalg.norm(a) + 1e-6)


res, log = {}, []
for mood, (cov, films) in COV.items():
    target = sig(get(M + cov))
    best = []
    for name, year in films:
        tid, real = g.find_movie(name, year)
        if not tid:
            continue
        im = tmdb(f"/movie/{tid}/images") or {}
        cands = [("tmdb", b["file_path"], "https://image.tmdb.org/t/p/w300" + b["file_path"]) for b in im.get("backdrops", [])[:80]]
        cands += [("fanart", u, u.replace("/fanart/", "/preview/")) for u in g.fanart_backgrounds(tid)[:30]]
        for kind, path, prev in cands:
            try:
                s = float((sig(get(prev)) * target).sum())
            except Exception:
                continue
            best.append((s, real, tid, kind, path))
    best.sort(reverse=True)
    res[mood] = best[:3]
    log.append(f"{mood}: " + " | ".join(f"{s:.3f} {r} {k} {p}" for s, r, _, k, p in best[:3]))
    if best:
        s, r, tid, k, p = best[0]
        src = g.load_img(p if k == "fanart" else p)
        Image.fromarray(np.hstack([np.asarray(src.resize((640, 360))), np.asarray(get(M + cov).convert("RGB").resize((640, 360)))])).save(f"refs/moods/{g.slug_of(mood)}.jpg", quality=80)
json.dump(res, open("refs/moods/match.json", "w"), indent=1, ensure_ascii=False)
open("refs/moods/log.txt", "w").write("\n".join(log))
