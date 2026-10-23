"""International Cinema row: Kaptain's country cards (the country's outline, its flag, "KOREAN CINEMA") brought to
life. On hover the outline draws itself again, the flag waves and steps aside, and the country's silhouette becomes a
window: three of its best-known films play inside the borders, the title under them; then the flag comes back.
Films: the folder's own language / country filters on TMDB, most-voted well-rated live action, a different three
every month (.github/workflows/intl-art.yml -> intl-art); pictures are TMDB textless stills.
Outlines: Natural Earth 1:50m countries (public domain). Flags: flagcdn.com.
usage: python3 art_tools/intl_art.py OUT_DIR [folder titles...]     (INTL_TEST=1: no TMDB / flag download)
"""
import datetime as dt, io, json, math, os, random, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from reletter import f as font, tracked, width

W, H = 1280, 720
OW, OH = 512, 288
TEST = bool(os.environ.get("INTL_TEST"))

# folder -> (name on the card, ISO codes drawn, lon/lat box (w, s, e, n), flag ISO or None, outline colours,
#            TMDB filters for the films)
CARDS = {
    "Türkiye": ("TURKISH CINEMA", ["TR"], (25.5, 35.6, 45.0, 42.3), "tr", [(227, 10, 23), (255, 255, 255)],
                {"with_original_language": "tr"}),
    "South Korea": ("KOREAN CINEMA", ["KR"], (125.8, 33.0, 129.7, 38.7), "kr", [(205, 46, 58), (0, 71, 160)],
                    {"with_original_language": "ko"}),
    "Japan": ("JAPANESE CINEMA", ["JP"], (128.5, 30.5, 146.0, 45.7), "jp", [(188, 0, 45), (255, 255, 255)],
              {"with_original_language": "ja"}),
    "Greater China": ("CHINESE CINEMA", ["CN", "HK", "TW"], (73.0, 17.5, 135.5, 54.0), "cn", [(222, 41, 16), (255, 222, 0)],
                      {"with_original_language": "zh|cn", "with_origin_country": "CN|HK|TW"}),
    "India": ("INDIAN CINEMA", ["IN"], (68.0, 6.5, 97.5, 35.8), "in", [(255, 153, 51), (19, 136, 8)],
              {"with_original_language": "hi|te|ta|ml"}),
    "UK & Ireland": ("BRITISH CINEMA", ["GB", "IE"], (-10.8, 49.8, 2.0, 59.5), "gb", [(1, 33, 105), (200, 16, 46)],
                     {"with_original_language": "en", "with_origin_country": "GB|IE"}),
    "France": ("FRENCH CINEMA", ["FR"], (-5.5, 41.2, 9.8, 51.3), "fr", [(0, 85, 164), (239, 65, 53)],
               {"with_original_language": "fr", "with_origin_country": "FR"}),
    "Spain": ("SPANISH CINEMA", ["ES"], (-9.6, 35.8, 4.5, 43.9), "es", [(170, 21, 27), (241, 191, 0)],
              {"with_original_language": "es", "with_origin_country": "ES"}),
    "Italy": ("ITALIAN CINEMA", ["IT"], (6.5, 36.5, 18.8, 47.2), "it", [(0, 146, 70), (206, 43, 55)],
              {"with_original_language": "it", "with_origin_country": "IT"}),
    "Germany": ("GERMAN CINEMA", ["DE"], (5.8, 47.2, 15.2, 55.1), "de", [(221, 0, 0), (255, 206, 0)],
                {"with_original_language": "de", "with_origin_country": "DE|AT|CH"}),
    "Nordic Noir": ("NORDIC CINEMA", ["DK", "SE", "NO", "FI", "IS"], (-24.8, 54.5, 31.8, 71.3), None,
                    [(0, 106, 167), (254, 204, 0)], {"with_original_language": "da|sv|no|fi|is"}),
    "Central & Eastern Europe": ("CENTRAL & EASTERN EUROPEAN CINEMA", ["PL", "CZ", "HU", "RO", "GR", "RS", "HR", "BA", "SI", "SK", "BG",
                                                                      "ME", "MK", "AL", "XK"],
                                 (12.0, 34.8, 30.0, 55.0), None, [(220, 20, 60), (60, 130, 230)],
                                 {"with_original_language": "pl|cs|hu|ro|el|sr|hr|bs|sl|sk|bg"}),
    "Latin America": ("LATIN AMERICAN CINEMA", ["MX", "GT", "BZ", "HN", "SV", "NI", "CR", "PA", "CO", "VE", "GY", "SR", "EC", "PE",
                                                "BR", "BO", "PY", "CL", "AR", "UY", "CU", "DO", "HT", "PR", "JM"],
                      (-118.0, -56.0, -34.0, 33.0), None, [(0, 156, 59), (255, 223, 0)],
                      {"with_original_language": "es|pt", "with_origin_country": "MX|AR|BR|CO|CL|PE|UY"}),
}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def amul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def cover_fit(im, w=W, h=H):
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def zoomed(im, z):
    w, h = im.size
    cw, ch = w / (1 + z), h / (1 + z)
    x, y = (w - cw) / 2, (h - ch) / 2
    return im.resize((w, h), Image.BILINEAR, box=(x, y, x + cw, y + ch))


def get(url):
    for _ in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}), timeout=90).read()
        except Exception as e:
            err = e
    raise err


# ---------------------------------------------------------------- the map
GEO = None


def rings_of(isos, box):
    """Outer rings (lon/lat) of the countries' polygons that fall in the box (mainland, no far-off territories)."""
    global GEO
    if GEO is None:
        cache = os.path.join(ROOT, "scripts", ".cache", "ne_50m_countries.geojson")
        if not os.path.exists(cache):
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            open(cache, "wb").write(get("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"))
        GEO = json.load(open(cache))
    w, s, e, n = box
    out = []
    for f in GEO["features"]:
        pr = f["properties"]
        iso = pr.get("ISO_A2_EH") if pr.get("ISO_A2_EH") not in (None, "-99") else pr.get("ISO_A2")
        if iso not in isos:
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            ring = poly[0]
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            if w <= cx <= e and s <= cy <= n:
                out.append(ring)
    return out


def projector(box, cx, cy, maxw, maxh):
    w, s, e, n = box
    k = math.cos(math.radians((s + n) / 2))
    sc = min(maxw / ((e - w) * k), maxh / (n - s))
    ox, oy = (w + e) / 2, (s + n) / 2
    return lambda lon, lat: (cx + (lon - ox) * k * sc, cy - (lat - oy) * sc)


def shape(rings, P, ss=2):
    """Filled mask and the outline paths in card pixels."""
    m = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(m)
    paths = []
    for r in rings:
        pts = [P(x, y) for x, y in r]
        d.polygon([(x * ss, y * ss) for x, y in pts], fill=255)
        paths.append(pts)
    return m.resize((W, H), Image.LANCZOS), paths


def outline(paths, cols, q=1.0, wpx=3):
    """The border drawn up to q (0..1) of its length, coloured along a gradient from the first colour to the second
    (top to bottom), with a soft glow."""
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    total = sum(sum(math.dist(a, b) for a, b in zip(p, p[1:])) for p in paths)
    left = total * q
    for p in sorted(paths, key=lambda p: -len(p)):
        if left <= 0:
            break
        run, out = 0.0, [p[0]]
        for a, b in zip(p, p[1:]):
            seg = math.dist(a, b)
            if run + seg > left:
                t = (left - run) / seg if seg else 0
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                run = left
                break
            out.append(b)
            run += seg
        if len(out) > 1:
            d.line(out, fill=255, width=wpx, joint="curve")
        left -= run
    ramp = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    c0, c1 = np.array(cols[0], np.float32), np.array(cols[1] if len(cols) > 1 else cols[0], np.float32)
    rgb = c0 * (1 - ramp) + c1 * ramp
    rgb = np.repeat(rgb, W, 1)
    glow = lay.filter(ImageFilter.GaussianBlur(8)).point(lambda v: min(255, v * 2))
    line = Image.fromarray(np.dstack([rgb, np.asarray(lay, np.float32)]).astype(np.uint8), "RGBA")
    gl = Image.fromarray(np.dstack([rgb, np.asarray(glow, np.float32) * 0.8]).astype(np.uint8), "RGBA")
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(gl)
    out.alpha_composite(line)
    return out


def flag_img(iso, h=150):
    if TEST or not iso:
        f = Image.new("RGB", (300, 200), (200, 30, 40))
        ImageDraw.Draw(f).ellipse((110, 60, 190, 140), fill=(255, 255, 255))
    else:
        f = Image.open(io.BytesIO(get(f"https://flagcdn.com/w640/{iso}.png"))).convert("RGB")
    return f.resize((round(f.width * h / f.height), h), Image.LANCZOS)


def waving(flag, t, amp=0.0):
    """The flag rippling: rows shifted by a travelling sine, light and shade on the folds."""
    a = np.asarray(flag.convert("RGB"), np.float32)
    h, w = a.shape[:2]
    pad = 14
    out = np.zeros((h + 2 * pad, w, 3), np.float32)
    alpha = np.zeros((h + 2 * pad, w), np.float32)
    xs = np.arange(w, dtype=np.float32)
    ph = xs / w * 2.4 * math.pi - t * 0.45
    dy = (np.sin(ph) * amp * (xs / w)).round().astype(int)
    shade = 1 + np.cos(ph) * 0.18 * amp / 10 * (xs / w)
    for x in range(w):
        y0 = pad + dy[x]
        out[y0:y0 + h, x] = a[:, x] * shade[x]
        alpha[y0:y0 + h, x] = 255
    return Image.fromarray(np.dstack([np.clip(out, 0, 255), alpha]).astype(np.uint8), "RGBA")


def framed_flag(im):
    """Kaptain's flags: a soft glow behind them."""
    pad = 30
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    gl = Image.new("RGBA", out.size, (255, 255, 255, 0))
    m = Image.new("L", out.size, 0)
    m.paste(im.getchannel("A"), (pad, pad))
    gl.putalpha(m.filter(ImageFilter.GaussianBlur(14)).point(lambda v: round(v * 0.5)))
    out.alpha_composite(gl)
    out.alpha_composite(im, (pad, pad))
    return out


# ---------------------------------------------------------------- films
def films_of(folder, n=3):
    flt = CARDS[folder][5]
    if TEST:
        import glob
        fs = [f for f in sorted(glob.glob("/home/claude/nuvio-art/mirror/files/*/*.jpg")) if os.path.getsize(f) > 150000]
        rnd = random.Random(folder)
        out = []
        while len(out) < n:
            p = rnd.choice(fs)
            im = Image.open(p)
            if im.width >= 1200 and 1.6 < im.width / im.height < 1.9:
                out.append((f"Test {len(out)}", 2000 + len(out), p))
        return out
    import kids_art as K
    pool = []
    for page in (1, 2):
        r = (K.tmdb("/discover/movie", sort_by="vote_count.desc", without_genres="16|99", page=page,
                    **{"vote_average.gte": 7.0, "vote_count.gte": 300}, **flt) or {}).get("results", [])
        pool += r
    pool = pool[:24]
    m = dt.date.today().year * 12 + dt.date.today().month
    start = (m * n) % max(1, len(pool))
    out = []
    for x in pool[start:] + pool[:start]:
        p = K.g.textless_backdrop("movie", x["id"])
        if p:
            out.append((x["title"], int((x.get("release_date") or "0")[:4] or 0), p))
        if len(out) == n:
            break
    return out


def load(p):
    if TEST:
        return Image.open(p).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


# ---------------------------------------------------------------- lettering
def name_layer(text, y, size=46, col=(205, 205, 210)):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fn = font("ExtraBold", size)
    while width(text, fn, 5) > W * 0.86 and fn.size > 24:
        fn = font("ExtraBold", fn.size - 2)
    tw = width(text, fn, 5)
    d = ImageDraw.Draw(lay)
    tracked(d, ((W - tw) / 2 + 3, y + 3), text, fn, (0, 0, 0, 200), 5)
    tracked(d, ((W - tw) / 2, y), text, fn, col + (255,), 5)
    return lay


def film_label(title, year):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    t = title.upper()
    fn = font("ExtraBold", 40)
    while width(t, fn, 3) > W - 140 and fn.size > 22:
        fn = font("ExtraBold", fn.size - 2)
    tracked(d, (58, H - 112), t, fn, (255, 255, 255, 255), 3)
    tracked(d, (60, H - 112 + fn.size + 10), str(year), font("SemiBold", 21), (220, 220, 225, 255), 8)
    return lay


def fall():
    f = np.clip((np.linspace(0, 1, H, dtype=np.float32) - 0.6) / 0.4, 0, 1) ** 1.3 * 0.85
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.putalpha(Image.fromarray((np.repeat(f[:, None], W, 1) * 255).astype(np.uint8)))
    return lay


# ---------------------------------------------------------------- the card
def build(folder, out):
    name, isos, box, fiso, cols, _ = CARDS[folder]
    films = films_of(folder)
    reals = [cover_fit(load(p)) for _, _, p in films]
    rings = rings_of(isos, box)
    # the map at rest (Kaptain's layout) and opened up (the silhouette as large as the card allows)
    P0 = projector(box, W / 2, H * 0.44, W * 0.86, H * 0.78)
    P1 = projector(box, W / 2, H * 0.5, W * 1.0, H * 0.98)
    m0, paths0 = shape(rings, P0)
    m1, paths1 = shape(rings, P1)
    ol0 = outline(paths0, cols)
    ol1 = outline(paths1, cols)
    fl = None if not fiso else flag_img(fiso)
    bg = Image.new("RGB", (W, H), (7, 7, 9))
    nm = name_layer(name, H * 0.72 if fiso else H * 0.8)
    fall_ = fall()
    labels = [film_label(t, y) for t, y, _ in films]

    def card(q_out=1.0, flag_t=0.0, flag_amp=0.0, flag_pos=0.0, name_a=1.0):
        """The resting card; flag_pos 0 = centre, 1 = top-left corner."""
        cv = bg.convert("RGBA")
        cv.alpha_composite(outline(paths0, cols, q_out) if q_out < 1 else ol0)
        if fl is not None:
            f = framed_flag(waving(fl, flag_t, flag_amp))
            sc = 1 - 0.55 * flag_pos
            f = f.resize((max(1, round(f.width * sc)), max(1, round(f.height * sc))), Image.LANCZOS)
            cx = W / 2 + (40 + f.width / 2 - W / 2) * flag_pos
            cy = H * 0.37 + (34 + f.height / 2 - H * 0.37) * flag_pos
            cv.alpha_composite(f, (round(cx - f.width / 2), round(cy - f.height / 2)))
        cv.alpha_composite(amul(nm, name_a))
        return cv

    cover = card().convert("RGB")
    HOLD, OPEN, SEG, CLOSE = 6, 22, 42, 18
    S = len(films)
    F0 = HOLD + OPEN
    N_ = F0 + SEG * S + CLOSE
    frames = []

    def window(pic, m, ol, a=1.0):
        # the whole film is there, held down in the dark; inside the borders it is lit
        dim = ImageEnhance.Brightness(pic.filter(ImageFilter.GaussianBlur(2))).enhance(0.3)
        cv = Image.blend(bg, dim, a).convert("RGBA")
        c = pic.convert("RGBA")
        c.putalpha(m.point(lambda v: round(v * a)))
        cv.alpha_composite(c)
        cv.alpha_composite(ol)
        return cv

    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < F0:
            # the border draws itself again, the map opens up and the first film comes in; the flag waves and steps aside
            u = (i - HOLD) / OPEN
            q = ease(u * 1.3)
            k = ease((u - 0.25) / 0.75)
            if k <= 0:
                cv = card(q_out=max(0.02, q), flag_t=i, flag_amp=10 * ease(u * 3), flag_pos=0, name_a=1 - ease(u * 3))
            else:
                P = projector(box, W / 2, H * (0.44 + 0.06 * k), W * (0.86 + 0.14 * k), H * (0.78 + 0.2 * k))
                m, paths = shape(rings, P, ss=1)
                ol = outline(paths, cols, q)
                cv = window(zoomed(reals[0], 0.02), m, ol, a=k)
                if fl is not None:
                    f = framed_flag(waving(fl, i, 10))
                    sc = 1 - 0.55 * k
                    f = f.resize((max(1, round(f.width * sc)), max(1, round(f.height * sc))), Image.LANCZOS)
                    cx = W / 2 + (40 + f.width / 2 - W / 2) * k
                    cy = H * 0.37 + (34 + f.height / 2 - H * 0.37) * k
                    cv.alpha_composite(f, (round(cx - f.width / 2), round(cy - f.height / 2)))
        elif i < F0 + SEG * S:
            kf, t = divmod(i - F0, SEG)
            pic = zoomed(reals[kf], 0.02 + 0.05 * t / SEG)
            if kf > 0 and t < 8:
                pic = Image.blend(zoomed(reals[kf - 1], 0.07), pic, ease(t / 8))
            cv = window(pic, m1, ol1)
            cv.alpha_composite(fall_)
            if fl is not None:
                f = framed_flag(waving(fl, i, 6))
                f = f.resize((round(f.width * 0.45), round(f.height * 0.45)), Image.LANCZOS)
                cv.alpha_composite(f, (40, 34))
            la = ease((t - 2) / 6) if t < 8 else (1 - ease((t - (SEG - 5)) / 5) if t >= SEG - 5 else 1.0)
            cv.alpha_composite(amul(labels[kf], la))
        else:
            # close up: the map shrinks back, the film leaves, the flag returns to the middle
            u = ease((i - (F0 + SEG * S)) / CLOSE)
            P = projector(box, W / 2, H * (0.5 - 0.06 * u), W * (1.0 - 0.14 * u), H * (0.98 - 0.2 * u))
            m, paths = shape(rings, P, ss=1)
            cv = window(zoomed(reals[-1], 0.07), m, outline(paths, cols), a=1 - u)
            if fl is not None:
                f = framed_flag(waving(fl, i, 6 * (1 - u)))
                sc = 0.45 + 0.55 * u
                f = f.resize((max(1, round(f.width * sc)), max(1, round(f.height * sc))), Image.LANCZOS)
                cx = 40 + f.width / 2 + (W / 2 - 40 - f.width / 2) * u
                cy = 34 + f.height / 2 + (H * 0.37 - 34 - f.height / 2) * u
                cv.alpha_composite(f, (round(cx - f.width / 2), round(cy - f.height / 2)))
            cv.alpha_composite(amul(nm, ease((u - 0.4) / 0.6)))
        frames.append(cv.convert("RGB").resize((OW, OH), Image.LANCZOS))
    d = os.path.join(out, slug_of(folder))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 12, 20, 30, 60, 100, 140, N_ - 6]):
        strip.paste(frames[min(idx, len(frames) - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return [f"{t} ({y})" for t, y, _ in films]


def save_reel(frames, cover, folder, out, suffix=""):
    d = os.path.join(out, slug_of(folder) + suffix)
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    n = len(frames)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 10, 18, 26, n // 3, n // 2, n * 3 // 4, n - 6]):
        strip.paste(frames[min(idx, n - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)


def main_ring(paths):
    p = max(paths, key=len)
    cum = [0.0]
    for a, b in zip(p, p[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    return p, cum


def runner(ring, cols, q, length=0.08, wpx=5):
    """A light running along the border: the stretch from q - length to q, brightest at its head."""
    p, cum = ring
    tot = cum[-1]
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    steps = 24
    for k in range(steps):
        a0 = (q - length + length * k / steps) % 1.0
        a1 = (q - length + length * (k + 1) / steps) % 1.0
        def at(fr):
            t = fr * tot
            i = max(0, min(len(cum) - 2, int(np.searchsorted(cum, t)) - 1))
            seg = cum[i + 1] - cum[i] or 1
            u = (t - cum[i]) / seg
            return (p[i][0] + (p[i + 1][0] - p[i][0]) * u, p[i][1] + (p[i + 1][1] - p[i][1]) * u)
        if a1 < a0:
            continue
        d.line([at(a0), at(a1)], fill=round(255 * (k + 1) / steps), width=wpx)
    glow = lay.filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, v * 3))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = Image.new("RGBA", (W, H), cols[1] if len(cols) > 1 and cols[1] != (255, 255, 255) else cols[0])
    g.putalpha(glow)
    out.alpha_composite(g)
    wl = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    wl.putalpha(lay)
    out.alpha_composite(wl)
    return out


def duotone(im, dark, light):
    g = np.asarray(im.convert("L"), np.float32)[..., None] / 255
    d_, l_ = np.array(dark, np.float32), np.array(light, np.float32)
    return Image.fromarray(np.clip(d_ * (1 - g) + l_ * g, 0, 255).astype(np.uint8))


def build_a2(folder, out):
    """Second take: the films fill the whole card and the country stays on top as its glowing border, with a light
    running round it; the flag spreads over the card and its colours give way to the film."""
    name, isos, box, fiso, cols, _ = CARDS[folder]
    films = films_of(folder)
    reals = [cover_fit(load(p)) for _, _, p in films]
    rings = rings_of(isos, box)
    P0 = projector(box, W / 2, H * 0.44, W * 0.86, H * 0.78)
    m0, paths0 = shape(rings, P0)
    ol0 = outline(paths0, cols)
    ring = main_ring(paths0)
    fl = None if not fiso else flag_img(fiso)
    bg = Image.new("RGB", (W, H), (7, 7, 9))
    nm = name_layer(name, H * 0.72 if fiso else H * 0.8)
    fall_ = fall()
    labels = [film_label(t, y) for t, y, _ in films]
    dark = tuple(int(v * 0.25) for v in cols[0])
    light = cols[1] if len(cols) > 1 and sum(cols[1]) < 700 else tuple(min(255, int(v * 1.3) + 60) for v in cols[0])
    first_tone = duotone(reals[0], dark, light)

    def flag_at(t, amp, sc, cx, cy, a=1.0):
        f = framed_flag(waving(fl, t, amp))
        f = f.resize((max(1, round(f.width * sc)), max(1, round(f.height * sc))), Image.LANCZOS)
        return f, round(cx - f.width / 2), round(cy - f.height / 2)

    cv = bg.convert("RGBA")
    cv.alpha_composite(ol0)
    if fl is not None:
        f, x, y = flag_at(0, 0, 1, W / 2, H * 0.37)
        cv.alpha_composite(f, (x, y))
    cv.alpha_composite(nm)
    cover = cv.convert("RGB")
    HOLD, OPEN, SEG, CLOSE = 6, 20, 44, 20
    S = len(films)
    F0 = HOLD + OPEN
    N_ = F0 + SEG * S + CLOSE
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < F0:
            u = (i - HOLD) / OPEN
            e = ease(u)
            # the film comes up in the flag's two colours, the true colours bloom after
            pic = Image.blend(first_tone, zoomed(reals[0], 0.01), ease((u - 0.55) / 0.45))
            cv = Image.blend(bg, pic, e).convert("RGBA")
            cv.alpha_composite(amul(fall_, e))
            cv.alpha_composite(amul(ol0, 1 - 0.45 * e))
            cv.alpha_composite(runner(ring, cols, (i - HOLD) / 60.0))
            if fl is not None:  # the flag swells and thins out over the card, then settles small in the corner
                if u < 0.6:
                    v = ease(u / 0.6)
                    f, x, y = flag_at(i, 10, 1 + 5 * v, W / 2, H * 0.37 + (H * 0.5 - H * 0.37) * v)
                    cv.alpha_composite(amul(f, 1 - v), (x, y))
                else:
                    v = ease((u - 0.6) / 0.4)
                    f, x, y = flag_at(i, 6, 0.45, 40 + 81, 34 + 52)
                    cv.alpha_composite(amul(f, v), (x, y))
            cv.alpha_composite(amul(nm, 1 - ease(u * 3)))
        elif i < F0 + SEG * S:
            kf, t = divmod(i - F0, SEG)
            pic = zoomed(reals[kf], 0.01 + 0.05 * t / SEG)
            if kf > 0 and t < 8:
                pic = Image.blend(zoomed(reals[kf - 1], 0.06), pic, ease(t / 8))
            cv = pic.convert("RGBA")
            cv.alpha_composite(fall_)
            cv.alpha_composite(amul(ol0, 0.55))
            cv.alpha_composite(runner(ring, cols, (i - HOLD) / 60.0))
            if fl is not None:
                f, x, y = flag_at(i, 6, 0.45, 40 + 81, 34 + 52)
                cv.alpha_composite(f, (x, y))
            la = ease((t - 2) / 6) if t < 8 else (1 - ease((t - (SEG - 5)) / 5) if t >= SEG - 5 else 1.0)
            cv.alpha_composite(amul(labels[kf], la))
        else:
            u = ease((i - (F0 + SEG * S)) / CLOSE)
            cv = Image.blend(zoomed(reals[-1], 0.06), bg, u).convert("RGBA")
            cv.alpha_composite(amul(fall_, 1 - u))
            cv.alpha_composite(amul(ol0, 0.55 + 0.45 * u))
            cv.alpha_composite(amul(runner(ring, cols, (i - HOLD) / 60.0), 1 - u))
            if fl is not None:
                sc = 0.45 + 0.55 * u
                f, x, y = flag_at(i, 6 * (1 - u), sc, (40 + 81) + (W / 2 - 121) * u, (34 + 52) + (H * 0.37 - 86) * u)
                cv.alpha_composite(f, (x, y))
            cv.alpha_composite(amul(nm, ease((u - 0.4) / 0.6)))
        frames.append(cv.convert("RGB").resize((OW, OH), Image.LANCZOS))
    save_reel(frames, cover, folder, out, "-a2")
    return [f"{t} ({y})" for t, y, _ in films]


def slug_of(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


if __name__ == "__main__":
    out = sys.argv[1]
    bad = False
    for fo in sys.argv[2:] or CARDS:
        try:
            fn = {"A2": build_a2}.get(os.environ.get("INTL_LOOK", "A"), build)
            print("built", fo, "·", ", ".join(fn(fo, out)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", fo, e)
            bad = True
    sys.exit(1 if bad else 0)
