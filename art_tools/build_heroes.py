"""Build folder heroes (heroBackdropUrl) and title logos (titleLogoUrl) for Nuvio TV from art_tools/heroes_spec.json,
into the nuvio-art repo (art/heroes/<row>/<folder>/hero.jpg, logo.png), and patch the delivered baseline with their
URLs (cache-busted with the file's md5). See hero_styles.py for the three styles (Ozzy, 31 Oct 2026).

spec: {"<Row>": {"<Folder title>": {
    "style": "scene" | "wall" | "portrait",
    "src": "file:<path>" | "tmdb:<path>" | "url:<url>",            scene: the picture; portrait: the film still
    "subject": [x0, y0, x1, y1],                                   scene: optional subject box (fractions)
    "posters": ["tmdb:<path>" | "url:<url>" | "catalog:<path in nuvio-awards>", ...],   wall
    "glow": "#rrggbb", "seed": 1,                                   wall
    "photos": ["tmdb:<path>", ...],                                portrait: the person's photos, best first
    "logo": "keep" | "file:<path>" | "tmdb:<path>" | "url:<url>" }}}
usage: python3 art_tools/build_heroes.py NUVIO_ART_DIR BASELINE_JSON [--rows "Row,Row"] [--only "Folder"] [--sheet OUT]
"""
import argparse, hashlib, io, json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hero_styles as hs

RAW = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/"
UA = {"User-Agent": "nuvio-heroes"}


def slug(s):
    s = s.lower().replace("&", "and").replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g") \
        .replace("ö", "o").replace("ü", "u").replace("İ", "i")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


_cache = {}


def load(ref, size="original"):
    if ref in _cache:
        return _cache[ref]
    kind, _, val = ref.partition(":")
    if kind == "file":
        im = Image.open(os.path.join(ROOT, val))
    else:
        url = f"https://image.tmdb.org/t/p/{size}{val}" if kind == "tmdb" else val
        for _ in range(3):
            try:
                im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                                                  timeout=90).read()))
                break
            except Exception:
                im = None
    if im is not None:
        im.load()
    _cache[ref] = im
    return im


def poster_refs(refs):
    out = []
    for r in refs:
        if r.startswith("catalog:"):
            metas = json.load(open(os.path.join(ROOT, r[8:]), encoding="utf-8")).get("metas", [])
            out += [f"url:{m['poster']}" for m in metas if m.get("poster")]
        else:
            out.append(r)
    return out


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build(spec, folder):
    st = spec["style"]
    if st == "scene":
        return hs.scene(load(spec["src"]), tuple(spec["subject"]) if spec.get("subject") else None)
    if st == "wall":
        refs = poster_refs(spec["posters"])[:36]
        with ThreadPoolExecutor(12) as ex:
            ps = [p for p in ex.map(lambda r: load(r, "w342"), refs) if p is not None]
        return hs.wall(ps, glow=hex_rgb(spec["glow"]) if spec.get("glow") else None, seed=spec.get("seed", 1),
                       shade=spec.get("shade", 1.0))
    if st == "portrait":
        with ThreadPoolExecutor(6) as ex:
            photos = list(ex.map(load, spec["photos"][:6]))
        still = load(spec["src"], "w1280") if spec.get("src") else None
        return hs.portrait(hs.best_photo(photos), still, mono=spec.get("mono", False))
    raise ValueError(st)


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("art"); ap.add_argument("baseline")
    ap.add_argument("--rows", default=""); ap.add_argument("--only", default="")
    ap.add_argument("--sheet", default="")
    a = ap.parse_args()
    spec = json.load(open(os.path.join(HERE, "heroes_spec.json"), encoding="utf-8"))
    data = json.load(open(a.baseline, encoding="utf-8"))
    rows = [r.strip() for r in a.rows.split(",") if r.strip()] or list(spec)
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    done = []
    for row in data:
        if row["title"] not in rows or row["title"] not in spec:
            continue
        for f in row["folders"]:
            sp = spec[row["title"]].get(f["title"])
            if not sp or (only and f["title"] not in only):
                continue
            rel = f"art/heroes/{slug(row['title'])}/{slug(f['title'])}"
            os.makedirs(os.path.join(a.art, rel), exist_ok=True)
            hero = build(sp, f)
            hp = os.path.join(a.art, rel, "hero.jpg")
            hero.save(hp, quality=88, optimize=True, progressive=True)
            f["heroBackdropUrl"] = f"{RAW}{rel}/hero.jpg?v={md5(hp)}"
            lg = sp.get("logo", "keep")
            if lg != "keep":
                im = load(lg).convert("RGBA")
                im = im.crop(im.getbbox() or (0, 0, im.width, im.height))
                im.thumbnail((1200, 545), Image.LANCZOS)          # the TV draws it in 220x100 dp at most
                lp = os.path.join(a.art, rel, "logo.png")
                im.save(lp, optimize=True)
                f["titleLogoUrl"] = f"{RAW}{rel}/logo.png?v={md5(lp)}"
            done.append((row["title"], f["title"], hp, f.get("titleLogoUrl")))
            print("built", row["title"], "/", f["title"])
    json.dump(data, open(a.baseline, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if a.sheet:
        sheet(done, a.sheet, a.art)


def sheet(done, out, art_dir):
    sys.path.insert(0, os.path.join(HERE))
    from tv_sim import partial, full
    from PIL import ImageDraw, ImageFont
    F = ImageFont.truetype(os.path.join(ROOT, "spotlight", "fonts", "Montserrat-SemiBold.ttf"), 16)
    sh = Image.new("RGB", (2 * 490 + 10, len(done) * 302 + 10), (40, 40, 46))
    d = ImageDraw.Draw(sh)
    for i, (row, title, hp, logo_url) in enumerate(done):
        hero = Image.open(hp)
        lg = None
        if logo_url:
            rel = logo_url.split("nuvio-art/main/")[-1].split("?")[0]
            p = os.path.join(art_dir, rel)
            lg = Image.open(p).convert("RGBA") if os.path.exists(p) else load("url:" + logo_url).convert("RGBA")
        y = 10 + i * 302
        d.text((10, y), f"{row} / {title}", font=F, fill=(240, 240, 240))
        sh.paste(partial(hero, lg).resize((480, 270)), (10, y + 22))
        sh.paste(full(hero, lg).resize((480, 270)), (500, y + 22))
    sh.save(out, quality=84)


if __name__ == "__main__":
    main()
