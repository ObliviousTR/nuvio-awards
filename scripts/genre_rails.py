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

# genre -> genres that may come before it (movie / tv ids). A genre not listed must lead (or be second at most).
BEFORE = {
    "movie": {
        35: {10749, 10751, 12, 28, 14, 16, 10402, 878},          # Comedy
    },
    "tv": {
        35: {10759, 10751, 16, 10765, 10762},                    # Comedy
    },
}
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
          "voteAverageGte": "vote_average.gte", "withRuntimeGte": "with_runtime.gte"}


class GenreCache:
    """A title's ordered genre list (TMDB details); kept 30 days."""
    def __init__(self):
        self.path = os.path.join(ROOT, "spotlight", "cache", "genres.json")
        self.d = json.load(open(self.path)) if os.path.exists(self.path) else {}

    def fresh(self, k):
        v = self.d.get(k)
        return v and (TODAY - dt.date.fromisoformat(v[0])).days < 30

    def prefetch(self, kind, ids):
        todo = [i for i in dict.fromkeys(ids) if not self.fresh(f"{kind}:{i}")]
        with ThreadPoolExecutor(8) as ex:
            for i, x in zip(todo, ex.map(lambda i: tmdb(f"/{kind}/{i}") or {}, todo)):
                if x.get("id"):
                    self.d[f"{kind}:{i}"] = [TODAY.isoformat(), [g["id"] for g in x.get("genres", [])]]

    def get(self, kind, i):
        return (self.d.get(f"{kind}:{i}") or [None, []])[1]

    def save(self):
        json.dump(self.d, open(self.path, "w"), sort_keys=True, separators=(",", ":"))


OVR = {}   # library/genre_overrides.json: {"movie:35": {"include": [ids], "exclude": [ids]}} - hand decisions per genre


def fits(kind, genres, want, tid=None):
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
        allowed = BEFORE[kind].get(t)
        ok.append(not before or (before <= allowed if allowed is not None else pos <= 1))
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
    res, kept, dropped = [], [], []
    for page in range(1, PAGES + 1):
        d = tmdb(f"/discover/{kind}", page=page, include_adult="false", **q) or {}
        batch = d.get("results", [])
        G.prefetch(kind, [x["id"] for x in batch])
        for x in batch:
            if fits(kind, G.get(kind, x["id"]), r["filters"]["withGenres"], x["id"]):
                kept.append(x)
            else:
                dropped.append(x)
        res += batch
        if page >= d.get("total_pages", 0) or len(kept) >= LIMIT * 1.25:
            break
    return kind, S.rows(kind, kept, limit=LIMIT), len(res), dropped


def main():
    rails = json.load(open(L("genre_rails.json"), encoding="utf-8"))
    OVR.update(json.load(open(L("genre_overrides.json"), encoding="utf-8")) if os.path.exists(L("genre_overrides.json")) else {})
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
        report += [f"- left out: {x.get('title') or x.get('name')} ({(x.get('release_date') or x.get('first_air_date') or '')[:4]})"
                   f" [{kind}:{x['id']}] - {names(kind, G.get(kind, x['id']))}" for x in top]
    # the Library's manifest: its own catalogs stay, ours (gen-*) are replaced
    man = json.load(open(L("manifest.json"), encoding="utf-8"))
    man["catalogs"] = [c for c in man["catalogs"] if not c["id"].startswith("gen-")] + cats
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
