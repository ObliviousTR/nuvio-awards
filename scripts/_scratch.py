import json, os, sys, io, re, collections, urllib.request, concurrent.futures as cf
from PIL import Image, ImageDraw
os.makedirs("refs/art", exist_ok=True)
d = json.load(open("builder/out/delivered/baseline.json"))
urls = {}
for c in d:
    if c.get("backdropImageUrl"): urls[c["backdropImageUrl"]] = (c["title"], "", "rowbackdrop")
    for f in c["folders"]:
        for k in ("coverImageUrl", "focusGifUrl", "titleLogoUrl", "heroBackdropUrl"):
            if f.get(k): urls.setdefault(f[k], (c["title"], f["title"], k))
def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40)
        return u, r.status, r.read()
    except Exception as e:
        return u, str(e)[:60], b""
res = {}
with cf.ThreadPoolExecutor(16) as ex:
    for u, st, b in ex.map(get, urls):
        res[u] = (st, b)
out, tot, bad = [], collections.Counter(), []
for u, (st, b) in res.items():
    row, fol, k = urls[u]
    tot[k] += len(b)
    if st != 200: bad.append(f"{st} {row} / {fol} / {k} {u}")
out.append("SIZES MB " + json.dumps({k: round(v / 1e6, 1) for k, v in tot.items()}) + f" total {round(sum(tot.values())/1e6,1)}")
out.append(f"BAD {len(bad)}"); out += bad
big = sorted(((len(b), u) for u, (st, b) in res.items()), reverse=True)[:10]
out += [f"BIG {round(n/1e6,1)}MB {u}" for n, u in big]
open("refs/art/report.txt", "w").write("\n".join(out))
# contact sheets: covers per row
for c in d:
    tiles = []
    for f in c["folders"][:30]:
        u = f.get("coverImageUrl")
        if not u or u not in res or not res[u][1]: continue
        try:
            im = Image.open(io.BytesIO(res[u][1])); im.seek(0); im = im.convert("RGB")
        except Exception: continue
        im.thumbnail((320, 320)); tiles.append((f["title"], im))
    if not tiles: continue
    W, H, cols = 330, 330, 6
    sheet = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols)), (30, 30, 30))
    dr = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(tiles):
        x, y = (i % cols) * W, (i // cols) * H
        sheet.paste(im, (x + 5, y + 5)); dr.text((x + 8, y + H - 18), t[:40], fill=(255, 255, 0))
    sheet.save(f"refs/art/{re.sub(r'[^a-z0-9]+', '-', c['title'].lower())}.jpg", quality=80)
