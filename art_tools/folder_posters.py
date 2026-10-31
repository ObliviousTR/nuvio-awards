"""Posters for a folder's hero wall, from the folder's own sources (Ozzy, 31 Oct 2026): TMDB discover/network results
(fetched by the scratch workflow into rows.json, best known first) and the repo's own catalogs (library/catalog).
Sources are interleaved so every rail of the folder shows on the wall; franchises appear once."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _key(t):
    return " ".join(re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).split()[:2])


def catalog(cid):
    for kind in ("movie", "series"):
        p = os.path.join(ROOT, "library", "catalog", kind, f"{cid}.json")
        if os.path.exists(p):
            ms = json.load(open(p, encoding="utf-8")).get("metas", [])
            return [{"title": m.get("name"), "poster": m.get("poster"), "votes": 0} for m in ms if m.get("poster")]
    return []


SKIP = {"A Serbian Film", "365 Days", "Ali G: Who Iz I?", "Law & Order: Special Victims Unit", "Depp V Heard",
        "Livestream from Hell", "Mums Make Porn", "High School DxD", "Super Dragon Ball Heroes"}


def posters(rows_json, sources, row, folder, n=28, used=()):
    lists = []
    fetched = {l["source"]: l["items"] for l in rows_json.get(row, {}).get(folder, [])}
    for s in sources:
        if s.get("tmdbSourceType") in ("DISCOVER", "NETWORK"):
            items = sorted(fetched.get(s["title"], []), key=lambda x: -x["votes"])
            lists.append([dict(x, ref=f"tmdb:{x['poster']}") for x in items])
        elif s.get("catalogId"):
            lists.append([dict(x, ref=x["poster"] if x["poster"].startswith("tmdb:") else f"url:{x['poster']}")
                          for x in catalog(s["catalogId"])])
    lists = [[x for x in l if x["title"] not in SKIP] for l in lists]
    out, seen = [], set(used)

    def fill(ls, upto):
        idx = [0] * len(ls)
        while len(out) < upto and any(idx[j] < len(l) for j, l in enumerate(ls)):
            for j, l in enumerate(ls):
                while idx[j] < len(l):
                    x = l[idx[j]]
                    idx[j] += 1
                    k = _key(x["title"])
                    if k and k not in seen:
                        seen.add(k)
                        out.append(x)
                        break
                if len(out) >= upto:
                    break
    # the best known (TMDB, by votes) first, so the posters in view are titles people recognise; then all sources
    fill([l for l in lists if l and l[0].get("votes")], min(n, 14))
    fill(lists, n)
    return out
