"""Hero backdrop styles beyond a single scene (Ozzy, 31 Oct 2026):
  wall      platforms and genres: their titles' posters on a tilted wall, standing in the right of the frame and fading
            out to the left, so the hero shows the platform's or the genre's work at a glance
  portrait  actors and directors: a good photograph of the person on the right, over a blurred, darkened still from
            their best-known film
  scene     everything else, awards included (a ceremony's stage or its statuette): hero_compose.compose
All return a 1920x1080 image laid out for Nuvio TV (see hero_compose for the two layouts it has to survive).
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hero_compose as hc

W, H = 1920, 1080


def _cover(im, w, h, cy=0.5):
    r = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * r)), max(h, round(im.height * r))), Image.LANCZOS)
    x = (im.width - w) // 2
    y = int((im.height - h) * cy)
    return im.crop((x, y, x + w, y + h))


def _hmask(w, h, stops):
    m = Image.new("L", (w, 1))
    px = m.load()
    for x in range(w):
        f = x / max(1, w - 1)
        for (a, va), (b, vb) in zip(stops, stops[1:]):
            if a <= f <= b:
                px[x, 0] = int(va + (vb - va) * (f - a) / max(1e-6, b - a))
                break
    return m.resize((w, h))


def wall(posters, tint=(20, 20, 26), glow=None, seed=1, angle=-9.0, cols=7, rows=4):
    """posters: PIL images (2:3). A tilted wall of them on the right, rows offset like bricks, fading left and down."""
    rnd = random.Random(seed)
    pw, ph = 230, 345
    gap = 16
    cw, chh = cols * (pw + gap) + pw, rows * (ph + gap) + ph
    sheet = Image.new("RGB", (cw, chh), tint)
    ps = list(posters)
    k = 0
    for r in range(rows + 1):
        off = (pw + gap) // 2 if r % 2 else 0
        for c in range(cols + 1):
            if not ps:
                break
            p = ps[k % len(ps)]
            k += 1
            p = _cover(p.convert("RGB"), pw, ph, cy=0.0)
            sheet.paste(p, (c * (pw + gap) - off, r * (ph + gap) - ph // 3))
    sheet = sheet.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=tint)
    # place: the wall's centre right of the frame's centre, a little high
    scale = 1.18
    sheet = sheet.resize((round(sheet.width * scale), round(sheet.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), tint)
    x = round(W * 0.70 - sheet.width / 2)
    y = round(H * 0.42 - sheet.height / 2)
    canvas.paste(sheet, (x, y))
    # depth: posters further left are darker and softer; a light falls on the right
    soft = canvas.filter(ImageFilter.GaussianBlur(3))
    canvas = Image.composite(canvas, soft, _hmask(W, H, [(0, 0), (0.45, 120), (0.7, 255), (1, 255)]))
    dark = Image.new("RGB", (W, H), tint)
    canvas = Image.composite(dark, canvas, _hmask(W, H, [(0, 235), (0.35, 150), (0.62, 40), (1, 0)]))
    vg = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(min(255, v * 0.9)))
    canvas = Image.composite(dark, canvas, vg.point(lambda v: int(v * 0.55)))
    if glow:
        g = Image.new("RGB", (W, H), glow)
        canvas = Image.composite(g, canvas, _hmask(W, H, [(0, 0), (0.6, 0), (1, 46)]))
    return left_fade(ImageEnhance.Contrast(canvas).enhance(1.05))


_RB = None


def best_photo(photos):
    """of a person's photos (best voted first), the one that frames them best for the hero: the face well inside the
    photo (not at an edge, where a cut would run through it), shoulders below the chin, sharp enough"""
    scored = []
    for i, im in enumerate(photos):
        if im is None or im.height < 700:
            continue
        fs = hc.faces(im.convert("RGB"))
        if not fs:
            continue
        x0, y0, x1, y1 = fs[0][:4]
        frac = y1 - y0
        cx = (x0 + x1) / 2
        fit = abs(frac - 0.3)
        fit += 0.6 * max(0.0, abs(cx - 0.5) - 0.12)          # face pushed towards a side of the photo
        if y1 > 0.72:                                         # the chin near the bottom: nothing below the head
            fit += 0.3
        if x0 < 0.08 or x1 > 0.92 or y0 < 0.04:              # the face touches an edge: never usable
            fit += 2
        scored.append((fit + i * 0.02, i))
    if not scored:
        return next((im for im in photos if im is not None), None)
    return photos[min(scored)[1]]


def cutout(photo):
    """the person on a transparent background (rembg, isnet-general-use)"""
    global _RB
    from rembg import remove, new_session
    if _RB is None:
        _RB = new_session("isnet-general-use")
    im = photo.convert("RGB")
    im.thumbnail((1600, 1600))
    out = remove(im, session=_RB)
    a = out.getchannel("A").point(lambda v: 0 if v < 12 else v)
    out.putalpha(a)
    return out


FACE_H = 0.27          # the face (YuNet's box, brow to chin) in every portrait hero: this share of the frame's height
FACE_C = (0.72, 0.37)  # and its centre


def _edge_ramp(n, width):
    r = np.clip(np.arange(n) / max(1.0, width), 0, 1)
    return r * r * (3 - 2 * r)


def portrait(photo, film_still=None, tint=(14, 14, 18), mono=False):
    """photo: the person (portrait-oriented; cut out if it has no alpha). film_still: a still from their best-known
    film, blurred and darkened behind them for atmosphere. Every portrait puts the face at the same size and place
    (FACE_H, FACE_C); wherever the photo ends inside the frame, the figure dissolves into the backdrop, never cut."""
    bg = Image.new("RGB", (W, H), tint)
    if film_still is not None:
        b = _cover(film_still.convert("RGB"), W, H)
        b = b.filter(ImageFilter.GaussianBlur(14))
        mean = float(np.asarray(b.convert("L"), np.float32)[:, W // 2:].mean()) / 255   # behind the person
        b = ImageEnhance.Color(ImageEnhance.Brightness(b).enhance(min(0.6, 0.15 / max(0.05, mean)))).enhance(0.75)
        bg = b
    p = photo if photo.mode == "RGBA" else cutout(photo)
    if mono:
        g = ImageOps.grayscale(p.convert("RGB")).convert("RGBA")
        g.putalpha(p.getchannel("A"))
        p = g
    fs = hc.faces(p.convert("RGB"))
    if fs:
        fb = fs[0][:4]
    else:                                                     # no face found: assume a standard head-and-shoulders
        fb = (0.32, 0.18, 0.68, 0.45)
    scale = (H * FACE_H) / max(1.0, (fb[3] - fb[1]) * p.height)
    pw, ph = round(p.width * scale), round(p.height * scale)
    p = p.resize((pw, ph), Image.LANCZOS)
    fx0, fy0, fx1, fy1 = fb[0] * pw, fb[1] * ph, fb[2] * pw, fb[3] * ph
    x = round(W * FACE_C[0] - (fx0 + fx1) / 2)
    y = round(H * FACE_C[1] - (fy0 + fy1) / 2)
    a = np.asarray(p.getchannel("A"), np.float32)
    # dissolve every photo edge that falls inside the frame and that the figure touches, as wide as possible
    # without reaching the face (the face itself is never faded)
    a0 = a > 8
    m = np.ones((ph, pw), np.float32)
    marg = H * 0.04
    if x > 0 and a0[:, :3].mean() > 0.01:
        m *= _edge_ramp(pw, max(24, min(pw * 0.3, fx0 - marg)))[None, :]
    if x + pw < W and a0[:, -3:].mean() > 0.01:
        m *= _edge_ramp(pw, max(24, min(pw * 0.3, pw - fx1 - marg)))[::-1][None, :]
    if y > 0 and a0[:3, :].mean() > 0.01:
        m *= _edge_ramp(ph, max(24, min(ph * 0.2, fy0 - marg)))[:, None]
    # the bottom: the photo's own lower edge, or the frame's, whichever comes first
    bottom = min(ph, H - y)
    ramp_h = max(60, min(ph * 0.35, bottom - fy1 - marg))
    rows_ = np.arange(ph)[:, None]
    m *= np.clip((bottom - rows_) / ramp_h, 0, 1) ** 1.5
    p.putalpha(Image.fromarray((a * m).astype(np.uint8)))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    blk = Image.new("RGBA", p.size, (0, 0, 0, 255))
    blk.putalpha(p.getchannel("A").point(lambda v: int(v * 0.6)))
    sh.paste(blk, (x - 18, y + 10), blk)
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    out = bg.convert("RGBA")
    out.alpha_composite(sh)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(p, (x, y), p)
    out.alpha_composite(layer)
    return left_fade(out.convert("RGB"))


def left_fade(im, tint=(13, 13, 16)):
    """the hero's own left side melts into the TV's background colour, so wherever the TV starts drawing it (its box
    begins about a third of the way across), there is no edge between the title side and the picture"""
    m = _hmask(W, H, [(0, 255), (0.18, 235), (0.34, 150), (0.5, 40), (0.62, 0), (1, 0)])
    m = m.filter(ImageFilter.GaussianBlur(30))
    return Image.composite(Image.new("RGB", (W, H), tint), im, m)


def scene(im, subject=None):
    out, _ = hc.compose(im, subject)
    return left_fade(out)
