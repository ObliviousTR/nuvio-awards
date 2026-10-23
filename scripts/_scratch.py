"""End-to-end check of the deployed tr-proxy worker (no secrets printed)."""
import json, os, re, urllib.parse, urllib.request
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
DIRECT = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
H = {"Authorization": "Bearer " + tok, "User-Agent": "nuvio-awards"}
sub = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain", headers=H), timeout=60).read())["result"]["subdomain"]
HOST = f"https://nuvio-tr.{sub}.workers.dev"
OUT = "refs/trproxy"; os.makedirs(OUT, exist_ok=True)
rep = [f"worker host: {HOST}"]


import time
TIMES = []


def get(url):
    t0 = time.time()
    try:
        return _get(url)
    finally:
        TIMES.append(round(time.time() - t0, 1))


def _get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}), timeout=90)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


for label, p in [("manifest", "/manifest.json"), ("Muhtesem Yuzyil", "/meta/series/tt1848220.json"),
                 ("Babam ve Oglum", "/meta/movie/tt0476735.json"), ("Kurulus Osman", "/meta/series/tt11093718.json"),
                 ("Breaking Bad (not Turkish)", "/meta/series/tt0903747.json")]:
    s1, a = get(HOST + PATH + p)
    s2, b = get(DIRECT + p)
    if label == "manifest":
        rep.append(f"manifest via worker: HTTP {s1}, same id as direct: {(a or {}).get('id') == (b or {}).get('id')}, catalogs {len((a or {}).get('catalogs', []))}/{len((b or {}).get('catalogs', []))}")
        continue
    ma, mb = (a or {}).get("meta") or {}, (b or {}).get("meta") or {}
    rep.append(f"{label}: worker HTTP {s1} name={ma.get('name')!r} (direct {mb.get('name')!r}); "
               f"logo {'TMDB tr' if 'image.tmdb.org' in (ma.get('logo') or '') else 'unchanged' if ma.get('logo') == mb.get('logo') else 'other'}; "
               f"poster logo_priority={'yes' if 'logo_priority' in (ma.get('poster') or '') else 'no'}; "
               f"episodes {len(ma.get('videos') or [])}/{len(mb.get('videos') or [])}, same ids: {[v.get('id') for v in ma.get('videos') or []] == [v.get('id') for v in mb.get('videos') or []]}")
for cat in ("tmdb.trending", "flixpatrol.netflix.tr.series"):
    for base, lab in ((HOST + PATH, "worker"), (DIRECT, "direct")):
        st, d = get(f"{base}/catalog/series/{cat}.json")
        names = [m.get("name") for m in (d or {}).get("metas", [])[:10]]
        rep.append(f"catalog {cat} {lab}: HTTP {st} {TIMES[-1]}s first: {names}")
rep.append(f"seconds per request (worker, direct pairs in order): {TIMES}")
s, _ = get(HOST + "/stremio/someone-else/manifest.json")
rep.append(f"other paths refused: HTTP {s}")
txt = "\n".join(rep).replace(PATH, "<path>").replace(u.netloc, "<aio-host>")
open(f"{OUT}/report.txt", "w").write(txt + "\n"); print(txt)
