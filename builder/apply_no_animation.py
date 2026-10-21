"""Keep animation and anime out of every rail that isn't explicitly an animation / anime rail.

Exempt: rails whose genres include Animation (16), rails titled Anime / Animation / Animated / Cartoon,
the Genres > Animation and Anime folders, Crunchyroll, and and the whole Networks row (a channel rail shows that channel's own shows).
Addon rails (FlixPatrol Top 10, MDBList) can't be filtered and are left alone.
usage: python3 apply_no_animation.py in.json out.json"""
import re, sys
from common import load, save, add, NOISE

ROWS = {"Streaming Services", "Genres", "By Decade", "Moods & Vibes", "Based On", "Documentaries",
        "International Cinema"}
EXEMPT_FOLDERS = {("Genres", "Animation"), ("Genres", "Anime"), ("Streaming Services", "Crunchyroll"),
}
TOON_TITLE = re.compile(r"anime|animat|cartoon", re.I)


def is_toon(s):
    g = (s.get("filters") or {}).get("withGenres") or ""
    return "16" in re.split(r"[|,]", g) or TOON_TITLE.search(s["title"] or "")


data = load(sys.argv[1])
changed = skipped = 0
for c in data:
    if c["title"] not in ROWS:
        continue
    for f in c["folders"]:
        if (c["title"], f["title"]) in EXEMPT_FOLDERS:
            continue
        for s in f["sources"]:
            if s["provider"] != "tmdb" or s["tmdbSourceType"] not in ("DISCOVER", "NETWORK"):
                continue
            if is_toon(s):
                skipped += 1
                continue
            extra = "16" if s["mediaType"] == "MOVIE" else "16|" + NOISE
            s["filters"] = add(s.get("filters") or {}, withoutGenres=extra)
            changed += 1
save(data, sys.argv[2])
print(f"no-animation: {changed} rails filtered, {skipped} animation/anime rails kept")
