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

# genre -> the genres that may come before it in a title's list and still leave it a title of that genre.
# ANY: a format / audience more than a genre (animation, documentary, reality, kids) - tagged is enough.
# A genre without an entry must lead or be second.
ANY = None
BEFORE = {
    "movie": {
        35: {10749, 10751, 12, 28, 14, 16, 10402, 878, 80, 9648},       # Comedy: rom-com, action / crime comedy - not after drama, thriller, horror, war
        28: {12, 80, 53, 878, 14, 10752, 37, 35, 9648},                  # Action
        12: {28, 14, 878, 10751, 35, 37, 10752, 36},                     # Adventure
        16: ANY, 99: ANY,                                                # Animation, Documentary
        10751: {16, 35, 12, 14, 10402, 10749, 878, 28, 18},              # Family
        18: {36, 10752, 10749, 10402, 80, 99},                           # Drama
        80: {18, 53, 28, 9648},                                          # Crime
        27: {53, 9648, 14, 878},                                         # Horror: not after comedy (Scary Movie)
        53: {28, 80, 9648, 18, 27, 878},                                 # Thriller
        9648: {53, 80, 18, 27, 14},                                      # Mystery
        10749: {35, 18, 10402, 14, 10751},                               # Romance
        878: {28, 12, 14, 53, 27, 9648},                                 # Sci-Fi
        14: {12, 28, 10751, 878, 10749},                                 # Fantasy
        36: {18, 28, 12, 10752}, 10752: {18, 28, 12, 36},                # History, War
        37: {28, 12, 18, 80},                                            # Western
        10402: {99, 18, 35, 10749},                                      # Music
    },
    "tv": {
        35: {10759, 10751, 16, 10765, 10762, 80, 9648},                  # Comedy (+ Drama for half-hour shows, see fits)
        18: {80, 9648, 10768, 10765, 10759, 37},                         # Drama
        10759: {10765, 80, 10768, 37},                                   # Action & Adventure
        10765: {10759, 18, 9648},                                        # Sci-Fi & Fantasy
        9648: {80, 18, 10765},                                           # Mystery
        80: {18, 9648, 10759},                                           # Crime
        10768: {18, 10759}, 37: {18, 10759},                             # War & Politics, Western
        10751: {16, 35, 10762, 10765, 10759, 18},                        # Family
        16: ANY, 99: ANY, 10764: ANY, 10762: ANY,                        # Animation, Documentary, Reality, Kids
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
          "withoutKeywords": "without_keywords"}


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
    ok = []
    for t in targets:
        if t not in genres:
            ok.append(False)
            continue
        pos = genres.index(t)
        before = set(genres[:pos]) - set(targets)
        if t not in BEFORE[kind]:
            ok.append(pos <= 1)
            continue
        allowed = BEFORE[kind][t]
        if allowed is ANY:
            ok.append(True)
            continue
        if kind == "tv" and t == 35 and 0 < runtime <= HALF_HOUR:
            allowed = allowed | {18}
        ok.append(before <= allowed)
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
        cats.append({"type": typ, "id": r["id"], "name": r["name"], "extra": [{"name": "skip", "isRequired": False}]})
        report.append(f"\n## {r['name']} ({typ}) - {len(items)} kept of {seen} looked at")
        top = sorted(dropped, key=lambda x: -(x.get("vote_count") or 0))[:25]
        lead = set(int(t) for t in re.split(r"[|,]", r["filters"]["withGenres"]))
        doubt = [x for x in items if (G.get(kind, x["tmdb"]) or [0])[0] not in lead][:15] if items and "tmdb" in items[0] else []
        report += [f"- kept (not its first genre): {x['name']} ({x['year']}) - {names(kind, G.get(kind, x['tmdb']))}" for x in doubt]
        report += [f"- left out: {x.get('title') or x.get('name')} ({(x.get('release_date') or x.get('first_air_date') or '')[:4]})"
                   f" [{kind}:{x['id']}] - {names(kind, G.get(kind, x['id']))}" for x in top]
    report.append("\n## Discover catalogs")
    disc = build_discover(G, report)
    # the Library's manifest: Discover catalogs first (they head Nuvio's Discover menu), its own catalogs, ours (gen-*)
    man = json.load(open(L("manifest.json"), encoding="utf-8"))
    man["catalogs"] = disc + [c for c in man["catalogs"] if not c["id"].startswith(("gen-", "disc-"))] + cats
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
