"""Favourites row: the user's own folders plus My Simkl, all in the Favourites style.

Covers are the show's key art with its logo (no vignette); hovering plays a GIF. Every image and GIF is served from
our repo (github.com/ObliviousTR/nuvio-awards → spotlight/art/favourites/), mirrored there so nothing depends on
Pinterest or Giphy. The logo carries the name, so folder titles are hidden.
"""
import sys
from common import load, save, row, addon_src, SPOT_ART

SRC, OUT = sys.argv[1], sys.argv[2]
FAV = f"{SPOT_ART}/favourites"


def style(f, slot, backdrop=True):
    f.update(tileShape="LANDSCAPE", hideTitle=True, coverEmoji=None, titleLogoUrl=None,
             coverImageUrl=f"{FAV}/{slot}/cover.jpg", focusGifUrl=f"{FAV}/{slot}/hover.gif", focusGifEnabled=True,
             heroBackdropUrl=f"{FAV}/{slot}/backdrop.jpg" if backdrop else None)
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
]}, "mysimkl", backdrop=False)
fav["folders"] = [f for f in fav["folders"] if f["title"] != "My Simkl"] + [simkl]
save(data, OUT)
print(f"ok: Favourites ({len(fav['folders'])} folders) -> {OUT}")
