import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
NETS = [("HBO", "49"), ("FX", "88"), ("AMC", "174"), ("Showtime", "67"), ("BBC", "4|332|3|100"), ("ITV", "9"),
        ("Channel 4", "26"), ("U&Dave", "388"), ("Sky Atlantic", "1063"), ("TV Tokyo", "98"), ("Fuji/MBS", "1|94"),
        ("Adult Swim", "80"), ("Comedy Central", "47"), ("Syfy", "77"), ("Cartoon Network", "56"), ("Discovery", "64"),
        ("NatGeo", "43"), ("History", "65"), ("Food Network", "143"), ("USA", "30"), ("NBC", "6"), ("FOX", "19"),
        ("ABC", "2"), ("CBS", "16")]
G = [("drama", "18"), ("comedy", "35"), ("crime", "80"), ("mystery", "9648"), ("scifi", "10765"), ("action", "10759"),
     ("docs", "99"), ("reality", "10764"), ("anim", "16"), ("kids", "10762"), ("war", "10768"), ("western", "37")]
out = []
def disc(**p):
    d = tmdb("/discover/tv", without_genres="10763|10767|10766", **p) or {}
    return d.get("total_results", 0), [r["name"] for r in d.get("results", [])[:6]]
for name, net in NETS:
    tot, _ = disc(with_networks=net, **{"vote_count.gte": 5})
    line = [f"{name} total(v5)={tot}"]
    for g, gid in G:
        n, t = disc(with_networks=net, with_genres=gid, sort_by="vote_count.desc", **{"vote_count.gte": 5})
        if n >= 8:
            line.append(f"   {g}={n}: " + ", ".join(t))
    out += line
open("refs/q/out.txt", "w").write("\n".join(out))
