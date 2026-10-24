"""Gold chiselled wordmark in the style of the Middle-earth film titles: Ringbearer letters (big initials), a bevel
from the distance field, lit, and coloured through a gold ramp taken from the Fellowship title logo."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage


def gold_ramp(logo_path, n=256):
    lg = np.asarray(Image.open(logo_path).convert("RGBA"), float)
    a = lg[..., 3] > 250
    px = lg[..., :3][a]
    lum = px @ [0.3, 0.55, 0.15]
    order = np.argsort(lum)
    px = px[order]
    idx = np.linspace(0, len(px) - 1, n).astype(int)
    ramp = np.array([px[max(0, i - 400):i + 400].mean(0) for i in idx])
    return ramp                                   # dark -> bright gold


def layout(parts, font_path, scale):
    """parts: [(text, size)] drawn on one baseline -> L mask"""
    fs = [(t, ImageFont.truetype(font_path, round(s * scale))) for t, s in parts]
    asc = max(f.getmetrics()[0] for _, f in fs)
    w = sum(round(f.getlength(t)) for t, f in fs) + 40
    h = asc + max(f.getmetrics()[1] for _, f in fs) + 40
    m = Image.new("L", (w, h), 0); d = ImageDraw.Draw(m); x = 20
    for t, f in fs:
        d.text((x, 20 + asc), t, font=f, fill=255, anchor="ls"); x += round(f.getlength(t))
    return m.crop(m.getbbox())


def chisel(mask, ramp, depth=7.0, light=(-0.55, -0.65, 0.52), grit=None):
    m = np.asarray(mask, float) / 255
    inside = m > 0.5
    dist = ndimage.distance_transform_edt(inside)
    h = np.clip(dist / depth, 0, 1)
    h = ndimage.gaussian_filter(h, 0.8)
    gy, gx = np.gradient(h * depth)
    n = np.dstack([-gx, -gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array(light); L /= np.linalg.norm(L)
    diff = np.clip((n * L).sum(-1), 0, 1)
    spec = np.clip((n * L).sum(-1), 0, 1) ** 18
    v = 0.04 + 0.78 * diff + 0.45 * spec
    if grit is not None:
        g = grit[:v.shape[0], :v.shape[1]]
        v = v * (0.62 + 0.55 * g) - 0.25 * np.clip(0.35 - g, 0, 1)   # stony grain and a few dark pits
    v = v * (0.55 + 0.45 * np.clip(dist / 1.6, 0, 1))                  # dark rim on the letter edges
    v = np.clip(v, 0, 1) ** 1.25
    col = ramp[(v * (len(ramp) - 1)).astype(int)]
    out = np.dstack([col, m * 255]).astype("uint8")
    return Image.fromarray(out, "RGBA")


def grit_field(shape, seed=3):
    rng = np.random.default_rng(seed)
    g = rng.random(shape)
    g = ndimage.gaussian_filter(g, 1.2) * 0.6 + ndimage.gaussian_filter(rng.random(shape), 6) * 0.4
    g = (g - g.min()) / (g.max() - g.min())
    return g


def wordmark(font_path, logo_path, height=150, small=0.68, words=("MIDDLE", "EARTH"), dash=True):
    """big initial + smaller capitals per word, like the film titles; Ringbearer has no hyphen (nor space glyph),
    so the hyphen is a short chiselled bar placed by hand"""
    scale = height / 100
    big, sm = ImageFont.truetype(font_path, round(100 * scale)), ImageFont.truetype(font_path, round(100 * small * scale))
    asc = big.getmetrics()[0]
    gap = round(sm.getlength("I") * 1.6)
    w = sum(big.getlength(wd[0]) + sm.getlength(wd[1:]) for wd in words) + gap * (len(words) - 1) + 80
    m = Image.new("L", (round(w), round(asc * 1.5) + 40), 0); d = ImageDraw.Draw(m)
    x, base = 30, 20 + asc
    for i, wd in enumerate(words):
        d.text((x, base), wd[0], font=big, fill=255, anchor="ls"); x += big.getlength(wd[0])
        d.text((x, base), wd[1:], font=sm, fill=255, anchor="ls"); x += sm.getlength(wd[1:])
        if i < len(words) - 1:
            if dash:
                bb = sm.getbbox("I", anchor="ls")
                cy = base + (bb[1] + bb[3]) / 2
                th = 0.06 * 100 * small * scale
                d.polygon([(x + gap * 0.2, cy - th * 0.7), (x + gap * 0.82, cy - th), (x + gap * 0.8, cy + th * 0.9),
                           (x + gap * 0.18, cy + th * 0.8)], fill=255)
            x += gap
    m = m.crop(m.getbbox())
    ramp = gold_ramp(logo_path)
    g = grit_field((m.height, m.width))
    return chisel(m, ramp, depth=max(3.0, height / 24), grit=g)


if __name__ == "__main__":
    import sys
    wm = wordmark(sys.argv[1], sys.argv[2], height=int(sys.argv[4]) if len(sys.argv) > 4 else 150)
    bg = Image.new("RGBA", (wm.width + 80, wm.height + 80), (14, 10, 8, 255)); bg.alpha_composite(wm, (40, 40))
    bg.convert("RGB").save(sys.argv[3])
