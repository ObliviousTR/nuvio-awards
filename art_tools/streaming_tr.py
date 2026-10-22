"""Streaming Services row: Turkish platforms (Exxen, GAİN, tabii) get what Kaptain's platforms have, an ident-style
focus animation, a logo-on-brand-field cover, a tilted poster-wall hero and a large title logo; HBO Max gets its
current (2025) wordmark on the cover. Logos come from Wikimedia Commons / TMDB, posters from TMDB.
usage: python3 art_tools/streaming_tr.py MATERIAL_DIR OUT_DIR [ids...]
  MATERIAL_DIR holds exxen.png, gain.png, tabii.png, hbomax_3186_2.png, posters.json and posters/ (see the scratch
  fetch in the history of scripts/_scratch.py); OUT_DIR/<id>/ receives cover.jpg, hover.webp, backdrop.jpg, logo.png
"""
import json, math, os, random, sys
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

W, H = 1280, 720
GW, GH = 512, 288


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def back(x, s=1.7):
    x = max(0.0, min(1.0, x))
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def trim(im):
    bb = im.getchannel("A").getbbox()
    return im.crop(bb) if bb else im


def fit(im, mw, mh):
    k = min(mw / im.width, mh / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def alpha(im, a):
    if a >= 1:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: round(v * max(0, a))))
    return im


def comp(cv, im, x, y):
    x, y = round(x), round(y)
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, cv.width - x), min(im.height, cv.height - y)
    if r > l and b > t:
        cv.alpha_composite(im.crop((l, t, r, b)), (x + l, y + t))


def place(cv, im, cx, cy, a=1.0):
    if a > 0:
        comp(cv, alpha(im, a), cx - im.width / 2, cy - im.height / 2)


def glow(layer, r, col, k=1.0):
    pad = r * 3
    p = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), col + (0,))
    m = Image.new("L", p.size, 0)
    m.paste(layer.getchannel("A"), (pad, pad))
    p.putalpha(m.filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, round(v * k))))
    return p


def clusters(im, axis=0, gap=3):
    """Column (axis 0) runs of ink: [(start, end), ...]."""
    a = im.getchannel("A")
    prof = a.resize((im.width, 1), Image.BOX) if axis == 0 else a.resize((1, im.height), Image.BOX)
    v = list(prof.getdata())
    runs, i = [], 0
    while i < len(v):
        if v[i] > 3:
            s = i
            while i < len(v) and (v[i] > 3 or any(x > 3 for x in v[i:i + gap])):
                i += 1
            runs.append((s, i))
        i += 1
    return runs


def field(top, bottom, glow_col=None, glow_a=0):
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        f = y / H
        d.line((0, y, W, y), fill=tuple(round(top[i] + (bottom[i] - top[i]) * f) for i in range(3)))
    if glow_col and glow_a:
        g = Image.new("L", (W, H), 0)
        ImageDraw.Draw(g).ellipse((W * 0.18, H * 0.05, W * 0.82, H * 0.95), fill=glow_a)
        bg = Image.composite(Image.new("RGB", (W, H), glow_col), bg, g.filter(ImageFilter.GaussianBlur(160)))
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse((-W * 0.2, -H * 0.3, W * 1.2, H * 1.3), fill=255)
    return Image.composite(bg, Image.new("RGB", (W, H)), v.filter(ImageFilter.GaussianBlur(140))).convert("RGBA")


def sweep(cv, layer, cx, cy, s, strength=140):
    band = Image.new("L", layer.size, 0)
    bx = -150 + s * (layer.width + 300)
    ImageDraw.Draw(band).polygon([(bx, 0), (bx + 60, 0), (bx - 50, layer.height), (bx - 110, layer.height)], fill=strength)
    band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(12)), layer.getchannel("A"))
    wl = Image.new("RGBA", layer.size, (255, 255, 255, 0))
    wl.putalpha(band)
    place(cv, wl, cx, cy)


# ---------------------------------------------------------------- logos
def exxen_logo(src):
    im = Image.open(src).convert("RGB")
    out = Image.new("RGBA", im.size)
    s, d = im.load(), out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = s[x, y]
            a = max(0, min(255, round((min(r, g) - b - 40) * 2.2)))
            if a:
                d[x, y] = (255, 205, 0, a)
    return trim(out)


def gain_logo(src):
    """Black ink on white -> white letters; the red balloon stays red. Returns (letters, balloon) on one canvas size."""
    im = Image.open(src).convert("RGB")
    ink = Image.new("RGBA", im.size)
    bal = Image.new("RGBA", im.size)
    s, di, db = im.load(), ink.load(), bal.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = s[x, y]
            if r - max(g, b) > 30:
                db[x, y] = (226, 36, 48, min(255, (r - max(g, b)) * 2))
            else:
                a = 255 - min(r, g, b)
                if a > 25:
                    di[x, y] = (255, 255, 255, a)
    # the balloon's soft edge must not stay behind in the letters: clear ink around the balloon
    bm = bal.getchannel("A").point(lambda v: 255 if v > 20 else 0).filter(ImageFilter.MaxFilter(15))
    ink.putalpha(ImageChops.subtract(ink.getchannel("A"), bm))
    bb = ImageChops.lighter(ink.getchannel("A"), bal.getchannel("A")).getbbox()
    return ink.crop(bb), bal.crop(bb)


def tabii_logo(src):
    im = trim(Image.open(src).convert("RGBA"))
    runs = clusters(im, 0, gap=12)
    icon_end = runs[0][1]
    icon = trim(im.crop((0, 0, icon_end + 2, im.height)))
    word = trim(im.crop((icon_end + 2, 0, im.width, im.height)))
    return im, icon, word, icon_end


# ---------------------------------------------------------------- idents: frame(i, n) -> RGBA
def push(layer, s):
    return layer.resize((max(1, round(layer.width * s)), max(1, round(layer.height * s))), Image.LANCZOS)


def exxen_ident(logo):
    """As Exxen's own ident: the logo comes up out of black and the camera keeps pushing in toward it."""
    lg = fit(logo, 1500, 640)  # drawn large, scaled down per frame so the push-in stays sharp

    def frame(i, n):
        t = i / n
        cv = field((10, 10, 10), (0, 0, 0), (255, 190, 0), round(30 * ease(t / 0.5)))
        s = 0.34 + 0.20 * ease(t / 0.55) + 0.10 * t  # fast approach, then a slow constant drift inward
        L = push(lg, s)
        a = ease(t / 0.18)
        cv.alpha_composite(glow(L, 20, (255, 180, 0), 0.8 * a), (round(W / 2 - L.width / 2 - 60), round(H / 2 - L.height / 2 - 60)))
        place(cv, L, W / 2, H / 2, a)
        if 0.55 < t < 0.8:
            sweep(cv, L, W / 2, H / 2, (t - 0.55) / 0.25, 150)
        return cv
    return frame


def gain_ident(letters, balloon):
    """As GAİN's own ident: a slow push-in toward the logo while the red balloon floats up into place."""
    k = min(1240 / letters.width, 760 / letters.height)
    L0 = letters.resize((round(letters.width * k), round(letters.height * k)), Image.LANCZOS)
    B0 = balloon.resize(L0.size, Image.LANCZOS)
    bb = B0.getchannel("A").getbbox()
    bal0 = B0.crop(bb)

    def frame(i, n):
        t = i / n
        cv = field((24, 22, 26), (6, 6, 8), (120, 20, 30), round(34 * ease((t - 0.3) / 0.5)))
        s = 0.42 + 0.12 * ease(t / 0.7) + 0.04 * t
        L = push(L0, s)
        x0, y0 = W / 2 - L.width / 2, H / 2 - L.height / 2 + 20
        place(cv, L, W / 2, H / 2 + 20, ease(t / 0.25))
        p = (t - 0.12) / 0.6
        if p > 0:
            e = ease(p)
            bal = push(bal0, s)
            tx, ty = x0 + bb[0] * s, y0 + bb[1] * s
            y = H + 30 + (ty - H - 30) * e
            sway = math.sin(p * 6) * 26 * (1 - e) + math.sin(t * 8) * 2
            rot = math.sin(p * 6 + 0.6) * 9 * (1 - e)
            bl = bal.rotate(rot, resample=Image.BICUBIC, expand=True)
            if p < 1:
                d = ImageDraw.Draw(cv)
                d.line((tx + bal.width / 2 + sway, y + bal.height, tx + bal.width / 2 + sway * 0.3, y + bal.height + 80 * (1 - e) + 4),
                       fill=(230, 230, 230, 150), width=2)
            cv.alpha_composite(glow(bl, 14, (255, 40, 50), 0.6), (round(tx + sway - 42), round(y - 42)))
            comp(cv, bl, tx + sway, y)
        return cv
    return frame


def tabii_ident(full, icon, word, icon_end):
    k = min(760 / full.width, 260 / full.height)
    F = full.resize((round(full.width * k), round(full.height * k)), Image.LANCZOS)
    I = icon.resize((round(icon.width * k), round(icon.height * k)), Image.LANCZOS)
    Wd = word.resize((round(word.width * k), round(word.height * k)), Image.LANCZOS)
    fx0 = W / 2 - F.width / 2
    icx_final = fx0 + I.width / 2
    wx = fx0 + (F.width - Wd.width)
    green = (0, 245, 150)

    def frame(i, n):
        t = i / n
        cv = field((4, 26, 28), (1, 6, 8), (0, 120, 80), round(40 * ease((t - 0.1) / 0.4)))
        p = (t - 0.04) / 0.22
        if p > 0:
            s = max(0.01, back(p))
            rot = (1 - ease(p)) * -140
            ic = I.resize((max(1, round(I.width * s)), max(1, round(I.height * s))), Image.LANCZOS).rotate(rot, resample=Image.BICUBIC, expand=True)
            slide = ease((t - 0.32) / 0.2)
            cx = W / 2 + (icx_final - W / 2) * slide
            # ring pulse
            r = (t - 0.12) / 0.25
            if 0 < r < 1:
                d = ImageDraw.Draw(cv)
                R = 60 + 420 * ease(r)
                d.ellipse((cx - R, H / 2 - R, cx + R, H / 2 + R), outline=green + (round(200 * (1 - r)),), width=4)
            if slide > 0:
                m = Image.new("L", Wd.size, 0)
                rev = ease((t - 0.36) / 0.22)
                ImageDraw.Draw(m).rectangle((0, 0, Wd.width * rev, Wd.height), fill=255)
                w2 = Wd.copy()
                w2.putalpha(ImageChops.multiply(w2.getchannel("A"), m))
                comp(cv, w2, wx - (1 - rev) * 40, H / 2 - Wd.height / 2 + (F.height - Wd.height) * 0.0)
            breath = 0.7 + 0.3 * math.sin(t * math.pi * 4) if t > 0.6 else 0.9
            cv.alpha_composite(glow(ic, 22, green, breath), (round(cx - ic.width / 2 - 66), round(H / 2 - ic.height / 2 - 66)))
            place(cv, ic, cx, H / 2)
        return cv
    return frame


def hbomax_cover(logo_src):
    lg = Image.open(logo_src).convert("RGBA")
    white = Image.new("RGBA", lg.size, (255, 255, 255, 0))
    white.putalpha(lg.getchannel("A"))
    cv = field((22, 18, 70), (6, 8, 40), (90, 60, 200), 50)
    place(cv, fit(trim(white), 820, 210), W / 2, H / 2)
    return cv


# ---------------------------------------------------------------- hero: tilted poster wall (Kaptain's look)
def poster_wall(paths, root, angle=-11):
    pw, ph, gap = 190, 285, 18
    cols, rows = 13, 6
    wall = Image.new("RGB", (cols * (pw + gap), rows * (ph + gap)), (8, 9, 12))
    imgs = []
    for p in paths:
        f = os.path.join(root, "posters" + p)
        if os.path.exists(f):
            imgs.append(Image.open(f).convert("RGB").resize((pw, ph), Image.LANCZOS))
    rnd = random.Random(4)
    for i in range(cols * (rows + 1)):
        im = imgs[(i * 7 + rnd.randint(0, 3)) % len(imgs)]
        c, r = i % cols, i // cols
        wall.paste(im, (c * (pw + gap), r * (ph + gap) - (ph // 2 if c % 2 else 0)))
    wall = wall.rotate(angle, resample=Image.BICUBIC, fillcolor=(8, 9, 12))
    x, y = (wall.width - 1920) // 2, (wall.height - 1080) // 2
    base = wall.crop((x, y, x + 1920, y + 1080))
    base = ImageEnhance.Brightness(ImageEnhance.Color(base).enhance(0.85)).enhance(0.55)
    m = Image.new("L", (1920, 1), 0)
    for xx in range(1920):
        m.putpixel((xx, 0), round(235 * max(0, 1 - xx / 1100) ** 1.4))
    return Image.composite(Image.new("RGB", (1920, 1080), (4, 4, 6)), base, m.resize((1920, 1080)))


def write(out, fid, frame, n, dur, cover_i, logo, hero):
    d = os.path.join(out, fid)
    os.makedirs(d, exist_ok=True)
    frames = [frame(i, n) for i in range(n)]
    frames[cover_i].convert("RGB").save(os.path.join(d, "cover.jpg"), quality=90)
    small = [f.convert("RGB").resize((GW, GH), Image.LANCZOS) for f in frames]
    small[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=small[1:], duration=dur, loop=0,
                  quality=82, method=5, minimize_size=True, allow_mixed=True)
    if logo is not None:
        logo.save(os.path.join(d, "logo.png"))
    if hero is not None:
        hero.save(os.path.join(d, "backdrop.jpg"), quality=86)
    strip = Image.new("RGB", (GW * 4, GH * 2))
    for j, idx in enumerate([round(k * (n - 1) / 7) for k in range(8)]):
        strip.paste(small[idx], ((j % 4) * GW, (j // 4) * GH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return d


def main():
    root, out = sys.argv[1], sys.argv[2]
    only = set(sys.argv[3:])
    posters = json.load(open(os.path.join(root, "posters.json")))
    n = 110  # 110 frames x 40 ms = 4.4 s
    dur = [40] * n
    if not only or "exxen" in only:
        lg = exxen_logo(os.path.join(root, "exxen.png"))
        print(write(out, "exxen", exxen_ident(lg), n, dur, n - 1, lg, poster_wall(posters["exxen"], root)))
    if not only or "gain" in only:
        letters, bal = gain_logo(os.path.join(root, "gain.png"))
        logo = letters.copy()
        logo.alpha_composite(bal)
        print(write(out, "gain", gain_ident(letters, bal), n, dur, n - 1, logo, poster_wall(posters["gain"], root)))
    if not only or "tabii" in only:
        full, icon, word, ie = tabii_logo(os.path.join(root, "tabii.png"))
        print(write(out, "tabii", tabii_ident(full, icon, word, ie), n, dur, n - 1, full, poster_wall(posters["tabii"], root)))
    if not only or "hbomax" in only:
        d = os.path.join(out, "hbomax")
        os.makedirs(d, exist_ok=True)
        hbomax_cover(os.path.join(root, "hbomax_3186_2.png")).convert("RGB").save(os.path.join(d, "cover.jpg"), quality=90)
        print(d)


if __name__ == "__main__":
    main()
