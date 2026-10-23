"""Favourites samples: pictures for Doctor Who, One Piece, sport (Commons) and a few trending series for My Simkl."""
import json, os, sys, urllib.request, urllib.parse
sys.path.insert(0, "scripts")
from spotlight import tmdb
os.makedirs("refs/fav", exist_ok=True)
UA = {"User-Agent": "nuvio-awards/1.0 (https://github.com/ObliviousTR/nuvio-awards)"}
log = []
def save(url, name):
    try:
        open(f"refs/fav/{name}", "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read())
        log.append(f"{name}\t{url}")
    except Exception as e:
        log.append(f"FAIL {name} {e}")
for key, kind, tid in (("dw", "tv", 57243), ("dw23", "tv", 239770), ("op", "tv", 37854)):
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null") or {}
    bd = sorted([b for b in im.get("backdrops", []) if not b.get("iso_639_1")], key=lambda b: (-b["vote_count"], -b["vote_average"]))
    for i, b in enumerate(bd[:8]):
        save("https://image.tmdb.org/t/p/w1280" + b["file_path"], f"{key}_{i}.jpg")
tr = (tmdb("/trending/tv/week") or {}).get("results", [])[:8]
for i, x in enumerate(tr):
    if x.get("backdrop_path"):
        save("https://image.tmdb.org/t/p/w1280" + x["backdrop_path"], f"simkl_{i}.jpg")
        log.append(f"simkl_{i}\t{x.get('name')}\t{(x.get('first_air_date') or '')[:4]}")
def commons(q, n, prefix):
    r = json.loads(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 20, "prop": "imageinfo",
         "iiprop": "url|size|extmetadata", "iiurlwidth": 1600, "format": "json"}), headers=UA), timeout=60).read())
    pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    k = 0
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("width", 0) < 1600 or ii.get("width", 0) < ii.get("height", 1) * 1.3:
            continue
        lic = (ii.get("extmetadata", {}).get("LicenseShortName") or {}).get("value", "")
        save(ii["thumburl"], f"{prefix}_{k}.jpg")
        log.append(f"{prefix}_{k}\t{p['title']}\t{lic}")
        k += 1
        if k == n:
            break
commons("football match stadium crowd night filetype:bitmap", 3, "sport_fb")
commons("basketball NBA game arena filetype:bitmap", 2, "sport_bb")
commons("Formula One race cars track filetype:bitmap", 2, "sport_f1")
open("refs/fav/list.txt", "w").write("\n".join(log))
