import json, os, urllib.request
K = os.environ["TMDB_API_KEY"].strip()
os.makedirs("refs/check", exist_ok=True)
out = []
for p in ("tv/1664", "tv/138503", "movie/557", "movie/558", "movie/1930", "movie/102382", "movie/315635", "movie/324857", "movie/634649", "movie/569094"):
    d = json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?api_key={K}", timeout=60).read())
    out.append(f"{p}\t{d.get('name') or d.get('title')}\t{(d.get('first_air_date') or d.get('release_date') or '')[:4]}")
open("refs/check/ids.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
