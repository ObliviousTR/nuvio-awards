"""Our own folder art from nuvio-art/art/folders/<row>/<folder>/ (made by art_tools/folder_art.py and reletter.py):
cover.jpg -> cover, hover.webp or focus.jpg -> focus image, backdrop.jpg -> hero. The GIF switch follows the row
(on if most of the folder's neighbours have it on). URLs carry ?v=<hash> so an updated file is fetched again."""
import hashlib, json, os, sys
from common import load, save

ART = "/home/claude/nuvio-art/art/folders"
RAW = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/art/folders/"


def slug(s):
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def url(rel):
    return RAW + rel + "?v=" + hashlib.md5(open(os.path.join(ART, rel), "rb").read()).hexdigest()[:8]


data = load(sys.argv[1])
n = 0
for row in data:
    fs = row.get("folders", [])
    gif_on = sum(1 for f in fs if f.get("focusGifEnabled")) * 2 > len(fs)
    hide = sum(1 for f in fs if f.get("hideTitle")) * 2 > len(fs)  # our covers carry their name like the row's
    for f in fs:
        rel = f"{slug(row['title'])}/{slug(f['title'])}"
        d = os.path.join(ART, rel)
        if not os.path.isdir(d):
            continue
        has = lambda x: os.path.exists(os.path.join(d, x))
        if has("cover.jpg"):
            f["coverImageUrl"], f["coverEmoji"] = url(rel + "/cover.jpg"), None
        for focus in ("hover.webp", "focus.jpg"):
            if has(focus):
                f["focusGifUrl"], f["focusGifEnabled"] = url(rel + "/" + focus), gif_on
                break
        if has("backdrop.jpg"):
            f["heroBackdropUrl"] = url(rel + "/backdrop.jpg")
        if has("logo.png"):
            f["titleLogoUrl"] = url(rel + "/logo.png")
        f["hideTitle"] = hide
        n += 1
# Discover: weekly art from the discover-art branch (scripts/discover_art.py); fixed URLs, the files change in place
DISC = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/discover-art/"
DISC_IDS = {"Trending Movies": "trending-movies", "Trending Series": "trending-series", "New Movies": "new-movies",
            "New Series": "new-series", "Box Office Champions": "box-office", "Certified Fresh & Must-See": "certified",
            "Hidden Gems": "hidden-gems", "Awards & Prestige": "prestige", "All-Time Top Rated": "top-rated"}
for row in data:
    if row["title"] != "Discover":
        continue
    for f in row["folders"]:
        i = DISC_IDS.get(f["title"])
        if i:
            f.update({"tileShape": "LANDSCAPE", "hideTitle": True, "coverEmoji": None,
                      "coverImageUrl": DISC + i + "/cover.jpg", "focusGifUrl": DISC + i + "/hover.webp",
                      "focusGifEnabled": True, "heroBackdropUrl": DISC + i + "/backdrop.jpg",
                      "titleLogoUrl": DISC + i + "/logo.png"})
            n += 1
save(data, sys.argv[2])
print(f"own art: {n} folders")
