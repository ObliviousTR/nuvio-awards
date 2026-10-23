"""Turkish productions keep their own name and logo: builds trmeta/map.json for the tr-proxy worker.

Every Turkish-original film and series on TMDB (at least one vote) -> original title, Turkish overview, best Turkish
logo (png) and Turkish poster. Keys are "<stremio type>|<id>" for every id form AIOMetadata uses: tt..., tmdb:N, tvdb:N.
Published for the worker as trmeta/keys.txt (one key per line, to tell quickly whether a title is Turkish) and
trmeta/s/<xx>.json (the data, in 256 shards by FNV-1a hash of the key, so the worker only reads what it needs).
External ids and images are cached (trmeta/cache.json) and refreshed after 30 days, so a daily run is quick.
usage: python3 scripts/tr_titles.py   (TMDB_API_KEY)
"""
import datetime, json, os, sys, time, urllib.error, urllib.parse, urllib.request

KEY = os.environ["TMDB_API_KEY"].strip()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "trmeta", "cache.json")
OUT = os.path.join(ROOT, "trmeta", "map.json")
TODAY = datetime.date.today()
STALE = 30


def tmdb(path, **q):
    q["api_key"] = KEY
    u = f"https://api.themoviedb.org/3/{path}?" + urllib.parse.urlencode(q)
    for attempt in range(5):
        try:
            return json.loads(urllib.request.urlopen(u, timeout=60).read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * attempt)
        except Exception:
            time.sleep(2 + 3 * attempt)
    return None


def discover(kind):
    """all Turkish-original titles with a vote, year by year (TMDB stops at 500 pages per query)"""
    field = "primary_release_year" if kind == "movie" else "first_air_date_year"
    ids = {}
    for year in range(1914, TODAY.year + 2):
        page, pages = 1, 1
        while page <= min(pages, 500):
            d = tmdb(f"discover/{kind}", with_original_language="tr", **{field: year, "vote_count.gte": 1},
                     sort_by="popularity.desc", page=page, include_adult="false")
            if not d:
                break
            pages = d.get("total_pages", 1)
            for r in d.get("results", []):
                ids[r["id"]] = r.get("original_title") or r.get("original_name") or ""
            page += 1
    return ids


def best(arr, lang, png=False):
    a = [x for x in arr or [] if x.get("iso_639_1") == lang and (not png or x.get("file_path", "").endswith(".png"))]
    return max(a, key=lambda x: (x.get("vote_average", 0), x.get("vote_count", 0), x.get("width", 0)))["file_path"] if a else None


def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    out, n_new = {}, 0
    for kind, st in (("movie", "movie"), ("tv", "series")):
        found = discover(kind)
        print(f"{kind}: {len(found)} Turkish titles", flush=True)
        for tid, orig in found.items():
            ck = f"{kind}:{tid}"
            c = cache.get(ck)
            if not c or "o" not in c or (TODAY - datetime.date.fromisoformat(c["d"])).days > STALE:
                d = tmdb(f"{kind}/{tid}", language="tr-TR", append_to_response="external_ids,images",
                         include_image_language="tr") or {}
                ext, im = d.get("external_ids") or {}, d.get("images") or {}
                c = {"d": TODAY.isoformat(), "tt": ext.get("imdb_id") or None, "tvdb": ext.get("tvdb_id") or None,
                     "l": best(im.get("logos"), "tr", png=True), "p": best(im.get("posters"), "tr"),
                     "o": (d.get("overview") or "").strip()}
                cache[ck] = c
                n_new += 1
            entry = [orig, c["l"], c["p"], c["o"]]
            out[f"{st}|tmdb:{tid}"] = entry
            if c["tt"]:
                out[f"{st}|{c['tt']}"] = entry
            if c["tvdb"]:
                out[f"{st}|tvdb:{c['tvdb']}"] = entry
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"v": 2, "date": TODAY.isoformat(), "img": "https://image.tmdb.org/t/p/", "items": out},
              open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    d = os.path.join(ROOT, "trmeta")
    open(os.path.join(d, "keys.txt"), "w").write("\n".join(sorted(out)) + "\n")
    shards = {}
    for k, v in out.items():
        shards.setdefault(f"{fnv(k) % 256:02x}", {})[k] = v
    os.makedirs(os.path.join(d, "s"), exist_ok=True)
    for f in os.listdir(os.path.join(d, "s")):
        os.remove(os.path.join(d, "s", f))
    for h, v in shards.items():
        json.dump(v, open(os.path.join(d, "s", h + ".json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"map: {len(out)} keys in {len(shards)} shards, {n_new} titles looked up today")


def fnv(key):
    """FNV-1a 32-bit over the UTF-8 key - the worker computes the same"""
    h = 0x811C9DC5
    for b in key.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


if __name__ == "__main__":
    main()
