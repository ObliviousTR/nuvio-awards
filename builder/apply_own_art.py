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


GIF_ROWS = {"Iconic Actors", "Legendary Directors"}  # rows whose every card now has our hover reel (art_tools/actor_art.py)
data = load(sys.argv[1])
n = 0
for row in data:
    fs = row.get("folders", [])
    gif_on = sum(1 for f in fs if f.get("focusGifEnabled")) * 2 > len(fs) or row["title"] in GIF_ROWS
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
# Networks: monthly art from the network-art branch (art_tools/network_art.py); fixed URLs
NET = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/network-art/"
NET_IDS = {x["title"]: x["title"] for x in json.load(open("/home/claude/nuvio-awards/art_tools/networks.json", encoding="utf-8"))}


def net_slug(t):
    s_ = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s_:
        s_ = s_.replace("--", "-")
    return s_


for row in data:
    if row["title"] != "Networks":
        continue
    for f in row["folders"]:
        if f["title"] in NET_IDS:
            u = NET + net_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True})
            if f["title"] == "Fuji TV / MBS":
                f.update({"heroBackdropUrl": u + "backdrop.jpg", "titleLogoUrl": u + "logo.png"})
            n += 1
# Genres: monthly art from the genre-art branch (art_tools/genre_art.py); fixed URLs. Kaptain's hero and logo stay.
GEN = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/genre-art/"
sys.path.insert(0, "/home/claude/nuvio-awards/art_tools")
from genre_art import GENRES, slug_of as genre_slug
for row in data:
    if row["title"] != "Genres":
        continue
    for f in row["folders"]:
        if f["title"] in GENRES:
            u = GEN + genre_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True})
            n += 1
# Moods & Vibes: monthly art from the mood-art branch (art_tools/mood_art.py). Kaptain's hero and logo stay.
MOOD = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/mood-art/"
from mood_art import MOODS
for row in data:
    if row["title"] != "Moods & Vibes":
        continue
    for f in row["folders"]:
        if f["title"] in MOODS:
            u = MOOD + genre_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True})
            n += 1
# Kids & Family: monthly art from the kids-art branch (art_tools/kids_art.py). Kaptain's hero and logo stay.
KIDS = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/kids-art/"
from kids_art import CARDS as KIDS_CARDS
for row in data:
    if row["title"] != "Kids & Family":
        continue
    for f in row["folders"]:
        if f["title"] in KIDS_CARDS:
            u = KIDS + genre_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True, "tileShape": "LANDSCAPE"})
            n += 1
# Studios: monthly art from the studio-art branch (art_tools/studio_art.py). Kaptain's hero and logo stay.
STUDIO = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/studio-art/"
from studio_art import STUDIOS
for row in data:
    if row["title"] != "Studios":
        continue
    for f in row["folders"]:
        if f["title"] in STUDIOS:
            u = STUDIO + genre_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True, "tileShape": "LANDSCAPE"})
            n += 1
# Awards & Festivals: monthly art from the awards-art branch (art_tools/awards_art.py): the award's mark, its winners
# playing behind it. Kaptain's hero and logo stay.
AWARDS = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/awards-art/"
from awards_art import CARDS as AWARD_CARDS, slug_of as award_slug
for row in data:
    if row["title"] != "Awards & Festivals":
        continue
    for f in row["folders"]:
        if f["title"] in AWARD_CARDS:
            u = AWARDS + award_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True, "tileShape": "LANDSCAPE"})
            n += 1
# Based On: monthly art from the basedon-art branch (art_tools/basedon_art.py): the card's emblem, then three
# adaptations turning from their source into the film. Kaptain's hero and logo stay.
BASEDON = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/basedon-art/"
from basedon_art import CARDS as BASED_CARDS, slug_of as based_slug
for row in data:
    if row["title"] != "Based On":
        continue
    for f in row["folders"]:
        if f["title"] in BASED_CARDS:
            u = BASEDON + based_slug(f["title"]) + "/"
            f.update({"coverImageUrl": u + "cover.jpg", "focusGifUrl": u + "hover.webp", "focusGifEnabled": True,
                      "coverEmoji": None, "hideTitle": True, "tileShape": "LANDSCAPE"})
            n += 1
# Nuvio Desktop keeps every hover animation it ever downloaded on disk, keyed by URL, and never checks for a newer
# one; a fixed URL would show the first version forever there. So the branch art's URLs carry ?v=<hash of the file
# as it is now> (raw.githubusercontent ignores the query, mobile still refreshes on its own).
import subprocess
REPO = "/home/claude/nuvio-awards"
_hash = {}


def branch_version(branch, path):
    key = (branch, path)
    if key not in _hash:
        if branch not in {b for b, _ in _hash}:
            subprocess.run(["git", "-C", REPO, "fetch", "-q", "origin", f"+{branch}:refs/remotes/origin/{branch}"], check=False)
        r = subprocess.run(["git", "-C", REPO, "show", f"origin/{branch}:{path}"], capture_output=True)
        _hash[key] = hashlib.md5(r.stdout).hexdigest()[:8] if r.returncode == 0 else None
    return _hash[key]


vn = 0
for row in data:
    for f in row.get("folders", []):
        for k in ("coverImageUrl", "focusGifUrl", "heroBackdropUrl", "titleLogoUrl"):
            u = f.get(k) or ""
            for base in (DISC, NET, GEN, MOOD, KIDS, STUDIO, AWARDS, BASEDON):
                if u.startswith(base) and "?" not in u:
                    v = branch_version(base.rstrip("/").rsplit("/", 1)[1], u[len(base):])
                    if v:
                        f[k] = u + "?v=" + v
                        vn += 1
save(data, sys.argv[2])
print(f"own art: {n} folders, {vn} branch links versioned")
