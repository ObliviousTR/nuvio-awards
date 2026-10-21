"""Language policy: general Genres / By Decade rails show English-language titles only (mainly US/UK).

Streaming rails are NOT filtered: their US watch-provider filter already keeps them to what the
service actually carries (global hits like Squid Game stay, TMDB-only bloat never appears).
Big non-English titles reach Genres / Decades through dedicated "International Hits" rails.

Applied to every native TMDB Discover/Network rail in the rows below, except rails that already pin a
language or origin country (anime rails = ja, Turkish Netflix rails = TR) and folders that exist for a
non-English catalogue (Crunchyroll). World cinema gets its own curated International row later.
The Networks row is left alone: each folder is one channel, and TV Tokyo / Fuji TV are Japanese by design.
"""
import json, sys

SRC, OUT = sys.argv[1], sys.argv[2]
ROWS = {"Genres", "By Decade", "Moods & Vibes", "Based On", "Documentaries"}
EXEMPT_FOLDERS = set()

data = json.load(open(SRC))
changed = skipped = 0
for c in data:
    if c["title"] not in ROWS:
        continue
    for f in c["folders"]:
        if f["title"] in EXEMPT_FOLDERS:
            continue
        for s in f["sources"]:
            if s.get("provider") != "tmdb" or s["tmdbSourceType"] not in ("DISCOVER", "NETWORK"):
                continue
            flt = s.setdefault("filters", {}) or {}
            s["filters"] = flt
            if flt.get("withOriginalLanguage") or flt.get("withOriginCountry"):
                skipped += 1
                continue
            flt["withOriginalLanguage"] = "en"
            changed += 1

json.dump(data, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"ok: {changed} rails set to English, {skipped} rails kept (anime / Turkish / pinned) -> {OUT}")
