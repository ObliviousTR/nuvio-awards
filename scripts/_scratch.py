"""Probe: logos (Commons + TMDB companies/networks) and backdrops for the remaining folder covers."""
import os, sys, io, json, urllib.parse
sys.path.insert(0, "scripts")
import universe_motion as um
from PIL import Image, ImageDraw
OUT = "refs/probe4"
os.makedirs(OUT, exist_ok=True)
log = open(f"{OUT}/log.txt", "w")
tiles = []


def commons_search(q, n=6):
    qs = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "format": "json", "srlimit": n})
    for r in json.loads(um.get("https://commons.wikimedia.org/w/api.php?" + qs))["query"]["search"]:
        try:
            q2 = urllib.parse.urlencode({"action": "query", "titles": r["title"], "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 500, "format": "json"})
            info = next(iter(json.loads(um.get("https://commons.wikimedia.org/w/api.php?" + q2))["query"]["pages"].values()))["imageinfo"][0]
            tiles.append((r["title"][5:45], info.get("thumburl") or info["url"]))
            log.write(f"{len(tiles)-1} commons {r['title']}\n")
        except Exception as e:
            log.write(f"  {r['title']} {e}\n")


for q in ("Exxen logo", "GAİN logo", "Tabii logo TRT", "Neon distributor logo", "Paramount Pictures logo",
          "Walt Disney Animation Studios logo", "Emmy Award logo", "Criterion Collection logo"):
    try:
        commons_search(q, 5)
    except Exception as e:
        log.write(f"search {q} {e}\n")
for kind, cid in (("company", 4), ("company", 90733), ("company", 10932), ("company", 6125), ("company", 3),
                  ("company", 521), ("company", 6704), ("network", 1)):
    try:
        im = um.tmdb(f"/{kind}/{cid}/images") or {}
        for x in im.get("logos", [])[:4]:
            if x["file_path"].endswith(".png"):
                tiles.append((f"{kind}{cid} {x['file_path']}", "https://image.tmdb.org/t/p/w500" + x["file_path"]))
                log.write(f"{len(tiles)-1} {kind}{cid} {x['file_path']}\n")
    except Exception as e:
        log.write(f"{kind}{cid} {e}\n")
# streaming provider / network logos for the Turkish services
for pid in (4405, 4409, 6854):
    try:
        im = um.tmdb(f"/watch/providers/tv", watch_region="TR") or {}
        for p in im.get("results", []):
            if p["provider_id"] == pid:
                tiles.append((f"provider{pid}", "https://image.tmdb.org/t/p/w500" + p["logo_path"]))
                log.write(f"{len(tiles)-1} provider {pid} {p['provider_name']} {p['logo_path']}\n")
    except Exception as e:
        log.write(f"prov {e}\n")
# best of 2026
try:
    r = um.tmdb("/discover/movie", primary_release_year=2026, sort_by="vote_count.desc")
    for m in r["results"][:10]:
        log.write(f"2026 {m['id']} {m['title']} votes={m['vote_count']} {m.get('backdrop_path')}\n")
except Exception as e:
    log.write(f"2026 {e}\n")
sheet = Image.new("RGB", (1200, 160 * ((len(tiles) + 3) // 4)), (110, 110, 110))
for j, (lab, u) in enumerate(tiles):
    try:
        p = um.fit(Image.open(io.BytesIO(um.get(u))).convert("RGBA"), 280, 120)
        sheet.paste(p, ((j % 4) * 300 + 10, (j // 4) * 160 + 30), p)
    except Exception as e:
        log.write(f"tile {lab} {e}\n")
    ImageDraw.Draw(sheet).text(((j % 4) * 300 + 4, (j // 4) * 160 + 3), f"{j} {lab}", fill=(255, 255, 0))
sheet.save(f"{OUT}/logos.jpg", quality=85)
log.close()
