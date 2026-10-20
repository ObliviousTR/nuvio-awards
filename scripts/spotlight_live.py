"""Keeps the Spotlight pool alive.

topical(): on a rotation day, The Headliner and The Saga first look at what is opening in cinemas around now
  (English-language theatrical releases from 7 days ago to 21 days ahead): the top-billed star of a big new film,
  or the franchise a new film belongs to. A subject shown in the last 365 days is never picked this way.
grow(): once a week, new candidates are added to spotlight/pool_auto.json (separate from the hand-made pool.json):
  stars and directors of popular new films and franchises with a new chapter (studios stay hand-picked).
  Names listed under "removed" in pool_auto.json are never added again.
"""
import datetime as dt, json, os, re

TOPICAL_SLOTS = ("headliner", "saga")
GROW_CAP = 3          # new entries per card per week
STAR_POPULARITY = 8   # TMDB person popularity a "star" needs
_releases = {}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def releases(tmdb, today, back, ahead, pages=2):
    """Popular English-language theatrical releases (US) in the window, most popular first, animation excluded."""
    key = (today, back, ahead)
    if key not in _releases:
        res = []
        for page in range(1, pages + 1):
            d = tmdb("/discover/movie", page=page, region="US", with_release_type="2|3",
                     **{"release_date.gte": (today - dt.timedelta(days=back)).isoformat(),
                        "release_date.lte": (today + dt.timedelta(days=ahead)).isoformat(),
                        "with_original_language": "en", "without_genres": "16|99",
                        "sort_by": "popularity.desc", "include_adult": "false"}) or {}
            res += d.get("results", [])
            if page >= d.get("total_pages", 0):
                break
        _releases[key] = res
    return _releases[key]


def stars(tmdb, movie_id, top=2):
    cast = (tmdb(f"/movie/{movie_id}/credits") or {}).get("cast", [])
    return [c for c in cast if c.get("order", 99) < top and c.get("known_for_department") == "Acting"
            and c.get("popularity", 0) >= STAR_POPULARITY]


def directors(tmdb, movie_id):
    crew = (tmdb(f"/movie/{movie_id}/credits") or {}).get("crew", [])
    return [c for c in crew if c.get("job") == "Director"]


def collection_of(tmdb, movie_id, min_parts=3):
    det = tmdb(f"/movie/{movie_id}") or {}
    col = det.get("belongs_to_collection")
    if not col:
        return None
    full = tmdb(f"/collection/{col['id']}") or {}
    parts = [p for p in full.get("parts", []) if 16 not in (p.get("genre_ids") or [])]
    out_now = [p for p in parts if p.get("release_date") and p["release_date"] <= dt.date.today().isoformat()]
    if len(parts) < min_parts or len(out_now) < 2:
        return None
    return {"id": col["id"], "name": re.sub(r"\s*(?:\(.*?\)\s*)?Collection$", "", col["name"]).strip(), "film": det}


def collection_ids(tmdb, state, entry):
    """TMDB ids of a pool saga's collections (names resolved once, cached in state)."""
    cache = state.setdefault("collection_ids", {})
    out = []
    for c in entry.get("collections", []):
        if isinstance(c, int):
            out.append(c)
            continue
        if c not in cache:
            res = (tmdb("/search/collection", query=c) or {}).get("results", [])
            exact = [r for r in res if norm(r["name"]) == norm(c)]
            cache[c] = (exact or res or [{"id": None}])[0]["id"]
        if cache[c]:
            out.append(cache[c])
    return out


def _recent(hist, name, today, days=365):
    last = hist.get(name)
    return bool(last) and last > (today - dt.timedelta(days=days)).isoformat()


def topical(slot, tmdb, today, pool_entries, hist, state):
    """[(entry, tag)] for subjects tied to films opening now; pool entries are reused when they match."""
    out, seen = [], set()
    by_name = {norm(e["name"]): e for e in pool_entries}
    for r in releases(tmdb, today, 7, 21)[:12]:
        title, date = r.get("title"), r.get("release_date", "")
        when = "In theaters now" if date <= today.isoformat() else "Coming to theaters"
        if slot == "headliner":
            for c in stars(tmdb, r["id"]):
                if norm(c["name"]) in seen or _recent(hist, c["name"], today):
                    continue
                seen.add(norm(c["name"]))
                out.append((by_name.get(norm(c["name"])) or {"name": c["name"], "auto": True},
                            f"{when}: {title}"))
        elif slot == "saga":
            col = collection_of(tmdb, r["id"])
            if not col or col["id"] in seen:
                continue
            seen.add(col["id"])
            entry = next((e for e in pool_entries if col["id"] in collection_ids(tmdb, state, e)), None)
            entry = entry or {"name": col["name"], "collections": [col["id"]], "auto": True}
            if not _recent(hist, entry["name"], today):
                out.append((entry, f"New chapter · {title}"))
    return out


def grow(tmdb, today, pool, auto, state, log):
    """Weekly: add fresh candidates to the auto pool. Returns {slot: [names added]}."""
    last = state.get("grown")
    if last and last > (today - dt.timedelta(days=7)).isoformat():
        return {}
    state["grown"] = today.isoformat()
    removed = {norm(x) for x in auto.get("removed", [])}
    known = {slot: {norm(e["name"]) for e in pool[slot]} | {norm(e.get("title", "")) for e in pool[slot]} | removed
             for slot in ("headliner", "visionary", "powerhouse", "saga")}
    known_cols = {i for e in pool["saga"] for i in collection_ids(tmdb, state, e)}
    added = {k: [] for k in known}

    def worth(slot, entry):
        """Cheap check that the card would have enough to show (same minimums as the rotation)."""
        if slot == "powerhouse":
            d = tmdb("/discover/movie", with_companies=entry["company"][0], without_genres="16",
                     **{"vote_count.gte": 50}) or {}
            return d.get("total_results", 0) >= 15
        if slot in ("headliner", "visionary"):
            hit = ((tmdb("/search/person", query=entry["name"]) or {}).get("results") or [None])[0]
            if not hit:
                return False
            cr = tmdb(f"/person/{hit['id']}/movie_credits") or {}
            if slot == "visionary":
                return sum(c.get("job") == "Director" for c in cr.get("crew", [])) >= 3
            return sum(c.get("vote_count", 0) >= 20 for c in cr.get("cast", [])) >= 6
        return True

    def add(slot, entry):
        if len(added[slot]) >= GROW_CAP or norm(entry["name"]) in known[slot]:
            return
        known[slot].add(norm(entry["name"]))
        if not worth(slot, entry):
            return
        entry.update(auto=True, added=today.isoformat())
        auto.setdefault(slot, []).append(entry)
        added[slot].append(entry["name"])

    films = releases(tmdb, today, 60, 60, pages=3)[:25]
    for r in films:
        for c in stars(tmdb, r["id"]):
            add("headliner", {"name": c["name"]})
        if films.index(r) < 12:
            for c in directors(tmdb, r["id"]):
                add("visionary", {"name": c["name"]})
        col = collection_of(tmdb, r["id"])
        if col and col["id"] not in known_cols:
            known_cols.add(col["id"])
            add("saga", {"name": col["name"], "collections": [col["id"]]})
    # Studios are not grown automatically: the box office credits financiers and co-producers (TSG Entertainment,
    # Pascal Pictures…) far more often than studios worth a spotlight, so The Powerhouse stays hand-picked.
    for slot, names in added.items():
        if names:
            log.append(f"- {slot}: added to the auto pool: {', '.join(names)}")
    return added
