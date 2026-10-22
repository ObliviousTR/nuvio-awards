"""Check candidate collections for the Film Collections re-shuffle, and a few films' TMDB genres."""
import json, os, sys
sys.path.insert(0, "scripts")
import library as L
from spotlight import tmdb
os.makedirs("refs/chk", exist_ok=True)
out = []
for n in ["Sin City Collection", "Den of Thieves Collection", "Wall Street Collection", "Get Shorty Collection",
          "Hercule Poirot Collection", "Murder Mystery Collection", "The Guns of Navarone Collection",
          "Iron Eagle Collection", "After Collection", "The Best Exotic Marigold Hotel Collection",
          "The Thin Man Collection", "Fletch Collection", "Analyze This Collection", "The Italian Job Collection",
          "Infernal Affairs Collection", "Hot Shots! Collection", "Kill Bill Collection", "Glass Onion",
          "Godfather", "Scarface", "Bad Lieutenant", "Snatch", "Now You See Me Collection"]:
    try:
        c = L.find_col(n, {})
        if c:
            name, parts = L.collection_parts(c["id"])
            out.append(f"{n} -> {c['id']} {name}: " + ", ".join(f"{p.get('title')} ({(p.get('release_date') or '')[:4]})" for p in parts))
        else:
            out.append(f"{n} -> NOT FOUND")
    except Exception as e:
        out.append(f"{n} -> error {e}")
gn = {g["id"]: g["name"] for g in (tmdb("/genre/movie/list") or {}).get("genres", [])}
for t, y in [("Step Up", 2006), ("Magic Mike", 2012), ("Fifty Shades of Grey", 2015), ("Goal!", 2005), ("Creed", 2015),
             ("Before Sunrise", 1995), ("After", 2019), ("The Best Exotic Marigold Hotel", 2011), ("Rocky", 1976),
             ("The Godfather", 1972), ("Rush Hour", 1998)]:
    r = (tmdb("/search/movie", query=t, year=y) or {}).get("results", [])
    if r:
        out.append(f"GENRES {t} ({y}): " + ", ".join(gn.get(g, str(g)) for g in r[0].get("genre_ids", [])))
open("refs/chk/out.txt", "w").write("\n".join(out))
