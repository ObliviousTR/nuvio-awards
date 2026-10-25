"""Godzilla & Kong card: idents built around a title that stays on screen for the whole hover.

modes
  charge  GODZILLA x KONG in brushed steel on a dark storm sky. Like Godzilla's dorsal plates before the atomic breath,
          blue charge climbs the letters from the bottom in three pulses, crackling along the edges, until the whole
          title is lit; the breath then fires behind it, a turbulent blue-white beam crossing the frame, and the charge
          drains back to the cover.
  storm   the same title under storm clouds and rain. Lightning flashes far away left and right, lighting the clouds and
          catching the steel; the last bolt strikes the x between the names and the charge runs out through the
          letters before it fades.
  fan     a fan-made MonsterVerse key art (the steel M with Godzilla firing his breath up through it, see _src/README).
          The plates light up from tail to head, the breath surges, the clouds flash, the camera breathes in and out.
All modes: 250 frames at 40 ms, first frame = last frame = cover; clouds and rain loop exactly.
usage: python3 art_tools/gk_ident.py SRC_DIR OUT_DIR --mode charge|storm|fan [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (GODZILLA x KONG line of the New Empire title logo), BarlowCondensed-Medium.ttf,
           monsterverse_fanart.jpg (fan mode)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
NAVY = np.array([9, 13, 24], np.float32)
CYAN = np.array([70, 165, 255], np.float32)
ICE = np.array([200, 230, 255], np.float32)
DEEP = np.array([30, 80, 210], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, ab):
    return float(smooth((k - ab[0]) / max(1, ab[1] - ab[0])))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def periodic_noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta
    spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


def drift(tex, k, v):
    """Tile `tex` (H x TW) drifting v px/frame; crossfaded so that frame N equals frame 0, contrast kept."""
    t = k / N
    a = np.roll(tex, -int(round(v * k)), axis=1)[:, :W]
    b = np.roll(tex, -int(round(v * k - v * N)), axis=1)[:, :W]
    m = float(tex.mean())
    mix = (1 - t) * a + t * b
    return np.clip(m + (mix - m) / math.sqrt((1 - t) ** 2 + t ** 2), 0, 1)


def make_rain(seed=9, count=1500):
    rng = np.random.default_rng(seed)
    lay = np.zeros((H, W), np.float32)
    for _ in range(count):
        x, y = rng.uniform(0, W), rng.uniform(0, H); L = rng.uniform(14, 34); b = rng.uniform(0.25, 1)
        for dx in (-W, 0, W):
            for dy in (-H, 0, H):
                p0 = (x + dx, y + dy); p1 = (x + dx - L * 0.22, y + dy + L)
                cv2.line(lay, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), b, 1, cv2.LINE_AA, 2)
    return lay


def rain_at(rain, k):
    return np.roll(np.roll(rain, (k * 6 * H // N) % H, axis=0), (-k * 2 * W // N) % W, axis=1)


def bolt_path(p0, p1, rng, rough=0.2, n=7):
    pts = [np.array(p0, float), np.array(p1, float)]
    disp = np.linalg.norm(pts[1] - pts[0]) * rough
    for _ in range(n):
        new = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            d = b - a; perp = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
            new += [(a + b) / 2 + perp * rng.normal() * disp, b]
        pts = new; disp *= 0.55
    return np.array(pts)


def bolt_layer(p0, p1, seed, branches=5, width=2):
    rng = np.random.default_rng(seed)
    lay = np.zeros((H, W), np.float32)
    main = bolt_path(p0, p1, rng)
    cv2.polylines(lay, [np.round(main * 4).astype(np.int32)], False, 1.0, width, cv2.LINE_AA, 2)
    total = np.linalg.norm(np.array(p1) - np.array(p0))
    for _ in range(branches):
        i = int(rng.uniform(0.15, 0.75) * len(main))
        d = main[min(i + 8, len(main) - 1)] - main[i]; d /= np.linalg.norm(d) + 1e-6
        ang = rng.choice([-1, 1]) * rng.uniform(0.35, 0.9)
        d = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang)])
        q = main[i] + d * total * rng.uniform(0.12, 0.3)
        br = bolt_path(main[i], q, rng, 0.25, 5)
        cv2.polylines(lay, [np.round(br * 4).astype(np.int32)], False, 0.55, 1, cv2.LINE_AA, 2)
    return lay


def collection(src, size=64, track=30, col=(196, 212, 236)):
    f = ImageFont.truetype(os.path.join(src, "BarlowCondensed-Medium.ttf"), size)
    txt = "THE COLLECTION"
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 20, size * 2), 0)
    d = ImageDraw.Draw(m); x = 10
    for c in txt:
        d.text((x, size * 1.6), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
    return Image.merge("RGBA", tuple(Image.new("L", m.size, v) for v in col) + (m,))


class Title:
    """GODZILLA x KONG as a full-frame alpha with brushed-steel faces, bevel normals and edge maps."""

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
        self.nx = n[..., 0]
        L = np.array([-0.45, -0.75, 0.5], np.float32); L /= np.linalg.norm(L)
        diff = np.clip(n @ L, 0, 1)
        spec = diff ** 14 * (1 - n[..., 2]) * 3
        yy = np.mgrid[0:H, 0:W][0].astype(np.float32)
        g = np.clip((yy - y0) / lh, 0, 1)[..., None]
        base = np.array([236, 242, 250], np.float32) * (1 - g) + np.array([150, 170, 198], np.float32) * g
        rng = np.random.default_rng(2)
        brush = cv2.GaussianBlur(rng.normal(size=(H, W)).astype(np.float32), (0, 0), sigmaX=24, sigmaY=0.6)
        brush = 1 + 0.05 * brush / (np.abs(brush).max() + 1e-6)
        self.face = np.clip(base * (0.42 + 0.78 * diff)[..., None] * brush[..., None] + (spec * 70)[..., None], 0, 255)
        er = cv2.erode(m, np.ones((5, 5), np.uint8))
        self.rim = blur(np.clip(la - er, 0, 1), 0.8) * la
        self.g1, self.g2, self.g3 = blur(la, 5), blur(la, 22), blur(la, 70)
        self.g4 = blur(la, 180)
        self.v = np.clip((y0 + lh - yy) / lh, -0.3, 1.3)               # 0 at the bottom of the title, 1 at the top
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        pts = np.concatenate([c[:, 0, :] for c in cs]).astype(np.float32)
        ggx = cv2.Sobel(self.g1, cv2.CV_32F, 1, 0, ksize=3); ggy = cv2.Sobel(self.g1, cv2.CV_32F, 0, 1, ksize=3)
        out = -np.stack([ggx[pts[:, 1].astype(int), pts[:, 0].astype(int)], ggy[pts[:, 1].astype(int), pts[:, 0].astype(int)]], 1)
        out /= np.linalg.norm(out, axis=1, keepdims=True) + 1e-6
        self.pts, self.out = pts, out
        # the x between the names: the small component in the middle
        n_, lab, st, cen = cv2.connectedComponentsWithStats(m)
        mid = [i for i in range(1, n_) if abs(cen[i][0] - W / 2) < lw * 0.06 and st[i][4] < st[1:, 4].max() * 0.4]
        i = mid[0] if mid else 1
        self.xm, self.ym, self.xm_top = float(cen[i][0]), float(cen[i][1]), float(st[i][1])

    def arcs(self, k, weight, count, reach):
        """Electric crackle on the outline: short jagged arcs, new every frame."""
        lay = np.zeros((H, W), np.float32)
        if count <= 0:
            return lay
        rng = np.random.default_rng(1000 + k)
        p = weight + 1e-6; p = p / p.sum()
        for i in rng.choice(len(self.pts), size=count, p=p):
            x, y = self.pts[i]; d = self.out[i]
            ang = rng.uniform(-1.0, 1.0)
            d = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang)])
            L = rng.uniform(0.4, 1.0) * reach
            pts = [(x, y)]; cx, cy = x, y
            for j in range(rng.integers(4, 8)):
                cx += d[0] * L / 5 + rng.normal() * L * 0.12; cy += d[1] * L / 5 + rng.normal() * L * 0.12
                pts.append((cx, cy))
                if rng.random() < 0.3:                                   # arcs bend back into the letters
                    d = -d * 0.5 + rng.normal(size=2) * 0.5; d /= np.linalg.norm(d) + 1e-6
            cv2.polylines(lay, [np.round(np.array(pts) * 4).astype(np.int32)], False, 1.0, 1, cv2.LINE_AA, 2)
        return lay

    def charge_light(self, img, E, Eg, arcs=None):
        """Blue charge: glow around the letters (E: per-pixel level, Eg: overall level). Before the title is composited."""
        glow = (self.g1 * 0.9 + self.g2 * 0.55) * E + self.g3 * 0.45 * Eg + self.g4 * 0.5 * Eg
        img += glow[..., None] * CYAN
        return img

    def composite(self, img, E, Eg, dark=0.0, extra=None):
        face = self.face
        tint = np.clip(E * 0.35, 0, 0.5)[..., None]
        face = face * (1 - tint) + ICE * tint
        white = np.clip((Eg - 1.0) * 2.2, 0, 0.55)
        if white > 0:
            face = face * (1 - white) + np.array([225, 240, 255], np.float32) * white
        face = face * (1 - dark)
        if extra is not None:
            face = face + extra
        a = self.la[..., None]
        img = img * (1 - a) + face * a
        img += (self.rim * np.clip(E, 0, 2) * 1.5)[..., None] * CYAN
        return img


def finish(img, xx, yy, sub, sub_y, strength=0.42):
    rr = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    img = img * (1 - strength * np.clip(rr - 0.4, 0, 1) ** 1.3)[..., None]
    out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
    out.alpha_composite(sub, (round(W / 2 - sub.width / 2), sub_y))
    return out.convert("RGB")


class Charge:
    PULSES = [(26, 0.3), (56, 0.55), (86, 0.82)]      # start frame, level the pulse leaves behind
    RISE = 26
    T_FULL = (112, 124)
    T_BEAM = (124, 170)
    T_DRAIN = (160, 222)

    def __init__(self, src):
        self.t = Title(src)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        tex = periodic_noise(180, 1024, 1.6, 3)
        self.cloud = cv2.resize(tex, (2 * W, H), interpolation=cv2.INTER_CUBIC)
        self.turb = cv2.resize(periodic_noise(64, 512, 1.2, 7), (2 * W, H), interpolation=cv2.INTER_CUBIC)
        self.sub = collection(src)
        self.sub_y = self.t.y0 + self.t.lh + 38

    def levels(self, k):
        v = self.t.v
        prev, E, band = 0.0, np.zeros((H, W), np.float32), np.zeros((H, W), np.float32)
        for ks, lvl in self.PULSES:
            if k < ks:
                break
            f = (k - ks) / self.RISE
            front = f * 1.35 - 0.15
            below = smooth((front - v) / 0.1)
            E = prev + (lvl - prev) * below
            band = np.exp(-((v - front) / 0.07) ** 2) * (1.1 - 0.9 * smooth(f - 1.0)) * (0.6 + lvl)
            prev = lvl
        Eg = prev
        if k >= self.T_FULL[0]:
            s = seg(k, self.T_FULL); E = E + (1.35 - E) * s; Eg = prev + (1.35 - prev) * s
        breathe = 1 + 0.07 * math.sin(k * 0.9)
        d = 1 - seg(k, self.T_DRAIN)
        return (E + band) * breathe * d, Eg * breathe * d, band * d

    def frame(self, k):
        t = self.t
        E, Eg, band = self.levels(k)
        c = drift(self.cloud, k, 2.0)
        img = NAVY + (c ** 1.6)[..., None] * np.array([26, 32, 46], np.float32)
        img = img + (t.g4 * 2.2 * Eg * c)[..., None] * DEEP * 0.6
        # the breath, behind the title
        dark = 0.0
        if self.T_BEAM[0] <= k <= self.T_BEAM[1] + 2:
            kk = k - self.T_BEAM[0]
            head = W * 1.15 * float(smooth(kk / 7.0))
            thick = float(smooth(kk / 4.0)) * (1 - seg(k, (self.T_BEAM[1] - 14, self.T_BEAM[1] + 2)))
            wc = t.lh * 0.32 * (0.35 + 0.65 * thick)
            tex = np.roll(self.turb, int(48 * k), axis=1)[:, :W]
            wob = 7 * np.sin(self.xx / 85 - k * 1.1) + 4 * np.sin(self.xx / 37 + k * 1.7)
            dy = self.yy - t.cy - wob
            along = smooth((head - self.xx) / 60) * smooth(self.xx / 40 + 0.4)
            core = np.exp(-(dy / (wc * 0.42)) ** 2) * (0.75 + 0.5 * tex)
            halo = np.exp(-(dy / (wc * 1.6)) ** 2) * (0.45 + 0.9 * tex)
            outer = np.exp(-(dy / (wc * 5.0)) ** 2)
            B = thick * along
            img += (core * B * 1.2)[..., None] * np.array([235, 245, 255], np.float32)
            img += (halo * B * 0.75)[..., None] * CYAN
            img += (outer * B * 0.22 + c * outer * B * 0.25)[..., None] * DEEP
            dark = 0.5 * thick
            fl = math.exp(-kk / 4.0) * 0.5
            img += fl * np.array([60, 110, 200], np.float32)
        img = t.charge_light(img, E, Eg)
        img = t.composite(img, E, Eg, dark)
        img += (t.rim * dark * 4)[..., None] * CYAN
        # crackle
        cnt = int(round(4 + 16 * min(Eg, 1.3))) if Eg > 0.05 else 0
        if cnt:
            w = band[t.pts[:, 1].astype(int), t.pts[:, 0].astype(int)] * 3 + E[t.pts[:, 1].astype(int), t.pts[:, 0].astype(int)]
            arc = t.arcs(k, w, cnt, 22 + 20 * min(Eg, 1.3))
            img += (arc * 0.9)[..., None] * ICE + (blur(arc, 2) * 2.2 + blur(arc, 7) * 1.6)[..., None] * CYAN
        return finish(img, self.xx, self.yy, self.sub, self.sub_y)


class Storm:
    FLICK = [1.0, 0.35, 0.95, 0.2, 0.55, 0.12, 0.05]
    T_STRIKE = 186

    def __init__(self, src):
        self.t = Title(src)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        self.cloud = cv2.resize(periodic_noise(200, 1024, 1.75, 11), (2 * W, H), interpolation=cv2.INTER_CUBIC)
        self.cloud2 = cv2.resize(periodic_noise(120, 512, 1.4, 12), (2 * W, H), interpolation=cv2.INTER_CUBIC)
        self.rain = make_rain()
        self.sub = collection(src)
        self.sub_y = self.t.y0 + self.t.lh + 38
        t = self.t
        self.events = [  # frame, bolt x, (end y), seed, strength
            (34, W * 0.065, H * 0.78, 21, 0.75),
            (90, W * 0.94, H * 0.72, 22, 0.8),
            (140, W * 0.36, t.y0 - 40, 23, 0.7),
        ]
        self.bolts = [bolt_layer((x + 40, -20), (x - 30, ye), s, 5, 2) for _, x, ye, s, _ in self.events]
        self.strike = bolt_layer((t.xm + 18, -20), (t.xm, t.xm_top + 4), 31, 4, 3)

    def flick(self, k, k0):
        i = k - k0
        return self.FLICK[i] if 0 <= i < len(self.FLICK) else 0.0

    def frame(self, k):
        t = self.t
        c = drift(self.cloud, k, 1.6); c2 = drift(self.cloud2, k, 3.0)
        cl = np.clip(c * 0.75 + c2 * 0.35, 0, 1)
        sky = 1 - smooth((self.yy - H * 0.2) / (H * 0.9)) * 0.45
        img = NAVY + ((cl ** 1.5) * sky)[..., None] * np.array([44, 52, 70], np.float32)
        light = np.zeros((H, W), np.float32); amb = 0.0
        extra = np.zeros((H, W, 3), np.float32)
        for (k0, x, ye, s, st), bl in zip(self.events, self.bolts):
            f = self.flick(k, k0) * st
            if f <= 0:
                continue
            L = np.exp(-((self.xx - x) / (W * 0.3)) ** 2 - ((self.yy - H * 0.2) / (H * 0.55)) ** 2)
            light += f * L; amb += f * 0.25
            img += ((blur(bl, 2) * 1.2 + blur(bl, 10) * 0.9) * f)[..., None] * np.array([150, 170, 230], np.float32)
            img += (bl * f)[..., None] * np.array([235, 240, 255], np.float32)
            side = np.clip(t.nx * (1 if x > W / 2 else -1), 0, 1)
            extra += ((side * 1.6 + 0.18) * f)[..., None] * np.array([190, 205, 240], np.float32)
        # the strike on the x and the charge it leaves
        E = np.zeros((H, W), np.float32); Eg = 0.0; band = E
        fs = self.flick(k, self.T_STRIKE) if k >= self.T_STRIKE else 0.0
        if k >= self.T_STRIKE:
            fs = max(fs, 0.0)
            light += fs * 1.3 * np.exp(-((self.xx - t.xm) / (W * 0.35)) ** 2 - ((self.yy - H * 0.15) / (H * 0.6)) ** 2)
            amb += fs * 0.35
            img += ((blur(self.strike, 2) * 1.5 + blur(self.strike, 12) * 1.1) * fs)[..., None] * np.array([150, 185, 255], np.float32)
            img += (self.strike * fs)[..., None] * np.array([240, 248, 255], np.float32)
            kk = k - self.T_STRIKE
            r = (kk - 1) / 15.0 * (t.lw / 2 + 60)
            dx = np.abs(self.xx - t.xm)
            fade = 1 - seg(k, (self.T_STRIKE + 14, 240))
            band = np.exp(-((dx - r) / 28) ** 2) * (1 - seg(kk, (14, 22))) * 1.3 * (kk >= 1)
            E = (smooth((r - dx) / 30) * 0.9 + band) * fade
            Eg = 0.9 * fade * float(kk >= 1)
            spot = np.exp(-(((self.xx - t.xm) ** 2 + (self.yy - t.ym) ** 2) / (2 * 22.0 ** 2)))
            img += (spot * (fs * 2.5 + 0.8 * fade))[..., None] * CYAN
        img += (light * cl ** 1.1)[..., None] * np.array([170, 185, 225], np.float32) + amb * np.array([26, 30, 44], np.float32)
        img = t.charge_light(img, E, Eg)
        img = t.composite(img, E, Eg, 0.0, extra)
        if Eg > 0.05:
            w = band[t.pts[:, 1].astype(int), t.pts[:, 0].astype(int)] * 3 + E[t.pts[:, 1].astype(int), t.pts[:, 0].astype(int)] * 0.3
            arc = t.arcs(k, w, int(4 + 10 * Eg), 22)
            img += (arc * 0.9)[..., None] * ICE + (blur(arc, 2) * 2.2 + blur(arc, 7) * 1.6)[..., None] * CYAN
        r = rain_at(self.rain, k)
        img += (r * (0.17 + 0.8 * min(1.0, amb * 2)))[..., None] * np.array([150, 160, 185], np.float32) * 0.55
        return finish(img, self.xx, self.yy, self.sub, self.sub_y)


class Fan:
    SHIFT = 64                 # the plate moves up this many px to make room for THE COLLECTION
    T_PLATES = (70, 132)       # plates light tail -> head
    T_SURGE = (122, 176)
    T_DECAY = (168, 226)

    def __init__(self, src):
        p = Image.open(os.path.join(src, "monsterverse_fanart.jpg")).convert("RGB").resize((W, H), Image.LANCZOS)
        a = np.asarray(p, np.float32)
        clean = a[-26:]                                                                    # sea below the wordmark
        fill = np.concatenate([clean[::-1], clean, clean[::-1]], 0)[:self.SHIFT]           # ping-pong, below the frame
        a = np.concatenate([a[self.SHIFT:], fill * np.linspace(1, 0.7, self.SHIFT)[:, None, None]], 0)
        self.p = a
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        lum = a.mean(2)
        teal = np.clip((np.minimum(g, b) - r - 25) / 50, 0, 1) * np.clip((lum - 60) / 80, 0, 1)
        sx = W / 960.0
        bx = 472 * sx
        mouth = 212 * sx - self.SHIFT
        self.beam = (np.clip((lum - 120) / 90, 0, 1) * np.exp(-((xx - bx) / 55) ** 2) * smooth((mouth - yy) / 25)).astype(np.float32)
        self.burst = np.exp(-(((xx - bx) / 260) ** 2 + ((yy - (10 - self.SHIFT)) / 120) ** 2)).astype(np.float32)
        # Godzilla's plates: teal light left of the M's inner edge, below the mouth
        gz = ((xx > 120 * sx) & (xx < 470 * sx) & (yy > 230 * sx - self.SHIFT) & (yy < 420 * sx - self.SHIFT)).astype(np.float32)
        self.plates = blur(teal * gz, 0.8)
        mz = ((xx > 300 * sx) & (xx < 650 * sx) & (yy > 80 * sx - self.SHIFT) & (yy < 420 * sx - self.SHIFT)).astype(np.float32)
        self.medge = blur(teal * mz * (1 - gz * (xx < 335 * sx)), 0.8)
        self.sky = (smooth((440 * sx - self.SHIFT - yy) / 80) * (1 - blur(mz, 30))).astype(np.float32)
        self.skylum = np.clip(lum / 255, 0, 1) ** 1.3
        self.ptail, self.phead = 130 * sx, 450 * sx
        self.turb = cv2.resize(periodic_noise(256, 64, 1.2, 8), (120, 2 * H), interpolation=cv2.INTER_CUBIC)
        self.rain = make_rain(13, 1100)
        self.sub = collection(src, 60, 30, (205, 214, 222))
        self.sub_y = 648
        self.events = [(28, W * 0.12, 41), (80, W * 0.88, 42), (150, W * 0.2, 43)]

    def frame(self, k):
        img = self.p.copy()
        u = (k - self.T_PLATES[0]) / (self.T_PLATES[1] - self.T_PLATES[0])
        dec = 1 - seg(k, self.T_DECAY)
        # plates: three waves tail -> head, then held while the breath surges
        pl = np.zeros((H, W), np.float32)
        span = self.phead - self.ptail
        for i, off in enumerate((0.0, 0.18, 0.36)):
            f = (u - off) / 0.55
            if 0 <= f <= 1.6:
                front = self.ptail + span * (f * 1.2 - 0.1)
                pl += np.exp(-((self.xx - front) / 45) ** 2) * (1 - smooth(f - 0.9) * 0.6) * (0.5 + 0.25 * i)
        held = seg(k, (self.T_PLATES[1] - 12, self.T_PLATES[1])) * dec
        pl = (pl + held * 0.9) * (u > -0.05)
        surge = seg(k, (self.T_SURGE[0], self.T_SURGE[0] + 10)) * dec
        flow = np.zeros((H, W), np.float32)
        if surge > 0:
            ty = np.roll(self.turb, -int(30 * k), axis=0)[:H]
            col = cv2.resize(ty, (120, H))
            strip = np.zeros((H, W), np.float32)
            x0 = int(472 * W / 960 - 60); strip[:, max(0, x0):x0 + 120] = col[:, :min(120, W - x0)]
            flow = strip
        lit = self.plates * pl * 2.2
        img += blur(lit, 1.5)[..., None] * np.array([120, 230, 255], np.float32) + blur(lit, 9)[..., None] * CYAN * 0.9
        me = self.medge * (0.8 * surge + 0.35 * held)
        img += (me * 1.3)[..., None] * np.array([110, 220, 240], np.float32) + blur(me, 10)[..., None] * CYAN * 0.8
        bm = self.beam * surge
        img += (bm * (0.5 + 0.9 * flow))[..., None] * np.array([200, 245, 255], np.float32) * 0.8
        img += (blur(self.beam, 18) * surge * 1.2)[..., None] * np.array([80, 200, 240], np.float32)
        img += (self.burst * surge * 0.38 * (0.8 + 0.2 * math.sin(k * 0.7)))[..., None] * np.array([110, 210, 235], np.float32)
        img += (self.sky * self.skylum * surge * 0.5)[..., None] * np.array([70, 170, 200], np.float32)
        # lightning in the clouds
        amb = 0.0
        for k0, x, s in self.events:
            i = k - k0
            f = Storm.FLICK[i] if 0 <= i < len(Storm.FLICK) else 0.0
            if f:
                L = np.exp(-((self.xx - x) / (W * 0.25)) ** 2 - ((self.yy - H * 0.15) / (H * 0.4)) ** 2)
                img += (L * self.sky * (0.25 + self.skylum) * f * 1.4)[..., None] * np.array([150, 190, 215], np.float32)
                amb += f * 0.2
        img += amb * np.array([20, 30, 36], np.float32)
        # camera breathes in and out around the M
        z = 1 + 0.035 * (1 - math.cos(2 * math.pi * k / N)) / 2
        cx, cy = 472 * W / 960, 300.0
        M = np.float32([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]])
        img = cv2.warpAffine(np.clip(img, 0, 255).astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        r = rain_at(self.rain, k)
        img += (r * (0.12 + amb))[..., None] * np.array([150, 175, 185], np.float32) * 0.5
        return finish(img, self.xx, self.yy, self.sub, self.sub_y, 0.3)


MODES = {"charge": Charge, "storm": Storm, "fan": Fan}


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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "charge"
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
