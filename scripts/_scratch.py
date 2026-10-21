import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
out = []
for n in (4, 332, 3, 100, 1155, 3990, 2484, 493, 1361):
    d = tmdb(f"/network/{n}") or {}
    out.append(f"NET {n} | {d.get('name')} | {d.get('origin_country')} | logo {d.get('logo_path')}")
for q in ["Cunk on Britain", "Cunk on Earth", "Cunk on Life", "Cunk on Shakespeare", "Cunk on Christmas", "Philomena Cunk",
          "Fleabag", "Ghosts", "The Thick of It", "Detectorists", "Inside No. 9", "This Country", "W1A", "Gavin & Stacey"]:
    for r in (tmdb("/search/tv", query=q) or {}).get("results", [])[:1]:
        d = tmdb(f"/tv/{r['id']}") or {}
        kw = tmdb(f"/tv/{r['id']}/keywords") or {}
        out.append(f"SHOW {q} -> {d.get('name')} ({(d.get('first_air_date') or '')[:4]}) nets: " +
                   "; ".join(f"{n['id']}:{n['name']}" for n in d.get("networks", [])) + " | genres " +
                   ",".join(str(g["id"]) for g in d.get("genres", [])) + " | kw " + ", ".join(k["name"] for k in kw.get("results", [])[:12]))
for q in ["Cunk"]:
    for r in (tmdb("/search/movie", query=q) or {}).get("results", [])[:6]:
        out.append(f"MOVIE {r['title']} ({(r.get('release_date') or '')[:4]}) id {r['id']}")
for kind in ("tv", "movie"):
    for p in (tmdb(f"/watch/providers/{kind}", watch_region="GB") or {}).get("results", []):
        if "BBC" in p["provider_name"] or "ITV" in p["provider_name"] or "Channel 4" in p["provider_name"] or "Sky" in p["provider_name"] or "NOW" in p["provider_name"]:
            out.append(f"PROVIDER GB {kind} | {p['provider_id']} | {p['provider_name']}")
def disc(kind, **p):
    d = tmdb(f"/discover/{kind}", **p) or {}
    return d.get("total_results", 0), [f"{r.get('name') or r.get('title')} ({(r.get('first_air_date') or r.get('release_date') or '')[:4]})" for r in d.get("results", [])[:20]]
for label, p in (("iplayer tv pop", dict(with_watch_providers="38", watch_region="GB", sort_by="popularity.desc", without_genres="10763|10767|10766")),
                 ("iplayer tv pop en", dict(with_watch_providers="38", watch_region="GB", sort_by="popularity.desc", with_original_language="en", without_genres="10763|10767|10766|16", **{"vote_count.gte": 10})),
                 ("iplayer tv top", dict(with_watch_providers="38", watch_region="GB", sort_by="vote_average.desc", without_genres="10763|10767|10766|16", **{"vote_count.gte": 100})),
                 ("iplayer tv comedy", dict(with_watch_providers="38", watch_region="GB", sort_by="vote_count.desc", with_genres="35", without_genres="16|10763|10767|10766")),
                 ("iplayer tv drama", dict(with_watch_providers="38", watch_region="GB", sort_by="popularity.desc", with_genres="18", without_genres="16|10763|10767|10766", **{"vote_count.gte": 10})),
                 ("iplayer tv crime", dict(with_watch_providers="38", watch_region="GB", sort_by="popularity.desc", with_genres="80|9648", without_genres="16|10763|10767|10766", **{"vote_count.gte": 10})),
                 ("iplayer tv docs", dict(with_watch_providers="38", watch_region="GB", sort_by="popularity.desc", with_genres="99", **{"vote_count.gte": 5})),
                 ("iplayer movie pop", dict(with_watch_providers="38", watch_region="GB", sort_by="popularity.desc", **{"vote_count.gte": 50})),
                 ("bbc nets sitcom", dict(with_networks="4|332|3|100", with_keywords="193171", without_genres="16", sort_by="vote_count.desc")),
                 ("bbc nets mockumentary", dict(with_networks="4|332|3|100", with_keywords="11800", sort_by="vote_count.desc")),
                 ("bbc nets comedy", dict(with_networks="4|332|3|100", with_genres="35", without_genres="16|10763|10767|10766", sort_by="vote_count.desc"))):
    n, t = disc("movie" if "movie" in label else "tv", **p)
    out.append(f"{label} total={n} | " + " | ".join(t))
open("refs/q/out.txt", "w").write("\n".join(out))
