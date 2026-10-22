"""Awards: TMDB logos of the award shows + remaining Commons candidates (contact sheets)."""
import io, json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, "scripts")
from spotlight import tmdb
from PIL import Image, ImageDraw
os.makedirs("refs/aw", exist_ok=True)
UA = {"User-Agent": "nuvio-awards/1.0 (github.com/ObliviousTR/nuvio-awards)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
res = {}
def sheet(k, items):  # items: (label, thumb url)
    sh = Image.new("RGB", (4 * 300, ((len(items) + 3) // 4 or 1) * 220), (70, 70, 74))
    dr = ImageDraw.Draw(sh)
    for i, (lab, u) in enumerate(items):
        try:
            im = Image.open(io.BytesIO(get(u))).convert("RGBA"); im.thumbnail((280, 180))
            sh.paste(im, ((i % 4) * 300 + 10, (i // 4) * 220 + 8), im)
        except Exception:
            pass
        dr.text(((i % 4) * 300 + 6, (i // 4) * 220 + 198), f"{i} {lab[:40]}", fill=(255, 255, 0))
    sh.save(f"refs/aw/{k}.jpg", quality=80)
for k, q in {"t_oscars": "The Oscars", "t_globes": "Golden Globe Awards", "t_bafta": "BAFTA Film Awards", "t_emmy": "The Emmy Awards",
             "t_cannes": "Cannes", "t_venice": "Venice", "t_sundance": "Sundance", "t_berlin": "Berlinale"}.items():
    r = (tmdb("/search/tv", query=q) or {}).get("results", [])[:3] + (tmdb("/search/movie", query=q) or {}).get("results", [])[:2]
    items, lst = [], []
    for x in r:
        kind = "tv" if "name" in x else "movie"
        im = tmdb(f"/{kind}/{x['id']}/images", include_image_language="en,null") or {}
        for lg in im.get("logos", [])[:6]:
            if lg["file_path"].endswith(".png"):
                lab = f"{kind}{x['id']} {(x.get('name') or x.get('title'))}"
                items.append((lab, "https://image.tmdb.org/t/p/w300" + lg["file_path"])); lst.append([len(lst), lab, lg["file_path"]])
    res[k] = lst
    sheet(k, items[:16])
for k, q in {"sundance": "Sundance Film Festival logo", "bear": "Goldener Bär", "berlinale": "Berlinale logo",
             "emmy": "Emmy statuette", "criterion": "Criterion Collection logo", "oscar3": "Oscar statuette"}.items():
    time.sleep(6)
    try:
        p = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": 6,
                                    "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 240})
        pages = sorted(json.loads(get("https://commons.wikimedia.org/w/api.php?" + p)).get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
        res[k] = [[i, pg["title"]] for i, pg in enumerate(pages)]
        time.sleep(3)
        sheet(k, [(pg["title"][5:], pg["imageinfo"][0]["thumburl"]) for pg in pages if pg.get("imageinfo")])
    except Exception as e:
        res[k] = str(e)
json.dump(res, open("refs/aw/cands2.json", "w"), indent=1, ensure_ascii=False)
