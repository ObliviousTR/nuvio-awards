import os, json, urllib.request, urllib.parse
# Streaming Services heroes: each platform's OWN originals (TV by the platform's network, films by its studio),
# best known first; plus discovery+ logo options.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]


def get(p, **q):
    q["api_key"] = K
    try:
        return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}",
                                                 timeout=60).read())
    except Exception as e:
        print("ERR", p, e)
        return {}


def nets_of(title):
    r = get("/search/tv", query=title).get("results", [])
    if not r:
        return []
    return [(n["id"], n["name"]) for n in get(f"/tv/{r[0]['id']}").get("networks", [])]


def companies(name):
    return [(c["id"], c["name"]) for c in get("/search/company", query=name).get("results", [])[:6]]


# platform: (network ids, seed original series (their networks are added), studio names for original films)
P = {
    "Netflix": ([213], [], ["Netflix"]),
    "Apple TV+": ([2552], [], ["Apple Original Films", "Apple Studios"]),
    "HBO Max": ([49, 3186], [], ["HBO Films", "HBO Max"]),
    "Disney+": ([2739], [], ["Disney+"]),
    "Prime Video": ([1024], [], ["Amazon Studios", "Amazon MGM Studios"]),
    "Crunchyroll": ([1112], ["Tower of God", "Onyx Equinox"], ["Crunchyroll"]),
    "Mubi": ([], [], ["MUBI"]),
    "Hulu": ([453], ["The Handmaid's Tale", "Only Murders in the Building"], ["Hulu"]),
    "Paramount+": ([4330], ["Tulsa King", "Halo"], ["Paramount+"]),
    "Shudder": ([], ["Creepshow", "The Boulet Brothers' Dragula", "Cursed Films"], ["Shudder"]),
}
res = {}
for name, (nets, seeds, studios) in P.items():
    nets = set(nets)
    for s in seeds:
        ns = nets_of(s)
        print(name, "seed", s, ns)
        nets |= {i for i, n in ns if name.split("+")[0].split()[0].lower() in n.lower()}
    comps = []
    for st in studios:
        cs = companies(st)
        print(name, "studio", st, cs)
        comps += [i for i, n in cs if n.lower() == st.lower()]
    items, seen = [], set()

    def add(kind, rs, src):
        for r in rs:
            if r.get("poster_path") and (kind, r["id"]) not in seen:
                seen.add((kind, r["id"]))
                items.append({"kind": kind, "id": r["id"], "title": r.get("title") or r.get("name"),
                              "poster": r["poster_path"], "votes": r.get("vote_count", 0), "src": src})
    for n in sorted(nets):
        for page in (1, 2, 3):
            add("tv", get("/discover/tv", with_networks=n, sort_by="vote_count.desc", page=page).get("results", []),
                f"net{n}")
    for c in comps:
        for page in (1, 2):
            add("movie", get("/discover/movie", with_companies=c, sort_by="vote_count.desc", page=page)
                .get("results", []), f"co{c}")
    items.sort(key=lambda x: -x["votes"])
    res[name] = {"networks": sorted(nets), "companies": comps, "items": items}
    print(name, sorted(nets), comps, len(items), [i["title"] for i in items[:15]])
res["_discovery_logos"] = {n: [(l["file_path"], l["width"], l["height"], l.get("file_type")) for l in
                               get(f"/network/{n}/images").get("logos", [])] for n in (4353, 64)}
print(res["_discovery_logos"])
json.dump(res, open(f"{OUT}/originals.json", "w"), indent=1, ensure_ascii=False)
