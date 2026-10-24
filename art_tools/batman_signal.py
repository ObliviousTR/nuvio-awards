"""Batman card: a cloudy Gotham night, the Bat-Signal (the 1989 emblem's bat, from the title logo on TMDB) thrown on the
clouds by a searchlight beam, the skyline below, BATMAN and THE COLLECTION between them. Hover: the clouds stir, the
signal flares, the bat fills with film frames and the camera dives into it until the Batmen of every era flip by -
West, Keaton, Kilmer, Clooney, the Phantasm, Bale, Affleck, Pattinson - then it pulls back out, the bat goes dark again
on the clouds and the title returns. Seamless loop (first frame = cover).
Everything but the stills and the title is drawn analytically in cover coordinates, so the dive stays sharp.
usage: python3 art_tools/batman_signal.py SRC_DIR OUT_DIR [--frames a,b]
  SRC_DIR: bat.json (bat outline + emblem ellipse in logo pixels), title.png, Oswald-VF.ttf, stills/NN_*.jpg
"""
import glob, json, math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 260
SIG_C, SIG_W = (640.0, 222.0), 370.0          # signal centre and width on the cover


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return smooth((k - a) / max(1, b - a))


rng0 = np.random.default_rng(5)
PERM = rng0.permutation(256)
VALS = rng0.random(256).astype(np.float32)


def vnoise(x, y):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)

    def h(i, j):
        return VALS[PERM[(PERM[i & 255] + j) & 255]]
    a, b, c, d = h(xi, yi), h(xi + 1, yi), h(xi, yi + 1), h(xi + 1, yi + 1)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, octaves=5):
    t, amp, f, norm = 0, 1.0, 1.0, 0
    for _ in range(octaves):
        t = t + amp * vnoise(x * f, y * f); norm += amp
        amp *= 0.5; f *= 2.03
    return t / norm


class Scene:
    def __init__(self, src):
        d = json.load(open(os.path.join(src, "bat.json")))
        ex, ey, erx, ery = d["ellipse"]
        self.k = SIG_W / (2 * erx)
        self.erx, self.ery = erx * self.k, ery * self.k
        self.bat = np.array(d["bat"], np.float64)
        self.bat = np.stack([(self.bat[:, 0] - ex) * self.k + SIG_C[0], (self.bat[:, 1] - ey) * self.k + SIG_C[1]], -1)
        self.anchor, r = self.find_core()
        self.s_max = max(20.0, 840 / r)
        tl = Image.open(os.path.join(src, "title.png")).convert("RGBA"); tl = tl.crop(tl.getbbox())
        tw = 400; self.title = tl.resize((tw, round(tl.height * tw / tl.width)), Image.LANCZOS)
        f = ImageFont.truetype(os.path.join(src, "Oswald-VF.ttf"), 44); f.set_variation_by_axes([400])
        txt = "THE COLLECTION"; tr = 26
        m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 20, 80), 0)
        dd = ImageDraw.Draw(m); x = 10
        for c in txt:
            dd.text((x, 60), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); self.sub = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        self.stills = []
        for fp in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            im = Image.open(fp).convert("RGB")
            kk = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * kk), math.ceil(im.height * kk)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            self.stills.append(np.asarray(im.crop((x0, y0, x0 + W, y0 + H)), np.float32))
        # skyline: a hazy far row and a dark near row of buildings, and lit windows on the near row (cover pixels)
        rng = np.random.default_rng(12)
        self.far, self.buildings, self.windows = [], [], []
        for layer, (hmin, hmax, wmin, wmax) in (("far", (120, 260, 30, 80)), ("near", (50, 170, 24, 66))):
            x = -20
            while x < W + 20:
                bw = rng.uniform(wmin, wmax); bh = rng.uniform(hmin, hmax) * (1.3 if rng.random() < 0.1 else 1)
                top = H - bh
                poly = [(x, H + 5), (x, top), (x + bw, top), (x + bw, H + 5)]
                r = rng.random()
                if r < 0.22:                                          # a spire
                    cxm = x + bw / 2; poly = [(x, H + 5), (x, top), (cxm - bw * 0.16, top), (cxm, top - rng.uniform(24, 70)),
                                              (cxm + bw * 0.16, top), (x + bw, top), (x + bw, H + 5)]
                elif r < 0.4:                                         # a stepped crown
                    st = bw * 0.22; h2 = rng.uniform(14, 30)
                    poly = [(x, H + 5), (x, top), (x + st, top), (x + st, top - h2), (x + bw - st, top - h2),
                            (x + bw - st, top), (x + bw, top), (x + bw, H + 5)]
                (self.far if layer == "far" else self.buildings).append(np.array(poly))
                if layer == "near":
                    dens = rng.uniform(0.02, 0.16)
                    for wy in np.arange(top + 8, H, 9):
                        for wx in np.arange(x + 4, x + bw - 5, 7):
                            if rng.random() < dens:
                                self.windows.append((wx, wy))
                x += bw + rng.uniform(-8, 3)
        self.windows = np.array(self.windows)
        self.cover = None

    def find_core(self):
        m = np.zeros((H * 4, W * 4), np.uint8)
        cv2.fillPoly(m, [np.round(self.bat * 4 * 16).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=4)
        dt = ndimage.distance_transform_edt(m > 127)
        y, x = np.unravel_index(np.argmax(dt), dt.shape)
        return (x / 4, y / 4), dt[y, x] / 4

    def poly_mask(self, polys, tf, ss=2):
        m = np.zeros((H * ss, W * ss), np.uint8)
        pts = [np.round(np.clip(tf(p) * ss, -1e6, 1e6) * 16).astype(np.int32) for p in polys]
        cv2.fillPoly(m, pts, 255, lineType=cv2.LINE_AA, shift=4)
        return cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255

    def frame(self, k):
        n = len(self.stills)
        flare = seg(k, 12, 34) * (1 - seg(k, 214, 240))
        to_frames = seg(k, 18, 36) * (1 - seg(k, 214, 236))
        dive = seg(k, 34, 80) * (1 - seg(k, 176, 220))
        s = math.exp(math.log(self.s_max) * dive ** 1.6)
        A = self.anchor
        c = (A[0] + (W / 2 - A[0]) * dive, A[1] + (H / 2 - A[1]) * dive)
        tf = lambda p: np.stack([c[0] + (p[:, 0] - A[0]) * s, c[1] + (p[:, 1] - A[1]) * s], -1)
        # cover coordinates of every screen pixel
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        px = A[0] + (xs - c[0]) / s; py = A[1] + (ys - c[1]) / s
        # sky
        t = np.clip(py / H, 0, 1)
        img = np.array([8, 11, 20], np.float32) * (1 - t[..., None]) + np.array([30, 30, 40], np.float32) * t[..., None]
        img += np.clip((py - 420) / 300, 0, 1)[..., None] * np.array([34, 20, 10], np.float32)       # city glow
        # clouds (sway back and forth over the loop)
        sway = 18 * math.sin(2 * math.pi * k / N)
        cl = fbm((px + sway) / 230, py / 150 + 3.1)
        cl2 = fbm((px - sway * 0.6) / 90 + 7.7, py / 70)
        cloud = np.clip((cl * 0.75 + cl2 * 0.35 - 0.42) * 2.2, 0, 1) * np.clip(1.15 - py / 640, 0, 1)
        img = img * (1 - 0.6 * cloud[..., None]) + cloud[..., None] * np.array([46, 52, 66], np.float32) * 0.9
        # searchlight beam from below the skyline to the signal
        P0 = np.array([905.0, 760.0]); P1 = np.array(SIG_C)
        ax = P1 - P0; L = np.linalg.norm(ax); ax /= L
        rx, ry = px - P0[0], py - P0[1]
        along = rx * ax[0] + ry * ax[1]; across = np.abs(-rx * ax[1] + ry * ax[0])
        wdt = 7 + (self.erx * 0.55 - 7) * np.clip(along / L, 0, 1)
        beam = np.clip(1 - across / wdt, 0, 1) ** 1.5 * np.clip(along / 40, 0, 1) * np.clip((L + 10 - along) / 60, 0, 1)
        beam *= (0.16 + 0.1 * flare) * (0.7 + 0.6 * cloud)
        img += beam[..., None] * np.array([255, 236, 190], np.float32)
        # the signal on the clouds: lit oval, soft edge, light on the surrounding clouds
        e = np.sqrt(((px - SIG_C[0]) / self.erx) ** 2 + ((py - SIG_C[1]) / self.ery) ** 2)
        edge = 0.06 * self.erx * s
        oval = np.clip((1 - e) * self.erx * s / max(edge, 1) + 0.5, 0, 1) if True else 0
        halo = np.exp(-np.clip(e - 1, 0, None) / 0.35) * (e > 0.98)
        lit = (0.55 + 0.6 * cloud) * (0.92 + 0.18 * flare)
        sigcol = np.array([255, 238, 186], np.float32)
        img = img * (1 - oval[..., None]) + (sigcol * lit[..., None]) * oval[..., None]
        img += halo[..., None] * np.array([90, 80, 60], np.float32) * (0.5 + 0.5 * cloud[..., None]) * (0.8 + 0.5 * flare)
        # the bat: dark on the oval, or a window onto the films
        bm = self.poly_mask([self.bat], tf)
        idx = min(n - 1, int((k - 74) / (178 - 74) * n)) if 74 <= k < 178 else (k // 3) % n
        dark = np.array([12, 14, 22], np.float32) * (0.9 + 0.2 * cloud[..., None])
        inside = dark * (1 - to_frames) + self.stills[idx] * to_frames
        img = img * (1 - bm[..., None]) + inside * bm[..., None]
        # skyline and windows
        if s < 6:
            fk = self.poly_mask(self.far, tf)
            img = img * (1 - fk[..., None]) + np.array([20, 22, 32], np.float32) * fk[..., None]
            sk = self.poly_mask(self.buildings, tf)
            img = img * (1 - sk[..., None]) + np.array([5, 6, 10], np.float32) * sk[..., None]
            if s < 1.6:
                lay = Image.new("L", (W, H), 0); dl = ImageDraw.Draw(lay)
                wp = tf(self.windows)
                for (wx, wy), i in zip(wp, range(len(wp))):
                    on = 1 if (hash((i, (k + i * 7) // 37 % 7)) % 23) else 0      # a few windows blink
                    if on:
                        dl.rectangle((wx, wy, wx + 2.2 * s, wy + 3 * s), fill=210)
                wl = np.asarray(lay, np.float32)[..., None] / 255
                img = img * (1 - wl * 0.9) + wl * 0.9 * np.array([255, 196, 110], np.float32)
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        ta = min(1.0, (1 - seg(k, 14, 36)) + seg(k, 222, 248))
        if ta > 0.001:
            for im, y in ((self.title, 392), (self.sub, 392 + self.title.height + 18)):
                t2 = im.copy() if im.mode == "RGBA" else Image.merge("RGBA", (*[Image.new("L", im.size, 236)] * 3, im))
                t2.putalpha(t2.getchannel("A").point(lambda v: round(v * ta)))
                out.alpha_composite(t2, (round(W / 2 - t2.width / 2), y))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
    print("core", [round(v) for v in sc.anchor], "zoom", round(sc.s_max, 1))
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            sc.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [sc.frame(k) for k in range(N)]
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for m, i in enumerate(range(0, N, N // 16)):
        if m < 16:
            sheet.paste(frames[i].resize((320, 180)), ((m % 4) * 320, (m // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", N, "seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")] if "--frames" in sys.argv else None
    render(sys.argv[1], sys.argv[2], only)
