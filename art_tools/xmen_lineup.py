"""X-Men card, line-up version (the sibling of the 007 card): the X-MEN title on a cold steel ground, THE COLLECTION
under it, and seven mutants rising out of a low mist as dark steel silhouettes, their names in the mist. The hover is a
camera that walks the line: it moves in on each one in turn - he or she comes alive in colour, the others step back into
ghosts, name and actor appear beside them - then pulls back out to the cover. Seamless loop (first frame = cover).
Figures: cut out (rembg, u2net_human_seg) from official character posters on TMDB, cut at the same height and sunk into
the mist; the title is the X-Men (2000) title logo on TMDB.
usage: python3 art_tools/xmen_lineup.py SRC_DIR OUT_DIR
  SRC_DIR: cut_<key>.png cutouts, logo.png, Oswald-VF.ttf
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
S = 2
# key, name, actor, cut (y in the cutout where the figure sinks into the mist), scale (poster px -> common px), dx
FIGS = [("127585_22", "PROFESSOR X", "Patrick Stewart", 1112, 1.0, 0),
        ("127585_35", "MAGNETO", "Michael Fassbender", 1112, 1.0, -30),
        ("127585_24", "STORM", "Halle Berry", 1112, 1.0, 0),
        ("127585_34", "WOLVERINE", "Hugh Jackman", 1112, 1.0, 20),
        ("36668_38", "JEAN GREY", "Famke Janssen", 1142, 0.95, 0),
        ("127585_36", "MYSTIQUE", "Jennifer Lawrence", 1112, 1.0, 0),
        ("293660_4", "DEADPOOL", "Ryan Reynolds", 986, 0.864, -25)]
MIST_Y = 560                                   # where the figures sink in (cover px)
FIG_K = 0.36                                   # common px -> cover px


def font(path, weight, size):
    f = ImageFont.truetype(path, size); f.set_variation_by_axes([weight]); return f


def tracked(text, ft, track, color):
    ws = [ft.getlength(c) for c in text]
    im = Image.new("RGBA", (round(sum(ws) + track * (len(text) - 1)) + 8, round(ft.size * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im); x = 4
    for c, w in zip(text, ws):
        d.text((x, 0), c, font=ft, fill=color); x += w + track
    return im.crop(im.getbbox())


def duotone(fig, dark=(10, 14, 22), light=(58, 74, 96)):
    a = np.asarray(fig.convert("L"), float) / 255
    a = np.clip((a - 0.05) / 0.9, 0, 1) ** 1.5 * 0.5
    c = np.array(dark) * (1 - a[..., None]) + np.array(light) * a[..., None]
    out = Image.fromarray(c.astype("uint8"), "RGB").convert("RGBA")
    out.putalpha(fig.getchannel("A"))
    return out


def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


class Lineup:
    def __init__(self, src):
        self.src = src
        self.osw = os.path.join(src, "Oswald-VF.ttf")
        n = len(FIGS)
        xs = np.linspace(150, 1130, n)
        self.figs = []
        for (key, name, actor, cut, sc, dx), x in zip(FIGS, xs):
            f = Image.open(os.path.join(src, f"cut_{key}.png")).convert("RGBA")
            # cut at the mist line, with the last stretch fading out
            a = np.asarray(f.getchannel("A"), np.float32)
            y = np.arange(f.height, dtype=np.float32)[:, None]
            fade = np.clip((cut - y) / 90, 0, 1)
            f.putalpha(Image.fromarray((a * fade).astype("uint8")))
            # keep only the figure itself: drop small detached bits (poster dust, remains of the title text)
            from scipy import ndimage
            al = np.asarray(f.getchannel("A"), np.float32)
            lab, nl = ndimage.label(al > 60)
            if nl > 1:
                sizes = ndimage.sum(np.ones_like(al), lab, range(1, nl + 1))
                keep = np.isin(lab, 1 + np.nonzero(sizes >= sizes.max() * 0.04)[0])
                keep = ndimage.binary_dilation(keep, iterations=3)
                f.putalpha(Image.fromarray((al * keep).astype("uint8")))
            bb = f.getbbox(); f = f.crop((bb[0], bb[1], bb[2], min(bb[3], cut)))
            top = bb[1]
            k = FIG_K * sc * S
            f = f.resize((max(1, round(f.width * k)), max(1, round(f.height * k))), Image.LANCZOS)
            self.figs.append({"img": f, "sil": duotone(f), "x": (x + dx) * S, "base": (MIST_Y + 18) * S,
                              "name": name, "actor": actor, "cx_off": 0})
        self.ground = self.make_ground()
        self.mist = self.make_mist()

    def make_ground(self):
        w, h = W * S, H * S
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((x / w - 0.5) * 1.25) ** 2 + ((y / h - 0.42) * 1.05) ** 2)
        k = np.clip(1 - 0.75 * d ** 1.3, 0, 1)[..., None]
        top = np.array([150, 162, 178], np.float32); low = np.array([34, 40, 50], np.float32)
        c = low + (top - low) * k
        cv = Image.fromarray(c.astype("uint8"), "RGB").convert("RGBA")
        lg = Image.open(os.path.join(self.src, "logo.png")).convert("RGBA")
        la = np.asarray(lg.getchannel("A"), np.float32)
        lg.putalpha(Image.fromarray(np.clip((la - 40) / 215 * 255, 0, 255).astype("uint8")))   # drop the faint box
        lg = lg.crop(lg.getbbox())
        lk = 440 * S / lg.width
        lg = lg.resize((round(lg.width * lk), round(lg.height * lk)), Image.LANCZOS)
        # a soft dark halo so the chrome reads on the light centre
        pad = 40 * S
        sa = Image.new("L", (lg.width + 2 * pad, lg.height + 2 * pad), 0)
        sa.paste(lg.getchannel("A").point(lambda v: round(v * 0.5)), (pad, pad))
        sh = Image.new("RGBA", sa.size, (8, 12, 20, 255)); sh.putalpha(sa.filter(ImageFilter.GaussianBlur(10 * S)))
        x0, y0 = round(W * S / 2 - lg.width / 2), 44 * S
        cv.alpha_composite(sh, (x0 - pad, y0 - pad + 4 * S)); cv.alpha_composite(lg, (x0, y0))
        tc = tracked("THE COLLECTION", font(self.osw, 400, 19 * S), 13 * S, (22, 28, 38, 255))
        cv.alpha_composite(tc, (round(W * S / 2 - tc.width / 2), y0 + lg.height + 16 * S))
        return cv

    def make_mist(self):
        """a low bank of mist the figures stand in; returns (rgba layer generator inputs)"""
        rng = np.random.default_rng(4)
        w, h = W * S // 4, H * S // 4
        base = np.zeros((h, w), np.float32)
        for sc, amp in ((40, 1.0), (14, 0.5), (6, 0.25)):
            nz = rng.random((h // sc + 3, w // sc + 3)).astype(np.float32)
            nz = np.asarray(Image.fromarray(nz).resize((w + 3 * sc, h + 3 * sc), Image.BICUBIC))
            base += amp * nz[:h, :w]
        base = (base - base.min()) / (base.max() - base.min())
        return base

    def mist_layer(self, phase):
        """mist band drifting sideways; phase 0..1 loops"""
        w, h = W * S // 4, H * S // 4
        shift = int(round(phase * w)) % w
        tex = np.roll(self.mist, shift, axis=1)
        y = np.arange(h, dtype=np.float32)[:, None] * 4 / S
        band = np.clip((y - (MIST_Y - 70)) / 80, 0, 1) * 0.85 + np.clip((y - (MIST_Y + 10)) / 60, 0, 1) * 0.15
        a = np.clip(band * (0.55 + 0.6 * tex), 0, 1)
        col = np.array([196, 204, 216], np.float32)
        lay = np.dstack([np.broadcast_to(col, (h, w, 3)), a[..., None] * 255]).astype("uint8")
        return Image.fromarray(lay, "RGBA").resize((W * S, H * S), Image.BICUBIC)

    def scene(self, alive, phase):
        cv = self.ground.copy()
        dim = max(alive) if alive else 0.0
        for f, a in zip(self.figs, alive):
            x0, y0 = round(f["x"] - f["img"].width / 2), round(f["base"] - f["img"].height)
            sil = f["sil"]
            k = 1 - 0.72 * dim * (1 - a)
            if k < 0.999:
                sil = sil.copy(); sil.putalpha(sil.getchannel("A").point(lambda v: round(v * k)))
            cv.alpha_composite(sil, (x0, y0))
            if a > 0:
                col = f["img"].copy(); col.putalpha(col.getchannel("A").point(lambda v: round(v * a)))
                cv.alpha_composite(col, (x0, y0))
        cv.alpha_composite(self.mist_layer(phase))
        # names in the mist
        for f, a in zip(self.figs, alive):
            nm = tracked(f["name"], font(self.osw, 500, 12 * S), 4 * S, (30, 36, 48, 255))
            cv.alpha_composite(nm, (round(f["x"] - nm.width / 2), round((MIST_Y + 50) * S)))
        return cv

    def label(self, cv, i, a):
        if a <= 0:
            return
        f = self.figs[i]
        nm = tracked(f["name"], font(self.osw, 600, 15 * S), 4 * S, (16, 20, 30, 255))
        ac = tracked(f["actor"].upper(), font(self.osw, 300, 11 * S), 4 * S, (36, 44, 58, 255))
        lay = Image.new("RGBA", (max(nm.width, ac.width), nm.height + 8 * S + ac.height), (0, 0, 0, 0))
        right = i < len(self.figs) // 2 + (1 if i == len(self.figs) // 2 else 0)
        right = i <= 3
        lay.alpha_composite(nm, (0 if right else lay.width - nm.width, 0))
        lay.alpha_composite(ac, (0 if right else lay.width - ac.width, nm.height + 8 * S))
        lay.putalpha(lay.getchannel("A").point(lambda v: round(v * a)))
        # centred under the figure, in the mist
        lay = Image.new("RGBA", (max(nm.width, ac.width), nm.height + 7 * S + ac.height), (0, 0, 0, 0))
        lay.alpha_composite(nm, ((lay.width - nm.width) // 2, 0))
        lay.alpha_composite(ac, ((lay.width - ac.width) // 2, nm.height + 7 * S))
        lay.putalpha(lay.getchannel("A").point(lambda v: round(v * a)))
        x = f["x"] - lay.width / 2
        y = (MIST_Y - 4) * S
        cv.alpha_composite(lay, (round(x), round(y)))


def camera_path(lu):
    Z = 2.0
    cy = (MIST_Y - 132)
    keys = [(0, 1.0, W / 2, H / 2, None)]
    t = 16
    keys.append((t, 1.0, W / 2, H / 2, None))
    for i, f in enumerate(lu.figs):
        t += 18 if i == 0 else 14
        keys.append((t, Z, f["x"] / S, cy, i))
        t += 15
        keys.append((t, Z, f["x"] / S, cy, i))
    t += 24
    keys.append((t, 1.0, W / 2, H / 2, None))
    t += 14
    keys.append((t, 1.0, W / 2, H / 2, None))
    return keys


def render(src, out):
    lu = Lineup(src)
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
        alive = [0.0] * len(lu.figs); lab = None
        for i in range(len(lu.figs)):
            hold = [kk for kk in keys if kk[4] == i]
            s0, s1 = hold[0][0], hold[-1][0]
            alive[i] = smooth((k - (s0 - 7)) / 7) * (1 - smooth((k - s1) / 7))
            if alive[i] > 0.01:
                lab = (i, alive[i])
        cv = lu.scene(alive, k / n)
        if lab:
            lu.label(cv, *lab)
        vw, vh = W * S / z, H * S / z
        x0 = min(max(0, cx * S - vw / 2), W * S - vw)
        y0 = min(max(0, cy * S - vh / 2), H * S - vh)
        frames.append(cv.crop((round(x0), round(y0), round(x0 + vw), round(y0 + vh))).resize((W, H), Image.LANCZOS).convert("RGB"))
    os.makedirs(out, exist_ok=True)
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * n, os.path.join(out, "hover.webp"), quality=78)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for m, i in enumerate(range(0, n, max(1, n // 16))):
        if m < 16:
            sheet.paste(frames[i].resize((320, 180)), ((m % 4) * 320, (m // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", n, "seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
