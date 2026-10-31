import os, json, urllib.request, urllib.parse, datetime as dt
# Streaming Services heroes: each platform's best-known titles (poster paths), for the poster walls.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]


def get(p, **q):
    q["api_key"] = K
    try:
        return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}",
                                                 timeout=60).read())
    except Exception as e:
        print("ERR", p, q.get("with_networks") or q.get("with_watch_providers"), e)
        return {}


# platform: (region, provider names to match, TV network ids for originals)
P = {
    "Netflix": ("US", ["Netflix"], [213]),
    "Apple TV+": ("US", ["Apple TV", "Apple TV+"], [2552]),
    "HBO Max": ("US", ["HBO Max", "Max"], [49, 3186]),
    "Disney+": ("US", ["Disney Plus", "Disney+"], [2739]),
    "Prime Video": ("US", ["Amazon Prime Video"], [1024]),
    "Exxen": ("TR", ["Exxen"], []),
    "GAİN": ("TR", ["Gain", "GAİN", "GAIN"], []),
    "Crunchyroll": ("US", ["Crunchyroll"], [1112]),
    "Mubi": ("US", ["MUBI", "Mubi"], []),
    "Discovery+": ("US", ["Discovery+", "discovery+"], [4353]),
    "Hulu": ("US", ["Hulu"], [453]),
    "Paramount+": ("US", ["Paramount Plus", "Paramount+"], [4330]),
    "Shudder": ("US", ["Shudder"], [1830]),
    "tabii": ("TR", ["tabii", "Tabii"], []),
}
prov = {}
for reg in ("US", "TR"):
    for kind in ("movie", "tv"):
        for r in get(f"/watch/providers/{kind}", watch_region=reg).get("results", []):
            prov.setdefault(reg, {}).setdefault(r["provider_name"].lower(), r["provider_id"])
res = {"_providers": {k: sorted(v.items())[:400] for k, v in prov.items()}}
for name, (reg, names, nets) in P.items():
    ids = sorted({prov.get(reg, {}).get(n.lower()) for n in names} - {None})
    items, seen = [], set()

    def add(kind, rs):
        for r in rs:
            if r.get("poster_path") and (kind, r["id"]) not in seen:
                seen.add((kind, r["id"]))
                items.append({"kind": kind, "id": r["id"], "title": r.get("title") or r.get("name"),
                              "poster": r["poster_path"], "pop": r.get("popularity", 0),
                              "votes": r.get("vote_count", 0)})
    vmin = 3 if reg == "TR" else 150
    for n in nets:
        print(name, "network", n, get(f"/network/{n}").get("name"))
        for page in (1, 2):
            add("tv", get("/discover/tv", with_networks=n, sort_by="popularity.desc", page=page,
                          **{"vote_count.gte": vmin}).get("results", []))
    if ids:
        pid = "|".join(map(str, ids))
        for kind in ("tv", "movie"):
            for page in (1, 2):
                add(kind, get(f"/discover/{kind}", with_watch_providers=pid, watch_region=reg,
                              sort_by="popularity.desc", page=page, **{"vote_count.gte": vmin}).get("results", []))
    res[name] = {"providers": ids, "items": items}
    print(name, ids, len(items), [i["title"] for i in items[:12]])
json.dump(res, open(f"{OUT}/streaming.json", "w"), indent=1, ensure_ascii=False)
