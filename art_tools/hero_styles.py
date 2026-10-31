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


def wall(posters, tint=(20, 20, 26), glow=None, seed=1, angle=-9.0, cols=7, rows=4, shade=1.0):
    """posters: PIL images (2:3). A tilted wall of them on the right, rows offset like bricks, fading left and down.
    shade: how much the wall itself is darkened (1 = the Favourites look; lower = brighter posters)."""
    rnd = random.Random(seed)
    pw, ph = 230, 345
    gap = 16
    cw, chh = cols * (pw + gap) + pw, rows * (ph + gap) + ph
    sheet = Image.new("RGB", (cw, chh), tint)
    ps = list(posters)
    scale = 1.18
    # the posters go best first into the slots nearest the spot both TV layouts show clearly (right, upper half), so
    # a platform's best-known titles are the ones in view, not those lost off the frame's edge or in the fade
    th = math.radians(angle)
    slots = []
    for r in range(rows + 1):
        off = (pw + gap) // 2 if r % 2 else 0
        for c in range(cols + 1):
            sx, sy = c * (pw + gap) - off, r * (ph + gap) - ph // 3
            dx, dy = sx + pw / 2 - cw / 2, sy + ph / 2 - chh / 2
            fx = W * 0.70 + scale * (math.cos(th) * dx + math.sin(th) * dy)
            fy = H * 0.42 + scale * (-math.sin(th) * dx + math.cos(th) * dy)
            slots.append((math.hypot((fx - W * 0.76) / W, (fy - H * 0.32) / H * 0.8), sx, sy))
    slots.sort()
    for k, (_, sx, sy) in enumerate(slots):
        if not ps:
            break
        sheet.paste(_cover(ps[k % len(ps)].convert("RGB"), pw, ph, cy=0.0), (sx, sy))
    sheet = sheet.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=tint)
    # place: the wall's centre right of the frame's centre, a little high
    sheet = sheet.resize((round(sheet.width * scale), round(sheet.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), tint)
    x = round(W * 0.70 - sheet.width / 2)
    y = round(H * 0.42 - sheet.height / 2)
    canvas.paste(sheet, (x, y))
    # depth: posters further left are darker and softer; a light falls on the right
    soft = canvas.filter(ImageFilter.GaussianBlur(3))
    canvas = Image.composite(canvas, soft, _hmask(W, H, [(0, 0), (0.45, 120), (0.7, 255), (1, 255)]))
    dark = Image.new("RGB", (W, H), tint)
    canvas = Image.composite(dark, canvas, _hmask(W, H, [(0, 235), (0.35, round(150 * shade)), (0.62, round(40 * shade)),
                                                         (1, 0)]))
    vg = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(min(255, v * 0.9)))
    canvas = Image.composite(dark, canvas, vg.point(lambda v: int(v * 0.55 * shade)))
    if glow:
        g = Image.new("RGB", (W, H), glow)
        canvas = Image.composite(g, canvas, _hmask(W, H, [(0, 0), (0.6, 0), (1, 46)]))
    return left_fade(ImageEnhance.Contrast(canvas).enhance(1.05))


_RB = None


def best_photo(photos, min_h=700):
    """of a person's photos (best voted first), the one that frames them best for the hero: the face well inside the
    photo (not at an edge, where a cut would run through it), shoulders below the chin, sharp enough"""
    scored = []
    for i, im in enumerate(photos):
        if im is None or im.height < min_h:
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
        # room below the chin, in face heights: a head and shoulders needs about 1.3; less leaves a floating head
        room = (1 - y1) / max(0.05, frac)
        fit += 3.0 * max(0.0, 1.3 - room)
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
    # rembg leaves a faint veil of the photo's own background (a pale halo on studio shots): drop the weak alpha
    a = out.getchannel("A").point(lambda v: 0 if v < 70 else min(255, int((v - 70) * 255 / 150)))
    a = a.filter(ImageFilter.GaussianBlur(1.2))
    out.putalpha(a)
    return out


FACE_H = 0.29          # the face (YuNet's box, brow to chin) in every portrait hero: this share of the frame's height
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
    # a cut-out that kept the photo's background (dark or busy studio backdrops) shows as a box: the top edge is
    # opaque across. Then blend the photo in with a soft oval around the head and shoulders instead.
    al = np.asarray(p.getchannel("A"), np.float32) / 255
    top, side = al[: max(2, p.height // 50), :].mean(), al[: p.height // 2, :max(2, p.width // 50)].mean()
    side = max(side, al[: p.height // 2, -max(2, p.width // 50):].mean())
    if os.environ.get("HERO_DEBUG"):
        print(f"  cutout: top {top:.2f} side {side:.2f} mean {al.mean():.2f}")
    room = (1 - fb[3]) / max(0.05, fb[3] - fb[1])           # face heights of figure below the chin
    if top > 0.6 and side > 0.6:                            # the cut-out kept the photo's box
        yy, xx = np.mgrid[0:p.height, 0:p.width]
        cx, cy = (fb[0] + fb[2]) / 2 * p.width, (fb[1] + fb[3]) / 2 * p.height
        fhh = (fb[3] - fb[1]) * p.height
        rx, ry = fhh * 1.25, fhh * 1.9
        dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy - fhh * 0.5) / ry) ** 2)
        oval = np.clip((1.25 - dist) / 0.55, 0, 1)
        oval = oval * oval * (3 - 2 * oval)
        p = photo.convert("RGB").resize(p.size, Image.LANCZOS).convert("RGBA")   # the photo itself, not the
        p.putalpha(Image.fromarray((oval * 255).astype(np.uint8)))
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
    # the fade starts below the shoulders (about a face height under the chin), never at the neck
    ramp_h = max(0.6 * (fy1 - fy0), min(ph * 0.35, bottom - fy1 - 0.9 * (fy1 - fy0)))
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


def straight_edge(im):
    """how far the longest sharp vertical step in the picture runs (share of its height): high in key art pasted
    together from panels and in letterboxed stills, low in an ordinary film frame"""
    g = np.asarray(im.convert("L").resize((480, 270)), np.float32)
    m = np.abs(np.diff(g, axis=1))[:, 20:-20] > 40
    best = 0
    run = np.zeros(m.shape[1], int)
    for row in m:
        run = np.where(row, run + 1, 0)
        best = max(best, int(run.max()))
    return best / 270


def pick_still(stills):
    """of a card's film stills (in the card's order), the one that makes the best scene hero: its subject at a good
    size without shrinking the picture (which would leave much of the frame to the blurred fill) and no hard,
    panel-like edges. Returns (index, image)."""
    best = None
    for i, im in enumerate(stills):
        if im is None:
            continue
        _, info = hc.compose(im)
        score = i * 0.08 + 1.5 * max(0.0, 0.9 - info["scale"]) + 0.002 * max(0, info["offset"][0] - 350) \
            + 4 * max(0.0, straight_edge(im) - 0.25)
        if best is None or score < best[0]:
            best = (score, i, im)
    return (best[1], best[2]) if best else (None, None)


def scene(im, subject=None):
    out, _ = hc.compose(im, subject)
    return left_fade(out)


def photo_panel(photo, tint=(13, 13, 16)):
    """the person's own photograph, not cut out: set on the right at the portrait size and place (FACE_H, FACE_C),
    its own background kept and dissolving into the dark on every side, over a blurred glow of the same photo"""
    p = photo.convert("RGB")
    fs = hc.faces(p)
    fb = fs[0][:4] if fs else (0.32, 0.18, 0.68, 0.45)
    scale = (H * FACE_H) / max(1.0, (fb[3] - fb[1]) * p.height)
    pw, ph = round(p.width * scale), round(p.height * scale)
    big = ImageEnhance.Color(p.resize((pw, ph), Image.LANCZOS)).enhance(0.9)
    fx0, fy0, fx1, fy1 = fb[0] * pw, fb[1] * ph, fb[2] * pw, fb[3] * ph
    x = round(W * FACE_C[0] - (fx0 + fx1) / 2)
    y = round(H * FACE_C[1] - (fy0 + fy1) / 2)
    fw, fh = fx1 - fx0, fy1 - fy0
    # an ellipse round the head and shoulders, wide and soft: the photo's own backdrop melts away from the person
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2 + fh * 0.55
    d = np.sqrt(((xx - cx) / (fw * 2.1)) ** 2 + ((yy - cy) / (fh * 2.0)) ** 2)
    m = np.clip((1.0 - d) / 0.55, 0, 1)
    m = m * m * (3 - 2 * m)
    # and never a hard photo edge inside the frame
    m *= _edge_ramp(pw, pw * 0.12)[None, :] * _edge_ramp(pw, pw * 0.12)[::-1][None, :]
    m *= _edge_ramp(ph, ph * 0.10)[:, None] * _edge_ramp(ph, ph * 0.25)[::-1][:, None]
    out = Image.new("RGB", (W, H), tint)
    glow = big.resize((W, H)).filter(ImageFilter.GaussianBlur(60))
    glow = ImageEnhance.Brightness(glow).enhance(0.35)
    out = Image.composite(glow, out, _hmask(W, H, [(0, 0), (0.45, 0), (0.75, 200), (1, 230)]))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bp = big.convert("RGBA"); bp.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    layer.paste(bp, (x, y), bp)
    out = out.convert("RGBA"); out.alpha_composite(layer)
    return left_fade(out.convert("RGB"))


SFACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "face_recognition_sface_2021dec.onnx")
_REC = None


def _embeds(im):
    """(box fractions, embedding) for every face YuNet finds in im"""
    global _REC
    import cv2
    if _REC is None:
        _REC = cv2.FaceRecognizerSF.create(SFACE, "")
    small = im.convert("RGB").copy()
    small.thumbnail((1280, 1280))
    a = cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2BGR)
    det = cv2.FaceDetectorYN.create(hc.YUNET, "", (a.shape[1], a.shape[0]), 0.7, 0.3, 50)
    _, found = det.detect(a)
    out = []
    for f in (found if found is not None else []):
        if f[2] * f[3] < a.shape[0] * a.shape[1] * 0.001:
            continue
        e = _REC.feature(_REC.alignCrop(a, f))
        x, y, w, h = f[:4]
        out.append(((x / a.shape[1], y / a.shape[0], (x + w) / a.shape[1], (y + h) / a.shape[0]), e))
    return out


def find_in_stills(photo, stills, thr=0.38):
    """the still in which the person of photo is seen best: their face recognised (SFace), large and clear.
    Returns (index, face box) or (None, None)."""
    import cv2
    ref = _embeds(photo)
    if not ref:
        return None, None
    ref = max(ref, key=lambda r: (r[0][2] - r[0][0]) * (r[0][3] - r[0][1]))[1]
    best = None
    for i, im in enumerate(stills):
        if im is None:
            continue
        found = _embeds(im)
        crowd = 0.06 * max(0, len(found) - 3)         # a collage of the cast (key art) is not a scene
        for box, e in found:
            s = _REC.match(ref, e, cv2.FaceRecognizerSF_FR_COSINE)
            if s < thr:
                continue
            size = box[3] - box[1]
            score = s + 1.5 * min(size, 0.35) - 0.02 * i - crowd
            if box[1] < 0.07 or box[0] < 0.03 or box[2] > 0.97:   # the head at the still's edge: it would be cut
                score -= 1.0
            if best is None or score > best[0]:
                best = (score, i, box)
    return (best[1], best[2]) if best else (None, None)


def person_scene(still, face):
    """a film still with the person in it, laid out like every hero: their face (and a body's room) is the subject"""
    x0, y0, x1, y1 = face
    fh, fw = y1 - y0, x1 - x0
    box = (x0 - fw * 0.9, y0 - fh * 0.35, x1 + fw * 0.9, min(1.0, y1 + fh * 1.6))
    return scene(still, box)
