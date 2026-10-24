"""Spider-Man stills across the films and series (textless TMDB backdrops) -> refs/spiderstills + contact sheets."""
import io, json, os, urllib.parse, urllib.request
from PIL import Image, ImageDraw
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/spiderstills"; os.makedirs(OUT, exist_ok=True)
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
items = [("movie", 557, "sm2002"), ("movie", 558, "sm2"), ("movie", 1930, "asm"), ("movie", 102382, "asm2"),
         ("movie", 315635, "homecoming"), ("movie", 634649, "nwh"), ("movie", 324857, "into"), ("movie", 569094, "across")]
for q in ("Spider-Man: The Animated Series", "Your Friendly Neighborhood Spider-Man", "Spider-Man (1967)"):
    r = t("search/tv", query=q)["results"]
    if r:
        items.append(("tv", r[0]["id"], "tv-" + str(r[0]["id"])))
listing = []
for kind, mid, tag in items:
    im = t(f"{kind}/{mid}/images", include_image_language="null")
    bs = sorted(im.get("backdrops", []), key=lambda x: -x.get("vote_average", 0))[:8]
    tiles = []
    for i, b in enumerate(bs):
        raw = urllib.request.urlopen("https://image.tmdb.org/t/p/w1280" + b["file_path"], timeout=60).read()
        name = f"{tag}_{i}.jpg"
        open(os.path.join(OUT, name), "wb").write(raw)
        listing.append(f"{name}\t{kind}/{mid}\t{b['file_path']}")
        th = Image.open(io.BytesIO(raw)).convert("RGB"); th.thumbnail((320, 180)); tiles.append((name, th))
    sh = Image.new("RGB", (4 * 320, 2 * 200), (20, 20, 20)); d = ImageDraw.Draw(sh)
    for n, (name, th) in enumerate(tiles):
        x, y = (n % 4) * 320, (n // 4) * 200; sh.paste(th, (x, y + 20)); d.text((x + 4, y + 4), name, fill=(255, 255, 255))
    sh.save(os.path.join(OUT, f"_sheet_{tag}.jpg"), quality=80)
open(os.path.join(OUT, "list.txt"), "w").write("\n".join(listing) + "\n")
print(len(listing))
