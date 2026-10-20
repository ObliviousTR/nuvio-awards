"""Temporary: preview Nuvio native rails (count + top titles) for a builder module."""
import datetime as dt, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "_nuvio"))
from spotlight import tmdb
import build_studios as B

OUT = "refs/preview"
os.makedirs(OUT, exist_ok=True)
F = [("withCompanies", "with_companies"), ("withNetworks", "with_networks"), ("withGenres", "with_genres"),
     ("withoutGenres", "without_genres"), ("voteCountGte", "vote_count.gte"), ("withOriginalLanguage", "with_original_language"),
     ("withOriginCountry", "with_origin_country"), ("withKeywords", "with_keywords"), ("withoutKeywords", "without_keywords")]
today = dt.date.today().isoformat()
md = []
for title, art, comp, toon, series, vp, vt in B.STUDIOS:
    md.append(f"## {title}")
    for s in B.rails(title, comp, toon, series, vp, vt):
        kind = "tv" if s["mediaType"] == "TV" else "movie"
        q = {"sort_by": s["sortBy"]}
        for a, b in F:
            if (s["filters"] or {}).get(a) not in (None, ""):
                q[b] = s["filters"][a]
        if "date" in s["sortBy"]:
            q["first_air_date.lte" if kind == "tv" else "primary_release_date.lte"] = today
        d = tmdb(f"/discover/{kind}", **q) or {}
        top = [f"{x.get('title') or x.get('name')} ({(x.get('release_date') or x.get('first_air_date') or '')[:4]})" for x in d.get("results", [])[:8]]
        md.append(f"- **{s['title']}** — {d.get('total_results', 0)}: " + "; ".join(top))
    md.append("")
open(f"{OUT}/report.md", "w").write("\n".join(md))
