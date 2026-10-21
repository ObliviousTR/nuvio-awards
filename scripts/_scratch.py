import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageDraw
OUT = "refs/cand"; os.makedirs(OUT, exist_ok=True)
defs = json.load(open("library/definitions.json"))
def search(spec):
    m = re.match(r"^(.*?)\s*\((\d{4})\)$", spec); t, y = (m.group(1), m.group(2)) if m else (spec, None)
    r = (tmdb("/search/movie", query=t, **({"primary_release_year": y} if y else {})) or {}).get("results", [])
    return r[0]["id"] if r else None
meta = {}
for f in defs["franchises"]:
    ids = []
    cols = list(f.get("cols", [])) + [c for r in f.get("rails", []) for c in r.get("cols", [])]
    for c in cols:
        parts = sorted((tmdb(f"/collection/{c}") or {}).get("parts", []), key=lambda p: -(p.get("vote_count") or 0))
        ids += [p["id"] for p in parts]
    for spec in f.get("movies", []) + f.get("toon_movies", []) + [t for r in f.get("rails", []) if r.get("type", "movie") == "movie" for t in r.get("titles", [])]:
        i = search(spec)
        if i: ids.append(i)
    ids = list(dict.fromkeys(ids))[:14]
    bds, logos = [], []
    for mid in ids:
        m = tmdb(f"/movie/{mid}") or {}
        im = tmdb(f"/movie/{mid}/images", include_image_language="en,null") or {}
        b = sorted([x for x in im.get("backdrops", []) if not x.get("iso_639_1") and x["width"] >= 1920], key=lambda x: -x["vote_average"])[:2]
        bds += [(m.get("title"), x["file_path"]) for x in b]
        l = sorted([x for x in im.get("logos", []) if x.get("iso_639_1") == "en"], key=lambda x: -x["vote_average"])[:1]
        logos += [(m.get("title"), x["file_path"]) for x in l]
    bds = bds[:28]
    meta[f["id"]] = {"title": f["title"], "backdrops": bds, "logos": logos}
    cols_n = 7; rows = (len(bds) + cols_n - 1) // cols_n or 1
    sheet = Image.new("RGB", (cols_n * 290, rows * 175), (40, 40, 40)); d = ImageDraw.Draw(sheet)
    for i, (t, p) in enumerate(bds):
        try:
            im = art.fetch(p, "w300").convert("RGB")
        except Exception:
            continue
        im.thumbnail((284, 160)); x, y = (i % cols_n) * 290, (i // cols_n) * 175
        sheet.paste(im, (x, y)); d.rectangle((x, y, x + 150, y + 14), fill=(0, 0, 0)); d.text((x + 3, y + 1), f"{i} {t}"[:26], fill=(255, 255, 0))
    sheet.save(f"{OUT}/{f['id']}.jpg", quality=72)
json.dump(meta, open(f"{OUT}/meta.json", "w"), indent=0)
