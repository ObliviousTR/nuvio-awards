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
    return ImageEnhance.Contrast(canvas).enhance(1.05)


_RB = None


def best_photo(photos):
    """of a person's photos (best voted first), the one that shows more than a face: a waist-up or shoulders-up
    portrait, sharp enough for the frame"""
    scored = []
    for i, im in enumerate(photos):
        if im is None or im.height < 900:
            continue
        fs = hc.faces(im.convert("RGB"))
        if not fs:
            continue
        frac = (fs[0][3] - fs[0][1])
        fit = abs(frac - 0.3)
        if fs[0][3] > 0.72:                 # the chin near the photo's bottom: a head with nothing below it
            fit += 0.3
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


def portrait(photo, film_still=None, tint=(14, 14, 18), mono=False):
    """photo: the person (portrait-oriented; cut out if it has no alpha). film_still: a still from their best-known
    film, blurred and darkened behind them for atmosphere."""
    bg = Image.new("RGB", (W, H), tint)
    if film_still is not None:
        b = _cover(film_still.convert("RGB"), W, H)
        b = b.filter(ImageFilter.GaussianBlur(14))
        # darken to a steady level whatever the still: about 15% mean brightness behind the person
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
        face_h = (fs[0][3] - fs[0][1]) * p.height
        ph = round(p.height * (H * 0.32) / max(1.0, face_h))
    else:
        ph = H
    ph = max(ph, round(H * 0.5))
    pw = round(p.width * ph / p.height)
    p = p.resize((pw, ph), Image.LANCZOS)
    if fs:
        fx = (fs[0][0] + fs[0][2]) / 2 * pw
        fy = (fs[0][1] + fs[0][3]) / 2 * ph
    else:
        fx, fy = pw / 2, ph * 0.3
    x = round(W * 0.72 - fx)
    y = min(round(H * 0.36 - fy), round(H * 0.04))
    # the body fades out towards the bottom of the frame
    a = np.asarray(p.getchannel("A"), np.float32)
    rows_ = np.arange(ph)[:, None] + y
    fade = np.clip((H * 0.98 - rows_) / (H * 0.28), 0, 1)
    own = np.clip((ph - np.arange(ph)[:, None]) / (ph * 0.3), 0, 1)     # and towards the photo's own bottom edge
    fade = np.minimum(fade, own)
    # where the photo itself cuts the figure (shoulders running off its sides), dissolve the cut: the figure fades
    # out over the last fifth of the photo's width on each side it touches, on a smooth curve, never a straight edge
    a0 = a > 8
    touch_l = a0[:, :3].mean() > 0.02
    touch_r = a0[:, -3:].mean() > 0.02
    xs = np.arange(pw)[None, :]
    side = np.ones((1, pw))
    fw = pw * 0.22
    if touch_l:
        side = np.minimum(side, np.clip(xs / fw, 0, 1))
    if touch_r:
        side = np.minimum(side, np.clip((pw - 1 - xs) / fw, 0, 1))
    side = side * side * (3 - 2 * side)                                  # smoothstep
    own = own * own * (3 - 2 * own)
    fade = np.minimum(np.clip((H * 0.98 - rows_) / (H * 0.28), 0, 1), own) * side
    p.putalpha(Image.fromarray((a * fade).astype(np.uint8)))
    # a soft shadow and a faint rim of the backdrop's light around the figure
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
    return out.convert("RGB")


def scene(im, subject=None):
    out, _ = hc.compose(im, subject)
    return out
