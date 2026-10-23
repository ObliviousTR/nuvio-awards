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
LIMIT, PAGES = 100, 15

# genre -> genres that may come before it (movie / tv ids). A genre not listed must lead (or be second at most).
BEFORE = {
    "movie": {
        35: {10749, 10751, 12, 28, 14, 16, 10402, 878},          # Comedy
    },
    "tv": {
        35: {10759, 10751, 16, 10765, 10762},                    # Comedy
    },
}
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


def fits(kind, genres, want):
    """want: the rail's with_genres ("35", "28|12" = any of, "16,35" = all of)."""
    allof = "," in want
    targets = [int(x) for x in re.split(r"[|,]", want) if x]
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
    res, kept = [], []
    for page in range(1, PAGES + 1):
        d = tmdb(f"/discover/{kind}", page=page, include_adult="false", **q) or {}
        batch = d.get("results", [])
        G.prefetch(kind, [x["id"] for x in batch])
        for x in batch:
            if fits(kind, G.get(kind, x["id"]), r["filters"]["withGenres"]):
                kept.append(x)
        res += batch
        if page >= d.get("total_pages", 0) or len(kept) >= LIMIT * 1.25:
            break
    return kind, S.rows(kind, kept, limit=LIMIT), len(res)


def main():
    rails = json.load(open(L("genre_rails.json"), encoding="utf-8"))
    S.IMDB = S.ImdbCache()
    G = GenreCache()
    cats, report = [], []
    for r in rails:
        kind, items, seen = build(r, G)
        typ = "series" if kind == "tv" else "movie"
        if not items:
            report.append(f"EMPTY {r['id']}")
            continue
        os.makedirs(L("catalog", typ), exist_ok=True)
        json.dump({"metas": [S.meta(x, typ) for x in items]}, open(L("catalog", typ, f"{r['id']}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        cats.append({"type": typ, "id": r["id"], "name": r["name"]})
        report.append(f"{r['id']}: {len(items)} kept of {seen} looked at")
    # the Library's manifest: its own catalogs stay, ours (gen-*) are replaced
    man = json.load(open(L("manifest.json"), encoding="utf-8"))
    man["catalogs"] = [c for c in man["catalogs"] if not c["id"].startswith("gen-")] + cats
    man["version"] = f"1.0.{TODAY.strftime('%Y%m%d')}"
    json.dump(man, open(L("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    S.IMDB.save()
    G.save()
    print("\n".join(report))


if __name__ == "__main__":
    main()
