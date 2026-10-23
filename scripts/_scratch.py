"""Rating-poster test: can the badge posters AIOMetadata uses come with the Turkish poster underneath?"""
import io, json, os, re, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

AIO = os.environ["AIOMETADATA_URL"].strip()
BASE = re.sub(r"/manifest\.json.*$", "", AIO)
OUT = "refs/trposter"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "nuvio-awards/1.0"}
TESTS = [("series", "tt1848220", "muhtesem-yuzyil"), ("series", "tt11093718", "kurulus-osman"),
         ("series", "tt1831164", "leyla-ile-mecnun"), ("movie", "tt0476735", "babam-ve-oglum")]


def shape(u):
    """the URL with anything key-like or uuid-like masked, so it can be shown"""
    if not u:
        return None
    p = urllib.parse.urlsplit(u)
    host = "<aio-host>" if u.startswith(BASE.split("/stremio")[0]) else p.netloc
    segs = ["<key>" if (len(s) > 20 and not re.match(r"^(series|movie)-\d+(\.jpg)?$", s)) or re.match(r"^t\d-", s) else s
            for s in p.path.split("/")]
    q = urllib.parse.parse_qsl(p.query)
    q = [(k, "<url>" if v.startswith("http") else v) for k, v in q]
    return f"{p.scheme}://{host}{'/'.join(segs)}" + ("?" + urllib.parse.urlencode(q) if q else "")


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90)


def variants(u):
    p = urllib.parse.urlsplit(u)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if k != "lang"]
    out = {"now": u}
    for lang in ("tr",):
        out["lang=" + lang] = urllib.parse.urlunsplit(p._replace(query=urllib.parse.urlencode(q + [("lang", lang)])))
    return out


F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(F, 18) if os.path.exists(F) else ImageFont.load_default()
rep = []
for st, tt, slug in TESTS:
    m = json.loads(get(f"{BASE}/meta/{st}/{tt}.json").read()).get("meta") or {}
    pu = m.get("poster")
    rep.append(f"{slug}: poster url shape = {shape(pu)}")
    tiles = []
    for name, u in variants(pu).items():
        try:
            r = get(u)
            final = r.geturl()
            im = Image.open(io.BytesIO(r.read())).convert("RGB")
            rep.append(f"   {name}: HTTP 200 {im.size} final={shape(final)}")
            im.thumbnail((300, 450)); tiles.append((name, im))
        except Exception as e:
            rep.append(f"   {name}: failed {type(e).__name__} {getattr(e, 'code', '')}")
    cv = Image.new("RGB", (40 + 320 * len(tiles), 520), (24, 24, 28)); dr = ImageDraw.Draw(cv)
    for i, (name, im) in enumerate(tiles):
        cv.paste(im, (20 + 320 * i, 40)); dr.text((20 + 320 * i, 10), name, font=font, fill=(200, 200, 210))
    cv.save(f"{OUT}/{slug}.jpg", quality=86)
txt = "\n".join(rep)
for s in (BASE, AIO):
    txt = txt.replace(s, "<aio>")
open(f"{OUT}/report.txt", "w").write(txt + "\n")
print(txt)
