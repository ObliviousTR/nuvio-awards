"""Stress test of the tr-proxy worker the way the app uses it: many parallel catalog + meta requests."""
import concurrent.futures as cf, json, os, time, urllib.error, urllib.parse, urllib.request
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
DIRECT = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
H = {"Authorization": "Bearer " + tok, "User-Agent": "nuvio-awards", "Content-Type": "application/json"}
sub = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain", headers=H), timeout=60).read())["result"]["subdomain"]
WORK = f"https://nuvio-tr.{sub}.workers.dev{PATH}"
OUT = "refs/trproxy"; os.makedirs(OUT, exist_ok=True)
rep = []


def get(url):
    t0 = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=60)
        b = r.read()
        try:
            j = json.loads(b)
        except Exception:
            j = None
        return r.status, j, b[:160], round(time.time() - t0, 2)
    except urllib.error.HTTPError as e:
        return e.code, None, e.read()[:200], round(time.time() - t0, 2)
    except Exception as e:
        return 0, None, str(e)[:160].encode(), round(time.time() - t0, 2)


man = get(DIRECT + "/manifest.json")[1]
cats = [(c["type"], c["id"]) for c in man["catalogs"] if not any(e.get("isRequired") for e in c.get("extra", []))][:30]
# the Netflix TR series ids for meta requests
_, nf, _, _ = get(DIRECT + "/catalog/series/flixpatrol.netflix.tr.series.json")
ids = [("series", m["id"]) for m in (nf or {}).get("metas", [])[:10]]
_, nm, _, _ = get(DIRECT + "/catalog/movie/flixpatrol.netflix.tr.movie.json")
ids += [("movie", m["id"]) for m in (nm or {}).get("metas", [])[:10]]
rep.append(f"meta ids sample: {[i for _, i in ids[:6]]}")
jobs = [f"/catalog/{t}/{c}.json" for t, c in cats] + [f"/meta/{t}/{i}.json" for t, i in ids]
for rnd in range(2):
    with cf.ThreadPoolExecutor(24) as ex:
        res = list(ex.map(lambda p: (p, get(WORK + p)), jobs))
    bad = [(p, s, b) for p, (s, j, b, t) in res if s != 200 or j is None]
    rep.append(f"round {rnd + 1}: {len(res)} parallel requests, {len(bad)} failed; slowest {max(t for _, (_, _, _, t) in res)}s")
    for p, s, b in bad[:8]:
        rep.append(f"   FAIL {s} {p.split('/')[1]} {b!r}")
# compare one Turkish series fully
for t, i in ids[:3]:
    a = get(WORK + f"/meta/{t}/{i}.json")[1] or {}
    d = get(DIRECT + f"/meta/{t}/{i}.json")[1] or {}
    ma, md = a.get("meta") or {}, d.get("meta") or {}
    diff = sorted(k for k in set(ma) | set(md) if ma.get(k) != md.get(k))
    rep.append(f"{i}: name {ma.get('name')!r} vs {md.get('name')!r}; fields that differ: {diff}; videos {len(ma.get('videos') or [])}/{len(md.get('videos') or [])}")
# Cloudflare analytics (if the token may read them)
q = {"query": """query($a:String!,$s:Time!){viewer{accounts(filter:{accountTag:$a}){workersInvocationsAdaptive(limit:20,filter:{datetime_geq:$s,scriptName:"nuvio-tr"}){sum{requests errors subrequests}quantiles{cpuTimeP50 cpuTimeP99} dimensions{status}}}}}""",
     "variables": {"a": acct, "s": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 6 * 3600))}}
try:
    r = json.loads(urllib.request.urlopen(urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", data=json.dumps(q).encode(), headers=H), timeout=60).read())
    rows = (((r.get("data") or {}).get("viewer") or {}).get("accounts") or [{}])[0].get("workersInvocationsAdaptive")
    rep.append(f"analytics: {json.dumps(rows) if rows is not None else json.dumps(r.get('errors'))[:400]}")
except Exception as e:
    rep.append(f"analytics: {e}")
txt = "\n".join(rep).replace(PATH, "<path>").replace(u.netloc, "<aio-host>")
open(f"{OUT}/stress.txt", "w").write(txt + "\n"); print(txt)
