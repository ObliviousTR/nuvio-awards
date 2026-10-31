"""Folder hero backdrops for Nuvio TV (Ozzy, 31 Oct 2026).

Nuvio TV shows a folder's heroBackdropUrl behind the home screen's top area when the folder is focused. In the default
layout the image fills a box 72% of the screen wide and about 57% high (roughly 2.25:1), cropped from its TOP RIGHT
corner, pushed slightly past the right edge, with the left 45% of the screen faded to the background. With the
full-screen backdrop setting it fills the whole 16:9 screen, the left 65% faded. A subject in the middle or low in a
16:9 still is therefore cut or hidden. compose() places the subject (faces, else the most salient region) in the area
both layouts show clearly, right of centre and in the upper three quarters, and fills what the move leaves empty with
a blurred, darkened continuation of the same picture.

usage: python3 art_tools/hero_compose.py SRC OUT.jpg [--subject x0,y0,x1,y1 (fractions)]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

W, H = 1920, 1080
HERE = os.path.dirname(os.path.abspath(__file__))
YUNET = os.path.join(HERE, "models", "face_detection_yunet_2023mar.onnx")
# where a subject should sit (fractions of the 16:9 frame): visible in both layouts, clear of the left fade
SAFE = (0.47, 0.05, 0.92, 0.74)
TARGET = (0.69, 0.40)


def faces(im):
    """face boxes (fractions) found by YuNet, largest first"""
    try:
        import cv2
    except Exception:
        return []
    if not os.path.exists(YUNET):
        return []
    small = im.copy()
    small.thumbnail((1280, 1280))
    a = cv2.cvtColor(np.asarray(small.convert("RGB")), cv2.COLOR_RGB2BGR)
    det = cv2.FaceDetectorYN.create(YUNET, "", (a.shape[1], a.shape[0]), 0.8, 0.3, 50)
    _, found = det.detect(a)
    out = []
    for f in (found if found is not None else []):
        x, y, w, h = f[:4]
        if w * h < (a.shape[0] * a.shape[1]) * 0.0015:          # crowd faces and posters on walls do not count
            continue
        out.append((x / a.shape[1], y / a.shape[0], (x + w) / a.shape[1], (y + h) / a.shape[0], float(f[-1])))
    out.sort(key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))
    return out


def salient(im):
    """the bounding box of the most salient region (fractions)"""
    # spectral residual saliency (Hou & Zhang 2007) on a small grey copy, plus a little colour contrast
    small = im.convert("RGB").resize((128, max(1, round(128 * im.height / im.width))), Image.BILINEAR)
    g = np.asarray(small.convert("L"), np.float64)
    f = np.fft.fft2(g)
    logamp = np.log(np.abs(f) + 1e-9)
    from scipy.ndimage import uniform_filter, gaussian_filter
    resid = logamp - uniform_filter(logamp, 3)
    sal = np.abs(np.fft.ifft2(np.exp(resid + 1j * np.angle(f)))) ** 2
    lab = np.asarray(small.convert("LAB"), np.float64)
    colour = np.sqrt(((lab - lab.reshape(-1, 3).mean(0)) ** 2).sum(-1))
    m = gaussian_filter(sal / (sal.max() + 1e-9), 4) + 0.6 * gaussian_filter(colour / (colour.max() + 1e-9), 4)
    t = np.percentile(m, 88)
    ys, xs = np.where(m >= t)
    if not len(xs):
        return (0.3, 0.2, 0.7, 0.8)
    wgt = m[ys, xs]
    cx, cy = np.average(xs, weights=wgt) / m.shape[1], np.average(ys, weights=wgt) / m.shape[0]
    x0, x1 = np.percentile(xs, [10, 90]) / m.shape[1]
    y0, y1 = np.percentile(ys, [10, 90]) / m.shape[0]
    return (min(x0, cx - 0.08), min(y0, cy - 0.1), max(x1, cx + 0.08), max(y1, cy + 0.1))


def subject_box(im):
    fs = faces(im)
    if fs:
        # the main faces and a body's worth of room below them
        keep = [f for f in fs if (f[2] - f[0]) >= 0.45 * (fs[0][2] - fs[0][0])][:4]
        x0 = min(f[0] for f in keep); x1 = max(f[2] for f in keep)
        y0 = min(f[1] for f in keep); y1 = max(f[3] for f in keep)
        fh = y1 - y0
        return (x0 - 0.35 * fh * im.height / im.width, y0 - 0.25 * fh, x1 + 0.35 * fh * im.height / im.width,
                min(1.0, y1 + 1.2 * fh)), "faces"
    return salient(im), "saliency"


def compose(src, subject=None, zoom_limit=1.35):
    im = src.convert("RGB")
    box, how = (subject, "given") if subject else subject_box(im)
    bx0, by0, bx1, by1 = [min(1.0, max(0.0, v)) for v in box]
    # base scale: the image covers the frame's height
    s0 = H / im.height
    if im.width * s0 < W:
        s0 = W / im.width
    # zoom in until the subject is a decent size, out until it fits the safe area
    sw, sh = (bx1 - bx0) * im.width, (by1 - by0) * im.height
    zw, zh = (SAFE[2] - SAFE[0]) * W, (SAFE[3] - SAFE[1]) * H
    fit = min(zw / max(1, sw * s0), zh / max(1, sh * s0))
    s = s0 * max(0.72, min(zoom_limit, fit))
    iw, ih = round(im.width * s), round(im.height * s)
    big = im.resize((iw, ih), Image.LANCZOS)
    cx, cy = (bx0 + bx1) / 2 * iw, (by0 + by1) / 2 * ih
    # a wide subject (a group) sits nearer the middle, so its left end is not lost in the fade
    wide = min(1.0, max(0.0, ((bx1 - bx0) - 0.35) / 0.3))
    ox, oy = (TARGET[0] - 0.1 * wide) * W - cx, TARGET[1] * H - cy
    # never leave a gap at the top or the right: those are the edges both layouts show
    ox = max(ox, W - iw)
    oy = min(oy, 0)
    ox = min(ox, W * 0.5)                      # at most half the frame comes from the fill
    oy = max(oy, H - ih - H * 0.0) if ih >= H else oy
    # the fill: the picture itself, covering the frame, blurred and darkened
    fill = im.resize((max(W, round(im.width * H / im.height)), H), Image.BILINEAR)
    fill = fill.crop((fill.width - W, 0, fill.width, H)) if fill.width > W else fill.resize((W, H))
    fill = fill.filter(ImageFilter.GaussianBlur(28))
    fill = ImageEnhance.Brightness(fill).enhance(0.62)
    out = fill.copy()
    mask = Image.new("L", (iw, ih), 255)
    # a long, smooth seam: the picture melts into its own blurred continuation, never a visible edge
    feather = max(260, round(min(ox, W * 0.5) * 1.1)) if ox > 0 else 1
    ramp = np.clip(np.arange(iw) / feather, 0, 1) if ox > 0 else np.ones(iw)
    rampy = np.clip((ih - 1 - np.arange(ih)) / 220, 0, 1) if oy + ih < H else np.ones(ih)
    ramp = ramp * ramp * (3 - 2 * ramp)
    rampy = rampy * rampy * (3 - 2 * rampy)
    mpx = (np.outer(rampy, ramp) * 255).astype(np.uint8)
    out.paste(big, (round(ox), round(oy)), Image.fromarray(mpx))
    return out, dict(box=(bx0, by0, bx1, by1), how=how, scale=s / s0, offset=(round(ox), round(oy)))


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    subj = None
    if "--subject" in sys.argv:
        subj = tuple(float(v) for v in sys.argv[sys.argv.index("--subject") + 1].split(","))
    out, info = compose(Image.open(src), subj)
    out.save(dst, quality=90)
    print(info)
