"""Anime row: source art for the four own sheet cards (pop-out character candidates)."""
import json, os, sys, urllib.request
sys.path.insert(0, "scripts")
from spotlight import tmdb
import spotlight_art as art

OUT = "refs/anime"
os.makedirs(OUT, exist_ok=True)
FA = os.environ.get("FANART_API_KEY", "")
log = []


def grab(url, path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"})
        open(path, "wb").write(urllib.request.urlopen(req, timeout=60).read())
        return True
    except Exception as e:
        log.append(f"fail {url} {e}")


for slug, kind, tid in (("seinen", "tv", 88803), ("legends", "tv", 31911), ("films", "movie", 372058), ("sagas", "movie", 149)):
    d = os.path.join(OUT, slug)
    os.makedirs(d, exist_ok=True)
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null,en,ja") or {}
    for i, p in enumerate(sorted(im.get("posters", []), key=lambda x: -x.get("vote_average", 0))[:10]):
        grab(art.IMG + "w780" + p["file_path"], f"{d}/poster{i:02d}_{p.get('iso_639_1')}.jpg")
    for i, p in enumerate(sorted(im.get("backdrops", []), key=lambda x: -x.get("vote_average", 0))[:10]):
        grab(art.IMG + "w1280" + p["file_path"], f"{d}/backdrop{i:02d}_{p.get('iso_639_1')}.jpg")
    if FA:
        if kind == "tv":
            tvdb = (tmdb(f"/tv/{tid}/external_ids") or {}).get("tvdb_id")
            url = f"https://webservice.fanart.tv/v3/tv/{tvdb}?api_key={FA}"
        else:
            url = f"https://webservice.fanart.tv/v3/movies/{tid}?api_key={FA}"
        try:
            fa = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}), timeout=60))
            for key in ("characterart", "hdclearart", "clearart", "hdmovieclearart", "movieart", "movieposter", "moviebackground", "showbackground", "tvposter"):
                for i, x in enumerate(fa.get(key, [])[:8]):
                    ext = os.path.splitext(x["url"])[1] or ".png"
                    grab(x["url"], f"{d}/fa_{key}{i:02d}_{x.get('lang', '')}{ext}")
            log.append(f"{slug}: fanart keys {sorted(k for k in fa if isinstance(fa[k], list))}")
        except Exception as e:
            log.append(f"{slug}: fanart error {e}")
    else:
        log.append("no FANART_API_KEY")
open(f"{OUT}/log.txt", "w").write("\n".join(log))
