"""Favourites row: the user's own folders plus My Simkl, all in the Favourites style.

Covers are the show's key art with its logo (no vignette); hovering plays the pinboard animation (hover.webp, art_tools/favourites_v2.py look A). Every image and GIF is served from
our repo (github.com/ObliviousTR/nuvio-awards → spotlight/art/favourites/), mirrored there so nothing depends on
Pinterest or Giphy. The logo carries the name, so folder titles are hidden.
"""
import hashlib, os, sys
from common import load, save, row, addon_src, SPOT_ART

SRC, OUT = sys.argv[1], sys.argv[2]
FAV = f"{SPOT_ART}/favourites"


LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "spotlight", "art", "favourites")


def url(slot, name):
    """repo URL plus a short content hash, so the app drops any older art it cached under the same path. My Simkl
    also changes weekly between deliveries; the app re-checks cached images in the background (stale-while-revalidate),
    so those weekly updates still arrive under the same URL."""
    p = os.path.join(LOCAL, slot, name)
    v = hashlib.sha1(open(p, "rb").read()).hexdigest()[:8] if os.path.exists(p) else "0"
    return f"{FAV}/{slot}/{name}?v={v}"


def style(f, slot, backdrop=True):
    f.update(tileShape="LANDSCAPE", hideTitle=True, coverEmoji=None, titleLogoUrl=None,
             coverImageUrl=url(slot, "cover.jpg"), focusGifUrl=url(slot, "hover.webp"), focusGifEnabled=True,
             heroBackdropUrl=url(slot, "backdrop.jpg") if backdrop else None)
    return f


data = load(SRC)
fav = row(data, "Favourites")
slots = {"Doctor Who": "doctorwho", "One Pace": "onepace", "Live Sport": "livesport"}
for f in fav["folders"]:
    if f["title"] in slots:
        style(f, slots[f["title"]])
simkl = style({"id": "folder-spotlight-simkl", "title": "My Simkl", "catalogSources": [], "sources": [
    addon_src("Up Next", "TV", "simkl.upnext"),
    addon_src("Watching", "TV", "simkl.watchlist.shows.watching"),
    addon_src("Plan to Watch · Movies", "MOVIE", "simkl.watchlist.movies.plantowatch"),
    addon_src("Plan to Watch · Series", "TV", "simkl.watchlist.shows.plantowatch"),
]}, "mysimkl")
fav["folders"] = [f for f in fav["folders"] if f["title"] != "My Simkl"] + [simkl]
save(data, OUT)
print(f"ok: Favourites ({len(fav['folders'])} folders) -> {OUT}")
