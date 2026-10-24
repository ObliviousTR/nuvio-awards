"""More Brosnan / Dalton figure candidates: every textless/English poster and backdrop."""
import io, json, os, urllib.parse, urllib.request
from PIL import Image, ImageDraw
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/bond2"; os.makedirs(OUT, exist_ok=True)
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
lst = []
for actor, ids in {"brosnan": [710, 714, 36643, 36669], "dalton": [708, 709]}.items():
    tiles = []
    for mid in ids:
        im = t(f"movie/{mid}/images", include_image_language="null,en")
        cand = [("p", x) for x in im.get("posters", []) if x.get("iso_639_1") in (None, "en")][5:25] + [("b", x) for x in im.get("backdrops", [])[:12]]
        for i, (k, x) in enumerate(cand):
            raw = urllib.request.urlopen("https://image.tmdb.org/t/p/w500" + x["file_path"], timeout=60).read()
            name = f"{actor}_{mid}_{k}{i}"
            lst.append(f"{name}\t{x['file_path']}")
            th = Image.open(io.BytesIO(raw)).convert("RGB"); th.thumbnail((150, 150)); tiles.append((name, th))
    cols = 10
    sh = Image.new("RGB", (cols * 150, ((len(tiles) + cols - 1) // cols) * 166), (20, 20, 20)); d = ImageDraw.Draw(sh)
    for n, (name, th) in enumerate(tiles):
        x, y = (n % cols) * 150, (n // cols) * 166; sh.paste(th, (x, y + 14)); d.text((x + 2, y + 1), name.split("_", 1)[1], fill=(255, 255, 255))
    sh.save(os.path.join(OUT, f"_sheet_{actor}.jpg"), quality=78)
open(os.path.join(OUT, "list.txt"), "w").write("\n".join(lst) + "\n")
