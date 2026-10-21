"""Build the Nuvio Spotlight addon (spotlight/manifest.json, spotlight/catalog/, spotlight/art/) from TMDB.

Rotating cards (new subject every `period_days`, picked from spotlight/pool.json):
  headliner (actor), visionary (director), powerhouse (studio), saga (franchise)
Seasonal card: pulse (theme from the calendar in pool.json, changes on its start dates)
Daily cards (rebuilt every run): fresh (new on digital / new series), boxoffice, certified (acclaimed recent)

Every card has a movie and a series catalog, except boxoffice (two movie charts).
State (current subjects, when each subject was last shown) lives in spotlight/state.json; set "pin" there to
force a subject. Art is regenerated only when a card's subject changes (daily cards: only when missing).
Needs TMDB_API_KEY (v3 key or v4 read token). Usage: python3 scripts/spotlight.py [--check] [--date YYYY-MM-DD]
"""
import argparse, csv, datetime as dt, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
import spotlight_live as live

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, "spotlight")
P = lambda *p: os.path.join(SP, *p)
API = "https://api.themoviedb.org/3"
KEY = os.environ.get("TMDB_API_KEY", "").strip()
LIMIT = 100
NOISE_TV = "16|99|10762|10763|10764|10766|10767"   # animation, docs, kids, news, reality, soap, talk
NO_TOON_M = "16"
MIN_MOVIES = {"headliner": 6, "visionary": 3, "powerhouse": 6, "saga": 3, "prestige": 6, "legend": 4, "retro": 10}
ROTATING = ("headliner", "visionary", "powerhouse", "saga", "prestige", "legend", "retro", "yerli")
PEOPLE = ("headliner", "visionary", "prestige", "legend", "yerli")
SELF = re.compile(r"\b(self|himself|herself|themselves|narrator|host|archive footage|uncredited)\b", re.I)

CARDS = {
    "headliner": dict(card="The Headliner", tag="Actor Spotlight", accent="#FF4D5A"),
    "visionary": dict(card="The Visionary", tag="Director Spotlight", accent="#F5A623"),
    "powerhouse": dict(card="The Powerhouse", tag="Studio Spotlight", accent="#8B5CF6"),
    "saga": dict(card="The Saga", tag="Universe Spotlight", accent="#FF7A1A"),
    "pulse": dict(card="The Cultural Pulse", tag="Seasonal Spotlight", accent="#14B8A6"),
    "fresh": dict(card="Fresh Out of Theaters", tag="Updated Daily", accent="#22C55E"),
    "boxoffice": dict(card="Box Office Champions", tag="Updated Daily", accent="#EAB308"),
    "certified": dict(card="Certified Fresh & Must-See", tag="Updated Daily", accent="#EF4444"),
    "simkl": dict(card="My Simkl", tag="Your Lists", accent="#3B82F6"),
    "prestige": dict(card="The Prestige Darling", tag="Oscar Spotlight", accent="#D4AF37"),
    "legend": dict(card="The Living Legend", tag="Legend Retrospective", accent="#C08457"),
    "retro": dict(card="Retro Rewind", tag="Era Spotlight", accent="#EC4899"),
    "yerli": dict(card="Yerli Yıldız", tag="Türk Sineması & Dizileri", accent="#E30A17"),
}


# ---------------------------------------------------------------- TMDB
def tmdb(path, **params):
    headers = {"User-Agent": "nuvio-spotlight", "Accept": "application/json"}
    if KEY.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + KEY
    else:
        params["api_key"] = KEY
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    for i in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 401:
                sys.exit("TMDB rejected the key (401): check the TMDB_API_KEY secret")
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"TMDB request failed: {path}")


def norm(s):
    s = (s or "").replace("ı", "i").replace("İ", "I")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


class ImdbCache:
    def __init__(self):
        self.path = P("cache", "imdb.json")
        self.d = json.load(open(self.path)) if os.path.exists(self.path) else {}

    def get(self, kind, tid):
        k = f"{kind}:{tid}"
        if k not in self.d:
            ext = tmdb(f"/{kind}/{tid}/external_ids") or {}
            self.d[k] = ext.get("imdb_id") or ""
        return self.d[k]

    def prefetch(self, kind, ids):
        todo = [i for i in dict.fromkeys(ids) if f"{kind}:{i}" not in self.d]
        with ThreadPoolExecutor(8) as ex:
            for i, ext in zip(todo, ex.map(lambda i: tmdb(f"/{kind}/{i}/external_ids") or {}, todo)):
                self.d[f"{kind}:{i}"] = ext.get("imdb_id") or ""

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        json.dump(self.d, open(self.path, "w"), sort_keys=True, separators=(",", ":"))


IMDB = None
AUTO = {}


def item(kind, r):
    """TMDB result -> catalog row (needs an IMDb id; Nuvio and the posters work on IMDb ids)."""
    imdb = IMDB.get(kind, r["id"])
    if not imdb:
        return None
    date = r.get("release_date") or r.get("first_air_date") or ""
    return dict(imdb=imdb, tmdb=r["id"], kind=kind, name=r.get("title") or r.get("name"), year=date[:4],
                date=date, votes=r.get("vote_count", 0), rating=r.get("vote_average", 0),
                backdrop=r.get("backdrop_path"), poster=r.get("poster_path"))


def rows(kind, results, limit=LIMIT):
    IMDB.prefetch(kind, [r["id"] for r in results[:int(limit * 1.5)]])
    out, seen = [], set()
    for r in results:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        x = item(kind, r)
        if x:
            out.append(x)
        if len(out) >= limit:
            break
    return out


def discover(kind, params, pages=5, limit=LIMIT):
    if params.get("with_genres") and params.get("without_genres"):
        want = set(re.split(r"[|,]", params["with_genres"]))
        params = {**params, "without_genres": "|".join(g for g in params["without_genres"].split("|") if g not in want)}
    res = []
    for page in range(1, pages + 1):
        d = tmdb(f"/discover/{kind}", page=page, include_adult="false", **params) or {}
        res += d.get("results", [])
        if page >= d.get("total_pages", 0) or len(res) >= limit * 1.3:
            break
    return rows(kind, res, limit)


def released(r, today):
    d = r.get("release_date") or r.get("first_air_date") or ""
    return bool(d) and d <= today.isoformat()


# ---------------------------------------------------------------- resolvers
def find_person(name, dept):
    res = (tmdb("/search/person", query=name) or {}).get("results", [])
    exact = [r for r in res if norm(r["name"]) == norm(name)] or res
    exact.sort(key=lambda r: (r.get("known_for_department") != dept, -r.get("popularity", 0)))
    return exact[0] if exact else None


def find_keywords(names):
    ids = []
    for n in names:
        for page in (1, 2):
            d = tmdb("/search/keyword", query=n, page=page) or {}
            ids += [str(r["id"]) for r in d.get("results", []) if norm(r["name"]) == norm(n)]
            if page >= d.get("total_pages", 0):
                break
    return "|".join(dict.fromkeys(ids))


def find_collection(name):
    res = (tmdb("/search/collection", query=name) or {}).get("results", [])
    exact = [r for r in res if norm(r["name"]) == norm(name)]
    return (exact or res or [None])[0], bool(exact)


def find_series(name):
    res = (tmdb("/search/tv", query=name) or {}).get("results", [])
    exact = [r for r in res if norm(r["name"]) == norm(name)]
    exact.sort(key=lambda r: -r.get("popularity", 0))
    return (exact or res or [None])[0], bool(exact)


# ---------------------------------------------------------------- card builders: return (movies, series, art, notes)
def person_card(entry, today, director, tr=False, toon_ok=False):
    director = director or entry.get("role") == "director"
    dept = "Directing" if director else "Acting"
    p = None
    if entry.get("imdb"):
        p = ((tmdb(f"/find/{entry['imdb']}", external_source="imdb_id") or {}).get("person_results") or [None])[0]
    p = p or find_person(entry["name"], dept)
    if not p:
        raise LookupError(f"person '{entry['name']}' not found")
    cr = tmdb(f"/person/{p['id']}/combined_credits") or {}
    pool = cr.get("crew", []) if director else cr.get("cast", [])
    mv, tv = [], []
    for c in pool:
        g = set(c.get("genre_ids") or [])
        if not released(c, today) or (16 in g and not toon_ok):
            continue
        if director:
            if c["media_type"] == "movie" and c.get("job") == "Director":
                mv.append(c)
            elif c["media_type"] == "tv" and c.get("job") in ("Director", "Creator") and not g & {99, 10763, 10764, 10767}:
                tv.append(c)
        else:
            if SELF.search(c.get("character") or ""):
                continue
            # Turkish classics have few TMDB votes, so the Turkish card takes smaller vote counts
            if c["media_type"] == "movie" and 99 not in g and c.get("vote_count", 0) >= (3 if tr else 20):
                mv.append(c)
            elif (c["media_type"] == "tv" and not g & {99, 10763, 10764, 10766, 10767}
                  and (c.get("episode_count") or 0) >= 3 and c.get("vote_count", 0) >= (2 if tr else 10)):
                tv.append(c)
    def weight(c):  # actors: main roles first (cast order 0-4), then supporting parts and cameos
        small = not director and c["media_type"] == "movie" and (c.get("order") or 0) > 4
        return (small, -c.get("vote_count", 0))
    mv.sort(key=weight)
    tv.sort(key=weight)
    m, s = rows("movie", mv), rows("tv", tv)
    lead = {c["id"] for c in mv + tv if director or (c.get("order") is not None and c["order"] <= 2)}
    backs = [x["backdrop"] for x in m + s if x["backdrop"] and x["tmdb"] in lead]
    backs += [x["backdrop"] for x in m + s if x["backdrop"] and x["backdrop"] not in backs]
    n = len(m) + len(s)
    if tr:
        what = f"{'Yönetmen' if director else 'Filmografi'} · {n} yapım"
    else:
        what = f"{'Directorial catalog' if director else 'Filmography'} · {n} titles"
    if entry.get("note"):
        what = entry["note"] + " · " + what
    a = dict(title=entry.get("title") or p["name"], subtitle=what, portrait=p.get("profile_path"),
             backdrops=backs[:12])
    return m, s, a, [f"TMDB person {p['id']} {p['name']} ({p.get('known_for_department')})"]


def studio_card(entry, today):
    notes, ids = [], []
    for cid in entry.get("company", []):
        c = tmdb(f"/company/{cid}")
        if c and (norm(entry["name"]) in norm(c["name"]) or norm(c["name"]) in norm(entry["name"])
                  or len(entry.get("company", [])) > 1):
            ids.append(cid)
            notes.append(f"company {cid} = {c['name']}")
        else:
            notes.append(f"WARNING company {cid} is '{c and c['name']}', not '{entry['name']}'")
    if not ids:
        res = (tmdb("/search/company", query=entry["name"]) or {}).get("results", [])
        res = [r for r in res if norm(r["name"]) == norm(entry["name"])]
        if not res:
            raise LookupError(f"company '{entry['name']}' not found")
        ids = [res[0]["id"]]
        notes.append(f"company found by name: {ids[0]}")
    comp = "|".join(map(str, ids))
    m = discover("movie", {"with_companies": comp, "sort_by": "vote_count.desc", "vote_count.gte": 50,
                           "without_genres": NO_TOON_M, "primary_release_date.lte": today.isoformat()})
    s = discover("tv", {"with_companies": comp, "sort_by": "vote_count.desc", "vote_count.gte": 10,
                        "without_genres": NOISE_TV})
    logo = (tmdb(f"/company/{ids[0]}") or {}).get("logo_path")
    a = dict(title=entry.get("title", entry["name"]), subtitle=f"Studio catalog · {len(m) + len(s)} titles", logo=logo,
             backdrops=[x["backdrop"] for x in m if x["backdrop"]][:12])
    return m, s, a, notes


def saga_card(entry, today):
    notes, parts, poster, back = [], [], None, None
    for name in entry.get("collections", []):
        if isinstance(name, int):
            d0 = tmdb(f"/collection/{name}")
            col, exact = (d0, True) if d0 else (None, False)
        else:
            col, exact = find_collection(name)
        if not col:
            notes.append(f"WARNING collection '{name}' not found")
            continue
        notes.append(f"collection {col['id']} = {col['name']}" + ("" if exact else "  (WARNING: not an exact name match)"))
        d = tmdb(f"/collection/{col['id']}") or {}
        poster, back = poster or d.get("poster_path"), back or d.get("backdrop_path")
        parts += [p for p in d.get("parts", []) if released(p, today)]
    parts.sort(key=lambda p: p.get("release_date") or "9999")
    shows = []
    for name in entry.get("series", []):
        t, exact = find_series(name)
        if t and exact and released(t, today):
            shows.append(t)
            notes.append(f"series {t['id']} = {t['name']}")
        else:
            notes.append(f"WARNING series '{name}' not found")
    shows.sort(key=lambda t: t.get("first_air_date") or "9999")
    m, s = rows("movie", parts), rows("tv", shows)
    t = entry.get("title", entry["name"])
    a = dict(title=t if re.search(r"saga|universe|trilogy|world", t, re.I) else t + " Saga",
             subtitle=f"In release order · {len(m) + len(s)} titles", poster=poster,
             backdrops=([back] if back else []) + [x["backdrop"] for x in m if x["backdrop"]][:12])
    return m, s, a, notes


def awards_catalog(typ, cid):
    path = os.path.join(ROOT, "catalog", typ, f"{cid}.json")
    metas = json.load(open(path))["metas"] if os.path.exists(path) else []
    return [dict(imdb=x["id"], tmdb=None, kind="movie" if typ == "movie" else "tv", name=x["name"],
                 year=x.get("releaseInfo", ""), date="", votes=0, backdrop=None, poster=None) for x in metas]


def next_start(pool, today):
    """Date the next calendar theme starts (after today)."""
    starts = sorted({t["start"] for t in pool["pulse"]})
    md = today.strftime("%m-%d")
    later = [x for x in starts if x > md]
    y, x = (today.year, later[0]) if later else (today.year + 1, starts[0])
    return dt.date(y, int(x[:2]), int(x[3:]))


def pulse_theme(pool, today, override=None):
    md = today.strftime("%m-%d")
    themes = sorted(pool["pulse"], key=lambda t: t["start"])
    cur = [t for t in themes if t["start"] <= md]
    t = dict(cur[-1] if cur else themes[-1])
    if override and today.isoformat() < override["until"]:
        t = dict(next(x for x in themes if x["title"] == override["theme"]))
    t["_raw"] = t["title"]
    best_year = today.year if today.month == 12 else today.year - 1
    t["title"] = t["title"].format(best_year=best_year)
    t["_best_year"] = best_year
    return t


def pulse_card(t, today):
    notes = []
    if t.get("awards_movie"):
        m = awards_catalog("movie", t["awards_movie"])
        s = awards_catalog("series", t["awards_series"]) if t.get("awards_series") else []
        backs = []
        for x in m[:6]:
            f = tmdb(f"/find/{x['imdb']}", external_source="imdb_id") or {}
            hit = (f.get("movie_results") or [None])[0]
            if hit and hit.get("backdrop_path"):
                backs.append(hit["backdrop_path"])
        a = dict(title=t["title"], subtitle=f"{t['subtitle']} · {len(m) + len(s)} titles", backdrops=backs)
        return m, s, a, ["from the awards catalogs"]
    base_m = {"sort_by": "vote_count.desc", "vote_count.gte": 150, "with_original_language": "en",
              "without_genres": NO_TOON_M, "primary_release_date.lte": today.isoformat()}
    base_t = {"sort_by": "vote_count.desc", "vote_count.gte": 30, "with_original_language": "en",
              "without_genres": NOISE_TV}
    if t.get("best_year"):
        y = t["_best_year"]
        base_m.update({"primary_release_date.gte": f"{y}-01-01", "primary_release_date.lte": f"{y}-12-31",
                       "sort_by": "vote_average.desc", "vote_count.gte": 300})
        base_t.update({"first_air_date.gte": f"{y}-01-01", "first_air_date.lte": f"{y}-12-31",
                       "sort_by": "vote_average.desc", "vote_count.gte": 80})
    kw_m = find_keywords(t.get("keywords", [])) if t.get("keywords") else ""
    kw_t = find_keywords(t["keywords_series"]) if t.get("keywords_series") else kw_m
    notes.append(f"keywords movie={kw_m or '-'} series={kw_t or '-'}")
    pm = {**base_m, **({"with_keywords": kw_m} if kw_m else {}), **t.get("movie", {})}
    pt = {**base_t, **({"with_keywords": kw_t} if kw_t else {}), **t.get("series", {})}
    m = discover("movie", pm)
    s = discover("tv", pt) if (kw_t or t.get("series") or t.get("best_year")) else []
    a = dict(title=t["title"], subtitle=f"{t['subtitle']} · {len(m) + len(s)} titles", backdrops=[x["backdrop"] for x in m if x["backdrop"]][:12])
    return m, s, a, notes


def daily_cards(today):
    d = lambda n: (today - dt.timedelta(days=n)).isoformat()
    t = today.isoformat()
    out = {}
    out["fresh"] = (
        discover("movie", {"with_release_type": "4|5", "region": "US", "release_date.gte": d(60), "release_date.lte": t,
                           "sort_by": "popularity.desc", "with_original_language": "en", "without_genres": NO_TOON_M,
                           "vote_count.gte": 3}, pages=3, limit=50),
        discover("tv", {"first_air_date.gte": d(45), "first_air_date.lte": t, "sort_by": "popularity.desc",
                        "with_original_language": "en", "without_genres": NOISE_TV, "vote_count.gte": 2},
                 pages=3, limit=50))
    # charts: animation and every language allowed (same exception as the Top 10 charts)
    out["boxoffice"] = (
        discover("movie", {"primary_release_date.gte": d(365), "primary_release_date.lte": t,
                           "sort_by": "revenue.desc", "vote_count.gte": 50}, pages=2, limit=40),
        discover("movie", {"sort_by": "revenue.desc", "vote_count.gte": 1000}, pages=5))
    out["certified"] = (
        discover("movie", {"primary_release_date.gte": d(730), "primary_release_date.lte": t,
                           "vote_average.gte": 7.2, "vote_count.gte": 400, "sort_by": "vote_average.desc",
                           "with_original_language": "en", "without_genres": NO_TOON_M}, pages=3, limit=60),
        discover("tv", {"first_air_date.gte": d(1095), "first_air_date.lte": t, "vote_average.gte": 7.8,
                        "vote_count.gte": 150, "sort_by": "vote_average.desc", "with_original_language": "en",
                        "without_genres": NOISE_TV}, pages=3, limit=60))
    return out


def retro_card(entry, today):
    y0, y1 = entry["from"], entry["to"]
    lang = {"with_original_language": "en"} if entry.get("lang", "en") else {}
    kw = find_keywords(entry["keywords"]) if entry.get("keywords") else ""
    pm = {"sort_by": "vote_count.desc", "vote_count.gte": 150, "without_genres": NO_TOON_M, **lang,
          "primary_release_date.gte": f"{y0}-01-01", "primary_release_date.lte": f"{y1}-12-31",
          **({"with_keywords": kw} if kw else {}), **entry.get("movie", {})}
    m = discover("movie", pm)
    s, notes = [], [f"{y0}–{y1}; keywords={kw or '-'}"]
    if entry.get("series", {}) is not False:
        ser = dict(entry.get("series") or {})
        kws = find_keywords(ser.pop("with_keywords_names")) if ser.get("with_keywords_names") else kw
        pt = {"sort_by": "vote_count.desc", "vote_count.gte": 40, "without_genres": NOISE_TV, **lang,
              "first_air_date.gte": f"{y0}-01-01", "first_air_date.lte": f"{y1}-12-31",
              **({"with_keywords": kws} if kws else {}), **ser}
        s = discover("tv", pt)
    era = f"{y0}–{y1}" if y1 - y0 != 9 else f"The {str(y0)[2:]}s"
    a = dict(title=entry["name"], subtitle=f"{era} · {len(m) + len(s)} titles",
             backdrops=[x["backdrop"] for x in m if x["backdrop"]][:12])
    return m, s, a, notes


ACTING = ("ACTOR IN A LEADING ROLE", "ACTRESS IN A LEADING ROLE", "ACTOR IN A SUPPORTING ROLE", "ACTRESS IN A SUPPORTING ROLE")


def prestige_pool(since=1990):
    """Oscar acting nominees since `since` (film year), most wins / nominations first. Built from the Oscar data."""
    path = os.path.join(ROOT, "data", "sources", "oscars.csv")
    people = {}
    for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
        if r["CanonicalCategory"] not in ACTING or not r["NomineeIds"].startswith("nm"):
            continue
        p = people.setdefault(r["NomineeIds"].split("|")[0], {"name": r["Name"], "wins": 0, "noms": 0, "last": 0, "year": 0})
        p["noms"] += 1  # counted over the whole history, so the card's "3× Oscar winner" is right
        p["wins"] += r["Winner"] == "True"
        p["last"] = max(p["last"], int(r["Ceremony"]))
        p["year"] = max(p["year"], int(r["Year"][:4]))
    latest = max(p["last"] for p in people.values())
    people = {k: v for k, v in people.items() if v["year"] >= since}  # a nomination since 1990
    out = []
    for nm, p in sorted(people.items(), key=lambda kv: (-kv[1]["wins"], -kv[1]["noms"], kv[1]["name"])):
        w, n = p["wins"], p["noms"]
        note = (f"{w}× Oscar winner" if w > 1 else "Oscar winner" if w else "Oscar nominee") + \
               (f" · {n} nominations" if n > 1 else "")
        out.append({"name": p["name"], "imdb": nm, "note": note, "latest": p["last"] == latest})
    return out


BUILDERS = {
    "headliner": lambda e, t: person_card(e, t, False),
    "visionary": lambda e, t: person_card(e, t, True),
    "powerhouse": studio_card,
    "saga": saga_card,
    "prestige": lambda e, t: person_card(e, t, False),
    "legend": lambda e, t: person_card(e, t, False),
    "retro": retro_card,
    "yerli": lambda e, t: person_card(e, t, False, tr=True),
}


def enough(slot, m, s):
    if slot == "yerli":
        return len(m) + len(s) >= 8
    return len(m) >= MIN_MOVIES[slot]


# ---------------------------------------------------------------- rotation
def period_of(pool, today):
    return (today - dt.date.fromisoformat(pool["anchor"])).days // pool["period_days"]


def candidates(entries, hist, today):
    """Seasonal entries first (not shown in the last 180 days), then the least recently shown others."""
    def last(e):
        return hist.get(e["name"], "0000-00-00")
    cutoff = (today - dt.timedelta(days=180)).isoformat()
    seasonal = [e for e in entries if today.month in e.get("months", []) and last(e) < cutoff]
    rest = [e for e in entries if not e.get("months")]
    seasonal.sort(key=last)
    rest.sort(key=last)  # stable: pool order breaks ties
    rest += sorted([e for e in entries if e.get("months") and e not in seasonal], key=last)
    return seasonal + rest


def build_rotating(slot, pool, state, today, period, log, force_next=False, force_subject=None, busy=()):
    st = state.setdefault("cards", {}).setdefault(slot, {})
    hist = state.setdefault("history", {}).setdefault(slot, {})
    entries = pool[slot]
    by_name = {norm(e["name"]): e for e in entries}
    by_name.update({norm(e["title"]): e for e in entries if e.get("title")})
    pin = state.get("pin", {}).get(slot)
    fresh_pick = False  # True when a new subject is being chosen by the rotation itself
    if force_subject:
        e = by_name.get(norm(force_subject))
        if not e and slot == "saga":
            raise SystemExit(f"saga '{force_subject}' is not in pool.json (sagas need their TMDB collections there)")
        order = [e or {"name": force_subject}]
        log.append(f"- {slot}: chosen by hand: {order[0]['name']}")
    elif force_next:
        order = [e for e in candidates(entries, hist, today) if e["name"] != st.get("subject")]
        log.append(f"- {slot}: skipped to the next subject by hand")
        fresh_pick = True
    elif pin and norm(pin) in by_name:
        order = [by_name[norm(pin)]]
    elif st.get("period") == period and st.get("subject"):
        order = [by_name.get(norm(st["subject"])) or {"name": st["subject"]}]
    else:
        order = candidates(entries, hist, today)
        fresh_pick = True
    reasons = {}
    if fresh_pick and slot in live.TOPICAL_SLOTS:
        tops = [(e, why) for e, why in live.topical(slot, tmdb, today, entries, hist, state)
                if e["name"] != st.get("subject")]
        reasons = {e["name"]: why for e, why in tops}
        order = [e for e, _ in tops] + [e for e in order if e["name"] not in reasons]
        if tops:
            log.append(f"- {slot}: topical: " + "; ".join(f"{e['name']} ({why})" for e, why in tops[:5]))
    elif st.get("reason") and order and order[0]["name"] == st.get("subject"):
        reasons = {st["subject"]: st["reason"]}
    if fresh_pick and slot == "prestige" and (1, 15) <= (today.month, today.day) <= (3, 31):
        # awards season: this year's acting nominees first
        cutoff = (today - dt.timedelta(days=365)).isoformat()
        season = [e for e in order if e.get("latest") and hist.get(e["name"], "0") < cutoff]
        order = season + [e for e in order if e not in season]
    if fresh_pick and slot in PEOPLE:  # never the same person on two cards at once
        order = [e for e in order if norm(e["name"]) not in busy]
    for e in order[:15]:
        try:
            m, s, a, notes = BUILDERS[slot](e, today)
        except LookupError as err:
            log.append(f"- {slot}: skipped {e['name']}: {err}")
            continue
        if not enough(slot, m, s):
            log.append(f"- {slot}: skipped {e['name']}: only {len(m)} movies / {len(s)} series")
            continue
        if st.get("subject") != e["name"]:
            hist[e["name"]] = today.isoformat()
        why = reasons.get(e["name"])
        st.update(subject=e["name"], period=period, reason=why)
        if why:
            a["tag"] = "Now in theaters" if why.startswith("In theaters") else "Coming to theaters" \
                if why.startswith("Coming") else "New chapter in theaters"
            a["subtitle"] = why.split(": ", 1)[-1].split(" · ", 1)[-1] + " · " + a["subtitle"]
            notes = notes + [f"topical pick: {why}"]
        if e.get("auto") and not any(norm(x["name"]) == norm(e["name"]) for x in AUTO.get(slot, [])):
            AUTO.setdefault(slot, []).append({**e, "added": today.isoformat()})
        return e["name"], m, s, a, notes
    raise RuntimeError(f"{slot}: no usable subject")


# ---------------------------------------------------------------- output
def meta(x, typ):
    return {"id": x["imdb"], "type": typ, "name": x["name"], "releaseInfo": x["year"],
            "poster": f"https://images.metahub.space/poster/medium/{x['imdb']}/img", "posterShape": "poster"}


def write_catalog(typ, cid, items):
    os.makedirs(P("catalog", typ), exist_ok=True)
    json.dump({"metas": [meta(x, typ) for x in items]}, open(P("catalog", typ, f"{cid}.json"), "w", encoding="utf-8"),
              ensure_ascii=False)


def make_art(slot, a, key, state, force=False):
    st = state.setdefault("art", {})
    have = os.path.exists(P("art", slot, "cover.jpg"))
    if have and st.get(slot) == key and not force:
        return False
    c = CARDS[slot]
    shown = state.setdefault("backdrops", {})
    taken = {v for k, v in shown.items() if k != slot}
    a["backdrop"] = next((b for b in a.get("backdrops", []) if b not in taken), (a.get("backdrops") or [None])[0])
    shown[slot] = a["backdrop"]
    art.cover(P("art", slot, "cover.jpg"), card=c["card"], tag=a.get("tag", c["tag"]), accent=c["accent"], title=a["title"],
              subtitle=a["subtitle"], backdrop=a.get("backdrop"), portrait=a.get("portrait"), logo=a.get("logo"),
              poster=a.get("poster"), tr=slot == "yerli")
    if a.get("backdrop"):
        art.backdrop(P("art", slot, "backdrop.jpg"), a["backdrop"])
    st[slot] = key
    return True


def main():
    global IMDB, AUTO
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--check", action="store_true", help="resolve every pool entry, write spotlight/CHECK.md")
    ap.add_argument("--redraw", action="store_true", help="regenerate all art")
    ap.add_argument("--next", default="", help="card (or 'all'): show the next subject now instead of waiting")
    ap.add_argument("--subject", default="", help="'card=Name': show this subject now (until the next rotation)")
    args = ap.parse_args()
    if not KEY:
        sys.exit("TMDB_API_KEY is not set")
    today = dt.date.fromisoformat(args.date) if args.date else dt.datetime.utcnow().date()
    pool = json.load(open(P("pool.json"), encoding="utf-8"))
    auto_path = P("pool_auto.json")
    AUTO = json.load(open(auto_path, encoding="utf-8")) if os.path.exists(auto_path) else {"removed": []}
    state_path = P("state.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"pin": {}}
    IMDB = ImdbCache()
    pool["prestige"] = prestige_pool()
    if args.check:
        return check(pool, today)

    rotating = ROTATING
    nxt = set(rotating) if args.next == "all" else {args.next} - {""}
    forced = {}
    if args.subject:
        card, _, name = args.subject.partition("=")
        if card.strip() not in rotating + ("pulse",) or not name.strip():
            sys.exit("--subject must look like 'headliner=Pedro Pascal' (cards: " + ", ".join(rotating + ("pulse",)) + ")")
        forced[card.strip()] = name.strip()
    if "pulse" in forced:
        bare = lambda x: norm(re.sub(r"\{best_year\}|\b\d{4}\b", "", x))
        hit = [t for t in pool["pulse"] if bare(t["title"]) == bare(forced["pulse"])]
        if not hit:
            sys.exit("pulse theme not in pool.json: " + forced["pulse"] + "\nthemes: " + ", ".join(t["title"] for t in pool["pulse"]))
        state["pulse_override"] = {"theme": hit[0]["title"], "until": next_start(pool, today).isoformat()}
    if args.next == "pulse":  # bring the next calendar theme forward; the calendar carries on from it
        themes = sorted(pool["pulse"], key=lambda t: t["start"])
        cur = state.get("pulse_override", {}).get("theme") or pulse_theme(pool, today)["_raw"]
        i = next(k for k, t in enumerate(themes) if t["title"] == cur)
        state["pulse_override"] = {"theme": themes[(i + 1) % len(themes)]["title"],
                                   "until": next_start(pool, today).isoformat()}
    log, status, catalogs = [], [], []
    live.grow(tmdb, today, pool, AUTO, state, log)
    removed = {norm(x) for x in AUTO.get("removed", [])}
    for slot in rotating:  # the rotation draws from both pools
        pool[slot] = pool[slot] + [e for e in AUTO.get(slot, []) if norm(e["name"]) not in removed]
    period = period_of(pool, today)
    next_change = dt.date.fromisoformat(pool["anchor"]) + dt.timedelta(days=(period + 1) * pool["period_days"])
    names = {}
    for slot in rotating:
        cards = state.setdefault("cards", {})
        busy = {norm(cards.get(o, {}).get("subject")) for o in PEOPLE if o != slot} - {""}
        subject, m, s, a, notes = build_rotating(slot, pool, state, today, period, log, slot in nxt, forced.get(slot),
                                                 busy)
        label = CARDS[slot]["card"]
        names[slot] = ((f"{label}: {a['title']} · Filmler", f"{label}: {a['title']} · Diziler") if slot == "yerli"
                       else (f"{label}: {a['title']}", f"{label}: {a['title']} · Series"))
        write_catalog("movie", f"spotlight-{slot}-movies", m)
        write_catalog("series", f"spotlight-{slot}-series", s)
        drew = make_art(slot, a, subject, state, args.redraw)
        status.append((label, a["title"], len(m), len(s), notes, drew))

    ov = state.get("pulse_override")
    if ov and today.isoformat() >= ov["until"]:
        state.pop("pulse_override")
        ov = None
    t = pulse_theme(pool, today, ov)
    m, s, a, notes = pulse_card(t, today)
    names["pulse"] = (f"{t['title']} · Movies", f"{t['title']} · Series")
    write_catalog("movie", "spotlight-pulse-movies", m)
    write_catalog("series", "spotlight-pulse-series", s)
    drew = make_art("pulse", a, t["title"], state, args.redraw)
    state.setdefault("cards", {})["pulse"] = {"subject": t["title"], "since": t["start"]}
    status.append(("The Cultural Pulse", t["title"], len(m), len(s), notes, drew))

    daily = daily_cards(today)
    titles = {"fresh": ("Fresh Out of Theaters · New on Digital", "Fresh Out of Theaters · New Series"),
              "boxoffice": ("Box Office · Last 12 Months", "Box Office · All-Time Champions"),
              "certified": ("Certified Fresh · Must-See Movies", "Certified Fresh · Must-See Series")}
    subtitles = {"fresh": "New on digital & new series", "boxoffice": "Top grossing films",
                 "certified": "The most acclaimed of the last two years"}
    for slot, (m, s) in daily.items():
        names[slot] = titles[slot]
        write_catalog("movie", f"spotlight-{slot}-movies", m)
        write_catalog("movie" if slot == "boxoffice" else "series", f"spotlight-{slot}-" +
                      ("alltime" if slot == "boxoffice" else "series"), s)
        a = dict(title=CARDS[slot]["card"], subtitle=subtitles[slot], backdrops=[x["backdrop"] for x in m + s if x["backdrop"]][:12])
        drew = make_art(slot, a, "static", state, args.redraw)
        status.append((CARDS[slot]["card"], "daily", len(m), len(s), [], drew))

    # My Simkl moved to Favourites: its art is drawn by scripts/favourites_art.py

    for slot in ROTATING + ("pulse", "fresh", "boxoffice", "certified"):
        mid = f"spotlight-{slot}-movies"
        sid, styp = (f"spotlight-{slot}-alltime", "movie") if slot == "boxoffice" else (f"spotlight-{slot}-series", "series")
        catalogs.append({"type": "movie", "id": mid, "name": names[slot][0]})
        catalogs.append({"type": styp, "id": sid, "name": names[slot][1]})
    manifest = {
        "id": "community.oblivioustr.nuvio-spotlight",
        "version": f"1.{period}.{today.strftime('%Y%m%d')}",
        "name": "Nuvio Spotlight",
        "description": "Rotating spotlights (actor, director, studio, saga, season, Oscar talent, legends, eras, Turkish stars) and daily charts, rebuilt from TMDB.",
        "resources": ["catalog"], "types": ["movie", "series"], "idPrefixes": ["tt"],
        "catalogs": catalogs,
        "behaviorHints": {"configurable": False, "configurationRequired": False},
    }
    json.dump(manifest, open(P("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    state["updated"] = today.isoformat()
    json.dump(AUTO, open(auto_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    IMDB.save()

    md = [f"# Spotlight status — {today.isoformat()}", "",
          f"Next rotation (all rotating cards): **{next_change.isoformat()}**",
          f"Next Cultural Pulse theme starts: **{next_start(pool, today).isoformat()}**", "",
          "| Card | Subject | Movies | Series | New art |", "|---|---|---:|---:|:-:|"]
    md += [f"| {c} | {sub} | {nm} | {ns} | {'✓' if d else ''} |" for c, sub, nm, ns, _, d in status]
    md += ["", "## Notes"] + [f"- **{c}**: {n}" for c, _, _, _, notes, _ in status for n in notes] + log
    open(P("STATUS.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


def check(pool, today):
    md = [f"# Spotlight pool check — {today.isoformat()}", ""]
    only = os.environ.get("CHECK_CARDS", "").split(",") if os.environ.get("CHECK_CARDS") else ROTATING
    for slot in ROTATING:
        if slot not in only:
            continue
        md += [f"## {CARDS[slot]['card']}", "", "| Subject | Movies | Series | Notes |", "|---|---:|---:|---|"]
        for e in pool[slot][:40] if slot == "prestige" else pool[slot]:
            try:
                m, s, a, notes = BUILDERS[slot](e, today)
                flag = " ⚠️" if not enough(slot, m, s) or any("WARNING" in n for n in notes) else ""
                md.append(f"| {e['name']}{flag} | {len(m)} | {len(s)} | {'; '.join(notes)} |")
            except Exception as err:
                md.append(f"| {e['name']} ⚠️ | – | – | {err} |")
        md.append("")
    if "pulse" in only or not os.environ.get("CHECK_CARDS"):
        md += ["## The Cultural Pulse", "", "| Start | Theme | Movies | Series | Notes |", "|---|---|---:|---:|---|"]
        for t in sorted(pool["pulse"], key=lambda t: t["start"]):
            day = dt.date(today.year, int(t["start"][:2]), int(t["start"][3:]))
            tt = pulse_theme(pool, day)
            m, s, a, notes = pulse_card(tt, today)
            flag = " ⚠️" if len(m) < 10 else ""
            md.append(f"| {t['start']} | {tt['title']}{flag} | {len(m)} | {len(s)} | {'; '.join(notes)} |")
    IMDB.save()
    open(P("CHECK.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
