"""Awards: candidate statuettes / logos from Wikimedia Commons (contact sheets to pick from)."""
import io, json, os, sys, urllib.parse, urllib.request
from PIL import Image, ImageDraw
os.makedirs("refs/aw", exist_ok=True)
UA = {"User-Agent": "nuvio-awards/1.0 (github.com/ObliviousTR/nuvio-awards)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
Q = {
    "oscar": "Academy Award statuette", "oscar2": "Oscar statuette png", "oscarlogo": "Academy Awards logo svg",
    "globe": "Golden Globe trophy", "globelogo": "Golden Globe Awards logo", "bafta": "BAFTA mask award", "baftalogo": "BAFTA logo svg",
    "palme": "Palme d'Or", "cannes": "Festival de Cannes logo", "lion": "Leone d'oro Venezia", "venice": "Venice Film Festival logo",
    "sundance": "Sundance Film Festival logo", "bear": "Goldener Bär Berlinale", "berlinale": "Berlinale logo svg",
    "emmy": "Emmy statuette", "emmylogo": "Emmy Awards logo", "criterion": "Criterion Collection logo",
}
res = {}
for k, q in Q.items():
    try:
        p = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": 6,
                                    "gsrlimit": 16, "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": 220})
        d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + p))
        pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
    except Exception as e:
        res[k] = str(e); continue
    sheet = Image.new("RGB", (4 * 240, 4 * 260), (90, 90, 90))
    dr = ImageDraw.Draw(sheet)
    lst = []
    for i, pg in enumerate(pages[:16]):
        ii = (pg.get("imageinfo") or [{}])[0]
        lst.append([i, pg["title"], ii.get("mime"), ii.get("width"), ii.get("height")])
        try:
            im = Image.open(io.BytesIO(get(ii["thumburl"]))).convert("RGBA")
            im.thumbnail((220, 220))
            x, y = (i % 4) * 240 + 10, (i // 4) * 260 + 10
            sheet.paste(im, (x, y), im)
        except Exception:
            pass
        dr.text(((i % 4) * 240 + 6, (i // 4) * 260 + 238), f"{i} {pg['title'][5:32]}", fill=(255, 255, 0))
    sheet.save(f"refs/aw/{k}.jpg", quality=80)
    res[k] = lst
json.dump(res, open("refs/aw/cands.json", "w"), indent=1, ensure_ascii=False)
