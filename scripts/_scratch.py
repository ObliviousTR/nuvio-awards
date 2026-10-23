"""Turkish titles test: what AIOMetadata shows now vs the Turkish original title / poster / logo (TMDB)."""
import io, json, os, re, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

TMDB = os.environ["TMDB_API_KEY"].strip()
AIO = os.environ["AIOMETADATA_URL"].strip()
BASE = re.sub(r"/manifest\.json.*$", "", AIO)
OUT = "refs/trtest"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "nuvio-awards/1.0"}
TESTS = [("tv", "Kuruluş: Osman"), ("tv", "Muhteşem Yüzyıl"), ("tv", "Ezel"), ("tv", "Leyla ile Mecnun"),
         ("movie", "G.O.R.A."), ("movie", "Babam ve Oğlum")]


def scrub(s):
    s = str(s).replace(BASE, "<aio>")
    for k in (TMDB,):
        s = s.replace(k, "***")
    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", s)


def js(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())


def img(u, size):
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())).convert("RGBA")
        im.thumbnail(size)
        return im
    except Exception:
        return None


def tmdb(path, **q):
    q["api_key"] = TMDB
    return js(f"https://api.themoviedb.org/3/{path}?" + urllib.parse.urlencode(q))


def pick(arr, lang):
    a = [x for x in arr if x.get("iso_639_1") == lang]
    return max(a, key=lambda x: (x.get("vote_average", 0), x.get("width", 0)))["file_path"] if a else None


F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = ImageFont.truetype(F, 22) if os.path.exists(F) else ImageFont.load_default()
small = ImageFont.truetype(F.replace("-Bold", ""), 17) if os.path.exists(F) else ImageFont.load_default()
rep = []
for kind, q in TESTS:
    r = [x for x in tmdb(f"search/{kind}", query=q, language="tr-TR")["results"] if x.get("original_language") == "tr"]
    if not r:
        rep.append(f"{q}: not found on TMDB"); continue
    tid = r[0]["id"]
    ext = tmdb(f"{kind}/{tid}/external_ids")
    tt = ext.get("imdb_id")
    d = tmdb(f"{kind}/{tid}", language="en-US")
    ims = tmdb(f"{kind}/{tid}/images", include_image_language="tr,en,null")
    orig = d.get("original_name") or d.get("original_title")
    trp, trl = pick(ims.get("posters", []), "tr"), pick(ims.get("logos", []), "tr")
    st = "series" if kind == "tv" else "movie"
    try:
        m = js(f"{BASE}/meta/{st}/{tt}.json").get("meta") or {}
    except Exception as e:
        m = {"error": scrub(e)}
    vids = m.get("videos") or []
    seasons = sorted({v.get("season") for v in vids if v.get("season") is not None})
    rep.append(f"{q} ({tt}, tmdb {tid})\n  AIOMetadata now: name={m.get('name')!r} logo={'yes' if m.get('logo') else 'no'} "
               f"episodes={len(vids)} seasons={seasons[:12]}{' ...' if len(seasons) > 12 else ''} first ids={[v.get('id') for v in vids[:2]]}\n"
               f"  Turkish: name={orig!r} tr poster={'yes' if trp else 'NO'} tr logo={'yes' if trl else 'NO'} (TMDB English name {d.get('name') or d.get('title')!r})"
               + (f"\n  error: {m['error']}" if "error" in m else ""))
    # side by side: now | Turkish
    W, H = 1000, 520
    cv = Image.new("RGB", (W, H), (24, 24, 28)); dr = ImageDraw.Draw(cv)
    for col, (label, name, pu, lu) in enumerate([
        ("AIOMetadata (now)", m.get("name", "?"), m.get("poster"), m.get("logo")),
        ("Turkish original", orig, trp and "https://image.tmdb.org/t/p/w500" + trp, trl and "https://image.tmdb.org/t/p/w500" + trl)]):
        x0 = col * 500 + 20
        dr.text((x0, 12), label, font=small, fill=(170, 170, 180))
        p = pu and img(pu, (240, 360))
        if p: cv.paste(p, (x0, 44), p)
        lg = lu and img(lu, (210, 120))
        if lg:
            bg = Image.new("RGBA", lg.size, (90, 90, 100, 255)); bg.alpha_composite(lg)
            cv.paste(bg.convert("RGB"), (x0 + 255, 60))
        else:
            dr.text((x0 + 255, 60), "(no logo)", font=small, fill=(140, 140, 150))
        dr.text((x0, 420), name or "?", font=font, fill=(240, 240, 240))
    cv.save(f"{OUT}/{re.sub(r'[^a-z0-9]+', '-', q.lower())}.jpg", quality=86)
open(f"{OUT}/report.txt", "w").write(scrub("\n".join(rep)) + "\n")
print(scrub("\n".join(rep)))
