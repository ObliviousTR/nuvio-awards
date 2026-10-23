"""Genre-true rails for the Nuvio Library addon (library/catalog/<type>/gen-*.json), rebuilt every day.

Why: a Nuvio TMDB rail asks TMDB for "every title tagged with the genre". TMDB gives a title several genres, in order
(the first is its main one), so Comedy also lists Pulp Fiction (Thriller, Crime, Comedy), Green Book (Drama, Comedy)
and Evil Dead II (Horror, Comedy). Here each rail runs the same TMDB discover query, then keeps a title only if the
rail's genre leads its genre list - or is preceded only by genres that go with it (Comedy may follow Romance,
Family, Adventure, Action, Fantasy, Animation, Music or Sci-Fi: a rom-com or an action comedy is still a comedy;
after Drama, Crime, Thriller, Horror, War or History it is not).
Rails to build: library/genre_rails.json (written by builder/apply_genre_rails.py from the collection's own rails).
usage: python3 scripts/genre_rails.py   (needs TMDB_API_KEY)
"""
import datetime as dt, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight as S
from spotlight import tmdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
L = lambda *p: os.path.join(LIB, *p)
TODAY = dt.date.today()
LIMIT, PAGES, PAGE = 500, 60, 100   # up to 500 titles a rail, served 100 at a time (Nuvio asks for skip=100, 200...)

# How a title earns a genre rail, from its ordered TMDB genre list (the first is its main genre). Per genre:
#   deny  - genres that, coming before it, mean the title is something else (Comedy after Drama/Horror/Thriller:
#           Green Book, Evil Dead II, Pulp Fiction)
#   allow - genres that may come before it at any depth (an action comedy, a crime comedy is still a comedy)
#   ANY   - a setting / format / audience more than a mood: tagged within the first `top` genres is enough
# First or second, with nothing from `deny` before it: in. Further down: everything before it must be in `allow`.
ANY = "any"
R = lambda deny=(), allow=(), top=None: {"deny": set(deny), "allow": allow if allow == ANY else set(allow), "top": top}
RULES = {
    "movie": {
        35: R(deny={18, 53, 27, 10752, 36}, allow={10749, 10751, 12, 28, 14, 16, 10402, 878, 80, 9648}),      # Comedy
        28: R(deny={27}, allow={12, 80, 53, 878, 14, 10752, 37, 35, 9648, 18}),                               # Action
        12: R(deny={27}, allow={28, 14, 878, 10751, 35, 37, 10752, 36, 18}),                                  # Adventure
        18: R(deny={35, 27, 10751, 16}, allow={36, 10752, 10749, 10402, 80, 99, 53, 9648, 12, 28, 878, 14, 37}),  # Drama
        80: R(deny={27}, allow={18, 53, 28, 9648, 35, 12}),                                                   # Crime
        27: R(deny={35, 10751}, allow={53, 9648, 14, 878, 80, 18, 28}),                                       # Horror
        53: R(deny={35, 10751}, allow={28, 80, 9648, 18, 27, 878, 12, 14}),                                   # Thriller
        9648: R(deny={35, 10751}, allow={53, 80, 18, 27, 14, 878, 12}),                                       # Mystery
        10749: R(deny={27}, allow={35, 18, 10402, 14, 10751, 12, 878}),                                       # Romance
        10751: R(deny={27, 53}, allow={16, 35, 12, 14, 10402, 10749, 878, 28, 18}),                            # Family
        36: R(deny={35}, allow={18, 28, 12, 10752, 53, 80}), 10752: R(deny={35}, allow={18, 28, 12, 36, 53, 80}),  # History, War
        10402: R(allow={99, 18, 35, 10749}),                                                                  # Music
        878: R(allow=ANY, top=3), 14: R(allow=ANY, top=3), 37: R(allow=ANY, top=3),                           # Sci-Fi, Fantasy, Western
        16: R(allow=ANY), 99: R(allow=ANY),                                                                   # Animation, Documentary
    },
    "tv": {
        35: R(deny={18}, allow={10759, 10751, 16, 10765, 10762, 80, 9648}),   # Comedy (Drama allowed for half-hour shows)
        18: R(deny={35}, allow={80, 9648, 10768, 10765, 10759, 37}),          # Drama
        10759: R(allow={10765, 80, 10768, 37, 18, 9648}),                     # Action & Adventure
        9648: R(allow={80, 18, 10765, 10759, 35}),                            # Mystery
        80: R(deny={35}, allow={18, 9648, 10759, 10765}),                     # Crime
        10768: R(allow={18, 10759, 80}), 37: R(allow={18, 10759}),            # War & Politics, Western
        10751: R(allow={16, 35, 10762, 10765, 10759, 18}),                    # Family
        10765: R(allow=ANY, top=3),                                           # Sci-Fi & Fantasy
        16: R(allow=ANY), 99: R(allow=ANY), 10764: R(allow=ANY), 10762: R(allow=ANY),
    },
}
HALF_HOUR = 40   # a series tagged Drama, Comedy whose episodes run up to this long is a comedy (Ted Lasso, The Bear)
MOVIE_G = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama",
           10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery",
           10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"}
TV_G = {10759: "Action & Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama",
        10751: "Family", 10762: "Kids", 9648: "Mystery", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy",
        10766: "Soap", 10767: "Talk", 10768: "War & Politics", 37: "Western"}
KEYMAP = {"voteCountGte": "vote_count.gte", "withGenres": "with_genres", "withoutGenres": "without_genres",
          "withOriginalLanguage": "with_original_language", "withKeywords": "with_keywords",
          "withOriginCountry": "with_origin_country", "withWatchProviders": "with_watch_providers",
          "watchRegion": "watch_region", "withCompanies": "with_companies", "withNetworks": "with_networks",
          "voteAverageGte": "vote_average.gte", "withRuntimeGte": "with_runtime.gte",
          "withoutKeywords": "without_keywords", "voteCountLte": "vote_count.lte"}


class GenreCache:
    """A title's ordered genre list and runtime (TMDB details); kept 30 days."""
    def __init__(self):
        self.path = os.path.join(ROOT, "spotlight", "cache", "genres.json")
        self.d = json.load(open(self.path)) if os.path.exists(self.path) else {}

    def fresh(self, k):
        v = self.d.get(k)
        return v and len(v) == 3 and (TODAY - dt.date.fromisoformat(v[0])).days < 30

    def prefetch(self, kind, ids):
        todo = [i for i in dict.fromkeys(ids) if not self.fresh(f"{kind}:{i}")]
        with ThreadPoolExecutor(8) as ex:
            for i, x in zip(todo, ex.map(lambda i: tmdb(f"/{kind}/{i}") or {}, todo)):
                if x.get("id"):
                    rt = x.get("runtime") or (sorted(x.get("episode_run_time") or [0])[len(x.get("episode_run_time") or [0]) // 2])
                    self.d[f"{kind}:{i}"] = [TODAY.isoformat(), [g["id"] for g in x.get("genres", [])], rt or 0]

    def get(self, kind, i):
        return (self.d.get(f"{kind}:{i}") or [None, []])[1]

    def runtime(self, kind, i):
        v = self.d.get(f"{kind}:{i}") or []
        return v[2] if len(v) > 2 else 0

    def save(self):
        json.dump(self.d, open(self.path, "w"), sort_keys=True, separators=(",", ":"))


OVR = {}   # library/genre_overrides.json: {"movie:35": {"include": [ids], "exclude": [ids]}} - hand decisions per genre


def fits(kind, genres, want, tid=None, runtime=0):
    """want: the rail's with_genres ("35", "28|12" = any of, "16,35" = all of)."""
    allof = "," in want
    targets = [int(x) for x in re.split(r"[|,]", want) if x]
    for t in targets:
        o = OVR.get(f"{kind}:{t}", {})
        if tid in o.get("exclude", []):
            return False
        if tid in o.get("include", []) and (t in genres or not allof):
            return True
    if allof and 16 in targets:   # anime / animation with a genre: animation is the format, the genre just has to be there
        return all(t in genres[:4] for t in targets if t != 16) and 16 in genres
    ok = []
    for t in targets:
        if t not in genres:
            ok.append(False)
            continue
        pos = genres.index(t)
        before = set(genres[:pos]) - set(targets)
        rule = RULES[kind].get(t)
        if rule is None:
            ok.append(pos <= 1)
            continue
        if rule["allow"] == ANY:
            ok.append(rule["top"] is None or pos < rule["top"])
            continue
        deny, allow = set(rule["deny"]), set(rule["allow"])
        if kind == "tv" and t == 35 and 0 < runtime <= HALF_HOUR:
            deny.discard(18)
            allow.add(18)
        if before & deny:
            ok.append(False)
        elif pos <= 1:
            ok.append(True)
        else:
            ok.append(before <= allow)
    return all(ok) if allof else any(ok)


def params_of(r):
    kind = "movie" if r["media"] == "MOVIE" else "tv"
    f = r["filters"]
    q = {KEYMAP[k]: v for k, v in f.items() if k in KEYMAP}
    if f.get("releaseDateGte"):
        q["primary_release_date.gte" if kind == "movie" else "first_air_date.gte"] = f["releaseDateGte"]
    if f.get("releaseDateLte"):
        q["primary_release_date.lte" if kind == "movie" else "first_air_date.lte"] = f["releaseDateLte"]
    if r.get("sort"):
        q["sort_by"] = r["sort"]
    if q.get("with_genres") and q.get("without_genres"):
        want = set(re.split(r"[|,]", q["with_genres"]))
        q["without_genres"] = "|".join(g for g in q["without_genres"].split("|") if g not in want)
    return kind, q


def build(r, G):
    kind, q = params_of(r)
    lim = r.get("limit", LIMIT)
    res, kept, dropped = [], [], []
    for page in range(1, PAGES + 1):
        d = tmdb(f"/discover/{kind}", page=page, include_adult="false", **q) or {}
        batch = d.get("results", [])
        G.prefetch(kind, [x["id"] for x in batch])
        for x in batch:
            if r.get("rule") is False or fits(kind, G.get(kind, x["id"]), r["filters"]["withGenres"], x["id"], G.runtime(kind, x["id"])):
                kept.append(x)
            else:
                dropped.append(x)
        res += batch
        if page >= d.get("total_pages", 0) or len(kept) >= lim * 1.25:
            break
    return kind, S.rows(kind, kept, limit=lim), len(res), dropped


KW = {}


def keyword_ids(names):
    """TMDB keyword ids for keyword names (exact name match)."""
    out = []
    for n in names:
        if n not in KW:
            res = (tmdb("/search/keyword", query=n) or {}).get("results", [])
            KW[n] = next((str(k["id"]) for k in res if k["name"].lower() == n.lower()), None)
        if KW[n]:
            out.append(KW[n])
    return "|".join(out)


def write_pages(typ, cid, items, name=None):
    """Static catalog pages: <cid>.json + <cid>/skip=N.json, or for a Genre choice <cid>/genre=<name>[&skip=N].json."""
    base = L("catalog", typ, cid)
    os.makedirs(base, exist_ok=True)
    for k in range(0, max(len(items), 1), PAGE):
        page = {"metas": [S.meta(x, typ) for x in items[k:k + PAGE]]}
        if name is None:
            paths = [base + ".json", os.path.join(base, "skip=0.json")] if k == 0 else [os.path.join(base, f"skip={k}.json")]
        else:
            paths = [os.path.join(base, f"genre={name}.json")] + ([os.path.join(base, f"genre={name}&skip={k}.json")] if k else [])
            if k:
                paths = [os.path.join(base, f"genre={name}&skip={k}.json")]
        for p in paths:
            json.dump(page, open(p, "w", encoding="utf-8"), ensure_ascii=False)


def build_discover(G, report):
    """Catalogs for Nuvio's Discover screen with a Genre menu of sub-genres and orders (library/discover.json)."""
    if not os.path.exists(L("discover.json")):
        return []
    spec = json.load(open(L("discover.json"), encoding="utf-8"))
    cats = []
    for c in spec["catalogs"]:
        typ = c["type"]
        base = L("catalog", typ, c["id"])
        if os.path.isdir(base):
            for old in os.listdir(base):
                os.remove(os.path.join(base, old))
        labels = []
        for i, o in enumerate(c["options"]):
            f = {**c["base"], "withGenres": c["genre"], **o.get("filters", {})}
            if o.get("kw"):
                ids = keyword_ids(o["kw"])
                if not ids:
                    report.append(f"- {c['id']} / {o['label']}: no keyword found for {o['kw']}")
                    continue
                f["withKeywords"] = ids
            if o.get("released"):
                f["releaseDateLte"] = TODAY.isoformat()
            r = {"media": "MOVIE" if typ == "movie" else "TV", "sort": o.get("sort", "popularity.desc"), "filters": f,
                 "limit": 300, "rule": o.get("rule", True)}
            kind, items, seen, _ = build(r, G)
            if not items:
                report.append(f"- {c['id']} / {o['label']}: empty")
                continue
            if i == 0:
                write_pages(typ, c["id"], items)
            write_pages(typ, c["id"], items, o["label"])
            labels.append(o["label"])
            report.append(f"- {c['name']} ({typ}) / {o['label']}: {len(items)}")
        cats.append({"type": typ, "id": c["id"], "name": c["name"],
                     "extra": [{"name": "genre", "options": labels, "isRequired": False}, {"name": "skip", "isRequired": False}],
                     "genres": labels})
    return cats


def mdb_items(lid, kind):
    """A MDBList list through the API (MDBLIST_API_KEY), as rows with IMDb ids; None if it can't be read."""
    key = os.environ.get("MDBLIST_API_KEY")
    if not key:
        return None
    out, offset = [], 0
    for _ in range(20):
        u = f"https://api.mdblist.com/lists/{lid}/items?limit=1000&offset={offset}&apikey={key}"
        d = None
        for attempt in range(4):   # dynamic lists are built on request and can be slow: wait longer each time
            try:
                import urllib.request, time
                d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "nuvio-awards"}),
                                                      timeout=60 + 60 * attempt).read())
                break
            except Exception as e:
                print(f"mdblist {lid} (try {attempt + 1}): {str(e).replace(key, '<key>')}")
                if "404" in str(e):
                    return None
                time.sleep(10 * (attempt + 1))
        if d is None:
            return None
        batch = d.get("movies" if kind == "movie" else "shows") or []
        out += batch
        if not batch or not (d.get("pagination") or {}).get("has_more"):
            break
        offset += len(d.get("movies") or []) + len(d.get("shows") or [])
    rows = []
    for x in out:
        imdb = x.get("imdb_id")
        if imdb:
            rows.append({"imdb": imdb, "name": x.get("title"), "year": str(x.get("release_year") or ""), "rank": x.get("rank") or 0})
    return rows


def old_rows(typ, cid):
    """The rows of a catalog as last published (all its pages)."""
    base = L("catalog", typ, cid)
    files = [base + ".json"] + ([os.path.join(base, f) for f in sorted(os.listdir(base), key=lambda f: int(re.sub(r"\D", "", f) or 0))
                                 if f.startswith("skip=") and f != "skip=0.json"] if os.path.isdir(base) else [])
    rows = []
    for f in files:
        if os.path.exists(f):
            rows += [{"imdb": m["id"], "name": m["name"], "year": m.get("releaseInfo", ""), "rank": len(rows)}
                     for m in json.load(open(f, encoding="utf-8"))["metas"]]
    return rows


def build_mdb(report):
    """MDBList lists we serve ourselves: folder-only mdb-<id> catalogs + Discover catalogs with one choice per list."""
    if not os.path.exists(L("mdb_lists.json")):
        return [], []
    spec = json.load(open(L("mdb_lists.json"), encoding="utf-8"))
    hidden, opts = [], {cid: [] for cid in spec["discover"]}
    for e in spec["lists"]:
        typ = e["type"]
        cid = f"mdb-{e['id']}"
        rows = mdb_items(e["id"], typ)
        if rows is None:   # the API can't be reached today: serve yesterday's list again
            rows = old_rows(typ, cid)
            report.append(f"- {cid}: not read today, {len(rows)} kept from before")
        rows.sort(key=(lambda x: -int(x["year"] or 0)) if e.get("sort") == "newest" else (lambda x: x["rank"]))
        if not rows:
            report.append(f"- {cid}: empty")
            continue
        if os.path.isdir(L("catalog", typ, cid)):
            for old in os.listdir(L("catalog", typ, cid)):
                os.remove(os.path.join(L("catalog", typ, cid), old))
        write_pages(typ, cid, rows)
        hidden.append({"type": typ, "id": cid, "name": e["discover"][1], "extra": HIDE_EXTRA})
        opts[e["discover"][0]].append((e["discover"][1], rows))
        report.append(f"- {cid} ({e['discover'][1]}): {len(rows)}")
    disc = []
    for dcid, d in spec["discover"].items():
        typ = d["type"]
        labels = []
        base = L("catalog", typ, dcid)
        if os.path.isdir(base):
            for old in os.listdir(base):
                os.remove(os.path.join(base, old))
        for i, (label, rows) in enumerate(opts[dcid]):
            if i == 0:
                write_pages(typ, dcid, rows)
            write_pages(typ, dcid, rows, label)
            labels.append(label)
        if labels:
            disc.append({"type": typ, "id": dcid, "name": d["name"],
                         "extra": [{"name": "genre", "options": labels, "isRequired": False}, {"name": "skip", "isRequired": False}]})
    return disc, hidden


HIDE_EXTRA = [{"name": "search", "isRequired": True}, {"name": "folder", "isRequired": True}, {"name": "skip", "isRequired": False}]


def main():
    rails = json.load(open(L("genre_rails.json"), encoding="utf-8"))
    OVR.update({k: v for k, v in (json.load(open(L("genre_overrides.json"), encoding="utf-8")) if os.path.exists(L("genre_overrides.json")) else {}).items() if not k.startswith("_")})
    S.IMDB = S.ImdbCache()
    G = GenreCache()
    cats, report = [], []
    names = lambda kind, gs: ", ".join((MOVIE_G if kind == "movie" else TV_G).get(g, str(g)) for g in gs)
    for r in rails:
        kind, items, seen, dropped = build(r, G)
        typ = "series" if kind == "tv" else "movie"
        if not items:
            report.append(f"EMPTY {r['id']}")
            continue
        base = L("catalog", typ, r["id"])
        os.makedirs(base, exist_ok=True)
        for old in os.listdir(base):
            os.remove(os.path.join(base, old))
        for k in range(0, len(items), PAGE):
            page = {"metas": [S.meta(x, typ) for x in items[k:k + PAGE]]}
            json.dump(page, open(base + ".json" if k == 0 else os.path.join(base, f"skip={k}.json"), "w", encoding="utf-8"),
                      ensure_ascii=False)
            if k == 0:
                json.dump(page, open(os.path.join(base, "skip=0.json"), "w", encoding="utf-8"), ensure_ascii=False)
        cats.append({"type": typ, "id": r["id"], "name": r["name"],   # folder-only: kept out of Discover, Home, search
                     "extra": [{"name": "search", "isRequired": True}, {"name": "folder", "isRequired": True},
                               {"name": "skip", "isRequired": False}]})
        report.append(f"\n## {r['name']} ({typ}) - {len(items)} kept of {seen} looked at")
        top = sorted(dropped, key=lambda x: -(x.get("vote_count") or 0))[:25]
        lead = set(int(t) for t in re.split(r"[|,]", r["filters"]["withGenres"]))
        doubt = [x for x in items if (G.get(kind, x["tmdb"]) or [0])[0] not in lead][:15] if items and "tmdb" in items[0] else []
        report += [f"- kept (not its first genre): {x['name']} ({x['year']}) - {names(kind, G.get(kind, x['tmdb']))}" for x in doubt]
        report += [f"- left out: {x.get('title') or x.get('name')} ({(x.get('release_date') or x.get('first_air_date') or '')[:4]})"
                   f" [{kind}:{x['id']}] - {names(kind, G.get(kind, x['id']))}" for x in top]
    report.append("\n## Discover catalogs")
    disc = build_discover(G, report)
    report.append("\n## MDBList lists")
    mdisc, mhidden = build_mdb(report)
    # the Library's manifest: Discover catalogs first (they head Nuvio's Discover menu), its own catalogs, ours (gen-*)
    man = json.load(open(L("manifest.json"), encoding="utf-8"))
    man["catalogs"] = disc + mdisc + [c for c in man["catalogs"] if not c["id"].startswith(("gen-", "disc-", "mdb-"))] + cats + mhidden
    man["version"] = f"1.0.{TODAY.strftime('%Y%m%d')}"
    json.dump(man, open(L("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    S.IMDB.save()
    G.save()
    open(L("GENRE_RAILS.md"), "w", encoding="utf-8").write(
        "# Genre-true rails\n\nThe best-known titles each rail leaves out (by vote count). To keep one, add its id under the "
        "rail's genre in library/genre_overrides.json, e.g. {\"movie:35\": {\"include\": [1832]}}.\n" + "\n".join(report))
    print("\n".join(x for x in report if x.startswith("\n##") or x.startswith("EMPTY")))


if __name__ == "__main__":
    main()
