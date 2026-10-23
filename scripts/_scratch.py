"""Follow-up: what exactly differs (manifest, 6 non-Turkish metas), and do bursts get 429 directly as well?"""
import concurrent.futures as cf, json, os, time, urllib.error, urllib.parse, urllib.request
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
D = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
sub = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain",
      headers={"Authorization": "Bearer " + tok}), timeout=60).read())["result"]["subdomain"]
W = f"https://nuvio-tr.{sub}.workers.dev{PATH}"
OUT = "refs/tracc"; os.makedirs(OUT, exist_ok=True)
def get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=60)
        return r.status, json.loads(r.read()), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, None, dict(e.headers)
    except Exception as e:
        return 0, None, {}
def diff(a, b, p=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), p + "/" + k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for n, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{p}[{n}]")
    elif a != b:
        out.append(f"{p}: worker={json.dumps(a, ensure_ascii=False)[:150]} | direct={json.dumps(b, ensure_ascii=False)[:150]}")
    return out
rep = []
for p in ["/manifest.json", "/meta/series/tt6320628.json", "/meta/movie/tt1365519.json", "/meta/series/tt3416828.json",
          "/meta/series/mal:11061.json", "/meta/series/mal:20.json", "/meta/movie/tt8398600.json"]:
    s1, a, _ = get(W + p); s2, b, _ = get(D + p)
    d = diff(a, b)
    rep.append(f"== {p}: {s1}/{s2}, {len(d)} differences")
    rep += ["   " + x for x in d[:6]]
    # same request twice directly: is it stable at all?
    s3, c, _ = get(D + p)
    rep.append(f"   direct vs direct again: {len(diff(b, c))} differences")
# bursts: direct and worker, alternately, same 60 URLs
man = get(D + "/manifest.json")[1]
cats = [(c["type"], c["id"]) for c in man["catalogs"]][:20]
paths = [f"/catalog/{t}/{c}.json" for t, c in cats]
ids = []
for t, c in cats[:6]:
    m = get(f"{D}/catalog/{t}/{c}.json")[1] or {}
    ids += [f"/meta/{x.get('type') or t}/{x['id']}.json" for x in m.get("metas", [])[:7]]
paths += ids[:40]
for rnd in range(3):
    for lab, base in (("direct", D), ("worker", W)):
        time.sleep(20)
        with cf.ThreadPoolExecutor(30) as ex:
            res = list(ex.map(lambda p: get(base + p), paths))
        codes = {}
        for s, _, h in res:
            codes[s] = codes.get(s, 0) + 1
        ra = [h.get("Retry-After") or h.get("retry-after") for s, _, h in res if s == 429][:1]
        rep.append(f"burst {rnd + 1} {lab}: {len(paths)} parallel -> {codes} retry-after {ra}")
txt = "\n".join(rep)
for s in (PATH, urllib.parse.quote(PATH, safe=""), PATH.split("/")[-1], u.netloc):
    txt = txt.replace(s, "<x>")
open(f"{OUT}/followup.txt", "w").write(txt + "\n"); print(txt)
