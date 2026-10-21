"""Discover row art, rebuilt every week by .github/workflows/discover-art.yml.

All nine Discover folders share one look (Kaptain's Discover style, now animated): a huge word, the front part filled
with a scene, the rest outlined; a small coloured kicker above, a tracked subtitle below. The hover WebP builds it:
outline draws in, letters fill one by one, kicker and subtitle slide in, then a light sweep and a slow push-in.

Which scene is used:
  weekly   Trending Movies / Series (#1 this week), New Movies / Series (most popular new release),
           Box Office Champions (top grosser of the last 12 months), Certified Fresh (rotates the acclaimed top 5)
  monthly  Hidden Gems, Awards & Prestige, All-Time Top Rated rotate through a hand-picked pool
A title is never used on two covers at once. Covers stay textless (only TMDB backdrops with no language tag).

Output: OUT/<id>/cover.jpg (1920x1080) · hover.webp (512x288) · backdrop.jpg (1920x1080) · logo.png, plus picks.json.
The workflow force-pushes OUT to the `discover-art` branch (one commit, no history), and the collection points at
raw.githubusercontent.com/ObliviousTR/nuvio-awards/discover-art/<id>/... with fixed URLs, so the app picks the new art
up on its own (raw.githubusercontent sends max-age=300; Nuvio's image loader honours it).
usage: python3 scripts/discover_art.py OUT [--date YYYY-MM-DD] [ids...]
"""
import datetime as dt, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "art_tools"))
import universe_motion as um
import spotlight_art as art
import folder_art as fa
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

W, H = 1920, 1080
NOISE = {16, 10763, 10764, 10766, 10767}  # animation, news, reality, soap, talk: not cover material

# id, folder title, kicker, word, letters filled, accent, subtitle (static) / rule
FOLDERS = [
    ("trending-movies", "Trending Movies", "MOVIES", "TRENDING", 5, (255, 140, 40), ("trending", "movie")),
    ("trending-series", "Trending Series", "SERIES", "TRENDING", 5, (255, 190, 60), ("trending", "tv")),
    ("new-movies", "New Movies", "JUST RELEASED", "NEW MOVIES", 3, (255, 70, 140), ("new", "movie")),
    ("new-series", "New Series", "JUST PREMIERED", "NEW SERIES", 3, (190, 110, 255), ("new", "tv")),
    ("box-office", "Box Office Champions", "TOP GROSSING", "BOX OFFICE", 3, (240, 190, 40), ("boxoffice", "movie")),
    ("certified", "Certified Fresh & Must-See", "CERTIFIED FRESH", "MUST-SEE", 4, (240, 70, 70), ("certified", "movie")),
    ("hidden-gems", "Hidden Gems", "UNDERRATED & CULT", "HIDDEN GEMS", 6, (80, 225, 190),
     ("pool", "movie", [14784, 17431, 206487, 220289, 103731, 210479, 290250, 188166, 12149, 49049],
      "UNDERRATED FILMS WORTH DISCOVERING")),
    ("prestige", "Awards & Prestige", "OSCARS · CANNES · VENICE", "PRESTIGE", 4, (235, 200, 110),
     ("pool", "movie", [496243, 872585, 545611, 1064213, 581734, 376867, 314365, 194662, 76203, 776503],
      "AWARD WINNERS & CRITICS' FAVOURITES")),
    ("top-rated", "All-Time Top Rated", "ALL-TIME", "TOP RATED", 3, (255, 170, 50),
     ("pool", "movie", [238, 278, 155, 389, 424, 122, 680, 769, 550, 13], "THE GREATEST FILMS EVER MADE")),
]


# ---------------------------------------------------------------- picking
def textless(kind, tid):
    """Best-voted textless backdrop that isn't too dark to fill letters with (checked on a small copy)."""
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null") or {}
    bd = [b for b in im.get("backdrops", []) if not b.get("iso_639_1") and b["width"] >= 1280]
    bd.sort(key=lambda b: (-b["vote_count"], -b["vote_average"], -b["width"]))
    from PIL import ImageStat
    for b in bd[:6]:
        sm = art.fetch(b["file_path"], "w300")
        if sm is not None and 60 <= ImageStat.Stat(sm.convert("L")).mean[0] <= 175:
            return b["file_path"]
    return None


def candidates(rule, kind, today):
    ago = lambda d: (today - dt.timedelta(days=d)).isoformat()
    common = {"with_original_language": "en", "without_genres": "16|10763|10764|10766|10767" + ("|10770" if kind == "movie" else "")}
    if rule == "trending":
        res = (tmdb(f"/trending/{kind}/week") or {}).get("results", [])
        return [r for r in res if r.get("original_language") == "en" and not NOISE & set(r.get("genre_ids", []))]
    date = "primary_release_date" if kind == "movie" else "first_air_date"
    if rule == "new":
        p = dict(common, sort_by="popularity.desc", **{f"{date}.gte": ago(75 if kind == "movie" else 120),
                                                         f"{date}.lte": today.isoformat(), "vote_count.gte": 30})
    elif rule == "boxoffice":
        p = dict(common, sort_by="revenue.desc", **{f"{date}.gte": ago(365), f"{date}.lte": today.isoformat()})
    elif rule == "certified":
        p = dict(common, sort_by="vote_average.desc", **{f"{date}.gte": ago(730), "vote_count.gte": 2500})
    res = (tmdb(f"/discover/{kind}", **p) or {}).get("results", [])
    if rule == "certified":  # a different one of the acclaimed top five each week
        k = today.isocalendar()[1] % max(1, min(5, len(res)))
        res = res[k:] + res[:k]
    return res


def pick(spec, today, used):
    rule = spec[0]
    if rule == "pool":
        _, kind, pool, sub = spec
        start = (today.year * 12 + today.month) % len(pool)
        order = pool[start:] + pool[:start]
        cands = [{"id": i} for i in order]
    else:
        kind = spec[1]
        cands = candidates(rule, kind, today)
    for c in cands:
        if c["id"] in used:
            continue
        path = textless(kind, c["id"])
        if not path:
            continue
        info = tmdb(f"/{kind}/{c['id']}") or {}
        name = info.get("title") or info.get("name") or ""
        used.add(c["id"])
        return kind, c["id"], name, path
    raise RuntimeError(f"nothing to pick for {spec[:2]}")


def subtitle(spec, name):
    rule = spec[0]
    if rule == "pool":
        return spec[3]
    n = name.upper()
    return {"trending": f"#1 THIS WEEK  ·  {n}", "new": f"NEW RELEASE  ·  {n}" if spec[1] == "movie" else f"NEW THIS SEASON  ·  {n}",
            "boxoffice": f"#1 OF THE YEAR  ·  {n}", "certified": f"CRITICS' PICK  ·  {n}"}[rule]


# ---------------------------------------------------------------- drawing
def fit_text(text, fnt_fn, size, maxw, tr):
    while um.text_layer(text, fnt_fn(size), (255, 255, 255), tr).width > maxw and size > 20:
        size -= 4
    return um.text_layer(text, fnt_fn(size), (255, 255, 255), tr), size


def make(img, kicker, word, split, accent, sub):
    full, size = fit_text(word, fa.black, 300, W * 0.8, 6)
    fnt = fa.black(size)
    K = um.text_layer(kicker, fa.semi(40), accent, 14)
    S, _ = fit_text(sub, fa.semi, 44, full.width * 1.02, 8)
    S = fa.tl(sub, fa.semi(_), (235, 235, 235), 8)
    # the word drawn letter by letter on one canvas, so each letter's span is known in the cropped layer
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    asc, desc = fnt.getmetrics()
    cv = Image.new("L", (round(sum(probe.textlength(c, font=fnt) + 6 for c in word)) + 80, asc + desc + 80), 0)
    cd = ImageDraw.Draw(cv)
    spans, x = [], 40
    for ch in word:
        cd.text((x, 40), ch, font=fnt, fill=255)
        bb = fnt.getbbox(ch)
        adv = probe.textlength(ch, font=fnt) + 6
        if ch != " ":
            spans.append((x + bb[0], x + bb[2]))
        x += adv
    box = cv.getbbox()
    full = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (255, 255, 255, 0))
    full.putalpha(cv.crop(box))
    edges = [(a - box[0], b - box[0], True) for a, b in spans]
    base = ImageEnhance.Brightness(art.graded(img, 1.0, 1.08, (W, H))).enhance(0.6)
    # the letters' fill: the same scene, contrast-stretched, lifted to a bright mean and warmed with the accent,
    # so even a dark still reads as a solid picture inside the letters
    from PIL import ImageOps, ImageStat
    t = ImageOps.autocontrast(art.graded(img, 1.0, 1.0, (W, H)), cutoff=2)
    t = ImageEnhance.Brightness(t).enhance(max(1.0, 165 / max(1, ImageStat.Stat(t.convert("L")).mean[0])))
    grad = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        f = y / H
        gd.line((0, y, W, y), fill=tuple(round(accent[i] * (1 - 0.35 * f) + 255 * 0.15 * (1 - f)) for i in range(3)))
    texsrc = ImageEnhance.Color(Image.blend(t, grad, 0.28)).enhance(1.2)
    ring = fa.outline_text(full, 3, (255, 255, 255), 235)
    cx, cy = W / 2, H * 0.48

    def frame(p, z, sweep_s=None):
        bg = fa.vignette(art.zoomed(base, 0.03 + 0.05 * z), 0.9).convert("RGBA")
        lay = Image.new("RGBA", full.size, (0, 0, 0, 0))
        lay.alpha_composite(um.alpha(ring, um.ease(p / 0.25)))
        m = Image.new("L", full.size, 0)
        md = ImageDraw.Draw(m)
        filled = [e for e in edges if e[2]][:split]
        for i, (x0, x1, _) in enumerate(filled):
            a = um.ease((p - 0.15 - i * 0.07) / 0.18)
            if a > 0:
                md.rectangle((x0 - 2, 0, x0 + (x1 - x0 + 4) * a, full.height), fill=255)
        tex = fa.textured(full, art.zoomed(texsrc, 0.12 + 0.05 * z))
        tex.putalpha(ImageChops.multiply(full.getchannel("A"), m))
        lay.alpha_composite(tex)
        if sweep_s is not None:  # light band across the letters
            band = Image.new("L", full.size, 0)
            bx = -200 + sweep_s * (full.width + 400)
            ImageDraw.Draw(band).polygon([(bx, 0), (bx + 70, 0), (bx - 40, full.height), (bx - 110, full.height)], fill=150)
            band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(14)), full.getchannel("A"))
            wl = Image.new("RGBA", full.size, (255, 255, 255, 0))
            wl.putalpha(band)
            lay.alpha_composite(wl)
        um.place(bg, lay, cx, cy)
        ka = um.ease((p - 0.05) / 0.3)
        um.place(bg, K, cx - (1 - ka) * 40, cy - full.height / 2 - 44, ka)
        sa = um.ease((p - 0.6) / 0.3)
        um.place(bg, S, cx, cy + full.height / 2 + 52 + (1 - sa) * 20, sa)
        return bg.convert("RGB")

    logo = Image.new("RGBA", full.size, (0, 0, 0, 0))
    logo.alpha_composite(fa.textured(full, texsrc))
    return frame, logo


def render(fid, kicker, word, split, accent, spec, out, today, used):
    kind, tid, name, path = pick(spec, today, used)
    img = art.fetch(path).convert("RGB")
    sub = subtitle(spec, name)
    frame, logo = make(img, kicker, word, split, accent, sub)
    d = os.path.join(out, fid)
    os.makedirs(d, exist_ok=True)
    frame(1.0, 0.5).save(os.path.join(d, "cover.jpg"), quality=88)
    art.graded(img, 0.95, 1.03, (W, H)).save(os.path.join(d, "backdrop.jpg"), quality=86)
    um.trim(logo).save(os.path.join(d, "logo.png"))
    B, HD = 42, 34
    frames, dur = [], []
    for i in range(B + HD):
        z = i / (B + HD)
        if i < B:
            f = frame(i / (B - 1), z)
            dur.append(45)
        else:
            s = (i - B) / (HD * 0.55)
            f = frame(1.0, z, s if s <= 1 else None)
            dur.append(60)
        frames.append(f.resize((512, 288), Image.LANCZOS))
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=dur, loop=0,
                   quality=80, method=5, minimize_size=True, allow_mixed=True)
    return {"id": fid, "kind": kind, "tmdb": tid, "title": name, "subtitle": sub, "backdrop": path}


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    today = dt.date.today()
    if "--date" in args:
        i = args.index("--date")
        today = dt.date.fromisoformat(args[i + 1])
        del args[i:i + 2]
    only = set(args)
    used, picks = set(), []
    for fid, title, kicker, word, split, accent, spec in FOLDERS:
        if only and fid not in only:
            continue
        try:
            picks.append(render(fid, kicker, word, split, accent, spec, out, today, used))
            print("built", fid, "·", picks[-1]["title"])
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", fid, e)
    json.dump({"date": today.isoformat(), "picks": picks}, open(os.path.join(out, "picks.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
