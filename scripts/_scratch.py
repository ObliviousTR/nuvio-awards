import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
out = []
for c in (6125, 3, 2):
    d = tmdb(f"/company/{c}") or {}
    out.append(f"CO {c} | {d.get('name')} | logo {d.get('logo_path')}")
    for vc, sort in ((25, "primary_release_date.desc"), (50, "popularity.desc"), (500, "vote_average.desc")):
        r = tmdb("/discover/movie", with_companies=c, without_genres="99", sort_by=sort, **{"vote_count.gte": vc}) or {}
        out.append(f"   vc{vc} {sort} total={r.get('total_results')} | " + " | ".join(
            f"{x['title']} ({(x.get('release_date') or '')[:4]})" for x in r.get("results", [])[:12]))
open("refs/q/out.txt", "w").write("\n".join(out))
