"""Godzilla & Kong card, built on the MonsterVerse's own devices instead of drawn weather.

modes
  mural    Godzilla vs. Kong's Hollow Earth wall painting (the ancient war of Godzilla's and Kong's kind, a still from
           the film) in a dark chamber, GODZILLA x KONG in steel in front of it. Two Monarch explorers' torches come on
           off frame: one finds Godzilla's painted back and follows it to the head, the other finds Kong; both meet on
           the title, which takes their light and throws its shadows on the wall, then they move on down the wall and
           go out. Only light: the wall's own relief answers each torch's angle, the camera moves in and back.
  archive  The title language of Godzilla (2014) and King of the Monsters' end credits: declassified archive film
           (Monarch's 1954 footage of the dorsal plates) behind the title, and pale redaction bars that run out from
           the text, strike the lines of the Monarch file and pull back.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/gk_mural.py SRC_DIR OUT_DIR [--mode mural|archive] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (GODZILLA x KONG line of the New Empire title logo), BarlowCondensed-Medium.ttf, mural.jpg,
           archive_fins.jpg (see the nuvio-art _src README)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / float(b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0 else a


def bigblur(a, s):
    h, w = a.shape[:2]
    sm = cv2.resize(a, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), s / 4)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)


def noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta; spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


def collection(src, size=64, track=30):
    f = ImageFont.truetype(os.path.join(src, "BarlowCondensed-Medium.ttf"), size)
    txt = "THE COLLECTION"
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 20, size * 2), 0)
    d = ImageDraw.Draw(m); x = 10
    for c in txt:
        d.text((x, size * 1.6), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
    return np.asarray(m, np.float32) / 255


class Steel:
    """The title as a full-frame alpha with bevel normals; lit per frame by a fixed soft key and by moving lights."""

    def __init__(self, src, lw=1000, cy=318):
        lg = Image.open(os.path.join(src, "logo.png")).getchannel("A")
        lh = round(lg.height * lw / lg.width)
        a = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        x0, y0 = (W - lw) // 2, cy - lh // 2
        la = np.zeros((H, W), np.float32); la[y0:y0 + lh, x0:x0 + lw] = a
        self.la, self.x0, self.y0, self.lw, self.lh, self.cy = la, x0, y0, lw, lh, cy
        m = (la > 0.5).astype(np.uint8)
        bw = 4.5
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        hgt = blur(smooth(dt / bw).astype(np.float32), 0.7)
        gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8 * bw
        gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8 * bw
        n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
        self.n = n.astype(np.float32)
        yy = np.mgrid[0:H, 0:W][0].astype(np.float32)
        g = np.clip((yy - y0) / lh, 0, 1)[..., None]
        self.base = (np.array([0.93, 0.95, 0.98], np.float32) * (1 - g) + np.array([0.60, 0.66, 0.76], np.float32) * g)
        rng = np.random.default_rng(2)
        brush = cv2.GaussianBlur(rng.normal(size=(H, W)).astype(np.float32), (0, 0), sigmaX=24, sigmaY=0.6)
        self.brush = (1 + 0.06 * brush / (np.abs(brush).max() + 1e-6))[..., None]
        L = np.array([-0.45, -0.75, 0.5], np.float32); L /= np.linalg.norm(L)
        self.key = np.clip(n @ L, 0, 1)

    def lit(self, lights, key=1.0):
        """lights: list of (irradiance map, origin x, origin y, depth, colour). Returns the face colour (linear)."""
        face = self.base * (0.13 + 0.36 * self.key * key)[..., None]
        face = face + (self.key ** 14 * (1 - self.n[..., 2]) * 3 * 0.25 * key)[..., None]
        for E, ox, oy, dz, col in lights:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            L = np.dstack([ox - xx, oy - yy, np.full_like(xx, dz)]); L /= np.linalg.norm(L, axis=2, keepdims=True)
            Hh = L + np.array([0, 0, 1], np.float32); Hh /= np.linalg.norm(Hh, axis=2, keepdims=True)
            nd = np.clip((self.n * L).sum(2), 0, 1)
            sp = np.clip((self.n * Hh).sum(2), 0, 1) ** 40
            face = face + (self.base * (E * nd * 0.9)[..., None] + (E * sp * 1.6)[..., None]) * col
        return face * self.brush


# ------------------------------------------------------------------------------------------------------------- mural
TORCH = {
    # origin off frame (x, y), depth, on, off, path [(frame, x, y)]
    "A": ((-260.0, 980.0), 900.0, (3, 6), (206, 214),
          [(0, 70, 600), (8, 90, 585), (34, 300, 380), (58, 560, 290), (80, 600, 330), (100, 470, 495), (128, 420, 505),
           (160, 520, 640), (190, 330, 690), (214, 240, 700), (250, 240, 700)]),
    "B": ((1560.0, 1000.0), 900.0, (34, 37), (194, 202),
          [(0, 820, 110), (37, 820, 110), (62, 950, 230), (84, 990, 360), (106, 830, 500), (132, 870, 495),
           (158, 1000, 620), (184, 1120, 680), (202, 1180, 700), (250, 1180, 700)]),
}
WARM = np.array([1.0, 0.93, 0.80], np.float32)
COOL = np.array([0.90, 0.95, 1.0], np.float32)


def path_at(pts, k):
    fr = [p[0] for p in pts]
    i = max(0, min(len(pts) - 2, int(np.searchsorted(fr, k, side="right")) - 1))
    p0, p1 = pts[i], pts[i + 1]
    pm = pts[i - 1] if i > 0 else p0
    p2 = pts[i + 2] if i + 2 < len(pts) else p1
    t = (k - p0[0]) / float(p1[0] - p0[0])
    t = min(1.0, max(0.0, t))
    out = []
    for j in (1, 2):                                                     # catmull-rom through the keys
        a, b, c, d = pm[j], p0[j], p1[j], p2[j]
        out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    return out


class Mural:
    def __init__(self, src):
        self.t = Steel(src, 880, 520)
        im = cv2.cvtColor(cv2.imread(os.path.join(src, "mural.jpg")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        im = cv2.resize(im, (1300, round(im.shape[0] * 1300 / im.shape[1])), interpolation=cv2.INTER_AREA)
        self.wall = (im ** 2.0).astype(np.float32)                       # roughly linear albedo
        lum = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
        hgt = blur(lum, 2.0)
        self.wgx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8
        self.wgy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8
        self.wh, self.ww = im.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        self.sub = collection(src, 60, 30)
        self.sub_y = self.t.y0 + self.t.lh + 34
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def jitter(self, name, k):
        s = sum(ord(c) for c in name)
        return (3.0 * math.sin(k * 0.21 + s) + 1.6 * math.sin(k * 0.53 + 2 * s),
                2.4 * math.sin(k * 0.17 + 3 * s) + 1.3 * math.sin(k * 0.61 + s))

    def spot(self, cx, cy, ox, oy, r=150.0):
        d = np.array([cx - ox, cy - oy]); d /= np.linalg.norm(d)
        u = (self.xx - cx) * d[0] + (self.yy - cy) * d[1]
        v = -(self.xx - cx) * d[1] + (self.yy - cy) * d[0]
        dist = np.sqrt((u / 1.25) ** 2 + v ** 2)                        # the beam meets the wall at an angle
        E = smooth((r - dist) / 34.0) * (0.55 + 0.45 * np.exp(-(dist / (0.42 * r)) ** 2))
        E = E + 0.10 * np.exp(-(dist / (2.2 * r)) ** 2)                  # spill round the spot
        return E.astype(np.float32)

    def frame(self, k):
        k = k % N
        ph = 2 * math.pi * k / N
        c = (1 - math.cos(ph)) / 2
        # camera: the wall moves in a little, the title (nearer) more
        zw = 1.0 + 0.03 * c; zt = 1.0 + 0.06 * c
        sx = (self.ww - W) / 2; sy = 28 + 18 * c
        M = np.float32([[1 / zw, 0, sx + W / 2 * (1 - 1 / zw)], [0, 1 / zw, sy + H / 2 * (1 - 1 / zw)]])
        Mi = cv2.invertAffineTransform(M)
        wall = cv2.warpAffine(self.wall, Mi, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        wgx = cv2.warpAffine(self.wgx, Mi, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        wgy = cv2.warpAffine(self.wgy, Mi, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        Tt = np.float32([[zt, 0, W / 2 * (1 - zt)], [0, zt, self.t.cy * (1 - zt)]])
        la = cv2.warpAffine(self.t.la, Tt, (W, H), flags=cv2.INTER_LINEAR)
        # light on the wall: a low cool ambient and the torches
        light = np.full((H, W, 3), 0.0, np.float32) + np.array([0.055, 0.062, 0.078], np.float32) * (0.85 + 0.3 * smooth(1.2 - self.yy / H))[..., None]
        lights = []
        for name, col in (("A", WARM), ("B", COOL)):
            (ox, oy), dz, on, off, pts = TORCH[name]
            lev = seg(k, *on) * (1 - seg(k, *off))
            if lev <= 0.001:
                continue
            cx, cy = path_at(pts, k); jx, jy = self.jitter(name, k); cx += jx; cy += jy
            E = self.spot(cx, cy, ox, oy) * lev
            # the title's shadow from this torch: thrown away from the torch onto the wall behind
            s = 0.07
            Ms = np.float32([[1 + s, 0, -ox * s], [0, 1 + s, -oy * s]])
            sh = blur(cv2.warpAffine(la, Ms, (W, H), flags=cv2.INTER_LINEAR), 4.0)
            # the wall's relief answers the torch's angle
            dx, dy = ox - cx, oy - cy; dn = math.hypot(dx, dy); dx, dy = dx / dn, dy / dn
            relief = np.clip(1 + 9.0 * (wgx * dx + wgy * dy), 0.45, 1.7)
            light += ((E * (1 - 0.88 * sh) * relief)[..., None] * col) * 3.4
            lights.append((E, ox, oy, dz, col))
        img = wall * light
        # the title, lit by the same torches
        face = self.t.lit(lights)
        face = cv2.warpAffine(face, Tt, (W, H), flags=cv2.INTER_LINEAR)
        # a soft contact shade under the steel so it reads off the wall at rest
        img = img * (1 - 0.45 * bigblur(la, 18))[..., None]
        img = img * (1 - la[..., None]) + face * la[..., None]
        # THE COLLECTION, with a shade behind it
        sa = np.zeros((H, W), np.float32)
        sh_, sw_ = self.sub.shape
        x0 = round(W / 2 - sw_ / 2); y0 = round(self.t.cy + (self.sub_y - self.t.cy) * zt)
        sa[y0:y0 + sh_, x0:x0 + sw_] = self.sub
        img = img * (1 - np.clip(bigblur(sa, 16) * 3.0, 0, 1) * 0.75)[..., None]
        img = img * (1 - sa[..., None]) + np.array([0.62, 0.66, 0.72], np.float32) * sa[..., None]
        # tone: soft shoulder, back to display gamma, vignette, still grain
        img = 1 - np.exp(-1.25 * img)
        img = np.clip(img, 0, 1) ** (1 / 2.0)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img = img * (1 - 0.45 * np.clip(rr - 0.45, 0, 1))[..., None]
        img = img + (self.grain[:H, :W] - 0.5)[..., None] * 0.015
        return Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))


# ----------------------------------------------------------------------------------------------------------- archive
PLATES = [("archive_fins.jpg", 0), ("archive_test.jpg", 66), ("archive_sonar.jpg", 128), ("archive_fins.jpg", 190)]


class Archive:
    def __init__(self, src):
        self.t = Steel(src, 860, 500)
        self.plates = {}
        for f, _ in PLATES:
            if f in self.plates:
                continue
            im = cv2.cvtColor(cv2.imread(os.path.join(src, f)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
            im = cv2.resize(im, (1360, round(im.shape[0] * 1360 / im.shape[1])), interpolation=cv2.INTER_AREA)
            g = im.mean(2, keepdims=True)
            im = g + (im - g) * 0.35                                     # archive grade: little colour left
            im = (im - 0.5) * 0.85 + 0.5
            im = im * np.array([0.92, 1.0, 0.97], np.float32)
            self.plates[f] = im.astype(np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        self.sub = collection(src, 60, 30)
        self.sub_y = self.t.y0 + self.t.lh + 34
        t = self.t
        lx0 = t.x0 + 30; lx1 = t.x0 + t.lw - 30
        ys = np.nonzero(t.la.max(1) > 0.3)[0]; ty0, ty1 = ys.min(), ys.max()
        sh_, sw_ = self.sub.shape
        cx0, cx1 = W / 2 - sw_ / 2, W / 2 + sw_ / 2
        # redaction bars (x from, x to, y, height, in, out): they run out from the text, as in the 2014 credits
        self.bars = [
            (lx0, lx0 + 520, ty0 - 46, 15, (3, 15), (204, 216)),
            (lx0, lx0 + 300, ty0 - 26, 15, (7, 19), (198, 210)),
            (lx1, lx1 - 220, ty0 - 26, 15, (10, 22), (194, 206)),
            (cx1 + 14, cx1 + 250, self.sub_y + 1, sh_ + 2, (16, 26), (186, 198)),
            (cx0 - 14, cx0 - 250, self.sub_y + 1, sh_ + 2, (20, 30), (182, 194)),
            (cx1 + 14, cx0 - 4, self.sub_y - 2, sh_ + 6, (58, 66), (100, 110)),   # strikes THE COLLECTION, pulls back
            (W / 2 - 330, W / 2 + 330, self.sub_y + sh_ + 26, 13, (120, 132), (150, 162)),
        ]
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        self.paper = noise(64, 1024, 1.0, 3)

    def plate(self, k):
        name, k0 = PLATES[0]
        for nm, kk in PLATES:
            if k >= kk:
                name, k0 = nm, kk
        im = self.plates[name]
        # each shot pushes in slowly; the fins shot runs on across the loop
        if name == "archive_fins.jpg":
            u = k / 66.0 if k < 128 else 1 - seg(k, 192, 244)          # in to the first cut; back to the cover
        else:
            u = (k - k0) / 64.0
        z = 1.0 + 0.06 * u
        env = seg(k, 0, 8) * (1 - seg(k, 236, 248))
        wx = (0.6 * math.sin(k * 1.7) + 0.4 * math.sin(k * 0.9)) * env   # gate weave
        wy = 0.5 * math.sin(k * 1.3 + 1) * env
        ih, iw = im.shape[:2]
        M = np.float32([[z, 0, W / 2 - iw / 2 * z + wx], [0, z, H / 2 - ih / 2 * z + wy]])
        out = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        flick = 1.0 + 0.025 * math.sin(k * 2.3) * math.sin(k * 0.7) * env
        return out * flick

    def frame(self, k):
        k = k % N
        ph = 2 * math.pi * k / N
        c = (1 - math.cos(ph)) / 2
        img = self.plate(k) ** 2.0 * 0.42                                # projected dim behind the type
        zt = 1.0 + 0.035 * c
        Tt = np.float32([[zt, 0, W / 2 * (1 - zt)], [0, zt, self.t.cy * (1 - zt)]])
        la = cv2.warpAffine(self.t.la, Tt, (W, H), flags=cv2.INTER_LINEAR)
        face = cv2.warpAffine(self.t.lit([]), Tt, (W, H), flags=cv2.INTER_LINEAR)
        env = bigblur(img, 60)                                           # the steel picks up what the film shows
        face = face * 1.35 + env * 0.9 * (1 - self.t.n[..., 2:3])
        img = img * (1 - 0.7 * bigblur(la, 26))[..., None]
        img = img * (1 - la[..., None]) + face * la[..., None]
        sa = np.zeros((H, W), np.float32)
        sh_, sw_ = self.sub.shape
        x0 = round(W / 2 - sw_ / 2); y0 = round(self.t.cy + (self.sub_y - self.t.cy) * zt)
        sa[y0:y0 + sh_, x0:x0 + sw_] = self.sub
        img = img * (1 - np.clip(bigblur(sa, 16) * 3.0, 0, 1) * 0.7)[..., None]
        img = img * (1 - sa[..., None]) + np.array([0.70, 0.72, 0.74], np.float32) * sa[..., None]
        # the bars: pale, matte, a little uneven like the credits' printed strips
        bars = np.zeros((H, W), np.float32)
        for xa, xb, y, h, tin, tout in self.bars:
            g = seg(k, *tin) * (1 - seg(k, *tout))
            if g <= 0.001:
                continue
            xe = xa + (xb - xa) * g
            lo, hi = min(xa, xe), max(xa, xe)
            yb = self.t.cy + (y - self.t.cy) * zt
            m = smooth((self.xx - lo) / 1.5) * smooth((hi - self.xx) / 1.5) * smooth((self.yy - yb) / 1.2) * smooth((yb + h * zt - self.yy) / 1.2)
            bars = np.maximum(bars, m)
        if bars.max() > 0:
            tex = 0.93 + 0.07 * cv2.resize(self.paper, (W, H))
            col = np.array([0.80, 0.81, 0.80], np.float32) ** 2.0
            img = img * (1 - bars[..., None]) + (col * tex[..., None]) * bars[..., None]
        img = 1 - np.exp(-1.3 * img)
        img = np.clip(img, 0, 1) ** (1 / 2.0)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img = img * (1 - 0.5 * np.clip(rr - 0.42, 0, 1))[..., None]
        img = img + (self.grain[:H, :W] - 0.5)[..., None] * 0.02
        return Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))


SCENES = {"mural": Mural, "archive": Archive}


def render(src, out, mode, only=None, mp4=None):
    s = SCENES[mode](src)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            s.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [s.frame(k) for k in range(N)]
    if mp4:
        p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", "25", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", mp4],
                             stdin=subprocess.PIPE)
        for _ in range(2):
            for f in frames:
                p.stdin.write(f.tobytes())
        p.stdin.close(); p.wait()
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    a = sys.argv
    mode = a[a.index("--mode") + 1] if "--mode" in a else "mural"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
