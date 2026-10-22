"""Awards: fetch marks + cut out statuettes (rembg) -> refs/awa (to keep in nuvio-art art/logos/awards)."""
import io, json, os, sys, time, subprocess, urllib.parse, urllib.request
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rembg[cpu]", "onnxruntime"], capture_output=True)
sys.path.insert(0, "scripts")
from spotlight import tmdb
from PIL import Image
from rembg import remove
os.makedirs("refs/awa", exist_ok=True)
UA = {"User-Agent": "nuvio-awards/1.0 (github.com/ObliviousTR/nuvio-awards)"}
def get(u):
    for _ in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read()
        except Exception as e:
            err = e; time.sleep(8)
    raise err
def commons(title, width=1600):
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": width, "format": "json"})
    info = next(iter(json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))["query"]["pages"].values()))["imageinfo"][0]
    time.sleep(3)
    return Image.open(io.BytesIO(get(info.get("thumburl") or info["url"]))).convert("RGBA")
def trim(im):
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return im.crop(bb) if bb else im
log = ""
def tmdb_logo(kind, tid, idx):
    lg = [x for x in (tmdb(f"/{kind}/{tid}/images", include_image_language="en,null") or {}).get("logos", []) if x["file_path"].endswith(".png")]
    return trim(Image.open(io.BytesIO(get("https://image.tmdb.org/t/p/original" + lg[idx]["file_path"]))).convert("RGBA"))
jobs = {
    "oscars-gold.png": lambda: tmdb_logo("tv", 27023, 1),
    "oscars-white.png": lambda: tmdb_logo("tv", 27023, 3),
    "golden-globes.png": lambda: tmdb_logo("tv", 71494, 3),
    "bafta.png": lambda: tmdb_logo("tv", 26183, 0),
    "palme-mark.png": lambda: trim(commons("File:Palme d'Or 2023.svg")),
    "lion-mark.png": lambda: trim(commons("File:Leone d'Oro gold silhouette.svg")),
    "bear-mark.png": lambda: trim(commons("File:Goldener Bär gold silhouette.svg")),
    "sundance-mark.png": lambda: trim(commons("File:Sundance Institute logo.svg")),
    "criterion-mark.png": lambda: trim(commons("File:The Criterion Collection Logo.svg")),
    "palme-trophy.png": lambda: trim(remove(commons("File:Palme d'or.jpg", 2000).convert("RGB"))),
    "lion-trophy.png": lambda: trim(remove(commons("File:Leone d'Oro miglior film, Deserto Rosso, 1964.jpg", 2000).convert("RGB"))),
    "emmy-trophy.png": lambda: trim(remove(commons("File:Dunkwu's Emmy Statuette.jpg", 2000).convert("RGB"))),
    "oscar-trophy.png": lambda: trim(remove(Image.open(io.BytesIO(get("https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/mirror/files/f1/f1a0400c91b86d07.png"))).convert("RGB").crop((620, 0, 1000, 562)) if False else Image.open(io.BytesIO(get("https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/mirror/files/f1/f1a0400c91b86d07.png"))).convert("RGB"))),
    "globe-trophy.png": lambda: trim(remove(Image.open(io.BytesIO(get("https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/mirror/files/" + "PLACEHOLDER"))).convert("RGB"))),
}
import json as _j
d = _j.load(open("builder/out/delivered/baseline.json"))
gg = [f for c in d if c["title"] == "Awards & Festivals" for f in c["folders"] if f["title"].startswith("Golden Globes")][0]["coverImageUrl"]
jobs["globe-trophy.png"] = lambda: trim(remove(Image.open(io.BytesIO(get(gg))).convert("RGB")))
for name, fn in jobs.items():
    try:
        im = fn(); im.save("refs/awa/" + name); log += f"ok {name} {im.size}\n"
    except Exception as e:
        import traceback; log += f"FAIL {name} {e}\n" + traceback.format_exc()[-600:]
open("refs/awa/log.txt", "w").write(log)
