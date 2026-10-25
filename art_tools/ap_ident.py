"""Alien & Predator card: idents in deep space (a dark planet's rim below, faint stars), the title on screen throughout.

modes
  hunt       the AVP logo of Alien vs. Predator (2004) in chrome. The Predator's cloak runs down over it - the letters
             turn to bent light with a sheen on their edges - a thermal sweep crosses the frame and shows the title as
             heat, three red laser dots hunt across the letters and lock on the V, and the cloak breaks with blue crackle.
  encounter  ALIENS / VS / PREDATOR (the Requiem lockup) with THE COLLECTION in the place of REQUIEM. ALIENS goes dark
             and comes back stroke by stroke like the 1979 title, a blue light blooms through the I (Aliens, 1986);
             then PREDATOR cloaks, the laser dots run along it and lock on VS, it decloaks with crackle and burns red
             like the 1987 title before cooling back to white.
All modes: 250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/ap_ident.py SRC_DIR OUT_DIR --mode hunt|encounter [--frames a,b] [--mp4 path]
  SRC_DIR: avp.png (TMDB, film 395), l2_lockup.png (TMDB, film 440, REQUIEM removed), Michroma-Regular.ttf,
           Montserrat-VF.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
BLUE = np.array([90, 170, 255], np.float32)
RED = np.array([255, 40, 30], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / max(1, b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def thermal(v):
    """Predator vision palette: deep blue, blue, cyan, green, yellow, orange, red, white"""
    stops = np.array([0, 0.15, 0.32, 0.48, 0.62, 0.75, 0.88, 1.0], np.float32)
    cols = np.array([[10, 10, 70], [20, 40, 200], [20, 200, 230], [40, 220, 80], [240, 240, 40], [255, 150, 20],
                     [240, 30, 20], [255, 255, 255]], np.float32)
    v = np.clip(v, 0, 1)
    out = np.zeros(v.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(v, stops, cols[:, c])
    return out


def spaced(font, size, txt, track, var=None):
    f = ImageFont.truetype(font, size)
    if var:
        f.set_variation_by_axes(var)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 40, size * 2), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def place(a, cx, top):
    out = np.zeros((H, W), np.float32)
    h, w = a.shape[:2]
    x0 = int(round(cx - w / 2))
    out[top:top + h, x0:x0 + w] = a
    return out


class Shape:
    """outline points and outward normals of a mask, for the electric crackle"""

    def __init__(self, la):
        m = (la > 0.5).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        pts = np.concatenate([c[:, 0, :] for c in cs]).astype(np.float32)
        g1 = blur(la, 4)
        gx = cv2.Sobel(g1, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g1, cv2.CV_32F, 0, 1, ksize=3)
        xi, yi = pts[:, 0].astype(int), pts[:, 1].astype(int)
        out = -np.stack([gx[yi, xi], gy[yi, xi]], 1)
        self.out = out / (np.linalg.norm(out, axis=1, keepdims=True) + 1e-6)
        self.pts = pts

    def arcs(self, k, weight, count, reach, seed=0):
        lay = np.zeros((H, W), np.float32)
        if count <= 0 or weight.sum() <= 0:
            return lay
        rng = np.random.default_rng(seed * 1000 + k)
        p = weight / weight.sum()
        for i in rng.choice(len(self.pts), size=count, p=p):
            x, y = self.pts[i]; d = self.out[i]
            ang = rng.uniform(-1.2, 1.2)
            d = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang)])
            L = rng.uniform(0.4, 1.0) * reach
            pts = [(x, y)]; cx, cy = x, y
            for j in range(rng.integers(4, 8)):
                cx += d[0] * L / 5 + rng.normal() * L * 0.13; cy += d[1] * L / 5 + rng.normal() * L * 0.13
                pts.append((cx, cy))
                if rng.random() < 0.35:
                    d = -d * 0.4 + rng.normal(size=2) * 0.6; d /= np.linalg.norm(d) + 1e-6
            cv2.polylines(lay, [np.round(np.array(pts) * 4).astype(np.int32)], False, 1.0, 1, cv2.LINE_AA, 2)
        return lay


class Base:
    def __init__(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        rng = np.random.default_rng(4)
        # space: faint stars that twinkle a whole number of times per loop, the rim of a dark planet below
        self.stars = np.zeros((H, W), np.float32); self.tw = []
        for _ in range(420):
            x, y = rng.integers(0, W), rng.integers(0, H)
            b = rng.uniform(0.15, 0.7) ** 2
            self.stars[y, x] = b
            if rng.random() < 0.15:
                self.tw.append((x, y, b, rng.integers(1, 4), rng.uniform(0, 1)))
        self.stars = blur(self.stars, 0.6) * 3
        R = 2300.0; cy = H - 80 + R
        d = np.sqrt((xx - W / 2) ** 2 + (yy - cy) ** 2) - R
        self.planet = (d > 0).astype(np.float32)
        self.rim = np.exp(-np.abs(d) / 3.0) * (d > -2) + np.exp(-np.maximum(-d, 0) / 40) * 0.25 * (d < 0)
        self.rim *= np.exp(-((xx - W * 0.42) / (W * 0.45)) ** 2)
        self.haze = np.exp(-np.maximum(-d, 0) / 140) * (d < 0) * np.exp(-((xx - W * 0.42) / (W * 0.5)) ** 2)
        fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.rfftfreq(W)[None, :]
        f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
        spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** 1.7; spec[0, 0] = 0
        neb = np.fft.irfft2(spec, s=(H, W)).astype(np.float32)
        self.neb = np.clip((neb - neb.mean()) / neb.std() * 0.5 + 0.3, 0, 1) ** 2

    def background(self, k):
        img = np.zeros((H, W, 3), np.float32) + np.array([5, 7, 12], np.float32)
        st = self.stars.copy()
        for x, y, b, m, ph in self.tw:
            st[y, x] += b * 2.5 * (0.5 + 0.5 * math.sin(2 * math.pi * (m * k / N + ph)))
        img += (st * (1 - self.planet))[..., None] * np.array([200, 210, 230], np.float32)
        img += (self.rim * (1 - self.planet * 0.3))[..., None] * np.array([150, 140, 118], np.float32) * 0.8
        img += self.haze[..., None] * np.array([40, 52, 60], np.float32) * 0.5
        img += self.neb[..., None] * np.array([22, 30, 36], np.float32)
        img = img * (1 - self.planet[..., None]) + self.planet[..., None] * np.array([6, 8, 10], np.float32)
        return img

    def refract(self, img, la, amount, strength=14.0):
        """the cloak: the letters become bent light (the scene behind, displaced by the letter shapes)"""
        g = blur(la, 5)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5) / 32; gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5) / 32
        bent = cv2.remap(img.astype(np.float32), self.xx + gx * strength * 8, self.yy + gy * strength * 8,
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return bent


class Hunt(Base):
    T_CLOAK = (20, 44)
    T_THERM_IN, T_THERM_OUT = (52, 80), (104, 132)
    T_LASER = (118, 172)
    T_DECLOAK = (160, 184)

    def __init__(self, src):
        super().__init__()
        lg = Image.open(os.path.join(src, "avp.png")).convert("RGBA")
        lg = lg.crop(lg.getchannel("A").getbbox())
        lw = 780; lh = round(lg.height * lw / lg.width)
        lg = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32)
        self.top = 300 - lh // 2 - 20
        self.la = place(lg[..., 3] / 255, W / 2, self.top)
        rgb = np.zeros((H, W, 3), np.float32)
        x0 = int(round(W / 2 - lw / 2)); rgb[self.top:self.top + lh, x0:x0 + lw] = lg[..., :3]
        self.rgb = rgb
        self.lum = rgb.mean(2) / 255
        self.x0, self.lw, self.lh = x0, lw, lh
        self.shape = Shape(self.la)
        m = (self.la > 0.5).astype(np.uint8)
        self.edge = blur(np.clip(self.la - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1), 0.7)
        sub = spaced(os.path.join(src, "Michroma-Regular.ttf"), 40, "THE COLLECTION", 30)
        self.sub = place(sub, W / 2, self.top + lh + 34)
        # the V: where the lasers lock
        self.lock = (W / 2, self.top + lh * 0.36)
        self.noise = blur(np.random.default_rng(3).normal(size=(H, W)).astype(np.float32), 18)
        self.noise /= np.abs(self.noise).max()

    def cloak_amount(self, k):
        f0 = self.top + (k - self.T_CLOAK[0]) / (self.T_CLOAK[1] - self.T_CLOAK[0]) * (self.lh + 60) - 30
        on = smooth((f0 - self.yy) / 14)
        r = (k - self.T_DECLOAK[0]) / (self.T_DECLOAK[1] - self.T_DECLOAK[0]) * 520
        d = np.sqrt((self.xx - self.lock[0]) ** 2 + ((self.yy - self.lock[1]) * 2) ** 2)
        off = smooth((r - d) / 20) if k >= self.T_DECLOAK[0] else np.zeros_like(d)
        front_on = np.exp(-((f0 - self.yy) / 7) ** 2) * (self.T_CLOAK[0] <= k <= self.T_CLOAK[1] + 3)
        front_off = np.exp(-((r - d) / 14) ** 2) * (self.T_DECLOAK[0] <= k <= self.T_DECLOAK[1] + 3)
        return on * (1 - off), front_on + front_off

    def frame(self, k):
        bg = self.background(k)
        c, front = self.cloak_amount(k)
        img = bg + blur(self.la, 14)[..., None] * np.array([60, 80, 110], np.float32) * 0.25 * (1 - c[..., None])
        solid = self.rgb
        bent = self.refract(bg, self.la, 1.0)
        shim = 0.3 + 0.2 * np.sin(self.noise * 9 + k * 0.6)
        ripple = 0.5 + 0.5 * np.sin(self.noise * 14 - k * 0.45 + self.yy * 0.05)
        cloaked = bent * 1.4 + (self.edge * shim * 2.4)[..., None] * np.array([190, 215, 240], np.float32) \
            + (self.la * (0.07 + 0.09 * ripple))[..., None] * np.array([150, 185, 215], np.float32)
        letter = solid * (1 - c[..., None]) + cloaked * c[..., None]
        a = self.la[..., None]
        img = img * (1 - a) + letter * a
        # crackle on the cloak's front
        w = front[self.shape.pts[:, 1].astype(int), self.shape.pts[:, 0].astype(int)]
        if w.sum() > 0.5:
            arc = self.shape.arcs(k, w, int(10 + 10 * min(1, w.mean() * 20)), 26, 1)
            img += arc[..., None] * np.array([220, 240, 255], np.float32) + (blur(arc, 2) * 2 + blur(arc, 7) * 1.5)[..., None] * BLUE
            img += (blur(front * self.la, 3) * 1.2)[..., None] * BLUE
        # thermal sweep
        fin = (k - self.T_THERM_IN[0]) / (self.T_THERM_IN[1] - self.T_THERM_IN[0]) * (W + 160) - 80
        fout = (k - self.T_THERM_OUT[0]) / (self.T_THERM_OUT[1] - self.T_THERM_OUT[0]) * (W + 160) - 80
        S = smooth((fin - self.xx) / 30) * smooth((self.xx - fout) / 30)
        if S.max() > 0:
            heat = 0.06 + 0.04 * self.noise + 0.12 * self.haze + 0.06 * self.neb
            heat = heat + blur(self.la, 16) * 0.2 + self.la * (0.36 + 0.22 * self.lum) + blur(self.la, 3) * 0.06
            th = thermal(heat)
            th *= (0.92 + 0.08 * np.sin(self.yy * 1.6))[..., None]           # scanlines
            edge_band = np.exp(-((fin - self.xx) / 6) ** 2) + np.exp(-((self.xx - fout) / 6) ** 2)
            img = img * (1 - S[..., None]) + th * S[..., None] + (edge_band * S.max())[..., None] * np.array([200, 60, 40], np.float32) * 0.6
        # the laser sight
        if self.T_LASER[0] <= k <= self.T_LASER[1]:
            kk = k - self.T_LASER[0]
            hunt = 1 - seg(k, 146, 156)
            px = self.x0 + self.lw * (0.5 + 0.38 * math.sin(kk * 0.11) * math.cos(kk * 0.037))
            py = self.top + self.lh * (0.4 + 0.25 * math.sin(kk * 0.17))
            cx = px * hunt + self.lock[0] * (1 - hunt); cy = py * hunt + self.lock[1] * (1 - hunt)
            al = seg(k, self.T_LASER[0], self.T_LASER[0] + 6) * (1 - seg(k, self.T_LASER[1] - 8, self.T_LASER[1]))
            lockp = seg(k, 154, 158) * (1 - seg(k, 162, 172))
            sz = 11 - 3 * lockp
            dots = np.zeros((H, W), np.float32)
            for i in range(3):
                ang = -math.pi / 2 + i * 2 * math.pi / 3
                dx, dy = cx + sz * math.cos(ang), cy + sz * math.sin(ang)
                dots += np.exp(-((self.xx - dx) ** 2 + (self.yy - dy) ** 2) / (2 * 2.2 ** 2))
                # faint beams from the shoulder cannon, off screen top right
                bl = np.zeros((H, W), np.float32)
                cv2.line(bl, (int((W + 260 + i * 6) * 4), int(-160 * 4)), (int(dx * 4), int(dy * 4)), 1.0, 1, cv2.LINE_AA, 2)
                dots += blur(bl, 1.2) * 0.18
            img += (dots * al * (1.6 + 1.2 * lockp))[..., None] * RED + (blur(dots, 6) * al * 3)[..., None] * RED * 0.5
            img += (np.exp(-((self.xx - cx) ** 2 + (self.yy - cy) ** 2) / (2 * 3.5 ** 2)) * al * lockp)[..., None] * np.array([255, 220, 210], np.float32)
        # the decloak flash
        fl = math.exp(-((k - self.T_DECLOAK[1]) / 4.0) ** 2)
        img += ((blur(self.la, 6) * 0.6 + self.la * 0.2) * fl)[..., None] * np.array([180, 210, 255], np.float32)
        img = img * (1 - self.sub[..., None] * 0.9) + self.sub[..., None] * np.array([196, 204, 214], np.float32)
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


class Encounter(Base):
    T_DARK = (16, 28)
    T_FRAG = (30, 80)
    T_BLUE = (78, 116)
    T_CLOAK = (114, 132)
    T_LASER = (128, 168)
    T_DECLOAK = (162, 182)
    T_RED = (180, 226)

    def __init__(self, src):
        super().__init__()
        lg = Image.open(os.path.join(src, "l2_lockup.png")).getchannel("A")
        lh = 392; lw = round(lg.width * lh / lg.height)
        a = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.top = 300 - lh // 2 - 26
        self.la = place(a, W / 2, self.top)
        self.x0, self.lw, self.lh = int(round(W / 2 - lw / 2)), lw, lh
        s = lh / 617.0
        y_al, y_vs, y_pr = self.top + int(300 * s), self.top + int(420 * s), self.top + lh
        self.m_al = self.la * (self.yy < y_al)
        self.m_vs = self.la * (self.yy >= y_al) * (self.yy < y_vs)
        self.m_pr = self.la * (self.yy >= y_vs)
        g = np.clip((self.yy - self.top) / lh, 0, 1)[..., None]
        self.white = np.array([246, 248, 252], np.float32) * (1 - 0.12 * g)
        # ALIENS cut into fragments: each letter in thirds, each third has its own moment (1979)
        m = (self.m_al > 0.5).astype(np.uint8)
        n, lab = cv2.connectedComponents(m)
        rng = np.random.default_rng(8)
        self.frag_t = np.full((H, W), 1e9, np.float32)
        band = np.clip(((self.yy - self.top) / (y_al - self.top) * 3).astype(int), 0, 2)
        times = rng.permutation(np.linspace(self.T_FRAG[0], self.T_FRAG[1] - 8, (n - 1) * 3))
        for i in range(1, n):
            for b in range(3):
                self.frag_t[(lab == i) & (band == b)] = times[(i - 1) * 3 + b]
        self.frag_t = cv2.dilate(np.where(self.frag_t > 1e8, 0, self.frag_t), np.ones((3, 3), np.uint8))
        # the I of ALIENS: the thin middle letter
        comps = [(cv2.boundingRect((lab == i).astype(np.uint8)), i) for i in range(1, n)]
        comps.sort(key=lambda c: c[0][0])
        (ix, iy, iw, ih), _ = comps[2]
        self.ic = (ix + iw / 2, iy + ih / 2)
        self.shape_pr = Shape(self.m_pr)
        mm = (self.m_pr > 0.5).astype(np.uint8)
        self.edge_pr = blur(np.clip(self.m_pr - cv2.erode(mm, np.ones((3, 3), np.uint8)), 0, 1), 0.7)
        self.vs = (W / 2, self.top + (300 + 60) * s)
        sub = spaced(os.path.join(src, "Montserrat-VF.ttf"), 56, "THE COLLECTION", 46, [800])
        self.sub = place(sub, W / 2, self.top + lh + 40)
        self.noise = blur(np.random.default_rng(3).normal(size=(H, W)).astype(np.float32), 18)
        self.noise /= np.abs(self.noise).max()

    def frame(self, k):
        bg = self.background(k)
        img = bg.copy()
        # ALIENS: dark, then stroke by stroke, then the blue light
        dark = seg(k, *self.T_DARK) * (k < self.T_FRAG[1] + 10)
        frag = smooth((k - self.frag_t) / 5) if k >= self.T_FRAG[0] else np.zeros((H, W), np.float32)
        al_a = (1 - dark) + dark * (0.05 + 0.95 * frag)
        blue = math.sin(math.pi * seg(k, *self.T_BLUE)) ** 1.5 if self.T_BLUE[0] <= k <= self.T_BLUE[1] else 0.0
        # PREDATOR: cloak by a front left to right, decloak from VS outwards
        f0 = self.x0 + (k - self.T_CLOAK[0]) / (self.T_CLOAK[1] - self.T_CLOAK[0]) * (self.lw + 80) - 40
        on = smooth((f0 - self.xx) / 16)
        r = (k - self.T_DECLOAK[0]) / (self.T_DECLOAK[1] - self.T_DECLOAK[0]) * (self.lw / 2 + 60)
        dxv = np.abs(self.xx - self.vs[0])
        off = smooth((r - dxv) / 18) if k >= self.T_DECLOAK[0] else 0.0
        c = (on * (1 - off)) if k >= self.T_CLOAK[0] else np.zeros((H, W), np.float32)
        front = np.exp(-((f0 - self.xx) / 8) ** 2) * (self.T_CLOAK[0] <= k <= self.T_CLOAK[1] + 3) \
            + np.exp(-((r - dxv) / 12) ** 2) * (self.T_DECLOAK[0] <= k <= self.T_DECLOAK[1] + 3)
        wipe = self.top + self.lh * 0.6 + (k - self.T_RED[0]) / (self.T_RED[1] - self.T_RED[0]) * self.lh * 0.5
        redp = seg(k, self.T_DECLOAK[0] + 4, self.T_DECLOAK[1]) * (smooth((self.yy - wipe) / 6) if k >= self.T_RED[0] else 1.0)
        # glows behind
        img += blur(self.la, 14)[..., None] * np.array([70, 80, 100], np.float32) * 0.22
        if blue > 0:
            ib = np.exp(-(((self.xx - self.ic[0]) / 38) ** 2 + ((self.yy - self.ic[1]) / 120) ** 2))
            streak = np.exp(-(((self.yy - self.ic[1]) / 5) ** 2)) * np.exp(-np.abs(self.xx - self.ic[0]) / 420)
            img += ((ib * 1.6 + streak * 0.9) * blue)[..., None] * BLUE + (ib * blue * 0.8)[..., None] * np.array([200, 230, 255], np.float32)
        img += (blur(self.m_pr * redp, 10) * 1.2)[..., None] * RED * 0.6
        # letters
        letter = np.broadcast_to(self.white, (H, W, 3)).copy()
        if blue > 0:
            tint = np.exp(-np.abs(self.xx - self.ic[0]) / 260) * blue * (self.yy < self.top + self.lh * 0.5)
            letter = letter * (1 - tint[..., None] * 0.5) + tint[..., None] * np.array([120, 190, 255], np.float32) * 0.5
        if np.max(redp) > 0:
            rt = (self.m_pr > 0) * redp
            red_col = np.array([230, 30, 25], np.float32) * (1 - 0.35 * np.clip((self.yy - (self.top + self.lh * 0.7)) / (self.lh * 0.3), 0, 1))[..., None]
            letter = letter * (1 - rt[..., None]) + red_col * rt[..., None]
        bent = self.refract(img, self.m_pr, 1.0)
        shim = 0.3 + 0.2 * np.sin(self.noise * 9 + k * 0.6)
        ripple = 0.5 + 0.5 * np.sin(self.noise * 14 - k * 0.45 + self.yy * 0.05)
        cloaked = bent * 1.4 + (self.edge_pr * shim * 2.4)[..., None] * np.array([190, 215, 240], np.float32) \
            + (self.m_pr * (0.07 + 0.09 * ripple))[..., None] * np.array([150, 185, 215], np.float32)
        cc = (c * (self.m_pr > 0))[..., None]
        letter = letter * (1 - cc) + cloaked * cc
        a = (self.m_al * al_a + self.m_vs + self.m_pr)[..., None]
        img = img * (1 - a) + letter * a
        # 1979: each stroke arrives with a faint flare
        if self.T_FRAG[0] <= k <= self.T_FRAG[1] + 6:
            fl = np.exp(-((k - self.frag_t - 2) / 2.0) ** 2) * (self.m_al > 0)
            img += (blur(fl * self.m_al, 4) * 1.2 + fl * self.m_al * 0.4)[..., None] * np.array([200, 215, 235], np.float32)
        # crackle
        w = (front * (self.m_pr > 0.2))[self.shape_pr.pts[:, 1].astype(int), self.shape_pr.pts[:, 0].astype(int)]
        if w.sum() > 0.5:
            arc = self.shape_pr.arcs(k, w, 14, 24, 2)
            img += arc[..., None] * np.array([220, 240, 255], np.float32) + (blur(arc, 2) * 2 + blur(arc, 7) * 1.5)[..., None] * BLUE
        # the laser sight: along PREDATOR, then up onto VS
        if self.T_LASER[0] <= k <= self.T_LASER[1] + 8:
            kk = k - self.T_LASER[0]
            hunt = 1 - seg(k, 150, 158)
            px = self.x0 + self.lw * (0.12 + 0.76 * smooth(kk / 24.0)) + 30 * math.sin(kk * 0.5)
            py = self.top + self.lh * 0.82 + 14 * math.sin(kk * 0.31)
            cx = px * hunt + self.vs[0] * (1 - hunt); cy = py * hunt + self.vs[1] * (1 - hunt)
            al = seg(k, self.T_LASER[0], self.T_LASER[0] + 5) * (1 - seg(k, self.T_LASER[1], self.T_LASER[1] + 8))
            lockp = seg(k, 156, 160)
            sz = 10 - 3 * lockp
            dots = np.zeros((H, W), np.float32)
            for i in range(3):
                ang = -math.pi / 2 + i * 2 * math.pi / 3
                dx, dy = cx + sz * math.cos(ang), cy + sz * math.sin(ang)
                dots += np.exp(-((self.xx - dx) ** 2 + (self.yy - dy) ** 2) / (2 * 2.2 ** 2))
            img += (dots * al * (1.6 + 1.2 * lockp))[..., None] * RED + (blur(dots, 6) * al * 3)[..., None] * RED * 0.5
        sub_col = np.array([225, 32, 28], np.float32)
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * sub_col
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


MODES = {"hunt": Hunt, "encounter": Encounter}


def render(src, out, mode, only=None, mp4=None):
    s = MODES[mode](src)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            s.frame(k).save(os.path.join(out, f"{mode}_f{k:03d}.jpg"), quality=90)
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
    print(mode, "seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    a = sys.argv
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mode = a[a.index("--mode") + 1] if "--mode" in a else "hunt"
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
