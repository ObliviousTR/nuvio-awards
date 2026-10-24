"""Bond figures: textless posters and backdrops of each Bond's films -> refs/bond + contact sheets."""
import io, json, os, urllib.parse, urllib.request
from PIL import Image, ImageDraw
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/bond"; os.makedirs(OUT, exist_ok=True)
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
films = {"connery": [646, 657, 658, 660, 667], "lazenby": [668], "moore": [253, 691, 698, 699, 709 - 0],
         "dalton": [708, 709], "brosnan": [710, 714, 36643, 36669], "craig": [36557, 37724, 206647, 370172, 10764]}
films["moore"] = [253, 682, 691, 698, 699, 700, 707]
for actor, ids in films.items():
    tiles = []
    for mid in ids:
        im = t(f"movie/{mid}/images", include_image_language="null,en")
        posters = [x for x in im.get("posters", []) if x.get("iso_639_1") in (None, "en")]
        posters = sorted(posters, key=lambda x: (x.get("iso_639_1") is not None, -x.get("vote_average", 0)))[:5]
        for i, p in enumerate(posters):
            raw = urllib.request.urlopen("https://image.tmdb.org/t/p/w780" + p["file_path"], timeout=60).read()
            name = f"{actor}_{mid}_p{i}.jpg"
            open(os.path.join(OUT, name), "wb").write(raw)
            th = Image.open(io.BytesIO(raw)).convert("RGB"); th.thumbnail((160, 240)); tiles.append((name, th))
    cols = 8
    sh = Image.new("RGB", (cols * 160, ((len(tiles) + cols - 1) // cols) * 256), (20, 20, 20)); d = ImageDraw.Draw(sh)
    for n, (name, th) in enumerate(tiles):
        x, y = (n % cols) * 160, (n // cols) * 256; sh.paste(th, (x, y + 14)); d.text((x + 2, y + 1), name.split("_", 1)[1], fill=(255, 255, 255))
    sh.save(os.path.join(OUT, f"_sheet_{actor}.jpg"), quality=80)
print("ok")
