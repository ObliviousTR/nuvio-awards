"""TR proxy v2 acceptance test against Ozzy's real AIOMetadata (nothing secret is written out).
1 catalogs: every catalog through the worker vs directly - same items, same order; only Turkish items may differ
2 details: every item's meta through the worker vs directly - non-Turkish byte-identical, Turkish: only
  name/description/logo/poster differ, episodes identical
3 what TMDB Artwork enrichment (now off) would have added where AIOMetadata has no logo / background
4 load: parallel bursts through the worker, plus Cloudflare's own error and CPU figures
5 a contact sheet of Turkish titles as the app will show them"""
import collections, concurrent.futures as cf, io, json, os, time, urllib.error, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
D = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
CH = {"Authorization": "Bearer " + tok, "User-Agent": "nuvio-awards", "Content-Type": "application/json"}
sub = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain", headers=CH), timeout=60).read())["result"]["subdomain"]
W = f"https://nuvio-tr.{sub}.workers.dev{PATH}"
TMDB = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/tracc"; os.makedirs(OUT, exist_ok=True)
KEYS = set(open("trmeta/keys.txt").read().split("\n"))
DATA = json.load(open("trmeta/map.json"))["items"]
T0 = time.time()


def get(url, raw=False, tries=4):
    err = None
    for a in range(tries):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=90).read()
            return b if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code == 404:
                break
        except Exception as e:
            err = type(e).__name__
        time.sleep(2 + 3 * a)
    raise RuntimeError(err)


def safe(f, *a):
    try:
        return f(*a)
    except Exception as e:
        return {"_err": str(e)}


rep, fails = [], []
man_w, man_d = get(W + "/manifest.json"), get(D + "/manifest.json")
rep.append(f"manifest identical: {man_w == man_d}")
if man_w != man_d:
    fails.append("manifest differs")
cats = [(c["type"], c["id"]) for c in man_d["catalogs"] if not any(e.get("name") == "search" and e.get("isRequired") for e in c.get("extra", []))]

# 1 catalogs
def catpair(tc):
    t, c = tc
    return tc, safe(get, f"{W}/catalog/{t}/{c}.json"), safe(get, f"{D}/catalog/{t}/{c}.json")
items, n_tr_cat = {}, 0
with cf.ThreadPoolExecutor(3) as ex:
    for (t, c), a, b in ex.map(catpair, cats):
        if "_err" in a or "_err" in b:
            if a.get("_err") != b.get("_err"):
                fails.append(f"catalog {c}: worker {a.get('_err')} direct {b.get('_err')}")
            continue
        ma, mb = a.get("metas", []), b.get("metas", [])
        if [x.get("id") for x in ma] != [x.get("id") for x in mb]:
            fails.append(f"catalog {c}: items differ")
            continue
        for x, y in zip(ma, mb):
            k = f"{y.get('type') or t}|{y['id']}"
            if k in KEYS:
                n_tr_cat += 1
                extra = {f for f in set(x) | set(y) if x.get(f) != y.get(f)} - {"name", "description", "logo", "poster"}
                if extra or x.get("name") != DATA[k][0]:
                    fails.append(f"catalog {c} Turkish {y['id']}: unexpected {sorted(extra)} name {x.get('name')!r}")
            elif x != y:
                fails.append(f"catalog {c} non-Turkish {y['id']} changed")
        for y in mb[:15]:
            items[(y.get("type") or t, y["id"])] = y.get("name")
rep.append(f"1 catalogs: {len(cats)} checked, {n_tr_cat} Turkish entries rewritten, failures so far {len(fails)}")

# 2 details
ids = [k for k in items if k[0] in ("movie", "series")]
def metapair(k):
    t, i = k
    return k, safe(get, f"{W}/meta/{t}/{i}.json"), safe(get, f"{D}/meta/{t}/{i}.json")
stats = collections.Counter()
tr_rows, direct_metas = [], {}
with cf.ThreadPoolExecutor(3) as ex:
    for (t, i), a, b in ex.map(metapair, ids):
        if "_err" in a or "_err" in b:
            stats["error (both)" if a.get("_err") and b.get("_err") else "error (one side)"] += 1
            if bool(a.get("_err")) != bool(b.get("_err")):
                fails.append(f"meta {i}: worker {a.get('_err')} direct {b.get('_err')}")
            continue
        ma, mb = a.get("meta") or {}, b.get("meta") or {}
        direct_metas[(t, i)] = mb
        k = f"{t}|{i}"
        if k not in KEYS:
            stats["non-Turkish identical" if ma == mb else "non-Turkish CHANGED"] += 1
            if ma != mb:
                fails.append(f"meta {i} non-Turkish changed")
            continue
        e = DATA[k]
        diff = {f for f in set(ma) | set(mb) if ma.get(f) != mb.get(f)}
        ok = (not (diff - {"name", "description", "logo", "poster"}) and ma.get("name") == e[0]
              and [v.get("id") for v in ma.get("videos") or []] == [v.get("id") for v in mb.get("videos") or []]
              and (("image.tmdb.org" in (ma.get("logo") or "")) if e[1] else not ma.get("logo")))
        stats["Turkish ok" if ok else "Turkish WRONG"] += 1
        if not ok:
            fails.append(f"meta {i} Turkish: diff {sorted(diff)}")
        tr_rows.append((i, mb.get("name"), ma.get("name"), bool(e[1]), bool(e[3]), len(ma.get("videos") or []), ma.get("poster"), ma.get("logo")))
rep.append(f"2 details: {len(ids)} titles - {dict(stats)}")
for i, old, new, lg, ov, nv, _, _ in tr_rows:
    rep.append(f"   {old!r} -> {new!r}  Turkish logo {'yes' if lg else 'no (name as text)'}; Turkish overview {'yes' if ov else 'no'}; episodes {nv}")

# 3 what Artwork enrichment would have added
def tm(p, **q):
    q["api_key"] = TMDB
    return safe(get, f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q))
gain = collections.Counter()
for (t, i), m in direct_metas.items():
    need_logo, need_bg = not m.get("logo"), not m.get("background") or "missing_" in str(m.get("background"))
    if not (need_logo or need_bg):
        continue
    tid = m.get("_tmdbId") or (i.split(":")[1] if i.startswith("tmdb:") else None)
    if not tid:
        gain["no TMDB id"] += 1
        continue
    im = tm(f"{'tv' if t == 'series' else 'movie'}/{tid}/images", include_image_language="en,null")
    if need_logo:
        gain["logo missing; TMDB has en/neutral logo" if im.get("logos") else "logo missing; TMDB has none either"] += 1
    if need_bg:
        gain["background missing; TMDB has one" if im.get("backdrops") else "background missing; TMDB has none either"] += 1
rep.append(f"3 Artwork off costs: {dict(gain)}  (out of {len(direct_metas)} titles)")

# 4 load
burst = [f"{W}/meta/{t}/{i}.json" for t, i in ids[:40]] + [f"{W}/catalog/{t}/{c}.json" for t, c in cats[:20]]
for r in range(2):
    t1 = time.time()
    with cf.ThreadPoolExecutor(30) as ex:
        res = list(ex.map(lambda x: safe(get, x, False, 1), burst))
    bad = [x.get("_err") for x in res if isinstance(x, dict) and "_err" in x]
    rep.append(f"4 burst {r + 1}: {len(burst)} parallel, {len(bad)} failed {collections.Counter(bad).most_common(3)} in {time.time() - t1:.1f}s")
    if bad:
        fails.append(f"burst {r + 1}: {len(bad)} failed")
q = {"query": """query($a:String!,$s:Time!){viewer{accounts(filter:{accountTag:$a}){workersInvocationsAdaptive(limit:20,filter:{datetime_geq:$s,scriptName:"nuvio-tr"}){sum{requests errors subrequests}quantiles{cpuTimeP50 cpuTimeP99} dimensions{status}}}}}""",
     "variables": {"a": acct, "s": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(T0 - 120))}}
time.sleep(60)
try:
    r = json.loads(urllib.request.urlopen(urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", data=json.dumps(q).encode(), headers=CH), timeout=60).read())
    rows = r["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"]
    rep.append(f"   Cloudflare during this test: {json.dumps(rows)}")
    if any(x["dimensions"]["status"] != "success" or x["sum"]["errors"] for x in rows):
        fails.append("Cloudflare reports worker errors")
except Exception as e:
    rep.append(f"   Cloudflare analytics unavailable: {e}")

# 5 contact sheet
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = ImageFont.truetype(F, 17) if os.path.exists(F) else ImageFont.load_default()
rows = tr_rows[:12]
cv = Image.new("RGB", (40 + 300 * 6, 40 + 560 * ((len(rows) + 5) // 6)), (20, 20, 24)); dr = ImageDraw.Draw(cv)
for n, (i, old, new, lg, ov, nv, poster, logo) in enumerate(rows):
    x, y = 20 + 300 * (n % 6), 20 + 560 * (n // 6)
    try:
        p = Image.open(io.BytesIO(get(poster, raw=True))).convert("RGB"); p.thumbnail((270, 405)); cv.paste(p, (x, y))
    except Exception:
        dr.text((x, y + 180), "(poster failed)", font=font, fill=(255, 90, 90))
    if logo:
        try:
            L = Image.open(io.BytesIO(get(logo, raw=True))).convert("RGBA"); L.thumbnail((250, 70))
            bg = Image.new("RGBA", (270, 80), (60, 60, 68, 255)); bg.alpha_composite(L, ((270 - L.width) // 2, (80 - L.height) // 2)); cv.paste(bg.convert("RGB"), (x, y + 412))
        except Exception:
            pass
    else:
        dr.text((x + 8, y + 440), "(no logo: name as text)", font=font, fill=(150, 150, 160))
    dr.text((x, y + 500), new or "?", font=font, fill=(240, 240, 240))
cv.save(f"{OUT}/sheet.jpg", quality=86)

rep.insert(0, "RESULT: " + ("PASS" if not fails else f"FAIL ({len(fails)})"))
rep += ["", "failures:"] + fails[:40]
txt = "\n".join(rep)
for s in (PATH, urllib.parse.quote(PATH, safe=""), PATH.split("/")[-1], u.netloc, TMDB):
    if s:
        txt = txt.replace(s, "<x>")
open(f"{OUT}/report.txt", "w").write(txt + "\n"); print(txt)
