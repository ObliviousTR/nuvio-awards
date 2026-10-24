"""Poster redirect route: Posters+ URLs through <worker>/pp/ - Turkish titles get the Turkish logo, others unchanged."""
import io, json, os, urllib.parse, urllib.request
from PIL import Image, ImageDraw
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
D = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
sub = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain",
      headers={"Authorization": "Bearer " + tok}), timeout=60).read())["result"]["subdomain"]
WP = f"https://nuvio-tr.{sub}.workers.dev{PATH}/pp"
OUT = "refs/tracc"; os.makedirs(OUT, exist_ok=True)
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=90)
rep, tiles = [], []
metas = []
for t, c in (("movie", "flixpatrol.netflix.tr.movie"), ("series", "flixpatrol.netflix.tr.series")):
    metas += json.loads(get(f"{D}/catalog/{t}/{c}.json").read())["metas"][:6]
for m in metas:
    p = m.get("poster") or ""
    if "postersplus" not in p:
        continue
    via = p.replace("https://postersplus.slokker.cc", WP)
    r = get(via)
    final = r.geturl(); img = r.read()
    rep.append(f"{m.get('name')!r}: HTTP {r.status}, Turkish logo asked: {'logo_priority' in final}")
    for lab, b in (("direct", get(p).read()), ("via worker", img)):
        im = Image.open(io.BytesIO(b)).convert("RGB"); im.thumbnail((220, 330)); tiles.append((f"{(m.get('name') or '')[:18]} {lab}", im))
cv = Image.new("RGB", (20 + 240 * 6, 380 * ((len(tiles) + 5) // 6)), (20, 20, 24)); dr = ImageDraw.Draw(cv)
for n, (lab, im) in enumerate(tiles):
    x, y = 20 + 240 * (n % 6), 380 * (n // 6); cv.paste(im, (x, y + 30)); dr.text((x, y + 10), lab, fill=(220, 220, 220))
cv.save(f"{OUT}/pp.jpg", quality=85)
txt = "\n".join(rep)
for s in (PATH, urllib.parse.quote(PATH, safe=""), PATH.split("/")[-1], u.netloc):
    txt = txt.replace(s, "<x>")
open(f"{OUT}/pp.txt", "w").write(txt + "\n"); print(txt)
