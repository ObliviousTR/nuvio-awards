"""How clean are the genre rails? For every Genres card: the top of its live TMDB discover rails, each title's own genre
list (TMDB order: the first is the main genre), and what a 'without' list per genre would keep / drop."""
import json, os, sys, collections
sys.path.insert(0, "scripts"); sys.path.insert(0, "art_tools")
from spotlight import tmdb
os.makedirs("refs/purity", exist_ok=True)
d = json.load(open("builder/out/delivered/baseline.json"))
MOV = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama",
       10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance",
       878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"}
TV = {10759: "Action&Adv", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
      10762: "Kids", 9648: "Mystery", 10763: "News", 10764: "Reality", 10765: "SciFi&Fantasy", 10766: "Soap",
      10767: "Talk", 10768: "War&Politics", 37: "Western"}
KEYMAP = {"voteCountGte": "vote_count.gte", "withGenres": "with_genres", "withoutGenres": "without_genres",
          "withOriginalLanguage": "with_original_language", "withKeywords": "with_keywords",
          "withOriginCountry": "with_origin_country"}
details = {}
def genres_of(kind, i):
    if (kind, i) not in details:
        x = tmdb(f"/{kind}/{i}") or {}
        details[(kind, i)] = ([g["id"] for g in x.get("genres", [])], x.get("title") or x.get("name"), (x.get("release_date") or x.get("first_air_date") or "")[:4])
    return details[(kind, i)]
out = {}
lines = []
for r in d:
    if r["title"] != "Genres":
        continue
    for f in r["folders"]:
        rec = []
        for s in f["sources"]:
            fl = s.get("filters") or {}
            if s.get("provider") != "tmdb" or not fl.get("withGenres") or s["title"] not in ("Popular Movies", "Top All Time Movies", "Popular Series", "Top All Time Series"):
                continue
            kind = "movie" if s["mediaType"] == "MOVIE" else "tv"
            q = {KEYMAP[k]: v for k, v in fl.items() if k in KEYMAP}
            q["sort_by"] = s["sortBy"]
            ids = []
            for page in (1, 2, 3):
                ids += [x["id"] for x in (tmdb(f"/discover/{kind}", page=page, **q) or {}).get("results", [])]
            for i in ids:
                gs, name, yr = genres_of(kind, i)
                rec.append(dict(rail=s["title"], kind=kind, id=i, name=name, year=yr, genres=gs, target=fl["withGenres"]))
        out[f["title"]] = rec
        lines.append(f"\n## {f['title']}  ({len(rec)} titles)")
        for x in rec[:400]:
            names = (MOV if x["kind"] == "movie" else TV)
            lines.append(f"{x['rail'][:14]:14s} {x['name']} ({x['year']}) : {', '.join(names.get(g, str(g)) for g in x['genres'])}")
json.dump(out, open("refs/purity/genres.json", "w"))
open("refs/purity/genres.txt", "w").write("\n".join(lines))
