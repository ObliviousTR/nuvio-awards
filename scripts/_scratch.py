import json, os, sys, io, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
from PIL import Image, ImageDraw
os.makedirs("refs/uni", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 nuvio-awards"}
def img(path, size="w500"):
    return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(f"https://image.tmdb.org/t/p/{size}{path}", headers=UA), timeout=40).read()))
U = {
 "wizarding": dict(cols=[1241, 435259], movies=[]),
 "mcu": dict(cols=[86311], movies=[1726, 118340, 284054, 284052, 284053, 634649, 299534, 533535]),
 "batman": dict(cols=[263], movies=[268, 414906, 475557, 364]),
}
meta = {}
for u, spec in U.items():
    ids = list(spec["movies"])
    for c in spec["cols"]:
        ids += [p["id"] for p in (tmdb(f"/collection/{c}") or {}).get("parts", [])]
    bds, logos = [], []
    for mid in dict.fromkeys(ids):
        m = tmdb(f"/movie/{mid}") or {}
        im = tmdb(f"/movie/{mid}/images", include_image_language="en,null") or {}
        b = sorted([x for x in im.get("backdrops", []) if not x.get("iso_639_1") and x["width"] >= 1920], key=lambda x: -x["vote_average"])[:2]
        bds += [(m.get("title"), x["file_path"]) for x in b]
        l = sorted([x for x in im.get("logos", []) if x.get("iso_639_1") == "en"], key=lambda x: -x["vote_average"])[:1]
        logos += [(m.get("title"), x["file_path"]) for x in l]
    for c in spec["cols"]:
        ci = tmdb(f"/collection/{c}/images", include_image_language="en,null") or {}
        bds += [("COL " + str(c), x["file_path"]) for x in sorted([x for x in ci.get("backdrops", []) if not x.get("iso_639_1")], key=lambda x: -x["vote_average"])[:4]]
    meta[u] = {"backdrops": bds, "logos": logos}
    for kind, items, tw, th in (("backdrops", bds, 400, 225), ("logos", logos, 400, 160)):
        cols = 5; rows = (len(items) + cols - 1) // cols or 1
        sheet = Image.new("RGB", (cols * (tw + 10), rows * (th + 30)), (60, 60, 60)); dr = ImageDraw.Draw(sheet)
        for i, (t, p) in enumerate(items):
            try:
                im = img(p, "w500").convert("RGBA"); im.thumbnail((tw, th))
            except Exception:
                continue
            x, y = (i % cols) * (tw + 10), (i // cols) * (th + 30)
            sheet.paste(im, (x, y), im); dr.text((x + 4, y + th + 4), f"{i}: {t}"[:60], fill=(255, 255, 0))
        sheet.save(f"refs/uni/{u}-{kind}.jpg", quality=82)
for c in (420, 9993, 128064, 429):
    d = tmdb(f"/company/{c}") or {}
    meta[f"company{c}"] = [d.get("name"), d.get("logo_path")]
# Wikimedia Commons logo search
for q in ("Wizarding World logo", "Marvel Cinematic Universe logo", "Batman logo", "Marvel Studios logo"):
    r = json.loads(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "format": "json", "srlimit": 8}), headers=UA), timeout=30).read())
    meta["commons " + q] = [x["title"] for x in r["query"]["search"]]
json.dump(meta, open("refs/uni/meta.json", "w"), indent=1)
