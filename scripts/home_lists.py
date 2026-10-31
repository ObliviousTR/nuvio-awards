"""Home lists in the Nuvio Library addon, rebuilt every day:
  home-trending-movies / home-trending-series   what is trending today (TMDB), for Nuvio's home hero
  home-foryou-movies   / home-foryou-series     recommendations from Ozzy's own Simkl history (like BingeCat's)
These four are the only Library catalogs left visible (no required extra): Nuvio offers a catalog for the home hero
only when it is not search-only, and hides a search-only one from its Discover menu just the same.
Every item carries a full-size background (TMDB original) and the title logo, which the hero shows over it.

For You: the titles Ozzy finished or is watching on Simkl are the seeds, weighted by how recently he watched them and
by his rating (a low rating counts against). Each seed's TMDB recommendations score the candidates, shaped by the genres
he watches, the titles' ratings and age (see for_you); titles on any of his Simkl lists are left out, and so is anime
(anime lives in the anime rails), as are news, talk and soap shows.
needs: TMDB_API_KEY, SIMKL_CLIENT_ID, SIMKL_CLIENT_SECRET, MDBLIST_API_KEY (simkl/token.enc, refreshed and re-saved)
usage: python3 scripts/home_lists.py [--no-simkl]
"""
import datetime as dt, json, math, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight as S
from spotlight import tmdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = lambda *p: os.path.join(ROOT, "library", *p)
TODAY = dt.date.today()
NOISE_TV = {10763, 10766, 10767}                     # news, soap, talk
SIZE = 60


def anime(r):
    """anime, and animation at all: both live in their own rails (the hero and For You are live action)"""
    return 16 in (r.get("genre_ids") or [g["id"] for g in r.get("genres", [])])


def noise(kind, r):
    return kind == "tv" and bool(NOISE_TV & set(r.get("genre_ids") or []))


def logo(kind, tid):
    d = tmdb(f"/{kind}/{tid}/images", include_image_language="en,null") or {}
    ls = [x for x in d.get("logos", []) if x.get("iso_639_1") == "en"] or d.get("logos", [])
    if not ls:
        return None
    x = max(ls, key=lambda x: (x.get("vote_average", 0), x.get("width", 0)))
    return "https://image.tmdb.org/t/p/w500" + x["file_path"].replace(".svg", ".png")


def write(cid, typ, name, items):
    kind = "tv" if typ == "series" else "movie"
    with ThreadPoolExecutor(8) as ex:
        logos = list(ex.map(lambda x: logo(kind, x["tmdb"]), items))
    metas = []
    for x, lg in zip(items, logos):
        m = S.meta(x, typ)
        if lg and not S.tr_name(typ, x["imdb"]):         # a Turkish title shows its own name, not an English logo
            m["logo"] = lg
        metas.append(m)
    os.makedirs(L("catalog", typ), exist_ok=True)
    json.dump({"metas": metas}, open(L("catalog", typ, f"{cid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{name}: {len(metas)} - " + ", ".join(m["name"] for m in metas[:12]))
    return {"type": typ, "id": cid, "name": name, "extra": []}


# ------------------------------------------------------------------------------------------------------- trending
def trending(kind):
    res = []
    for page in (1, 2, 3, 4):
        res += (tmdb(f"/trending/{kind}/day", page=page) or {}).get("results", [])
    keep = [r for r in res if not anime(r) and not noise(kind, r) and r.get("original_language") in ("en", "tr")
            and r.get("backdrop_path") and r.get("vote_count", 0) >= 10]
    return S.rows(kind, keep, SIZE)


# -------------------------------------------------------------------------------------------------------- for you
def simkl_history():
    import simkl_auth as K
    tok = K.access_token()
    seen, seeds = set(), {"movie": [], "tv": []}
    ratings = {}
    for kind in ("movies", "shows", "anime"):
        try:
            d = K.get(f"/sync/ratings/{kind}", tok)
            for it in (d.get(kind) if isinstance(d, dict) else None) or []:
                m = it.get("movie") or it.get("show") or {}
                t = (m.get("ids") or {}).get("tmdb")
                if t and it.get("user_rating"):
                    ratings[("movie" if kind == "movies" else "tv", int(t))] = it["user_rating"]
        except Exception as e:
            print("ratings", kind, type(e).__name__)
    for kind in ("movies", "shows", "anime"):
        k2 = "movie" if kind == "movies" else "tv"
        for status in ("completed", "watching", "plantowatch", "hold", "dropped"):
            d = K.get(f"/sync/all-items/{kind}/{status}", tok)
            for it in (d.get(kind) if isinstance(d, dict) else None) or []:
                m = it.get("movie") or it.get("show") or {}
                t = (m.get("ids") or {}).get("tmdb")
                if not t:
                    continue
                t = int(t)
                seen.add((k2, t))
                if status in ("completed", "watching") and kind != "anime":
                    when = (it.get("last_watched_at") or it.get("added_to_watchlist_at") or "")[:10]
                    seeds[k2].append((t, when, ratings.get((k2, t)), m.get("title", "")))
                if status == "dropped":
                    seeds[k2].append((t, (it.get("last_watched_at") or "")[:10], 3, m.get("title", "")))
    return seen, seeds


def weight(when, rating):
    try:
        days = (TODAY - dt.date.fromisoformat(when)).days
    except Exception:
        days = 720
    rec = 0.35 + 0.65 * math.exp(-max(days, 0) / 240)
    if rating is None:
        return rec * 0.7
    return rec * (rating - 5.5) / 4.5                    # 10 -> 1, 6 -> ~0.1, 5 and below count against


def for_you(kind, seen, seeds):
    """Every seed's TMDB recommendations, weighted by the seed (recent and well rated counts most), then:
    - the genres he watches most count up, the others down (from the seeds themselves);
    - well-rated titles count up, weak ones are left out (movies under 6.2, shows under 6.8);
    - a sequel is not suggested before its first film: the first one he has not seen takes its place, one per series;
    - the huge, older hits he has most likely seen off Simkl count less, as do old sitcoms and films;
    - no single seed fills the list: at most 8 titles mainly owed to one seed (Ozzy, 31 Oct 2026)."""
    seeds = sorted(seeds, key=lambda s: -abs(weight(s[1], s[2])))[:40]
    score, hits, data, owe = {}, {}, {}, {}

    def recs(s):
        out = []
        for page in (1, 2):
            out += (tmdb(f"/{kind}/{s[0]}/recommendations", page=page) or {}).get("results", [])
        info = tmdb(f"/{kind}/{s[0]}") or {}
        return s, out, [g["id"] for g in info.get("genres", [])]

    taste, total = {}, 0.0
    with ThreadPoolExecutor(8) as ex:
        for s, res, genres in ex.map(recs, seeds):
            w = weight(s[1], s[2])
            if w > 0:
                total += w
                for g in genres:
                    taste[g] = taste.get(g, 0) + w
            for rank, r in enumerate(res):
                if (kind, r["id"]) in seen or anime(r) or noise(kind, r) or not r.get("backdrop_path"):
                    continue
                if r.get("vote_count", 0) < (150 if kind == "movie" else 60):
                    continue
                c = w * (1 - rank / 45)
                score[r["id"]] = score.get(r["id"], 0) + c
                hits[r["id"]] = hits.get(r["id"], 0) + (1 if w > 0 else 0)
                data[r["id"]] = r
                if c > owe.get(r["id"], (None, 0))[1]:
                    owe[r["id"]] = (s[0], c)
    taste = {g: v / max(total, 1e-6) for g, v in taste.items()}            # 0..1: share of the seeds with the genre
    floor = 6.2 if kind == "movie" else 6.8
    for i in list(score):
        r = data[i]
        va = r.get("vote_average", 0)
        if va < floor:
            score[i] = 0
            continue
        year = int(((r.get("release_date") or r.get("first_air_date") or "1900")[:4]) or 1900)
        if kind == "tv":
            age = 1.0 if year >= 2012 else 0.75 if year >= 2005 else 0.4
        else:
            age = 1.0 if year >= 2012 else 0.8 if year >= 2000 else 0.5
        gs = r.get("genre_ids") or []
        fit = 0.65 + 0.7 * (sum(taste.get(g, 0) for g in gs) / len(gs) if gs else 0.3)
        quality = min(1.2, max(0.15, (va - 5.8) / 1.7))
        famous = r.get("vote_count", 0) > (15000 if kind == "movie" else 5000) and year <= TODAY.year - 3
        score[i] *= (1 + 0.25 * (hits[i] - 1)) * age * fit * quality * (0.6 if famous else 1.0)
    ranked = [i for i in sorted(score, key=lambda i: -score[i]) if score[i] > 0]
    if kind == "movie":
        ranked = first_films(ranked[:220], score, data, seen)
    out, per_seed = [], {}
    for i in ranked:
        sd = owe.get(i, (None, 0))[0]
        if per_seed.get(sd, 0) >= 8:
            continue
        per_seed[sd] = per_seed.get(sd, 0) + 1
        out.append(data[i])
    return S.rows(kind, out, SIZE)


def first_films(ranked, score, data, seen):
    """a later film of a series stands in for the series: suggest the first film he has not seen, once per series"""
    with ThreadPoolExecutor(8) as ex:
        info = dict(zip(ranked, ex.map(lambda i: tmdb(f"/movie/{i}") or {}, ranked)))
    colls = {}
    for i in ranked:
        c = (info[i].get("belongs_to_collection") or {}).get("id")
        if c and c not in colls:
            colls[c] = None
    with ThreadPoolExecutor(8) as ex:
        for c, d in zip(list(colls), ex.map(lambda c: tmdb(f"/collection/{c}") or {}, list(colls))):
            parts = [p for p in d.get("parts", []) if p.get("release_date") and p["release_date"] <= TODAY.isoformat()]
            colls[c] = sorted(parts, key=lambda p: p["release_date"])
    out, used = [], set()
    for i in ranked:
        c = (info[i].get("belongs_to_collection") or {}).get("id")
        if not c or not colls.get(c):
            out.append(i)
            continue
        if c in used:
            continue
        used.add(c)
        parts = colls[c]
        nxt = next((p for p in parts if ("movie", p["id"]) not in seen), None)
        if nxt is None:
            continue
        if nxt["id"] != i:
            if not nxt.get("backdrop_path") or anime(nxt) or nxt.get("vote_average", 0) < 6.0:
                continue
            data[nxt["id"]] = nxt
            score[nxt["id"]] = score[i]
        out.append(nxt["id"])
    return out


def main():
    S.IMDB = S.ImdbCache()
    cats = [write("home-trending-movies", "movie", "Trending Movies", trending("movie")),
            write("home-trending-series", "series", "Trending Series", trending("tv"))]
    if "--no-simkl" not in sys.argv:
        seen, seeds = simkl_history()
        print(f"Simkl: {len(seen)} titles on his lists, seeds {len(seeds['movie'])} films / {len(seeds['tv'])} shows")
        cats += [write("home-foryou-movies", "movie", "For You · Movies", for_you("movie", seen, seeds["movie"])),
                 write("home-foryou-series", "series", "For You · Series", for_you("tv", seen, seeds["tv"]))]
    man = json.load(open(L("manifest.json"), encoding="utf-8"))
    ids = {c["id"] for c in cats}
    man["catalogs"] = cats + [c for c in man["catalogs"] if c["id"] not in ids]
    json.dump(man, open(L("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    S.IMDB.save()


if __name__ == "__main__":
    main()
