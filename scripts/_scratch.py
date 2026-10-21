import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
out = []
tally = collections.Counter()
for page in (1, 2):
    for r in (tmdb("/discover/tv", with_watch_providers="2235", watch_region="TR", sort_by="popularity.desc", page=page) or {}).get("results", []):
        d = tmdb(f"/tv/{r['id']}") or {}
        for n in d.get("networks", []):
            tally[f"{n['id']}:{n['name']}"] += 1
out.append("TABII NETWORKS " + str(tally.most_common(10)))
def disc(kind, **p):
    d = tmdb(f"/discover/{kind}", **p) or {}
    return d.get("total_results", 0), [r.get("name") or r.get("title") for r in d.get("results", [])[:15]]
for name, net in (("exxen", "4405"), ("gain", "4409"), ("blutv+max", "1747|6783|8304"), ("puhutv", "1925")):
    for g in (None, "35", "18", "80|9648"):
        p = dict(with_networks=net, sort_by="popularity.desc")
        if g: p["with_genres"] = g
        if name == "blutv+max": p["with_origin_country"] = "TR"
        n, t = disc("tv", **p)
        out.append(f"{name} genre={g} total={n} | " + " | ".join(t))
for name, prov in (("exxen", "1791"), ("tabii", "2235"), ("hbomax", "1899")):
    n, t = disc("movie", with_watch_providers=prov, watch_region="TR", with_origin_country="TR", sort_by="popularity.desc")
    out.append(f"MOVIES {name} TR total={n} | " + " | ".join(t))
    n, t = disc("tv", with_watch_providers=prov, watch_region="TR", with_origin_country="TR", sort_by="popularity.desc")
    out.append(f"TVPROV {name} TR total={n} | " + " | ".join(t))
for net in ("6", "16", "2", "19", "47", "4", "26"):
    n, t = disc("tv", with_networks=net, with_keywords="193171", without_genres="16", sort_by="vote_count.desc")
    out.append(f"SITCOM net {net} total={n} | " + " | ".join(t[:10]))
for a, b in (("1980", "1989"), ("1990", "1999"), ("2000", "2009"), ("2010", "2019"), ("2020", "2029")):
    n, t = disc("tv", with_keywords="193171", without_genres="16", with_original_language="en", **{"first_air_date.gte": a + "-01-01", "first_air_date.lte": b + "-12-31"}, sort_by="vote_count.desc")
    out.append(f"SITCOM {a}s total={n} | " + " | ".join(t[:10]))
for kw in ("210605", "11800"):
    n, t = disc("tv", with_keywords=kw, without_genres="16", with_original_language="en", sort_by="vote_count.desc")
    out.append(f"KW {kw} total={n} | " + " | ".join(t[:12]))
n, t = disc("tv", with_keywords="193171", without_genres="16", with_origin_country="GB", sort_by="vote_count.desc")
out.append(f"SITCOM GB total={n} | " + " | ".join(t[:12]))
open("refs/q/out.txt", "w").write("\n".join(out))
