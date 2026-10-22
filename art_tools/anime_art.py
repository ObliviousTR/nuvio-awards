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


def fit_group(C, Hv):
    """Find how Kaptain scaled the pop-out group between cover and hover (scale + anchor), coarse to fine."""
    w, h = 320, 180
    c = np.asarray(Image.fromarray(C.astype(np.uint8)).resize((w, h)), dtype=np.float32)
    hv = np.asarray(Image.fromarray(Hv.astype(np.uint8)).resize((w, h)), dtype=np.float32)
    reg = np.zeros((h, w), bool)
    reg[int(h * .12):int(h * .95), int(w * .60):int(w * .93)] = True

    def err(s, ax, ay):
        a = 1 / s
        im = Image.fromarray(c.astype(np.uint8)).transform((w, h), Image.AFFINE, (a, 0, ax - a * ax, 0, a, ay - a * ay),
                                                           Image.BILINEAR)
        return np.abs(np.asarray(im, dtype=np.float32) - hv)[reg].mean()

    best = (err(1, 0, 0), 1.0, 0, 0)
    for s in np.arange(1.01, 1.16, 0.01):
        for ax in range(int(w * .4), w + 1, 8):
            for ay in range(int(h * .2), h + 41, 8):
                e = err(s, ax, ay)
                if e < best[0]:
                    best = (e, s, ax, ay)
    e, s, ax, ay = best
    for s2 in np.arange(s - .01, s + .0101, .0025):
        for ax2 in range(ax - 8, ax + 9, 2):
            for ay2 in range(ay - 8, ay + 9, 2):
                e2 = err(s2, ax2, ay2)
                if e2 < best[0]:
                    best = (e2, s2, ax2, ay2)
    e, s, ax, ay = best
    return float(s), ax * W / w, ay * H / h


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
    C, Hv = load(slug, "cover"), load(slug, "hover")
    D = (np.abs(C - Hv).max(2) > 18).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    # zones: card edge, left-hand type, pop-out group
    edge_d = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy])
    Bz = soft(D * (edge_d < 22), 3, 2)
    left = (xx < W * 0.46) & (edge_d >= 22)
    Tz = soft(D * left, 3, 1)
    Gz = soft(D * (xx >= W * 0.40) * (edge_d >= 22), 10, 6)
    Gz = np.maximum(Gz - Tz, 0)

    # arc-length position of every edge pixel, clockwise from the top-left corner
    per = 2 * (W + H)
    k = np.argmin(np.stack([yy, W - 1 - xx, H - 1 - yy, xx]), 0)
    arc = np.select([k == 0, k == 1, k == 2, k == 3], [xx, W + yy, W + H + (W - xx), 2 * W + H + (H - yy)]) / per

    # type sub-zones: kanji column, the big word, the show line under it
    ys, xs = np.nonzero(D * left > 0)
    kanji = xx < W * 0.055
    word_bottom = H * 0.86
    s, ax, ay = fit_group(C, Hv)
    print(slug, "group scale %.3f anchor (%d, %d)" % (s, ax, ay))

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

        # base: cover, with Kaptain's hover pixels revealed per zone
        m_edge = Bz * (np.clip((lap * (1 + 0.012) - arc) / 0.012, 0, 1) * (1 - drain))
        m_type = Tz * np.where(kanji, wipe(yy, H * 0.05, H * 0.36, kan),
                      np.where(yy < word_bottom, wipe(xx, W * 0.03, W * 0.44, wrd), wipe(xx, W * 0.03, W * 0.40, ttl)))
        out = C + ed(np.maximum(m_edge, m_type)) * (Hv - C)
        if breath > 0:
            out = out + ed(Bz * breath) * np.clip(Hv - C, 0, None)

        # pop-out group: cover pose scaled up toward the hover pose, cross-faded into the hover pixels
        if grp > 0:
            g = max(0.0, grp)
            sc = 1 + (s - 1) * g
            cs = warp(C, sc, ax, ay)
            hs = warp(Hv, sc / s, ax, ay)
            a = min(1.0, g * 1.25)
            mix = cs + a * (hs - cs)
            out = out + ed(Gz) * (mix - out)
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
