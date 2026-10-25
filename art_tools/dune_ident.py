"""Dune card: the copper DUNE title of the Villeneuve films (with the glint on the E), on screen for the whole hover.

modes
  eclipse  the eclipse of the Dune posters: a black moon holds the sun behind U and N, a gold ring of fire round it,
           the corona's rays turning slowly. The moon drifts off to the right, the sun's edge breaks out and floods
           the copper letters, then the moon comes back - a diamond-ring flash as it closes, the glint on the E flares -
           and the ring settles. THE COLLECTION sits inside the moon, under the title.
  worm     dusk over the deep desert, the title in the sky over the dunes, sand blowing. Worm sign: a ripple runs
           under the sand and the dune swells and sprays, then the sandworm's mouth rises behind the title, sand
           pouring off its rim, and sinks back in a burst of sand.
All modes: 250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/dune_ident.py SRC_DIR OUT_DIR --mode eclipse|worm [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (the Dune (2021) title logo on TMDB, copper with the glint), Montserrat-VF.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
GOLD = np.array([255, 176, 70], np.float32)
WARM = np.array([255, 226, 180], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / max(1, b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


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


def noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta; spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


class Base:
    def __init__(self, src, lw=880, cy=300):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA")
        a = np.asarray(lg, np.float32)
        al = a[..., 3] / 255
        n, lab, st, cen = cv2.connectedComponentsWithStats((al > 0.5).astype(np.uint8))
        order = sorted(range(1, n), key=lambda i: st[i][0])
        # letters: D U N E; the E's component carries the glint line, so take the E by its bowl only
        d0 = st[order[0]][0]
        u1, n0 = st[order[1]][0] + st[order[1]][2], st[order[2]][0]
        mid = (u1 + n0) / 2                                    # between U and N: the true centre of the word
        s = lw / a.shape[1]
        self.lh = round(a.shape[0] * s)
        im = Image.fromarray(a.astype(np.uint8), "RGBA").resize((lw, self.lh), Image.LANCZOS)
        a = np.asarray(im, np.float32)
        self.cx = W / 2
        x0 = int(round(self.cx - mid * s)); y0 = int(round(cy - self.lh / 2))
        self.la = np.zeros((H, W), np.float32); self.rgb = np.zeros((H, W, 3), np.float32)
        xs0, xs1 = max(0, x0), min(W, x0 + lw)
        self.la[y0:y0 + self.lh, xs0:xs1] = a[:, xs0 - x0:xs1 - x0, 3] / 255
        self.rgb[y0:y0 + self.lh, xs0:xs1] = a[:, xs0 - x0:xs1 - x0, :3]
        self.cy, self.y0 = cy, y0
        # the glint's dot on the E: the darkest solid pixel on the glint's row inside the E
        e = order[3]
        ex0, ex1 = x0 + int(st[e][0] * s), x0 + int((st[e][0] + st[e][2]) * s)
        right = self.la[:, min(W - 1, ex1):]
        row = int(np.argmax((right > 0.03).sum(1))) if right.size else cy
        lum = self.rgb[row, ex0:min(W, ex1)].mean(1) + (self.la[row, ex0:min(W, ex1)] < 0.5) * 999
        self.dot = (ex0 + int(np.argmin(lum)), row)
        m = (self.la > 0.5).astype(np.uint8)
        self.rim = blur(np.clip(self.la - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1), 0.7)
        self.sub = np.zeros((H, W), np.float32)

    def put_sub(self, src, top, size=34, track=28, weight=500):
        sub = spaced(os.path.join(src, "Montserrat-VF.ttf"), size, "THE COLLECTION", track, [weight])
        h, w = sub.shape
        x0 = int(round(self.cx - w / 2))
        self.sub[top:top + h, x0:x0 + w] = sub

    def title(self, img, light=0.0, glint=0.0, lightpos=None):
        a = self.la[..., None]
        face = self.rgb * (1 + 0.6 * light)
        if lightpos is not None and light > 0:
            d = np.sqrt((self.xx - lightpos[0]) ** 2 + (self.yy - lightpos[1]) ** 2)
            face = face + (np.exp(-d / 260) * light * 0.8)[..., None] * WARM * self.la[..., None]
        img = img * (1 - a) + face * a
        if glint > 0:
            gx, gy = self.dot
            streak = np.exp(-((self.yy - gy) / 1.6) ** 2) * np.exp(-np.abs(self.xx - gx) / 260)
            core = np.exp(-((self.xx - gx) ** 2 + (self.yy - gy) ** 2) / (2 * 5.0 ** 2))
            img += ((streak * 1.4 + blur(streak, 3) * 0.8 + core * 2.5) * glint)[..., None] * WARM
        return img


class Eclipse(Base):
    T_OUT = (34, 104)      # the moon drifts off
    T_IN = (128, 196)      # and comes back
    R = 196.0

    def __init__(self, src):
        super().__init__(src)
        self.put_sub(src, self.cy + 66, 30, 26, 500)
        d = np.sqrt((self.xx - self.cx) ** 2 + (self.yy - self.cy) ** 2)
        self.d = d
        self.ang = np.arctan2(self.yy - self.cy, self.xx - self.cx)
        rng = np.random.default_rng(3)
        # corona streamers: angular noise, a few strong rays
        nang = 720
        prof = noise(8, nang, 1.2, 5)[4]
        prof = np.clip((prof - 0.35) / 0.65, 0, 1) ** 1.6
        idx = ((self.ang + math.pi) / (2 * math.pi) * nang).astype(int) % nang
        self.prof = prof; self.idx = idx
        self.dust = noise(H, W, 1.5, 9)
        # thin orbit scratches, like the Part Two poster's
        self.orbits = []
        for _ in range(9):
            self.orbits.append((rng.uniform(1.15, 2.6) * self.R, rng.uniform(0.25, 1.0), rng.uniform(0, 2 * math.pi),
                                rng.uniform(0.6, 1.6) * rng.choice([-1, 1]), rng.uniform(0.15, 0.45)))

    def moon_dx(self, k):
        return self.R * 0.32 * (seg(k, *self.T_OUT) - seg(k, *self.T_IN))

    def frame(self, k):
        R = self.R
        dx = self.moon_dx(k)
        dm = np.sqrt((self.xx - self.cx - dx) ** 2 + (self.yy - self.cy) ** 2)
        sun = smooth((R - self.d) / 1.5)
        moon = smooth((R * 1.012 - dm) / 1.2)
        vis = sun * (1 - moon)
        frac = float(vis.sum() / max(1.0, sun.sum()))                  # how much of the sun shows
        img = np.zeros((H, W, 3), np.float32) + np.array([7, 5, 4], np.float32)
        img += (self.dust ** 3 * 0.6)[..., None] * np.array([40, 26, 14], np.float32)
        # corona: streamers turning slowly (one turn would take ages: a tiny rotation that returns)
        rot = int(round(6 * math.sin(2 * math.pi * k / N)))
        prof = np.roll(self.prof, rot)[self.idx]
        out = np.clip(self.d - R, 0, None)
        corona = (np.exp(-out / 34) * 1.1 + np.exp(-out / 120) * (0.25 + 0.75 * prof) * 0.8) * (self.d > R * 0.98)
        tot = 1 - min(1.0, frac * 6)                                    # the corona shows best in totality
        img += (corona * (0.45 + 0.55 * tot))[..., None] * GOLD
        # the ring of fire at the moon's edge (chromosphere), strongest in totality
        ring = np.exp(-((dm - R * 1.012) / 3.2) ** 2) * smooth((R * 1.03 - self.d) / 2.0) * (0.7 + 0.3 * tot)
        hot = np.exp(-((dm - R * 1.012) / 1.4) ** 2) * smooth((R * 1.02 - self.d) / 1.5)
        img += (ring * 2.0 + blur(ring, 5) * 2.0 + blur(ring, 16) * 1.0)[..., None] * np.array([255, 150, 45], np.float32)
        img += (hot * 0.9)[..., None] * np.array([255, 235, 180], np.float32)
        # the bare sun
        limb = np.clip(1 - (self.d / R) ** 2, 0, 1) ** 0.35
        img += (vis * (0.75 + 0.25 * limb))[..., None] * np.array([255, 240, 214], np.float32) * 1.3
        bloom = blur(vis, 22) * 2.2 + blur(vis, 70) * 3.5
        img += bloom[..., None] * GOLD * 0.7
        # anamorphic streak through the bare limb
        if frac > 0.001:
            ys = np.where(vis.max(1) > 0.5)[0]
            cyl = float(ys.mean()) if len(ys) else self.cy
            xsun = float((vis.sum(0) * np.arange(W)).sum() / max(1, vis.sum()))
            streak = np.exp(-((self.yy - cyl) / 3.0) ** 2) * np.exp(-np.abs(self.xx - xsun) / 520)
            img += (streak * min(1.0, frac * 4) * 1.4)[..., None] * WARM
        # diamond ring: a bead of light where the moon's edge leaves / meets the sun
        for kc, side in ((self.T_OUT[0] + 4, 1), (self.T_IN[1] - 6, 1)):
            f = math.exp(-((k - kc) / 4.0) ** 2)
            if f > 0.01:
                bx, by = self.cx - R * 0.99 * side, self.cy
                d2 = (self.xx - bx) ** 2 + (self.yy - by) ** 2
                bead = np.exp(-d2 / (2 * 6.0 ** 2)) * 3 + np.exp(-d2 / (2 * 40.0 ** 2)) * 1.2
                star = (np.exp(-((self.yy - by) / 2.0) ** 2) * np.exp(-np.abs(self.xx - bx) / 380)
                        + np.exp(-((self.xx - bx) / 2.0) ** 2) * np.exp(-np.abs(self.yy - by) / 70) * 0.6)
                img += ((bead + star * 1.3) * f)[..., None] * WARM
        # orbit scratches
        orb = np.zeros((H, W), np.float32)
        for r0, ecc, a0, spd, b in self.orbits:
            t = a0 + spd * 2 * math.pi * k / N
            pts = []
            for u in np.linspace(t, t + 1.2, 40):
                pts.append((self.cx + r0 * math.cos(u), self.cy + r0 * ecc * math.sin(u)))
            cv2.polylines(orb, [np.round(np.array(pts) * 4).astype(np.int32)], False, b, 1, cv2.LINE_AA, 2)
        img += (orb * (0.5 + 0.5 * tot))[..., None] * np.array([200, 140, 80], np.float32) * 0.6
        # the moon itself: black, faintly lit at the edge facing the sun
        img = img * (1 - moon[..., None] * (1 - 0.0)) + moon[..., None] * np.array([5, 4, 4], np.float32)
        # title, lit by the bare sun; the glint flares with the diamond rings
        gl = max(math.exp(-((k - self.T_OUT[0] - 4) / 6.0) ** 2), math.exp(-((k - self.T_IN[1] + 6) / 6.0) ** 2))
        img = self.title(img, light=min(1.0, frac * 3), glint=gl, lightpos=(self.cx - R, self.cy))
        img += (blur(self.la, 6) * (0.35 * tot + 0.8 * min(1.0, frac * 3)))[..., None] * GOLD * 0.35
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([228, 196, 172], np.float32)
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


class Worm(Base):
    T_SIGN = (30, 110)
    T_RISE = (104, 150)
    T_SINK = (168, 206)

    def __init__(self, src):
        super().__init__(src, lw=860, cy=262)
        self.put_sub(src, self.cy + 64, 32, 28, 500)
        rng = np.random.default_rng(6)
        # sky: dusk haze
        t = self.yy / H
        self.sky = (np.array([46, 26, 16], np.float32) * (1 - t[..., None]) + np.array([150, 82, 36], np.float32) * t[..., None])
        sunx, suny = W * 0.5, H * 0.66
        ds = np.sqrt((self.xx - sunx) ** 2 + ((self.yy - suny) * 1.6) ** 2)
        self.sky += (np.exp(-ds / 260) * 1.0)[..., None] * np.array([120, 70, 30], np.float32)
        # dunes: three ridgelines
        xs = np.arange(W, dtype=np.float32)
        self.ridges = []
        for i, (base, amp, col) in enumerate([(500, 26, (64, 34, 18)), (556, 34, (88, 48, 24)), (624, 40, (112, 62, 30))]):
            n = noise(4, W, 2.2, 20 + i)[2]
            y = base - amp * (n - 0.5) * 2 - 10 * np.sin(xs / (180 + 60 * i) + i)
            self.ridges.append((y.astype(np.float32), np.array(col, np.float32)))
        self.wind = noise(H, 2 * W, 1.2, 31)
        self.grain = noise(H, W, 0.6, 32)
        # the worm's mouth: polar texture
        self.mcx, self.mR = self.cx, 250.0
        self.wr = noise(16, 720, 1.4, 33)
        self.parts = rng.uniform(0, 1, (900, 4)).astype(np.float32)   # spray / pouring sand

    def dunes(self, img, k, bump_x=None, bump=0.0):
        for i, (y, col) in enumerate(self.ridges):
            yl = y.copy()
            if bump_x is not None and i == 1:
                yl = yl - bump * 42 * np.exp(-((np.arange(W) - bump_x) / 70.0) ** 2)
            m = smooth((self.yy - yl[None, :]) / 1.5)
            shade = np.clip((self.yy - yl[None, :]) / 140, 0, 1)
            lit = np.exp(-np.maximum(self.yy - yl[None, :], 0) / 5) * 0.8
            c = col * (1.0 - 0.45 * shade[..., None]) + lit[..., None] * np.array([150, 90, 40], np.float32)
            c *= (0.92 + 0.16 * self.grain)[..., None]
            img = img * (1 - m[..., None]) + c * m[..., None]
        return img

    def mouth(self, img, k, rise):
        """the open mouth seen head-on: a lip, rings of teeth, the dark throat; rising from below the dunes"""
        cy = 760 - rise * 340
        R = self.mR
        dx, dy = self.xx - self.mcx, (self.yy - cy) * 1.05
        r = np.sqrt(dx * dx + dy * dy) / R
        ang = np.arctan2(dy, dx)
        idx = ((ang + math.pi) / (2 * math.pi) * 720).astype(int) % 720
        rr = np.clip(r, 0, 1.5)
        tex = self.wr[(rr * 10).astype(int).clip(0, 15), idx]
        wob = 1 + 0.035 * (self.wr[3, idx] - 0.5) * 2                  # the rim is not a perfect circle
        rw = r / wob
        body = smooth((1.0 - rw) / 0.015)
        lip = smooth((rw - 0.8) / 0.04) * body
        seg_rings = 0.75 + 0.25 * np.cos(rw * 2 * math.pi * 7)          # ridges of the lip
        # teeth: several rows of fine baleen spikes pointing in, lengths and spacing irregular
        teeth = np.zeros_like(r)
        for row, (r1, nn, sh) in enumerate(((0.8, 140, 0.0), (0.68, 110, 0.4), (0.56, 86, 0.8))):
            jitter = self.wr[6 + row, idx] - 0.5
            spike = np.clip(np.cos(ang * nn + sh + jitter * 3.0), 0, 1) ** 6
            length = 0.09 + 0.07 * self.wr[9 + row, idx]
            teeth += spike * smooth((rw - (r1 - length)) / 0.02) * (1 - smooth((rw - r1) / 0.015)) * (1 - 0.25 * row)
        throat = 1 - smooth((rw - 0.1) / 0.45)
        col = np.array([96, 60, 34], np.float32) * (0.55 + 0.6 * tex)[..., None] * seg_rings[..., None] * (0.35 + 0.75 * lip)[..., None]
        col = col * (1 - lip[..., None]) * 0.5 + col * lip[..., None]
        col = col + np.clip(teeth, 0, 1)[..., None] * np.array([150, 116, 80], np.float32) * (1 - lip)[..., None]
        col = col * (1 - throat[..., None] * 0.94)
        light = np.clip((dy * 0.6 - dx * 0.3) / (R * 1.2) + 0.2, 0, 1) * lip
        col = col + light[..., None] * np.array([110, 62, 26], np.float32)
        img = img * (1 - body[..., None]) + col * body[..., None]
        # dust hangs in front of it
        haze = blur(body, 30) * 0.35
        img = img * (1 - haze[..., None]) + haze[..., None] * np.array([150, 86, 40], np.float32)
        return img, cy

    def frame(self, k):
        img = self.sky.copy()
        # haze bands drifting (loops: the wind texture tiles over 2W)
        w = np.roll(self.wind, -int(round(2 * W * k / N)), axis=1)[:, :W]
        img += (w ** 2 * smooth((self.yy - 300) / 260))[..., None] * np.array([70, 40, 20], np.float32) * 0.6
        rise = seg(k, *self.T_RISE) * (1 - seg(k, *self.T_SINK))
        mcy = None
        if rise > 0:
            img, mcy = self.mouth(img, k, rise)
        # worm sign: the bump runs left to right under the middle dune
        bx = None; bump = 0.0
        if self.T_SIGN[0] <= k <= self.T_SIGN[1]:
            u = (k - self.T_SIGN[0]) / (self.T_SIGN[1] - self.T_SIGN[0])
            bx = -100 + u * (self.cx + 100)
            bump = math.sin(math.pi * min(1.0, u * 1.1)) * (1 - seg(k, 96, 110))
        img = self.dunes(img, k, bx, bump)
        # sand: spray behind the bump, pouring off the mouth, the burst as it sinks
        sp = np.zeros((H, W), np.float32)
        P = self.parts
        if bx is not None and bump > 0.05:
            for i in range(0, 300):
                age = (P[i, 0] * 18)
                x = bx - age * 6 + (P[i, 1] - 0.5) * 60
                ridge = self.ridges[1][0][int(np.clip(x, 0, W - 1))] - bump * 40
                y = ridge - (P[i, 2] * 50) * math.sin(math.pi * min(1, age / 18)) * bump
                if 0 <= x < W and 0 <= y < H:
                    sp[int(y), int(x)] += 0.6 * (1 - age / 18)
        if mcy is not None and rise > 0.2:
            for i in range(300, 700):
                a = P[i, 0] * math.pi + math.pi            # the upper rim
                x = self.mcx + math.cos(a) * self.mR * 0.98
                y0 = mcy + math.sin(a) * self.mR * 0.93
                fall = ((P[i, 1] + k * 0.035) % 1.0) * 180
                y = y0 + fall + (P[i, 2] - 0.5) * 6
                x += (P[i, 3] - 0.5) * 10 + fall * 0.05
                if 0 <= x < W and 0 <= y < H:
                    sp[int(y), int(x)] += 0.7 * rise
        burst = seg(k, self.T_SINK[0], self.T_SINK[0] + 6) * (1 - seg(k, self.T_SINK[0] + 10, self.T_SINK[1] + 20))
        if burst > 0:
            for i in range(700, 900):
                t = (k - self.T_SINK[0]) / 30.0
                a = P[i, 0] * math.pi + math.pi
                v = 120 + P[i, 1] * 260
                x = self.mcx + math.cos(a) * v * t * 1.4
                y = 520 + math.sin(a) * v * t + 90 * t * t
                if 0 <= x < W and 0 <= y < H:
                    sp[int(y), int(x)] += 1.0 * burst
        sp = blur(sp, 1.2) * 3 + blur(sp, 4) * 3
        img += np.clip(sp, 0, 1.2)[..., None] * np.array([200, 140, 84], np.float32) * 0.45
        dust = burst * 0.5 + rise * 0.1
        cloud = np.clip(blur(sp, 24) * 40, 0, 1) * dust
        img = img * (1 - cloud[..., None] * 0.6) + cloud[..., None] * 0.6 * np.array([170, 104, 52], np.float32)
        img = self.title(img, light=0.15 + 0.25 * burst, glint=0.25 + 0.25 * math.sin(2 * math.pi * k / N) ** 2,
                         lightpos=(W * 0.5, H * 0.66))
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([240, 214, 190], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img *= (1 - 0.4 * np.clip(rr - 0.45, 0, 1))[..., None]
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


MODES = {"eclipse": Eclipse, "worm": Worm}


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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "eclipse"
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
