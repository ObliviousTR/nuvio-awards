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
# (row, folder) -> on. Trial: Comedy first; then Genres, Moods & Vibes, Kids & Family.
SCOPE = {("Genres", "Comedy")}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main(src, dst):
    data = load(src)
    defs, n = [], 0
    for row in data:
        for f in row.get("folders", []):
            if (row["title"], f["title"]) not in SCOPE:
                continue
            new = []
            for s in f["sources"]:
                fl = s.get("filters") or {}
                if s.get("provider") == "tmdb" and s.get("tmdbSourceType") == "DISCOVER" and fl.get("withGenres"):
                    cid = f"gen-{slug(row['title'])}-{slug(f['title'])}-{slug(s['title'])}"
                    defs.append({"id": cid, "name": f"{f['title']} · {s['title']}", "media": s["mediaType"],
                                 "sort": s.get("sortBy"), "filters": fl})
                    a = addon_src(s["title"], s["mediaType"], cid, addon_id=LIB)
                    a["genre"] = None   # static catalogs take no extras
                    new.append(a)
                    n += 1
                else:
                    new.append(s)
            f["sources"] = new
    json.dump(defs, open(DEFS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    save(data, dst)
    print(f"genre rails: {n} rails now genre-true ({len(SCOPE)} folders)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
