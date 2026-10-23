"""Bond: look for a clean official 007 logo (Commons, TMDB collection 645, fanart)."""
import json, os, urllib.request, urllib.parse
os.makedirs("refs/bond", exist_ok=True)
log = []
UA = {"User-Agent": "nuvio-awards/1.0 (github.com/ObliviousTR)"}


def get(u, raw=False):
    b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
    return b if raw else json.loads(b)


def save(u, name):
    try:
        open("refs/bond/" + name, "wb").write(get(u, True)); log.append("saved " + name + " <- " + u)
    except Exception as e:
        log.append("FAIL " + u + " " + str(e))


try:
    for q in ("007 logo", "James Bond 007 logo", "007 gun logo"):
        r = get("https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&format=json&srlimit=15&srsearch=" + urllib.parse.quote(q))
        for h in r["query"]["search"]:
            log.append("commons: " + h["title"])
except Exception as e:
    log.append("commons search fail " + str(e))
titles = []
for line in list(log):
    if line.startswith("commons: "):
        t = line[9:]
        if t not in titles and ("007" in t) and t.lower().endswith((".svg", ".png")):
            titles.append(t)
for i, t in enumerate(titles[:12]):
    try:
        r = get("https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=1200&format=json&titles=" + urllib.parse.quote(t))
        p = next(iter(r["query"]["pages"].values()))["imageinfo"][0]
        lic = p.get("extmetadata", {}).get("LicenseShortName", {}).get("value")
        log.append(f"{t} | {p['width']}x{p['height']} | {lic}")
        save(p.get("thumburl") or p["url"], f"c{i:02d}.png")
    except Exception as e:
        log.append("FAIL info " + t + " " + str(e))
k = os.environ["TMDB_API_KEY"]
try:
    r = get(f"https://api.themoviedb.org/3/collection/645/images?api_key={k}")
    log.append("tmdb collection keys: " + str({a: len(b) for a, b in r.items() if isinstance(b, list)}))
    for i, l in enumerate((r.get("logos") or [])[:6]):
        save("https://image.tmdb.org/t/p/original" + l["file_path"], f"t{i:02d}.png")
except Exception as e:
    log.append("tmdb fail " + str(e))
# fanart: Craig films' logos often carry the 007 mark
fk = os.environ.get("FANART_API_KEY")
for mid in (36557, 10764, 37724, 206647, 370172):
    try:
        r = get(f"https://webservice.fanart.tv/v3/movies/{mid}?api_key={fk}")
        for i, l in enumerate([x for x in r.get("hdmovielogo", []) if x.get("lang") in ("en", "00")][:3]):
            save(l["url"], f"f{mid}_{i}.png")
    except Exception as e:
        log.append(f"fanart {mid} fail {e}")
open("refs/bond/log.txt", "w").write("\n".join(log).replace(k, "<key>").replace(fk or "§", "<key>"))
