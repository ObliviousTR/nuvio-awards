"""Anime row hovers: Kaptain's "layout sheet" cover comes alive and turns into his hover state.

Kaptain ships each Anime card as two stills, a cover (outlined word, white kanji, pop-out characters) and a hover
(card edge lit in the category colour, word / kanji / show line filled with it, pop-out group a little bigger and
glowing). This animates the step from one to the other, in the same rhythm as the Networks and Genres rows:
  hold the cover -> a colour line runs once round the card edge at constant speed (5 s lap)
  -> kanji fill top to bottom, the word fills left to right, the show line after it
  -> the pop-out group steps forward into its hover pose and its glow comes up
  -> lap closes, one breath of the edge light -> everything drains back to the cover (seamless loop).
Nothing is redrawn: every pixel comes from Kaptain's two images, so the look is exactly his.
usage: python3 art_tools/anime_art.py OUT_DIR slug [slug ...]   (slugs as in Kaptain's art/anime/<slug>/)
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from keyframe_webp import encode

KAPTAIN = os.environ.get("KAPTAIN_ART", "/home/claude/imkaptain/nuvio-art/art/anime")
W, H = 1280, 720          # working size
OUT = (512, 288)          # hover size, as the other landscape rows
N, MS = 100, 50           # 5 s


def load(slug, kind):
    return np.asarray(Image.open(f"{KAPTAIN}/{slug}/{slug}-{kind}.png").convert("RGB").resize((W, H), Image.LANCZOS),
                      dtype=np.float32)


def warp(img, s, ax, ay):
    """Scale about (ax, ay) by s."""
    a = 1 / s
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return np.asarray(im.transform((W, H), Image.AFFINE, (a, 0, ax - a * ax, 0, a, ay - a * ay), Image.BICUBIC),
                      dtype=np.float32)


def fit_group(C, Hv, region):
    """Find how Kaptain moved the pop-out group between cover and hover (scale about an anchor), coarse to fine,
    judged on the pixels that changed (region)."""
    w, h = 320, 180
    c = np.asarray(Image.fromarray(C.astype(np.uint8)).resize((w, h)), dtype=np.float32)
    hv = np.asarray(Image.fromarray(Hv.astype(np.uint8)).resize((w, h)), dtype=np.float32)
    reg = np.asarray(Image.fromarray((region * 255).astype(np.uint8)).resize((w, h))) > 127
    cim = Image.fromarray(c.astype(np.uint8))

    def err(s, ax, ay):
        a = 1 / s
        im = cim.transform((w, h), Image.AFFINE, (a, 0, ax - a * ax, 0, a, ay - a * ay), Image.BILINEAR)
        return np.abs(np.asarray(im, dtype=np.float32) - hv)[reg].mean()

    best = (err(1, 0, 0), 1.0, 0, 0)
    for s in np.arange(1.01, 1.21, 0.01):
        for ax in range(-w // 2, w * 3 // 2 + 1, 10):
            for ay in range(-h // 2, h * 3 // 2 + 1, 10):
                e = err(s, ax, ay)
                if e < best[0]:
                    best = (e, s, ax, ay)
    e, s, ax, ay = best
    for s2 in np.arange(s - .01, s + .0101, .0025):
        for ax2 in range(ax - 10, ax + 11, 2):
            for ay2 in range(ay - 10, ay + 11, 2):
                e2 = err(s2, ax2, ay2)
                if e2 < best[0]:
                    best = (e2, s2, ax2, ay2)
    e, s, ax, ay = best
    return float(s), ax * W / w, ay * H / h


def group_core(C, Hv, s, ax, ay):
    """Silhouette of the pop-out group in its hover pose: pixels that the scaled cover explains clearly better than
    the cover in place (they moved), closed and hole-filled; flat areas that can't tell are kept when inside."""
    from scipy import ndimage as ndi
    bl = lambda x: np.asarray(Image.fromarray(np.clip(x, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)),
                              dtype=np.float32)
    hb = bl(Hv)
    ec = np.abs(hb - bl(C)).mean(2)
    eg = np.abs(hb - bl(warp(C, s, ax, ay))).mean(2)
    moved = (ec - eg > 8) & (eg < 16)
    static = eg - ec > 8
    core = ndi.binary_opening(moved, iterations=2)
    core = ndi.binary_closing(core, iterations=14) & ~static
    core = ndi.binary_fill_holes(core)
    core |= (ec < 10) & (eg < 10) & ndi.binary_dilation(core, iterations=10)
    core = ndi.binary_fill_holes(ndi.binary_closing(core, iterations=3))
    lab, n = ndi.label(core)
    if n:
        sz = ndi.sum(core, lab, range(1, n + 1))
        core = np.isin(lab, 1 + np.nonzero(sz > 3000)[0])
    return core.astype(np.float32)


def soft(mask, grow=0, feather=0):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    if grow:
        im = im.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    if feather:
        im = im.filter(ImageFilter.GaussianBlur(feather))
    return np.asarray(im, dtype=np.float32) / 255


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def back(x, k=1.6):
    """Ease out with a small overshoot, for the group stepping forward."""
    x = min(1.0, max(0.0, x)) - 1
    return 1 + x * x * ((k + 1) * x + k)


def wipe(coord, lo, hi, p, edge=0.06):
    """1 where the sweep (lo->hi along coord) has passed, with a soft leading edge."""
    t = (coord - lo) / max(1e-6, hi - lo)
    return np.clip((p * (1 + edge) - t) / edge, 0, 1)


def build(slug, out_dir):
    from scipy import ndimage as ndi
    C, Hv = load(slug, "cover"), load(slug, "hover")
    D = np.abs(C - Hv).max(2) > 18
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    edge_d = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy])
    Bz = soft(D * (edge_d < 22), 3, 2)

    # the category colour, read off the lit card edge
    band = D & (edge_d >= 1) & (edge_d <= 6)
    px = Hv[band]
    px = px[px.max(1) - px.min(1) > 60]
    accent = np.median(px, 0) if len(px) else np.array([230., 80., 110.])
    acc_like = (np.abs(Hv - accent).max(2) < 62) & D & (edge_d >= 22)

    # pop-out group: fit on what changed outside the type, then its silhouette in the hover pose
    fit = f"{KAPTAIN}/{slug}/{slug}-fit.json"
    if os.path.exists(fit):                      # our own sheets (anime_sheet.py) say exactly how the group moved
        import json
        j = json.load(open(fit))
        s, ax, ay = j["scale"], j["anchor"][0] * W / j["size"][0], j["anchor"][1] * H / j["size"][1]
        core = (np.asarray(Image.open(f"{KAPTAIN}/{slug}/{slug}-core.png").convert("L").resize((W, H))) > 127).astype(np.float32)
    else:
        s, ax, ay = fit_group(C, Hv, (D & (edge_d >= 22) & ~acc_like & (xx > W * 0.3)).astype(np.float32))
        core = group_core(C, Hv, s, ax, ay)
    print(slug, "accent", accent.round(), "group scale %.3f anchor (%d, %d)" % (s, ax, ay))
    coreH = soft(core, 0, 0.8)                                                        # hover pose
    coreC = warp(coreH[..., None].repeat(3, 2) * 255, 1 / s, ax, ay)[..., 0] / 255    # cover pose

    # type: solid colour shapes (kanji, word, show line) that are not part of the glow round the group
    lab, n = ndi.label(acc_like)
    near = ndi.binary_dilation(core > 0.5, iterations=4)
    kanji_z, word_z, title_z = (np.zeros((H, W), bool) for _ in range(3))
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == i
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        solid = comp.sum() / comp.size
        if comp.sum() < 12 or ((near[sl] & comp).any() and (y1 - y0 > H * 0.2 or solid < 0.35)):
            continue                                   # glow round the group, not a letter that merely touches it
        if x1 > W * 0.7:
            continue
        if x1 < W * 0.06 and y0 < H * 0.5:
            kanji_z[sl] |= comp
        elif y1 - y0 > H * 0.045:
            word_z[sl] |= comp
        else:
            title_z[sl] |= comp
    grow = lambda m: ndi.binary_dilation(m, iterations=3)
    kanji_z, word_z, title_z = grow(kanji_z), grow(word_z), grow(title_z)
    Tz = soft(kanji_z | word_z | title_z, 0, 0.8)
    span = lambda m, ax_: (np.nonzero(m.any(0 if ax_ == "x" else 1))[0][[0, -1]] if m.any() else (0, 1))
    kx = span(kanji_z, "y")
    wx = span(word_z, "x")
    tx = span(title_z, "x")
    glow = soft(D & (edge_d >= 22) & ~(kanji_z | word_z | title_z), 6, 4) * (1 - coreH)

    # arc-length position of every edge pixel, clockwise from the top-left corner
    per = 2 * (W + H)
    k = np.argmin(np.stack([yy, W - 1 - xx, H - 1 - yy, xx]), 0)
    arc = np.select([k == 0, k == 1, k == 2, k == 3], [xx, W + yy, W + H + (W - xx), 2 * W + H + (H - yy)]) / per

    ed = lambda m: m[..., None]
    frames = []
    for i in range(N):
        t = i / N
        lap = np.clip((i - 4) / 80, 0, 1)                      # f4..f84, constant speed
        drain = ease((i - 91) / 8)                              # f91..f99 back to the cover
        kan = ease((i - 8) / 10) * (1 - drain)
        wrd = ease((i - 10) / 24) * (1 - drain)
        ttl = ease((i - 30) / 14) * (1 - drain)
        grp = back((i - 18) / 12) if i < 91 else 1 - ease((i - 91) / 8)
        breath = np.sin(np.pi * np.clip((i - 84) / 8, 0, 1)) * 0.45

        # base: cover, edge light running round
        m_edge = Bz * (np.clip((lap * (1 + 0.012) - arc) / 0.012, 0, 1) * (1 - drain))
        out = C + ed(m_edge) * (Hv - C)
        if breath > 0:
            out = out + ed(Bz * breath) * np.clip(Hv - C, 0, None)

        # pop-out group: only the characters step forward; the background stays put and the glow fades up
        if grp > 0:
            g = max(0.0, grp)
            a = min(1.0, g * 1.25)
            out = out + ed(glow * min(1.0, g)) * (Hv - out)
            sc = 1 + (s - 1) * g
            cs = warp(C, sc, ax, ay)
            hs = warp(Hv, sc / s, ax, ay)
            mt = warp(coreC[..., None].repeat(3, 2) * 255, sc, ax, ay)[..., 0] / 255
            out = out + ed(mt) * (cs + a * (hs - cs) - out)

        # type on top: kanji top to bottom, the word left to right, the show line after it
        fill = (kanji_z * wipe(yy, kx[0], kx[1], kan) + word_z * wipe(xx, wx[0], wx[1], wrd)
                + title_z * wipe(xx, tx[0], tx[1], ttl))
        out = out + ed(Tz) * (C + ed(fill) * (Hv - C) - out)
        frames.append(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize(OUT, Image.LANCZOS))

    os.makedirs(out_dir, exist_ok=True)
    encode(frames, [MS] * N, os.path.join(out_dir, "hover.webp"), quality=75)
    Image.fromarray(C.astype(np.uint8)).save(os.path.join(out_dir, "cover.jpg"), quality=90)
    strip = Image.new("RGB", (OUT[0] * 4, OUT[1] * 2))
    for j, fi in enumerate((0, 12, 20, 26, 34, 50, 86, 95)):
        strip.paste(frames[fi], ((j % 4) * OUT[0], (j // 4) * OUT[1]))
    strip.save(os.path.join(out_dir, "frames.jpg"), quality=82)
    return frames


if __name__ == "__main__":
    for sl in sys.argv[2:]:
        build(sl, os.path.join(sys.argv[1], sl))
