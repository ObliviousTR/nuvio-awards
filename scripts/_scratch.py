"""1) Anime revisions: cut-out art (fanart.tv) + backdrops for the new cards.
2) Genres: what the popular films' landscape key art (titled backdrops) looks like per genre, with stricter picks."""
import datetime as dt, json, os, sys, urllib.request
sys.path.insert(0, "scripts")
sys.path.insert(0, "art_tools")
from spotlight import tmdb
import spotlight_art as art

FA = os.environ["FANART_API_KEY"]
log = []


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}), timeout=60).read()


# ---------------------------------------------------------------- anime
A = "refs/anime2"
os.makedirs(A, exist_ok=True)
SHOWS = [("apothecary", "tv", 220542), ("jjk", "tv", 95479), ("kaguya", "tv", 83121), ("aot", "tv", 1429),
         ("eva", "tv", 890), ("eva_movie", "movie", 283566), ("frieren", "tv", 209867), ("totoro", "movie", 8392),
         ("spirited", "movie", 129)]
for slug, kind, tid in SHOWS:
    d = f"{A}/{slug}"
    os.makedirs(d, exist_ok=True)
    try:
        im = tmdb(f"/{kind}/{tid}/images", include_image_language="null,en,ja") or {}
        for i, p in enumerate(sorted(im.get("backdrops", []), key=lambda x: -x.get("vote_count", 0))[:12]):
            open(f"{d}/bd{i:02d}_{p.get('iso_639_1')}.jpg", "wb").write(get(art.IMG + "w1280" + p["file_path"]))
        for i, p in enumerate(sorted(im.get("posters", []), key=lambda x: -x.get("vote_count", 0))[:6]):
            open(f"{d}/po{i:02d}_{p.get('iso_639_1')}.jpg", "wb").write(get(art.IMG + "w780" + p["file_path"]))
        if kind == "tv":
            tvdb = (tmdb(f"/tv/{tid}/external_ids") or {}).get("tvdb_id")
            fa = json.loads(get(f"https://webservice.fanart.tv/v3/tv/{tvdb}?api_key={FA}"))
            keys = ("characterart", "hdclearart", "clearart")
        else:
            fa = json.loads(get(f"https://webservice.fanart.tv/v3/movies/{tid}?api_key={FA}"))
            keys = ("hdmovieclearart", "movieart", "clearart")
        for k in keys:
            for i, x in enumerate(fa.get(k, [])[:20]):
                open(f"{d}/fa_{k}{i:02d}_{x.get('lang', '')}.png", "wb").write(get(x["url"]))
        log.append(f"{slug}: ok")
    except Exception as e:
        log.append(f"{slug}: {e}")

# ---------------------------------------------------------------- genres
G = "refs/genres2"
os.makedirs(G, exist_ok=True)
GEN = {"comedy": ("35", "28|878|27|53|80|10752|14"), "animation": ("16", "27"), "action": ("28", "35|27|10749|16"),
       "horror": ("27", "35|16|10751"), "romance": ("10749", "28|27|878|53|80"), "drama": ("18", "28|35|27|878|14|16"),
       "scifi": ("878|14", "35|27|16"), "crime": ("80", "35|16|878|14"), "thriller": ("53|9648", "35|16|10751"),
       "war": ("10752", "35|16"), "western": ("37", "35|16")}
since = (dt.date.today() - dt.timedelta(days=4 * 365)).isoformat()
for g, (wg, wo) in GEN.items():
    p = {"with_genres": wg, "without_genres": wo + ("" if g == "animation" else "|16|99"), "sort_by": "popularity.desc",
         "with_original_language": "en", "vote_count.gte": 300, "primary_release_date.gte": since}
    r = (tmdb("/discover/movie", **p) or {}).get("results", [])
    first = wg.split("|")
    r = [x for x in r if x.get("genre_ids") and str(x["genre_ids"][0]) in first]   # the genre leads, not a side tag
    rows = []
    for x in r[:8]:
        im = tmdb(f"/movie/{x['id']}/images", include_image_language="en,null") or {}
        bds = im.get("backdrops", [])
        titled = sorted([b for b in bds if b.get("iso_639_1") == "en"], key=lambda b: (-b["vote_count"], -b["vote_average"]))
        plain = sorted([b for b in bds if not b.get("iso_639_1")], key=lambda b: (-b["vote_count"], -b["vote_average"]))
        for tag, lst in (("en", titled), ("na", plain)):
            if lst:
                open(f"{G}/{g}__{x['id']}_{tag}.jpg", "wb").write(get(art.IMG + "w780" + lst[0]["file_path"]))
        rows.append(f"{x['id']} {x['title']} {x['genre_ids']} en={len(titled)} plain={len(plain)}")
    log.append(f"[{g}] " + " | ".join(rows))
open("refs/log.txt", "w").write("\n".join(log))
