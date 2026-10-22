"""Hero backdrops and title logos for folders that lack them, in the language of Kaptain's rows:
  wall    hero: a tilted wall of the folder's own posters, darkened, fading to near black on the left (Kaptain's
          Streaming / Genres / Anime / Moods / Kids / Studios / Decades / International / Reality / Docs heroes)
  row     logo: the folder name in Montserrat Bold caps, silver gradient, soft shadow, a thin rule under the first
          line, at most two lines, left aligned on a 1200x400 canvas (Kaptain's Anime / Moods / Kids / Docs logos)
  script  logo: a person's name in Alex Brush, silver, a rule with a small diamond, "CINEMATIC COLLECTION" spaced
          below (Kaptain's Iconic Actors / Legendary Directors logos)
Posters come from the folder's own rails: TMDB sources are queried with their filters, addon rails are read from
this repo's static catalogs.
usage: python3 art_tools/hero_logo.py BASELINE_JSON OUT_DIR "Row/Folder=kind:arg" ...
  kinds: wall (hero) · row:LINE1|LINE2 (logo) · script:Name[|SUBTITLE] (logo)
"""
import glob, io, json, math, os, random, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONTS = os.path.join(ROOT, "spotlight", "fonts")
SCRIPT_FONT = "https://raw.githubusercontent.com/google/fonts/main/ofl/alexbrush/AlexBrush-Regular.ttf"
CACHE = os.path.join(ROOT, "scripts", ".cache")


def get(url):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]", "_", url)[-150:])
    if not os.path.exists(p):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 nuvio-awards"})
        open(p, "wb").write(urllib.request.urlopen(req, timeout=60).read())
    return open(p, "rb").read()


def mont(w, s):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat-{w}.ttf"), s)


# ---------------------------------------------------------------- posters of a folder
def tmdb_params(f, media):
    out = {}
    for k, v in (f or {}).items():
        if v in (None, "", [], {}):
            continue
        if k.startswith("releaseDate"):
            base = "primary_release_date" if media == "movie" else "first_air_date"
            out[base + (".gte" if k.endswith("Gte") else ".lte")] = v
            continue
        m = re.match(r"(.+?)(Gte|Lte)$", k)
        name, suf = (m.group(1), "." + m.group(2).lower()) if m else (k, "")
        out[re.sub(r"([A-Z])", lambda x: "_" + x.group(1).lower(), name) + suf] = v
    return out


def posters_of(folder, want=40):
    paths = []
    for s in folder.get("sources", []):
        try:
            if s.get("provider") == "tmdb":
                media = "movie" if s.get("mediaType") == "MOVIE" else "tv"
                p = tmdb_params(s.get("filters"), media)
                if s.get("tmdbSourceType") == "NETWORK":
                    p["with_networks"] = s.get("tmdbId")
                p["sort_by"] = s.get("sortBy") or "popularity.desc"
                for page in (1, 2):
                    r = (tmdb(f"/discover/{media}", page=page, **p) or {}).get("results", [])
                    paths += ["tmdb:" + x["poster_path"] for x in r if x.get("poster_path")]
            elif s.get("provider") == "addon":
                for f in glob.glob(os.path.join(ROOT, "**", "catalog", s.get("type", "*"), s["catalogId"] + ".json"), recursive=True):
                    paths += [m["poster"] for m in json.load(open(f)).get("metas", []) if m.get("poster")]
                    break
        except Exception as e:
            print("  rail skipped:", s.get("title"), e)
        if len(set(paths)) >= want:
            break
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:want]


def load_poster(p):
    try:
        if p.startswith("tmdb:"):
            return art.fetch(p[5:], "w342").convert("RGB")
        return Image.open(io.BytesIO(get(p))).convert("RGB")
    except Exception:
        return None


def wall(paths, angle=-11, seed=4):
    """Kaptain's hero: tilted poster wall, darkened, heaviest on the left where the logo sits."""
    pw, ph, gap = 190, 285, 18
    cols, rows = 13, 6
    imgs = [im.resize((pw, ph), Image.LANCZOS) for im in (load_poster(p) for p in paths) if im]
    if not imgs:
        raise RuntimeError("no posters")
    canvas = Image.new("RGB", (cols * (pw + gap), rows * (ph + gap)), (8, 9, 12))
    rnd = random.Random(seed)
    order = list(range(len(imgs)))
    for i in range(cols * (rows + 1)):
        if i % len(imgs) == 0:
            rnd.shuffle(order)
        im = imgs[order[i % len(imgs)]]
        c, r = i % cols, i // cols
        canvas.paste(im, (c * (pw + gap), r * (ph + gap) - (ph // 2 if c % 2 else 0)))
    canvas = canvas.rotate(angle, resample=Image.BICUBIC, fillcolor=(8, 9, 12))
    x, y = (canvas.width - 1920) // 2, (canvas.height - 1080) // 2
    base = canvas.crop((x, y, x + 1920, y + 1080))
    base = ImageEnhance.Brightness(ImageEnhance.Color(base).enhance(0.85)).enhance(0.55)
    m = Image.new("L", (1920, 1), 0)
    for xx in range(1920):
        m.putpixel((xx, 0), round(235 * max(0, 1 - xx / 1100) ** 1.4))
    return Image.composite(Image.new("RGB", (1920, 1080), (4, 4, 6)), base, m.resize((1920, 1080)))


# ---------------------------------------------------------------- logos
def silver(mask):
    """White to cool grey from top to bottom, with a soft dark shadow below-right."""
    w, h = mask.size
    g = Image.new("RGB", (1, h))
    for y in range(h):
        f = y / max(1, h - 1)
        g.putpixel((0, y), (round(252 - 40 * f), round(252 - 34 * f), round(255 - 22 * f)))
    fill = g.resize((w, h))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh.putalpha(mask.filter(ImageFilter.GaussianBlur(6)).point(lambda v: v * 150 // 255))
    out.alpha_composite(sh, (0, 0))
    out = ImageChops.offset(out, 4, 5)
    lay = fill.convert("RGBA")
    lay.putalpha(mask)
    out.alpha_composite(lay)
    return out


def row_logo(lines):
    W, H = 1200, 400
    f = mont("ExtraBold", 140)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    while max(probe.textlength(l, font=f) for l in lines) > W - 80 and f.size > 40:
        f = mont("ExtraBold", f.size - 6)
    lh = round(f.size * 1.02)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    top = (H - lh * len(lines)) // 2
    for i, l in enumerate(lines):
        d.text((40, top + i * lh), l, font=f, fill=255)
    out = silver(mask)
    # thin rule under the first line, fading to the right
    y = top + lh * (len(lines) - 1) + round(f.getbbox("A")[3] + f.size * 0.12)  # under the last line
    w1 = probe.textlength(lines[-1], font=f) * 0.55
    rule = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for x in range(int(w1)):
        rule.putpixel((40 + x, y), (200, 205, 215, round(200 * (1 - x / w1))))
        rule.putpixel((40 + x, y + 1), (200, 205, 215, round(120 * (1 - x / w1))))
    out.alpha_composite(rule)
    return out


def script_logo(name, sub="CINEMATIC COLLECTION"):
    f = ImageFont.truetype(io.BytesIO(get(SCRIPT_FONT)), 230)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    tr = 18
    w = round(sum(probe.textlength(c, font=f) + tr for c in name)) + 160
    W, H = max(1400, w), 640
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    x = (W - (w - 160)) // 2
    for c in name:
        d.text((x, 40), c, font=f, fill=255)
        x += probe.textlength(c, font=f) + tr
    out = silver(mask)
    d2 = ImageDraw.Draw(out)
    cy, cx = mask.getbbox()[3] + 45, W // 2
    for side in (-1, 1):
        for k in range(int(W * 0.36)):
            a = round(170 * (1 - k / (W * 0.36)))
            d2.point((cx + side * (26 + k), cy), fill=(200, 205, 215, a))
    d2.polygon([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)], outline=(220, 225, 235, 230))
    d2.text((cx - 22, cy - 9), "‹", font=mont("SemiBold", 18), fill=(200, 205, 215, 200))
    d2.text((cx + 14, cy - 9), "›", font=mont("SemiBold", 18), fill=(200, 205, 215, 200))
    sf = mont("SemiBold", 34)
    sp = 26
    sw = sum(probe.textlength(c, font=sf) + sp for c in sub) - sp
    x = cx - sw / 2
    for c in sub:
        d2.text((x, cy + 55), c, font=sf, fill=(235, 238, 245, 255))
        x += probe.textlength(c, font=sf) + sp
    bb = out.getchannel("A").getbbox()
    return out.crop(bb)


def slug(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    base, out = sys.argv[1], sys.argv[2]
    d = json.load(open(base, encoding="utf-8"))
    for job in sys.argv[3:]:
        target, spec = job.split("=", 1)
        row, title = target.split("/", 1)
        kind, _, arg = spec.partition(":")
        f = [x for c in d if c["title"] == row for x in c["folders"] if x["title"] == title][0]
        dd = os.path.join(out, slug(row), slug(title))
        os.makedirs(dd, exist_ok=True)
        try:
            if kind == "wall":
                wall(posters_of(f)).save(os.path.join(dd, "backdrop.jpg"), quality=86)
            elif kind == "row":
                row_logo(arg.split("|")).save(os.path.join(dd, "logo.png"))
            elif kind == "script":
                name, _, sub = arg.partition("|")
                script_logo(name, sub or "CINEMATIC COLLECTION").save(os.path.join(dd, "logo.png"))
            print("built", row, "/", title, kind)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", row, "/", title, kind, e)


if __name__ == "__main__":
    main()
