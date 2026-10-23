"""Survey before the TR proxy v2: (1) how often AIOMetadata metas lack poster/background/logo (what TMDB Artwork
enrichment used to cover), (2) Turkish titles in the catalogs and their Turkish logo coverage, (3) Posters+ text
fallback for Turkish titles without a Turkish logo."""
import concurrent.futures as cf, io, json, os, re, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
D = f"{u.scheme}://{u.netloc}{PATH}"
OUT = "refs/trsurvey"; os.makedirs(OUT, exist_ok=True)
MAP = json.load(open("trmeta/map.json"))["items"]


def get(url, raw=False):
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=90).read()
    return r if raw else json.loads(r)


man = get(D + "/manifest.json")
cats = [(c["type"], c["id"]) for c in man["catalogs"] if not any(e.get("isRequired") for e in c.get("extra", []))]
items = {}
def cat(tc):
    t, c = tc
    try:
        return [(m.get("type") or t, m["id"]) for m in get(f"{D}/catalog/{t}/{c}.json").get("metas", [])[:15]]
    except Exception:
        return []
with cf.ThreadPoolExecutor(8) as ex:
    for lst in ex.map(cat, cats):
        for t, i in lst:
            items[(t, i)] = 1
ids = [k for k in items if k[0] in ("movie", "series")]
def meta(k):
    t, i = k
    try:
        return k, get(f"{D}/meta/{t}/{urllib.parse.quote(i)}.json").get("meta") or {}
    except Exception as e:
        return k, {"_err": str(e)}
with cf.ThreadPoolExecutor(8) as ex:
    metas = dict(ex.map(meta, ids))
def bad(v):
    return not v or "missing_" in str(v)
rep = [f"catalogs {len(cats)}, items {len(ids)}"]
miss = {f: [k for k, m in metas.items() if bad(m.get(f))] for f in ("poster", "background", "logo")}
for f, ks in miss.items():
    rep.append(f"missing {f}: {len(ks)}  e.g. {[metas[k].get('name') for k in ks[:8]]}")
rep.append(f"errors: {sum(1 for m in metas.values() if '_err' in m)}")
tr = [(k, m) for k, m in metas.items() if f"{k[0]}|{k[1]}" in MAP]
rep.append(f"Turkish in catalogs: {len(tr)}; with a Turkish logo in our map: {sum(1 for k, m in tr if MAP[f'{k[0]}|{k[1]}'][1])}")
for k, m in tr[:40]:
    e = MAP[f"{k[0]}|{k[1]}"]
    rep.append(f"   {k[1]} {m.get('name')!r} -> {e[0]!r} trlogo={'yes' if e[1] else 'NO'} poster={'P+' if 'postersplus' in str(m.get('poster')) else 'other' if m.get('poster') else 'none'}")
# Posters+ text fallback test on Turkish titles without a Turkish logo
nolog = [(k, m) for k, m in tr if not MAP[f"{k[0]}|{k[1]}"][1] and "postersplus" in str(m.get("poster"))][:4]
tiles = []
for k, m in nolog:
    p = urllib.parse.urlsplit(m["poster"]); q = [(a, b) for a, b in urllib.parse.parse_qsl(p.query) if a != "logo_priority"]
    for lab, lp in (("now", None), ("original,text", "original,text")):
        url = urllib.parse.urlunsplit(p._replace(query=urllib.parse.urlencode(q + ([("logo_priority", lp)] if lp else []))))
        try:
            im = Image.open(io.BytesIO(get(url, raw=True))).convert("RGB"); im.thumbnail((260, 390)); tiles.append((f"{MAP[f'{k[0]}|{k[1]}'][0][:22]} {lab}", im))
        except Exception as e:
            rep.append(f"poster fetch failed {e}")
if tiles:
    cv = Image.new("RGB", (20 + 280 * len(tiles), 440), (24, 24, 28)); dr = ImageDraw.Draw(cv)
    for n, (lab, im) in enumerate(tiles):
        cv.paste(im, (20 + 280 * n, 40)); dr.text((20 + 280 * n, 12), lab, fill=(220, 220, 220))
    cv.save(f"{OUT}/text_fallback.jpg", quality=85)
txt = "\n".join(rep)
for s in (PATH, u.netloc, urllib.parse.quote(PATH, safe=""), PATH.split("/")[-1]):
    txt = txt.replace(s, "<x>")
open(f"{OUT}/survey.txt", "w").write(txt + "\n"); print(txt)
