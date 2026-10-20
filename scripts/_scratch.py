"""Temporary: resolve the Reality TV keyword names and preview every rail (count + top titles)."""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb, find_keywords
from _reality_spec import FOLDERS, ANGLO

OUT = "refs/reality"
os.makedirs(OUT, exist_ok=True)
SORT = {"pop": "popularity.desc", "top": "vote_average.desc", "new": "first_air_date.desc", "votes": "vote_count.desc"}
today = dt.date.today().isoformat()
ids, md = {}, []
names = sorted({k for _, _, rails in FOLDERS for _, r in rails for k in r.get("kw", [])})
for n in names:
    ids[n] = find_keywords([n])
json.dump(ids, open(f"{OUT}/keywords.json", "w"), indent=1)
md.append("## Keywords\n" + "\n".join(f"- {n}: {ids[n] or 'NOT FOUND'}" for n in names) + "\n")
for folder, _, rails in FOLDERS:
    md.append(f"## {folder}")
    for title, r in rails:
        q = {"sort_by": SORT[r["sort"]], "vote_count.gte": r.get("vc", 0), "without_genres": "16",
             "with_original_language": r.get("lang", "en"), "with_origin_country": r.get("country", ANGLO)}
        g = r.get("genres", "10764")
        if g:
            q["with_genres"] = g
        if r.get("kw"):
            k = "|".join(i for n in r["kw"] for i in ids[n].split("|") if i)
            q["with_keywords"] = k or "0"
        if r.get("net"):
            q["with_networks"] = r["net"]
        if r.get("since"):
            q["first_air_date.gte"] = f"{r['since']}-01-01"
        if r.get("until"):
            q["first_air_date.lte"] = f"{r['until']}-12-31"
        if r["sort"] == "new":
            q["first_air_date.lte"] = today
        d = tmdb("/discover/tv", **q) or {}
        top = [f"{x['name']} ({(x.get('first_air_date') or '')[:4]}, {'/'.join(x.get('origin_country', []))})" for x in d.get("results", [])[:10]]
        md.append(f"- **{title}** — {d.get('total_results', 0)} results\n  " + "; ".join(top))
    md.append("")
open(f"{OUT}/report.md", "w").write("\n".join(md))
