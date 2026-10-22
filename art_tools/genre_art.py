"""Genres row: Kaptain's genre cards (photo, accent bar, bold title, tracked subtitle; on hover the subtitle turns to
the genre colour, the bar to white and a coloured frame lights up), rebuilt by us so they can move:
  cover   the genre's iconic film (the one on Kaptain's card), plain state
  hover   starts as the cover, eases into the hover state; a glowing frame runs once round the card at one speed
          (5 s) while the genre's currently popular films play behind the title; the lap closes with a breath and
          the card settles back to the cover, so the loop is seamless.
Popular films are refreshed monthly (.github/workflows/genre-art.yml -> genre-art branch, fixed URLs); a film stays
while it is still in the genre's top 6, so the art only changes when the genre's line-up really moves.
usage: python3 art_tools/genre_art.py OUT_DIR [--prev picks.json] [titles...]
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1280, 720
OW, OH = 512, 288
FONTS = os.path.join(ROOT, "spotlight", "fonts")

# title on the card, subtitle, accent (Kaptain's frame colour), iconic film (TMDB id), filters for "popular now"
GENRES = {
    "Action & Adventure": ("ACTION", "HIGH-OCTANE THRILLS & BLOCKBUSTERS", (221, 109, 105), 76341, {"with_genres": "28|12"}),
    "Sci-Fi & Fantasy": ("SCI-FI", "FUTURISTIC WORLDS & COSMIC SAGAS", (63, 180, 223), 157336, {"with_genres": "878|14"}),
    "Comedy": ("COMEDY", "LAUGH-OUT-LOUD FAVORITES & SATIRE", (244, 194, 81), 120467, {"with_genres": "35"}),
    "Animation": ("ANIMATION", "TIMELESS CLASSICS & MODERN MASTERPIECES", (59, 187, 136), 129, {"with_genres": "16"}),
    "Drama": ("DRAMA", "POWERHOUSE PERFORMANCES & HUMAN STORIES", (155, 73, 96), 278, {"with_genres": "18"}),
    "Crime": ("CRIME", "GRITTY HEISTS, MOBSTERS & DETECTIVES", (188, 159, 125), 238, {"with_genres": "80"}),
    "Horror": ("HORROR", "CHILLING TERROR & SUPERNATURAL DREAD", (145, 39, 191), 694, {"with_genres": "27"}),
    "Mystery & Thriller": ("THRILLER", "TENSION THAT NEVER LETS GO", (182, 61, 78), 6977, {"with_genres": "53|9648"}),
    "Romance & Rom-Com": ("ROMANCE", "LOVE STORIES WORTH FALLING FOR", (216, 91, 123), 4348, {"with_genres": "10749"}),
    "Stand-Up Comedy": ("STAND-UP", "COMICS, SPECIALS & LIVE WIRE SETS", (234, 160, 39), None, {"with_keywords": "9716"}),
    "Superhero": ("SUPERHERO", "CAPES, POWERS & COMIC-BOOK MYTH", (39, 91, 174), 155, {"with_keywords": "9715"}),
    "Martial Arts": ("MARTIAL ARTS", "DISCIPLINE, HONOR & FIGHTING GRACE", (199, 116, 100), 146, {"with_keywords": "779"}),
    "History & War": ("WAR", "BATTLEFIELDS, BROTHERHOOD & COST", (147, 154, 121), 857, {"with_genres": "10752|36"}),
    "Western": ("WESTERN", "DUST, GUNSMOKE & FRONTIER JUSTICE", (172, 124, 75), 429, {"with_genres": "37"}),
}


def font(w, s):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat-{w}.ttf"), s)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- material
def textless_backdrop(kind, tid):
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null") or {}
    bd = sorted([b for b in im.get("backdrops", []) if not b.get("iso_639_1") and b["width"] >= 1280],
                key=lambda b: (-b["vote_count"], -b["vote_average"]))
    return bd[0]["file_path"] if bd else None


def popular(title, filters, n=3, keep=(), avoid=()):
    """The genre's popular films right now: TMDB popularity, English, a vote floor, released in the last 4 years."""
    import datetime as dt
    since = (dt.date.today() - dt.timedelta(days=4 * 365)).isoformat()
    p = dict(filters, sort_by="popularity.desc", with_original_language="en", **{"vote_count.gte": 300,
             "primary_release_date.gte": since})
    if title != "Animation":
        p["without_genres"] = "16" + ("|99" if title != "Stand-Up Comedy" else "")
    r = [x for x in (tmdb("/discover/movie", **p) or {}).get("results", []) if x["id"] not in avoid]
    kept = [x for x in r[:6] if x["id"] in keep]
    order = kept + [x for x in r if x not in kept]
    out = []
    for x in order:
        path = textless_backdrop("movie", x["id"])
        if path:
            out.append((x["id"], x.get("title"), path))
        if len(out) == n:
            break
    rank = {x["id"]: i for i, x in enumerate(r)}
    return sorted(out, key=lambda x: rank.get(x[0], 99))


# ---------------------------------------------------------------- drawing
_PATH = {}


def frame_path(p, w=W, h=H, m=5, r=22):
    """The rounded card outline from the top centre clockwise, cut at fraction p of its length (constant speed)."""
    if (w, h) not in _PATH:
        x0, y0, x1, y1 = m, m, w - m, h - m
        pts = []

        def line(ax, ay, bx, by):
            k = max(2, int(math.hypot(bx - ax, by - ay) / 2))
            pts.extend((ax + (bx - ax) * i / k, ay + (by - ay) * i / k) for i in range(k))

        def arc(cx, cy, a0, a1):
            k = max(2, int(r * math.radians(abs(a1 - a0)) / 2))
            pts.extend((cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / k)),
                        cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / k))) for i in range(k))
        line(w / 2, y0, x1 - r, y0); arc(x1 - r, y0 + r, -90, 0)
        line(x1, y0 + r, x1, y1 - r); arc(x1 - r, y1 - r, 0, 90)
        line(x1 - r, y1, x0 + r, y1); arc(x0 + r, y1 - r, 90, 180)
        line(x0, y1 - r, x0, y0 + r); arc(x0 + r, y0 + r, 180, 270)
        line(x0 + r, y0, w / 2, y0)
        pts.append((w / 2, y0))
        cum = [0.0]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.hypot(bx - ax, by - ay))
        _PATH[(w, h)] = (pts, cum)
    pts, cum = _PATH[(w, h)]
    target = cum[-1] * max(0.0, min(1.0, p))
    out = [pts[0]]
    for k in range(1, len(pts)):
        if cum[k] <= target:
            out.append(pts[k])
        else:
            f = (target - cum[k - 1]) / max(1e-9, cum[k] - cum[k - 1])
            out.append((pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f))
            break
    return out


def tracked(d, xy, text, fnt, fill, sp):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + sp


def scene(img):
    """Kaptain's grade: the still, a dark gradient rising from the bottom and from the left behind the type."""
    im = art.graded(img, 0.95, 1.06, (W, H))
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for y in range(H):
        f = max(0.0, (y / H - 0.42) / 0.58)
        d.line((0, y, W, y), fill=round(225 * f ** 1.3))
    side = Image.new("L", (W, 1))
    for x in range(W):
        side.putpixel((x, 0), round(120 * max(0.0, 1 - x / (W * 0.6)) ** 1.6))
    m = ImageChops.lighter(m, ImageChops.multiply(side.resize((W, H)), Image.linear_gradient("L").resize((W, H))))
    return Image.composite(Image.new("RGB", (W, H), (6, 6, 10)), im, m)


def make(title, sub, accent, imgs):
    k = W / 1920
    tf, sf = font("ExtraBold", round(124 * k)), font("SemiBold", round(42 * k))
    sp_t, sp_s = round(3 * k), round(5 * k)
    x0 = round(106 * k)
    bars = [scene(i) for i in imgs]
    S = len(bars)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    title_y = round(H * 0.752) - tf.getbbox("A")[1]  # cap top at 73.8 % of the height, as on Kaptain's cards
    sub_y = round(H * 0.866) - sf.getbbox("A")[1]
    bar = (x0 - round(26 * k), round(H * 0.728), x0 - round(20 * k), round(H * 0.888))
    grey = (214, 220, 232)
    L0, L1 = 5 / 120, 105 / 120

    def mix(a, b, f):
        return tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3))

    def frame(i, n):
        t = i / n
        c = ease(t / L0) if t < 0.94 else 1 - ease((t - 0.94) / 0.06)
        q = min(1.0, max(0.0, (t - L0) / (L1 - L0)))
        seg = q * S
        j = min(S - 1, int(seg))
        loc = seg - j
        nxt, fade = (j + 1) % S, ((loc - 0.85) / 0.15 if loc > 0.85 and j < S - 1 else 0.0)
        if t > L1:
            j, nxt, loc, fade = S - 1, 0, 1.0, min(1.0, (t - L1) / (1 - L1))
        bg = art.zoomed(bars[j], 0.02 + 0.06 * min(1, loc))
        if fade > 0:
            bg = Image.blend(bg, art.zoomed(bars[nxt], 0.02), fade)
        breath = math.sin(math.pi * (t - L1) / 0.1) if L1 < t < L1 + 0.1 else 0.0
        cv = bg.convert("RGBA")
        d = ImageDraw.Draw(cv)
        d.rectangle(bar, fill=mix(accent, (255, 255, 255), c) + (255,))
        tracked(d, (x0, title_y), title, tf, (255, 255, 255, 255), sp_t)
        tracked(d, (x0 + 2, sub_y), sub, sf, mix(grey, accent, c) + (255,), sp_s)
        if c > 0:
            fr = Image.new("L", (W, H), 0)
            pts = frame_path(q)
            if len(pts) > 1 and q > 0:
                ImageDraw.Draw(fr).line(pts, fill=255, width=4, joint="curve")
            head = Image.new("L", (W, H), 0)
            if 0 < q < 1 and len(pts) > 1:
                hx, hy = pts[-1]
                ImageDraw.Draw(head).ellipse((hx - 9, hy - 9, hx + 9, hy + 9), fill=255)
            gm = ImageChops.lighter(fr, head).filter(ImageFilter.GaussianBlur(9 + 7 * breath))
            gl = Image.new("RGBA", (W, H), accent + (0,))
            gl.putalpha(gm.point(lambda v: min(255, round(v * (1.1 + 0.9 * breath) * c))))
            cv.alpha_composite(gl)
            ln = Image.new("RGBA", (W, H), accent + (0,))
            ln.putalpha(fr.point(lambda v: round(v * c)))
            cv.alpha_composite(ln)
        return cv.convert("RGB")
    return frame


def slug_of(t):
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


def build_one(job):
    t, keep, out = job
    title, sub, accent, icon, filters = GENRES[t]
    try:
        first = []
        if icon:
            p = textless_backdrop("movie", icon)
            info = tmdb(f"/movie/{icon}") or {}
            first = [(icon, info.get("title"), p)] if p else []
        picks = popular(t, filters, 3, keep, avoid={icon})
        seq = first + picks
        imgs = [art.fetch(p).convert("RGB") for _, _, p in seq]
        frame = make(title, sub, accent, imgs)
        dd = os.path.join(out, slug_of(t))
        os.makedirs(dd, exist_ok=True)
        n = 120  # 50 ms: 0.25 s in, 5 s lap with the films, 0.75 s breath and back
        frames = [frame(i, n).resize((OW, OH), Image.LANCZOS) for i in range(n)]
        frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * n,
                       loop=0, quality=80, method=5, minimize_size=True, allow_mixed=True)
        frame(0, n).save(os.path.join(dd, "cover.jpg"), quality=90)
        strip = Image.new("RGB", (OW * 3, OH * 2))
        for jj, idx in enumerate([0, 20, 45, 70, 104, 119]):
            strip.paste(frames[idx], ((jj % 3) * OW, (jj // 3) * OH))
        strip.save(os.path.join(dd, "frames.jpg"), quality=80)
        return t, [(x[0], x[1]) for x in picks], None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return t, [], str(e)


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    prev = {}
    if "--prev" in args:
        i = args.index("--prev")
        try:
            prev = json.load(open(args[i + 1])).get("picks", {})
        except Exception:
            prev = {}
        del args[i:i + 2]
    only = set(args)
    jobs = [(t, [p[0] for p in prev.get(t, [])], out) for t in GENRES if not only or t in only]
    from multiprocessing import Pool
    with Pool(4) as pool:
        res = pool.map(build_one, jobs)
    picks, failed = dict(prev), []
    for t, pk, err in res:
        if err:
            failed.append(t)
            print("FAILED", t, err)
        else:
            picks[t] = pk
            print("built", t, "·", ", ".join(str(x[1]) for x in pk))
    import datetime as dt
    os.makedirs(out, exist_ok=True)
    json.dump({"date": dt.date.today().isoformat(), "picks": picks}, open(os.path.join(out, "picks.json"), "w"),
              indent=1, ensure_ascii=False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
