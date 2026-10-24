"""Spider-Verse cover alternatives: official title logos over textless key art (TMDB)."""
import io, json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, "scripts")
import spotlight_art as art
import universe_motion as U
from PIL import Image, ImageEnhance, ImageFilter
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/spiderverse"; os.makedirs(OUT, exist_ok=True)
W, H = 1280, 720
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
def img(path, size="original"):
    return Image.open(io.BytesIO(urllib.request.urlopen(f"https://image.tmdb.org/t/p/{size}{path}", timeout=60).read()))
def best(arr, lang):
    a = [x for x in arr if x.get("iso_639_1") == lang]
    return sorted(a, key=lambda x: (-x.get("vote_average", 0), -x.get("width", 0)))
rep = []
films = {"into": 324857, "across": 569094, "nwh": 634649, "beyond": 911916}
assets = {}
for k, mid in films.items():
    im = t(f"movie/{mid}/images", include_image_language="en,null")
    assets[k] = {"logos": [x["file_path"] for x in best(im.get("logos", []), "en") if x["file_path"].endswith(".png")][:3],
                 "back": [x["file_path"] for x in best(im.get("backdrops", []), None)][:6]}
    rep.append(f"{k}: logos {len(assets[k]['logos'])}, textless backdrops {len(assets[k]['back'])}")
def cover(back, logo, name, tag="EVERY SPIDER  ·  EVERY UNIVERSE", dark=0.62):
    bg = art.graded(img(back), 0.92, 1.08, (W, H)).convert("RGB")
    bg = ImageEnhance.Brightness(bg).enhance(dark + 0.2)
    cv = U.vignette(bg, 1.1).convert("RGBA") if hasattr(U, "vignette") else bg.convert("RGBA")
    lg = U.fit(U.trim(img(logo).convert("RGBA")), 760, 300)
    U.place(cv, U.glow(U.padded(lg, 40), 26, (0, 0, 0), 0.9), W / 2, H / 2 - 20, 1)
    U.place(cv, lg, W / 2, H / 2 - 20, 1)
    U.tagline(cv, tag, H / 2 - 20 + lg.height / 2 + 44, 1)
    cv.convert("RGB").save(f"{OUT}/{name}.jpg", quality=88)
    return cv
n = 0
for k in ("across", "into", "nwh", "beyond"):
    a = assets[k]
    for i, b in enumerate(a["back"][:2]):
        if a["logos"]:
            cover(b, a["logos"][0], f"{k}_{i}"); n += 1
rep.append(f"covers: {n}")
tiles = [Image.open(f"{OUT}/{f}").resize((426, 240)) for f in sorted(os.listdir(OUT)) if f.endswith(".jpg") and f != "sheet.jpg"]
sh = Image.new("RGB", (426 * 3, 240 * ((len(tiles) + 2) // 3)))
for i, im in enumerate(tiles):
    sh.paste(im, ((i % 3) * 426, (i // 3) * 240))
sh.save(f"{OUT}/sheet.jpg", quality=86)
open(f"{OUT}/report.txt", "w").write("\n".join(rep) + "\n"); print("\n".join(rep), sorted(os.listdir(OUT)))
