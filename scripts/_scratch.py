"""When was TMDB tv/339300 (the empty 'Karun Hazinesi' entry) created and edited? And 320754?"""
import json, os, urllib.parse, urllib.request
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/trproxy"; os.makedirs(OUT, exist_ok=True)
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
rep = []
import datetime
end = datetime.date.today()
for tid in (339300, 320754):
    times = []
    for back in range(0, 98, 14):
        e = end - datetime.timedelta(days=back); s = e - datetime.timedelta(days=13)
        ch = t(f"tv/{tid}/changes", start_date=s.isoformat(), end_date=e.isoformat())
        for c in ch.get("changes", []):
            for it in c.get("items", []):
                times.append((it.get("time"), c.get("key"), it.get("action")))
    times.sort()
    rep.append(f"tv/{tid}: {len(times)} changes in the last 98 days; first {times[:4]}; last {times[-3:]}")
open(f"{OUT}/organize3.txt", "w").write("\n".join(rep).replace(K, "***") + "\n"); print("\n".join(rep))
