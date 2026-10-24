"""Swap the genre rails of chosen folders for genre-true ones from the Library addon (scripts/genre_rails.py).

A Nuvio TMDB rail lists every title TMDB tags with the genre (Comedy also showed Pulp Fiction, Green Book, Evil Dead II).
For the folders below, each TMDB discover rail with a genre filter becomes a Library addon rail of the same name; its
query (the rail's own filters, sort) goes to library/genre_rails.json, and the daily workflow keeps only the titles whose
genre list the rail's genre leads (or follows only genres that go with it).
usage: python3 apply_genre_rails.py IN OUT
"""
import json, os, re, sys
from common import addon_src, load, save

LIB = "community.oblivioustr.nuvio-library"
DEFS = "/home/claude/nuvio-awards/library/genre_rails.json"
# rows whose genre rails are made genre-true (every folder). Streaming Services: its platform genre rails too - a title
# left out of one genre there still sits in the rail of its own (first) genre, and the platform's Popular / New / Top
# Rated rails (no genre filter) stay live TMDB rails.
ROWS = {"Genres", "Moods & Vibes", "Kids & Family", "Streaming Services"}
# Turkish rails, in any row, are served by the Library too - same TMDB query, no genre rule - so that Turkish titles show
# their own names (Nuvio's own TMDB rails always use the app language, English): rails filtered to Turkish productions
# and every TMDB rail of the Turkish platforms.
TR_FOLDERS = {"Exxen", "GAİN", "tabii"}


def turkish(f, s):
    fl = s.get("filters") or {}
    return s.get("provider") == "tmdb" and s.get("tmdbSourceType") in ("DISCOVER", "NETWORK") and (
        f["title"] in TR_FOLDERS or str(fl.get("withOriginCountry", "")).upper() == "TR" or fl.get("withOriginalLanguage") == "tr")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def published():
    """gen-* / mdb-* catalogs the Library serves now (a rail the daily run found empty is not there: keep it live)."""
    try:
        return {c["id"] for c in json.load(open(os.path.join(os.path.dirname(DEFS), "manifest.json"), encoding="utf-8"))["catalogs"]
                if c["id"].startswith(("gen-", "mdb-"))}
    except Exception:
        return set()


def main(src, dst):
    data = load(src)
    live = published()
    defs, n, t = [], 0, 0
    for row in data:
        for f in row.get("folders", []):
            new = []
            for s in f["sources"]:
                fl = s.get("filters") or {}
                tr = turkish(f, s) and not (row["title"] in ROWS and s.get("tmdbSourceType") == "DISCOVER" and fl.get("withGenres"))
                if tr:
                    cid = f"gen-{slug(row['title'])}-{slug(f['title'])}-{slug(s['title'])}"
                    q = dict(fl)   # the same query Nuvio itself sends for the rail
                    if s.get("tmdbSourceType") == "NETWORK" and s.get("tmdbId"):
                        q.update(withNetworks=str(s["tmdbId"]), withStatus="0|3|4", airedByToday=True)
                    if q.get("withWatchProviders"):
                        q.setdefault("watchRegion", "US")
                        q["withWatchMonetizationTypes"] = "flatrate|free|ads|rent|buy"
                    defs.append({"id": cid, "name": f"{f['title']} · {s['title']}", "media": s["mediaType"],
                                 "sort": s.get("sortBy"), "filters": q, "limit": 300, "rule": False})
                    if cid not in live:
                        new.append(s)
                        continue
                    a = addon_src(s["title"], s["mediaType"], cid, addon_id=LIB)
                    a["genre"] = None
                    new.append(a)
                    t += 1
                elif row["title"] in ROWS and s.get("provider") == "tmdb" and s.get("tmdbSourceType") == "DISCOVER" and fl.get("withGenres"):
                    cid = f"gen-{slug(row['title'])}-{slug(f['title'])}-{slug(s['title'])}"
                    defs.append({"id": cid, "name": f"{f['title']} · {s['title']}", "media": s["mediaType"],
                                 "sort": s.get("sortBy"), "filters": fl,
                                 "limit": 300 if row["title"] == "Streaming Services" else 500})
                    if live and cid not in live:   # empty or not built yet: the live TMDB rail stays
                        new.append(s)
                        continue
                    a = addon_src(s["title"], s["mediaType"], cid, addon_id=LIB)
                    a["genre"] = None   # static catalogs take no extras
                    new.append(a)
                    n += 1
                else:
                    new.append(s)
            f["sources"] = new
    # MDBList lists: our own copies (library mdb-<id>) instead of AIOMetadata's, wherever a folder uses one
    m = 0
    for row in data:
        for f in row.get("folders", []):
            for i, s in enumerate(f["sources"]):
                cid = s.get("catalogId") or ""
                if s.get("addonId") == "aio-metadata" and cid.startswith("mdblist.") and f"mdb-{cid.split('.')[1]}" in live:
                    a = addon_src(s["title"], "MOVIE" if s["type"] == "movie" else "TV", f"mdb-{cid.split('.')[1]}", addon_id=LIB)
                    a["genre"] = None
                    f["sources"][i] = a
                    m += 1
    print(f"mdblist: {m} rails now from the Library's own copies")
    json.dump(defs, open(DEFS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    save(data, dst)
    print(f"genre rails: {n} rails now genre-true ({', '.join(sorted(ROWS))}); Turkish rails from the Library: {t} "
          f"of {sum(1 for d in defs if d.get('rule') is False)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
