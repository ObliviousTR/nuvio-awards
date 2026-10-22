"""Anime row: cut-out art candidates (fanart.tv characterart / clearart) for alternative pop-out characters."""
import json, os, sys, urllib.request
sys.path.insert(0, "scripts")
from spotlight import tmdb

OUT = "refs/alt"
os.makedirs(OUT, exist_ok=True)
FA = os.environ["FANART_API_KEY"]
log = []
CANDS = [("tv", "The Apothecary Diaries"), ("tv", "JoJo's Bizarre Adventure"), ("tv", "Kaguya-sama: Love Is War"),
         ("tv", "Spy x Family"), ("tv", "Horimiya"), ("tv", "Your Lie in April"), ("movie", "My Neighbor Totoro"),
         ("movie", "Princess Mononoke"), ("tv", "Attack on Titan"), ("tv", "Steins;Gate"), ("tv", "Cowboy Bebop"),
         ("tv", "Jujutsu Kaisen"), ("tv", "One Piece"), ("tv", "Neon Genesis Evangelion"), ("tv", "Dragon Ball Z"),
         ("tv", "Naruto Shippuden"), ("movie", "Suzume"), ("movie", "Spirited Away"), ("tv", "Chainsaw Man"),
         ("tv", "Mob Psycho 100")]


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}), timeout=60).read()


for kind, name in CANDS:
    try:
        r = (tmdb(f"/search/{kind}", query=name) or {}).get("results", [])
        r = [x for x in r if x.get("original_language") == "ja"] or r
        tid = r[0]["id"]
        slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
        if kind == "tv":
            tvdb = (tmdb(f"/tv/{tid}/external_ids") or {}).get("tvdb_id")
            fa = json.loads(get(f"https://webservice.fanart.tv/v3/tv/{tvdb}?api_key={FA}"))
            keys = ("characterart", "hdclearart")
        else:
            fa = json.loads(get(f"https://webservice.fanart.tv/v3/movies/{tid}?api_key={FA}"))
            keys = ("hdmovieclearart", "movieart")
        n = 0
        for k in keys:
            for i, x in enumerate(sorted(fa.get(k, []), key=lambda y: -int(y.get("likes", 0)))[:6]):
                if x.get("lang") not in ("en", "00", "", None, "ja"):
                    continue
                open(f"{OUT}/{slug}__{k}{i:02d}.png", "wb").write(get(x["url"]))
                n += 1
        log.append(f"{name}: tmdb {kind} {tid}, {n} files")
    except Exception as e:
        log.append(f"{name}: error {e}")
open(f"{OUT}/log.txt", "w").write("\n".join(log))
