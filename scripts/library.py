"""Build the Nuvio Library addon (library/manifest.json, library/catalog/) from TMDB, weekly.

Rows it serves: Film Collections & Universes (universes, single franchises, Kaptain's genre collection folders),
Iconic Actors, Legendary Directors. Definitions: library/definitions.json.

Keeping franchises current
  1. TMDB collections: new films TMDB adds to a collection appear on the next run.
  2. Discovery: for each universe / franchise, TMDB is searched for new titles with three signals:
     kw (the franchise's TMDB keywords), co (its production companies), title (its title pattern).
     strong_keyword franchises (MCU) take a keyword hit alone; the rest need title + (kw or co).
     Those are added automatically (library/auto.json, with the reason). A title with one signal only becomes a
     candidate, listed in the weekly issue; move its key ("movie:123" / "tv:456") into approved.json or
     rejected.json (per franchise id). Rejected titles are never suggested again.
  3. People: filmographies are rebuilt from TMDB credits every run; unreleased titles wait for their date.
Rails only exist when they have titles. Unreleased titles are kept but hidden until released.
usage: python3 scripts/library.py [--summary path]   (needs TMDB_API_KEY)
"""
import argparse, datetime as dt, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight as S
from spotlight import tmdb, norm, find_keywords

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
L = lambda *p: os.path.join(LIB, *p)
TODAY = dt.date.today()
NOISE_TV = {99, 10763, 10764, 10767}


def jload(name, default):
    p = L(name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(name, data):
    json.dump(data, open(L(name), "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)


RESOLVED = {}


def resolve(kind, spec):
    """'Title (YYYY)' -> TMDB result dict (cached by id)."""
    key = f"{kind}:{spec}"
    if key in RESOLVED:
        rid = RESOLVED[key]
        return tmdb(f"/{kind}/{rid}") if rid else None
    m = re.match(r"^(.*?)\s*\((\d{4})\)$", spec)
    title, year = (m.group(1), int(m.group(2))) if m else (spec, None)
    params = {"query": title}
    if year:
        params["primary_release_year" if kind == "movie" else "first_air_date_year"] = year
    res = (tmdb(f"/search/{kind}", **params) or {}).get("results", [])
    if not res and year:
        res = (tmdb(f"/search/{kind}", query=title) or {}).get("results", [])
    exact = [r for r in res if norm(r.get("title") or r.get("name")) == norm(title)]
    hit = (exact or res or [None])[0]
    RESOLVED[key] = hit["id"] if hit else None
    return tmdb(f"/{kind}/{hit['id']}") if hit else None


def genres_of(r):
    return set(r.get("genre_ids") or [g["id"] for g in r.get("genres", [])])


def date_of(r):
    return r.get("release_date") or r.get("first_air_date") or ""


def title_of(r):
    return r.get("title") or r.get("name") or ""


def collection_parts(cid):
    d = tmdb(f"/collection/{cid}") or {}
    return d.get("name"), [dict(p, _kind="movie") for p in d.get("parts", [])]


def released(r):
    d = date_of(r)
    return bool(d) and d <= TODAY.isoformat()


# ---------------------------------------------------------------- discovery
def discover_candidates(f, members):
    """{key: (result, signals)} for titles not yet in the franchise."""
    found = {}

    def note(kind, r, sig):
        k = f"{kind}:{r['id']}"
        if k in members:
            return
        rr, sigs = found.setdefault(k, (dict(r, _kind=kind), set()))
        sigs.add(sig)

    kw = "|".join(i for n in f.get("keywords", []) for i in find_keywords([n]).split("|") if i)
    for kind in ("movie", "tv"):
        if kw:
            for page in (1, 2, 3):
                d = tmdb(f"/discover/{kind}", with_keywords=kw, sort_by="popularity.desc", page=page,
                         **{"vote_count.gte": 5 if kind == "movie" else 2}) or {}
                for r in d.get("results", []):
                    note(kind, r, "kw")
                if page >= d.get("total_pages", 0):
                    break
        comp = "|".join(map(str, f.get("companies", [])))
        if comp:
            for page in (1, 2):
                d = tmdb(f"/discover/{kind}", with_companies=comp, sort_by="popularity.desc", page=page,
                         **{"vote_count.gte": 5 if kind == "movie" else 2}) or {}
                for r in d.get("results", []):
                    note(kind, r, "co")
                if page >= d.get("total_pages", 0):
                    break
        for term in f.get("search", []):
            for r in (tmdb(f"/search/{kind}", query=term) or {}).get("results", []):
                note(kind, r, "search")
    pat = re.compile(f.get("pattern") or r"(?!)", re.I)
    out = {}
    for k, (r, sigs) in found.items():
        if pat.search(title_of(r)) or pat.search(r.get("original_title") or r.get("original_name") or ""):
            sigs.add("title")
        sigs.discard("search")
        if not sigs or genres_of(r) & ({99} if r["_kind"] == "movie" else NOISE_TV):
            continue
        out[k] = (r, sigs)
    return out


def find_col(name, aliases):
    """TMDB collection for a Kaptain collection name: alias id / alias name, then a strict name match."""
    a = aliases.get(name)
    if isinstance(a, int):
        d = tmdb(f"/collection/{a}") or {}
        return {"id": a, "name": d.get("name"), "poster_path": d.get("poster_path")} if d else None
    query = a or name
    bare = lambda x: " ".join(re.sub(r"\b(the|collection|trilogy|saga)\b", "", norm(x)).split())
    want, equal, near = bare(query), {}, {}
    for q in dict.fromkeys([query, re.sub(r"\s*\(.*?\)", "", query), re.sub(r"(?i)\s*collection$", "", query)]):
        for r in (tmdb("/search/collection", query=q) or {}).get("results", []):
            got = bare(r["name"])
            if want and want == got:
                equal[r["id"]] = r
            elif want and (want in got or got in want) and len(got.split()) - len(want.split()) <= 1:
                near[r["id"]] = r
    # several collections can share a name (fan-made duplicates): the oldest TMDB id is the canonical one
    pool = equal or near
    return pool[min(pool)] if pool else None


def is_short(r):
    if r["_kind"] != "movie":
        return False
    d = tmdb(f"/movie/{r['id']}") or {}
    return 0 < (d.get("runtime") or 0) < 40


# ---------------------------------------------------------------- franchises
def build_franchise(f, auto, approved, rejected, log, cands_out):
    fid = f["id"]
    members = {}

    def add(kind, r, why=None):
        if r and f"{kind}:{r['id']}" not in rejected.get(fid, []):
            members.setdefault(f"{kind}:{r['id']}", dict(r, _kind=kind, _why=why))

    groups = f.get("groups") or [dict(title=None, cols=f.get("cols", []), movies=f.get("movies", []))]
    group_members = []
    for g in groups:
        gm = {}
        for cid in g.get("cols", []):
            name, parts = collection_parts(cid)
            for p in parts:
                gm[f"movie:{p['id']}"] = p
        for spec in g.get("movies", []):
            r = resolve("movie", spec)
            if r:
                gm[f"movie:{r['id']}"] = dict(r, _kind="movie")
            else:
                log.append(f"- {f['title']}: film not found: {spec}")
        group_members.append((g.get("title"), gm))
        for k, r in gm.items():
            add("movie", r)
    for spec in f.get("toon_movies", []):
        r = resolve("movie", spec)
        add("movie", r) if r else log.append(f"- {f['title']}: film not found: {spec}")
    for spec in f.get("tv", []) + f.get("toon_tv", []):
        r = resolve("tv", spec)
        add("tv", r) if r else log.append(f"- {f['title']}: series not found: {spec}")
    for key in approved.get(fid, []):
        kind, tid = key.split(":")
        add(kind, tmdb(f"/{kind}/{tid}"), "approved")
    for key, info in auto.get(fid, {}).items():
        kind, tid = key.split(":")
        add(kind, tmdb(f"/{kind}/{tid}"), info.get("why"))
    for t in f.get("exclude_titles", []):
        for k in [k for k, r in members.items() if norm(f"{title_of(r)} ({date_of(r)[:4]})") == norm(t)
                  or norm(title_of(r)) == norm(t)]:
            members.pop(k)

    # discovery
    for k, (r, sigs) in discover_candidates(f, members).items():
        if k in rejected.get(fid, []):
            continue
        if f.get("min_year") and date_of(r)[:4] and int(date_of(r)[:4]) < f["min_year"]:
            continue
        if sigs == {"title"} and f.get("companies"):  # check the title's own production companies
            det = tmdb(f"/{r['_kind']}/{r['id']}") or {}
            if {c["id"] for c in det.get("production_companies", [])} & set(f["companies"]):
                sigs.add("co")
        sure = ("kw" in sigs and f.get("strong_keyword")) or ("title" in sigs and sigs & {"kw", "co"})
        enough_votes = r.get("vote_count", 0) >= (10 if r["_kind"] == "movie" else 5)
        if sure and (not enough_votes or 10762 in genres_of(r)):  # junk extras and pre-school spin-offs
            continue
        if sure:
            if is_short(r):
                continue
            why = "+".join(sorted(sigs))
            auto.setdefault(fid, {})[k] = {"title": f"{title_of(r)} ({date_of(r)[:4]})", "why": why,
                                          "added": TODAY.isoformat()}
            members[k] = dict(r, _why=why)
            log.append(f"- {f['title']}: added {title_of(r)} ({date_of(r)[:4]}) [{why}]")
        elif "title" in sigs and (r.get("vote_count", 0) >= 30 or r.get("popularity", 0) >= 5):
            cands_out.append((fid, f["title"], k, f"{title_of(r)} ({date_of(r)[:4]})", "+".join(sorted(sigs))))

    # rails
    def toon(r):
        return 16 in genres_of(r)

    live_m = [r for r in members.values() if r["_kind"] == "movie" and (not toon(r) or f.get("toon_in_main"))
              and 99 not in genres_of(r)]
    live_t = [r for r in members.values() if r["_kind"] == "tv" and not toon(r) and not genres_of(r) & NOISE_TV]
    toon_m = [] if f.get("toon_in_main") else [r for r in members.values() if r["_kind"] == "movie" and toon(r)]
    toon_t = [r for r in members.values() if r["_kind"] == "tv" and toon(r)]
    rails = []
    order = lambda xs: sorted([x for x in xs if released(x)], key=date_of)
    if f.get("groups"):
        for gtitle, gm in group_members:
            rails.append((gtitle, "movie", order([members[k] for k in gm if k in members])))
    else:
        rails.append(("Films", "movie", order(live_m)))
    rails += [("Series", "series", order(live_t)), ("Animated Films", "movie", order(toon_m)),
              ("Animated Series", "series", order(toon_t))]
    return rails


# ---------------------------------------------------------------- output
CATALOGS = []
WRITTEN = {}


def write(cid, typ, name, results):
    if cid in WRITTEN:  # the same collection can sit in two genre folders
        return WRITTEN[cid]
    kind = "tv" if typ == "series" else "movie"
    items = S.rows(kind, results, limit=400)
    if not items:
        return None
    os.makedirs(L("catalog", typ), exist_ok=True)
    json.dump({"metas": [S.meta(x, typ) for x in items]}, open(L("catalog", typ, f"{cid}.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    CATALOGS.append({"type": typ, "id": cid, "name": name})
    WRITTEN[cid] = {"id": cid, "type": typ, "name": name, "count": len(items), "titles": [x["name"] for x in items]}
    return WRITTEN[cid]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", help="write a Turkish summary of new additions / candidates here")
    args = ap.parse_args()
    global RESOLVED
    defs = jload("definitions.json", {})
    RESOLVED = jload("resolved.json", {})
    auto, approved, rejected = jload("auto.json", {}), jload("approved.json", {}), jload("rejected.json", {})
    S.IMDB = S.ImdbCache()
    index = {"franchises": [], "genre_folders": [], "anime_collections": [], "actors": [], "directors": []}
    log, cands = [], []
    before = {k: set(v) for k, v in auto.items()}

    for f in defs["franchises"]:
        rails = build_franchise(f, auto, approved, rejected, log, cands)
        entry = {"id": f["id"], "title": f["title"], "kind": f["kind"], "rails": []}
        poster = None
        if f.get("cols") or f.get("groups"):
            cid = (f.get("cols") or f["groups"][0]["cols"])[0]
            poster = (tmdb(f"/collection/{cid}") or {}).get("poster_path")
        entry["poster"] = poster
        for rname, typ, results in rails:
            c = write(f"lib-{f['id']}-{slug(rname)}", typ, f"{f['title']} · {rname}", results)
            if c:
                entry["rails"].append(c)
        index["franchises"].append(entry)

    for folder, names in list(defs["genre_folders"].items()) + [("Anime Film Collections", defs["anime_collections"])]:
        toon_ok = folder in ("Family & Animation Collections", "Anime Film Collections")
        fentry = {"title": folder, "rails": []}
        for n in names:
            alias = defs.get("collection_aliases", {}).get(n)
            if isinstance(alias, list):  # no TMDB collection: the films are listed by hand
                films = [r for r in (resolve("movie", spec) for spec in alias) if r]
                films = sorted([dict(r, _kind="movie") for r in films if released(r)], key=date_of)
                c = write(f"lib-list-{slug(n)}", "movie", re.sub(r"(?i)\s*(collection|trilogy)$", "", n).strip(), films)
                if c:
                    c["poster"] = films[0].get("poster_path") if films else None
                    fentry["rails"].append(c)
                continue
            col = find_col(n, defs.get("collection_aliases", {}))
            if not col:
                log.append(f"- {folder}: collection not found: {n}"); continue
            name, parts = collection_parts(col["id"])
            parts = sorted([p for p in parts if released(p) and (toon_ok or 16 not in genres_of(p))], key=date_of)
            label = re.sub(r"\s*Collection$", "", n).strip()
            c = write(f"lib-col-{col['id']}", "movie", label, parts)
            if c:
                c["poster"] = col.get("poster_path")
                fentry["rails"].append(c)
        (index["anime_collections"] if folder == "Anime Film Collections" else index["genre_folders"]).append(fentry)

    for p in defs["people"]["actors"]:
        try:
            m, s, a, notes = S.person_card(p, TODAY, False)
        except LookupError as e:
            log.append(f"- actor {p['name']}: {e}"); continue
        pe = {"name": p["name"], "portrait": a.get("portrait"), "rails": []}
        base = f"lib-a-{slug(p['name'])}"
        movies = [dict(id=x["tmdb"], title=x["name"], release_date=x["date"], vote_count=x["votes"],
                       vote_average=x["rating"]) for x in m]
        top = sorted([x for x in movies if x["vote_count"] >= 200], key=lambda x: -x["vote_average"])
        latest = sorted(movies, key=lambda x: x["release_date"], reverse=True)
        for rname, typ, res in (("Essential Films", "movie", movies), ("Top Rated", "movie", top),
                                ("Latest", "movie", latest)):
            c = write(f"{base}-{slug(rname)}", typ, f"{p['name']} · {rname}", res)
            if c: pe["rails"].append(c)
        if len(s) >= 2:
            c = write(f"{base}-series", "series", f"{p['name']} · Series",
                      [dict(id=x["tmdb"], name=x["name"], first_air_date=x["date"]) for x in s])
            if c: pe["rails"].append(c)
        index["actors"].append(pe)

    for p in defs["people"]["directors"]:
        ms, ss, portrait = {}, {}, None
        for member in p.get("members", [p["name"]]):
            try:
                m, s, a, notes = S.person_card({"name": member}, TODAY, True, toon_ok=p.get("toon_ok", False))
            except LookupError as e:
                log.append(f"- director {member}: {e}"); continue
            portrait = portrait or a.get("portrait")
            for x in m: ms[x["tmdb"]] = x
            for x in s: ss[x["tmdb"]] = x
        pe = {"name": p["name"], "portrait": portrait, "rails": []}
        base = f"lib-d-{slug(p['name'])}"
        films = [dict(id=x["tmdb"], title=x["name"], release_date=x["date"], vote_count=x["votes"],
                      vote_average=x["rating"]) for x in ms.values()]
        recent = sorted(films, key=lambda x: x["release_date"], reverse=True)
        if len(films) >= 10:
            best = sorted([x for x in films if x["vote_count"] >= 100], key=lambda x: -x["vote_average"])
            rails = (("Best Of", best), ("Recent", recent))
        else:
            rails = (("Filmography", recent),)
        for rname, res in rails:
            c = write(f"{base}-{slug(rname)}", "movie", f"{p['name']} · {rname}", res)
            if c: pe["rails"].append(c)
        if len(ss) >= 2:
            c = write(f"{base}-series", "series", f"{p['name']} · Series",
                      [dict(id=x["tmdb"], name=x["name"], first_air_date=x["date"]) for x in ss.values()])
            if c: pe["rails"].append(c)
        index["directors"].append(pe)

    manifest = {"id": "community.oblivioustr.nuvio-library", "version": f"1.0.{TODAY.strftime('%Y%m%d')}",
                "name": "Nuvio Library",
                "description": "Film universes & franchises, collection folders, iconic actors and legendary directors, rebuilt weekly from TMDB.",
                "resources": ["catalog"], "types": ["movie", "series"], "idPrefixes": ["tt"], "catalogs": CATALOGS,
                "behaviorHints": {"configurable": False, "configurationRequired": False}}
    json.dump(manifest, open(L("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    jsave("index.json", index)
    jsave("auto.json", auto)
    jsave("resolved.json", RESOLVED)
    jsave("candidates.json", {f"{fid}": [{"key": k, "title": t, "signals": sg} for f2, _, k, t, sg in cands if f2 == fid]
                              for fid in sorted({c[0] for c in cands})})
    S.IMDB.save()

    md = [f"# Library report — {TODAY.isoformat()}", "", f"{len(CATALOGS)} catalogs", ""]
    for e in index["franchises"]:
        md.append(f"## {e['title']} ({e['kind']})")
        md += [f"- **{c['name'].split(' · ')[-1]}** ({c['count']}): " + ", ".join(c["titles"][:60]) for c in e["rails"]]
        md.append("")
    md.append("## Genre collection folders")
    for g in index["genre_folders"] + index["anime_collections"]:
        md.append(f"- **{g['title']}**: {len(g['rails'])} rails — " + ", ".join(f"{c['name']} ({c['count']})" for c in g["rails"]))
    md.append("\n## People")
    for grp in ("actors", "directors"):
        for pe in index[grp]:
            md.append(f"- {pe['name']}: " + "; ".join(f"{c['name'].split(' · ')[-1]} {c['count']}" for c in pe["rails"]))
    md += ["", "## Candidates (one signal — approve or reject)"] + \
          [f"- {t} → {title} `{k}` [{sg}]" for f2, t, k, title, sg in cands] + ["", "## Log"] + log
    open(L("REPORT.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    seen = set(jload("seen_candidates.json", []))
    fresh = [c for c in cands if f"{c[0]}|{c[2]}" not in seen]
    jsave("seen_candidates.json", sorted(seen | {f"{c[0]}|{c[2]}" for c in cands}))
    if args.summary:
        new = [(fid, k, v) for fid, d in auto.items() for k, v in d.items() if k not in before.get(fid, set())]
        cands = fresh  # the issue lists only candidates it has not reported before (candidates.json has all)
        if new or cands:
            out = ["Kütüphane (Film Collections, oyuncular, yönetmenler) haftalık güncellemesi.", ""]
            if new:
                out += ["### Otomatik eklenenler"] + [f"- **{fid}**: {v['title']} (`{k}`, işaretler: {v['why']})" for fid, k, v in new] + [""]
            if cands:
                out += ["### Onay bekleyen adaylar",
                        "Eklemek için `library/approved.json`, istemezsen `library/rejected.json` içine franchise id'si altında ekle:", ""]
                out += [f"- **{fid}** ({t}): {title} → `{k}` [{sg}]" for fid, t, k, title, sg in cands]
            open(args.summary, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(md[:5]))


if __name__ == "__main__":
    main()
