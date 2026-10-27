import os, json, re, urllib.request, urllib.parse
# Home hero quality: how AIOMetadata's catalog items carry their landscape image (host + size only; no secrets out).
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
base = os.environ["AIOMETADATA_URL"].strip().rsplit("/manifest.json", 1)[0]


def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read())


def shape(u):
    if not u:
        return None
    p = urllib.parse.urlsplit(u)
    host = p.netloc if any(h in p.netloc for h in ("tmdb.org", "metahub", "fanart", "trakt", "simkl", "imdb", "postersplus")) else "<other>"
    path = re.sub(r"/[A-Za-z0-9_-]{20,}", "/<id>", p.path)
    return host + path[:80] + (" ?query" if p.query else "")


log = []
man = get(base + "/manifest.json")
cats = [(c["type"], c["id"], c.get("name"), [e["name"] + ("!" if e.get("isRequired") else "") for e in c.get("extra", [])],
         c.get("showInHome")) for c in man.get("catalogs", [])]
json.dump(cats, open(OUT + "/aio_catalogs.json", "w"), indent=1, ensure_ascii=False)
for t, cid, genre in (("movie", "tmdb.trending", "Day"), ("series", "tmdb.trending", "Week"), ("movie", "trakt.trending.movies", None),
                      ("series", "trakt.trending.shows", None), ("movie", "mdblist.205811", None)):
    u = f"{base}/catalog/{t}/{cid}" + (f"/genre={genre}" if genre else "") + ".json"
    try:
        metas = get(u).get("metas", [])
        for m in metas[:3]:
            log.append(f"{t} {cid}: name={m.get('name')!r} background={shape(m.get('background'))} poster={shape(m.get('poster'))} "
                       f"landscape={shape(m.get('landscapePoster'))} logo={shape(m.get('logo'))}")
        log.append(f"{t} {cid}: {len(metas)} items, with background: {sum(1 for m in metas if m.get('background'))}")
    except Exception as e:
        log.append(f"{t} {cid}: error {type(e).__name__}")
open(OUT + "/log.txt", "w").write("\n".join(log)); print("\n".join(log))
