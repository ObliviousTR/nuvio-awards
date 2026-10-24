"""007 James Bond card, line-up version: on a warm beige ground the 007 mark, JAMES BOND and a thin THE COLLECTION, and
the six Bonds standing in a row as purple-dark silhouettes over soft reflections, their names below. The hover is a
camera that walks the line: it moves in on each Bond in turn - the silhouette comes alive in his own colours and his
years appear - then pulls back out to the cover. Seamless loop (the first and last frames are the cover).
Figures: cut out (rembg, u2net_human_seg) from official posters on TMDB; the 007 mark is the public-domain one.
usage: python3 art_tools/bond_lineup.py FIGURES_DIR OUT_DIR
  FIGURES_DIR holds final_<actor>.png cutouts (connery, lazenby, moore_alt, dalton_gb, brosnan_gb, craig)
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH = 1280, 720, 512, 288
S = 2                                   # render at 2x, so the camera can move in without going soft
MS = 40
BONDS = [("connery646", "SEAN CONNERY", "1962 – 1971"), ("lazenby", "GEORGE LAZENBY", "1969"),
         ("moore691", "ROGER MOORE", "1973 – 1985"), ("dalton_gb", "TIMOTHY DALTON", "1987 – 1989"),
         ("brosnan_gb", "PIERCE BROSNAN", "1995 – 2002"), ("craig", "DANIEL CRAIG", "2006 – 2021")]
BEIGE = (221, 196, 156)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = "/home/claude/nuvio-art/art/logos/bond/007.png"


def font(weight, size):
    d = os.path.join(ROOT, "scripts", ".cache")
    f = next(os.path.join(d, x) for x in sorted(os.listdir(d)) if "Montserrat" in x)
    ft = ImageFont.truetype(f, size)
    ft.set_variation_by_axes([weight])
    return ft


def tracked(text, ft, track, color):
    ws = [ft.getlength(c) for c in text]
    tw = round(sum(ws) + track * (len(text) - 1)) + 4
    im = Image.new("RGBA", (tw, round(ft.size * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im); x = 2
    for c, w in zip(text, ws):
        d.text((x, 0), c, font=ft, fill=color); x += w + track
    return im.crop(im.getbbox())


def duotone(fig, dark=(26, 12, 32), light=(108, 64, 128)):
    """the poster's look: the figure as a deep plum shape that still keeps a hint of its folds"""
    a = np.asarray(fig.convert("L"), float) / 255
    a = np.clip((a - 0.05) / 0.9, 0, 1) ** 1.4 * 0.55
    c = np.array(dark) * (1 - a[..., None]) + np.array(light) * a[..., None]
    out = Image.fromarray(c.astype("uint8"), "RGB").convert("RGBA")
    out.putalpha(fig.getchannel("A"))
    return out


def reflection(fig, h_frac=0.28, a0=0.32):
    r = fig.transpose(Image.FLIP_TOP_BOTTOM)
    h = max(1, round(r.height * h_frac))
    r = r.crop((0, 0, r.width, h)).filter(ImageFilter.GaussianBlur(2 * S))
    g = Image.linear_gradient("L").resize((r.width, h)).point(lambda v: round((255 - v) * a0))
    m = Image.fromarray((np.asarray(r.getchannel("A"), float) * np.asarray(g, float) / 255).astype("uint8"))
    r.putalpha(m)
    return r


class Lineup:
    def __init__(self, figs_dir):
        self.figs = []
        fh = 300 * S                                      # figure height on the canvas
        base = 548 * S                                    # where the feet stand
        xs = np.linspace(170, 1110, len(BONDS)) * S
        for (key, name, years), x in zip(BONDS, xs):
            f = Image.open(os.path.join(figs_dir, f"final_{key}.png")).convert("RGBA")
            k = fh / f.height
            f = f.resize((round(f.width * k), fh), Image.LANCZOS)
            self.figs.append({"img": f, "sil": duotone(f), "x": x, "base": base, "name": name, "years": years})
        self.base = self.ground()

    def ground(self):
        w, h = W * S, H * S
        y, x = np.mgrid[0:h, 0:w]
        d = np.sqrt(((x / w - 0.5) * 1.3) ** 2 + ((y / h - 0.45) * 1.0) ** 2)
        k = np.clip(1 - 0.32 * d ** 1.6, 0, 1)[..., None]
        c = np.array(BEIGE, float) * k
        cv = Image.fromarray(c.astype("uint8"), "RGB").convert("RGBA")
        lg = Image.open(LOGO).convert("RGBA")
        lg = lg.crop(lg.getbbox())
        lk = 74 * S / lg.height
        lg = lg.resize((round(lg.width * lk), round(lg.height * lk)), Image.LANCZOS)
        a = np.asarray(lg.getchannel("A"))
        ink = Image.new("RGBA", lg.size, (40, 18, 44, 255)); ink.putalpha(Image.fromarray(a))
        cv.alpha_composite(ink, (round(W * S / 2 - lg.width / 2), 58 * S))
        jb = tracked("JAMES BOND", font(700, 30 * S), 10 * S, (40, 18, 44, 255))
        cv.alpha_composite(jb, (round(W * S / 2 - jb.width / 2), 152 * S))
        tc = tracked("THE COLLECTION", font(300, 17 * S), 12 * S, (60, 34, 64, 255))
        cv.alpha_composite(tc, (round(W * S / 2 - tc.width / 2), 196 * S))
        for f in self.figs:
            sil = f["sil"]
            x0 = round(f["x"] - sil.width / 2)
            cv.alpha_composite(reflection(sil), (x0, round(f["base"])))
            nm = tracked(f["name"], font(600, 11 * S), 3 * S, (64, 38, 68, 255))
            cv.alpha_composite(nm, (round(f["x"] - nm.width / 2), round(f["base"] + 62 * S)))
        return cv

    def scene(self, alive):
        """alive[i] 0..1: how far figure i has turned from silhouette to his own colours"""
        cv = self.base.copy()
        dim = max(alive) if alive else 0.0               # while one Bond is lit, the others step back into ghosts
        for f, a in zip(self.figs, alive):
            x0, y0 = round(f["x"] - f["img"].width / 2), round(f["base"] - f["img"].height)
            sil = f["sil"]
            k = 1 - 0.78 * dim * (1 - a)
            if k < 0.999:
                sil = sil.copy(); sil.putalpha(sil.getchannel("A").point(lambda v: round(v * k)))
            cv.alpha_composite(sil, (x0, y0))
            if a > 0:
                col = f["img"].copy()
                col.putalpha(col.getchannel("A").point(lambda v: round(v * a)))
                cv.alpha_composite(col, (x0, y0))
        return cv

    def label(self, cv, i, a):
        """name and years beside the Bond the camera is on (right of him for the first three, left for the rest)"""
        if a <= 0:
            return
        f = self.figs[i]
        nm = tracked(f["name"], font(700, 13 * S), 3 * S, (40, 18, 44, 255))
        yr = tracked(f["years"], font(400, 11 * S), 4 * S, (78, 46, 82, 255))
        lay = Image.new("RGBA", (max(nm.width, yr.width), nm.height + 8 * S + yr.height), (0, 0, 0, 0))
        right = i < 3
        lay.alpha_composite(nm, (0 if right else lay.width - nm.width, 0))
        lay.alpha_composite(yr, (0 if right else lay.width - yr.width, nm.height + 8 * S))
        lay.putalpha(lay.getchannel("A").point(lambda v: round(v * a)))
        gap = f["img"].width / 2 + 14 * S
        x = f["x"] + gap if right else f["x"] - gap - lay.width
        y = f["base"] - f["img"].height * 0.62
        cv.alpha_composite(lay, (round(x), round(y)))


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def camera_path(lu):
    """keyframes: (frame, zoom, centre x, centre y, focus index or None); the camera eases between them"""
    Z = 2.25
    cy = (lu.figs[0]["base"] - 150 * S) / S
    keys = [(0, 1.0, W / 2, H / 2, None)]
    t = 18                                               # a breath on the cover first
    keys.append((t, 1.0, W / 2, H / 2, None))
    for i, f in enumerate(lu.figs):
        t += 20 if i == 0 else 16                        # move in / across
        keys.append((t, Z, f["x"] / S, cy, i))
        t += 15                                          # stay with him
        keys.append((t, Z, f["x"] / S, cy, i))
    t += 26                                              # pull back out
    keys.append((t, 1.0, W / 2, H / 2, None))
    t += 14
    keys.append((t, 1.0, W / 2, H / 2, None))
    return keys


def render(figs_dir, out):
    lu = Lineup(figs_dir)
    keys = camera_path(lu)
    n = keys[-1][0]
    frames = []
    for k in range(n):
        j = max(i for i in range(len(keys)) if keys[i][0] <= k)
        a, b = keys[j], keys[min(j + 1, len(keys) - 1)]
        p = smooth((k - a[0]) / max(1, b[0] - a[0])) if b is not a else 0
        z = a[1] + (b[1] - a[1]) * p
        cx = a[2] + (b[2] - a[2]) * p
        cy = a[3] + (b[3] - a[3]) * p
        alive = [0.0] * len(lu.figs)
        lab = None
        for i in range(len(lu.figs)):
            # alive while the camera holds on him, fading in as it arrives and out as it leaves
            hold = [kk for kk in keys if kk[4] == i]
            s0, s1 = hold[0][0], hold[-1][0]
            alive[i] = smooth((k - (s0 - 8)) / 8) * (1 - smooth((k - s1) / 8))
            if alive[i] > 0.01:
                lab = (i, alive[i])
        cv = lu.scene(alive)
        if lab:
            lu.label(cv, *lab)
        # camera: crop the 2x canvas around (cx, cy) at zoom z, keep inside the picture
        vw, vh = W * S / z, H * S / z
        x0 = min(max(0, cx * S - vw / 2), W * S - vw)
        y0 = min(max(0, cy * S - vh / 2), H * S - vh)
        fr = cv.crop((round(x0), round(y0), round(x0 + vw), round(y0 + vh))).resize((W, H), Image.LANCZOS).convert("RGB")
        frames.append(fr)
    cover = lu.scene([0.0] * len(lu.figs)).resize((W, H), Image.LANCZOS).convert("RGB")
    os.makedirs(out, exist_ok=True)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * n, os.path.join(out, "hover.webp"), quality=80)
    cover.save(os.path.join(out, "cover.jpg"), quality=92)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(cover, float)).mean())
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for m, i in enumerate(range(0, n, max(1, n // 16))):
        if m < 16:
            sheet.paste(frames[i].resize((320, 180)), ((m % 4) * 320, (m // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", n, "seam", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
