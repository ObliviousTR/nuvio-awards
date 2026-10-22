"""Point every image / GIF at our own copy in github.com/ObliviousTR/nuvio-art (mirror/map.json), so the
collections keep their art even if Kaptain or another host removes it. URLs not mirrored yet stay as they are and
are added to the mirror's source list (push nuvio-art afterwards; its workflow downloads them).
usage: python3 apply_art_mirror.py in.json out.json
"""
import json, os, sys, urllib.request
from common import load, save

ART = os.environ.get("NUVIO_ART", "/home/claude/nuvio-art")
RAW = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/"
KEYS = ("coverImageUrl", "focusGifUrl", "titleLogoUrl", "heroBackdropUrl")
local = os.path.join(ART, "mirror", "map.json")
mp = json.load(open(local)) if os.path.exists(local) else json.loads(urllib.request.urlopen(RAW + "mirror/map.json").read())

data = load(sys.argv[1])
done, missing = 0, set()


def swap(obj, k):
    global done
    u = obj.get(k)
    if not u or u.startswith(RAW) or "ObliviousTR/" in u:
        return
    if u in mp:
        rel = mp[u]
        # animated focus images: the all-keyframe WebP next to the mirrored file (art_tools/keyframe_webp.py), which
        # Nuvio Desktop can play at full speed
        kf = os.path.splitext(rel)[0] + ".kf.webp"
        if k == "focusGifUrl" and os.path.exists(os.path.join(ART, kf)):
            rel = kf
        obj[k] = RAW + rel; done += 1
    else:
        missing.add(u)


for c in data:
    swap(c, "backdropImageUrl")
    for f in c["folders"]:
        for k in KEYS:
            swap(f, k)
save(data, sys.argv[2])
if missing and os.path.exists(os.path.join(ART, "mirror", "urls.json")):
    p = os.path.join(ART, "mirror", "urls.json")
    urls = sorted(set(json.load(open(p))) | missing)
    json.dump(urls, open(p, "w"), indent=0)
print(f"art mirror: {done} links point at nuvio-art, {len(missing)} not mirrored yet" +
      (" (added to nuvio-art/mirror/urls.json: push it)" if missing else ""))
