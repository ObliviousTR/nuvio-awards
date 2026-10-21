import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
out = []
for n in (4405, 4409, 6854, 869, 1747, 8304):
    d = tmdb(f"/network/{n}") or {}
    out.append(f"NET {n} | {d.get('name')} | logo {d.get('logo_path')} | {d.get('origin_country')}")
    for sort in ("popularity.desc", "first_air_date.desc", "vote_average.desc"):
        r = tmdb("/discover/tv", with_networks=n, sort_by=sort, without_genres="10763|10767|10766",
                 **({"vote_count.gte": 3} if sort == "vote_average.desc" else {})) or {}
        out.append(f"   {sort} total={r.get('total_results')} | " + " | ".join(
            f"{x['name']} ({(x.get('first_air_date') or '')[:4]})" for x in r.get("results", [])[:12]))
open("refs/q/out.txt", "w").write("\n".join(out))
