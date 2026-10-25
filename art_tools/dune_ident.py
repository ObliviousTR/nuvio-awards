"""Dune card: the copper DUNE title of the Villeneuve films (with the glint on the E), on screen for the whole hover.

modes
  eclipse  the eclipse of the Dune posters: a black moon holds the sun behind U and N, a gold ring of fire round it,
           the corona's rays turning slowly. The moon sinks a little, the sun's upper edge breaks out above the title
           and lights the copper letters from above, then the moon comes back - a diamond-ring flash as it closes, the glint on the E flares -
           and the ring settles. THE COLLECTION sits inside the moon, under the title.
  worm     dusk over the deep desert, the title in the sky over the dunes, sand blowing. Worm sign: a plume of sand
           runs in under the dunes towards the middle, then the sandworm rises behind the title - its open mouth in
           the storm, from the Part Two still, the dust in it boiling - sand pouring off it, and it sinks back in a
           cloud of sand.
All modes: 250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/dune_ident.py SRC_DIR OUT_DIR --mode eclipse|worm [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (the Dune (2021) title logo on TMDB, copper with the glint), Montserrat-VF.ttf,
           worm_plate.jpg (worm mode: a Dune: Part Two backdrop on TMDB, cropped, the ornithopter painted out)
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
        dm = np.sqrt((self.xx - self.cx) ** 2 + (self.yy - self.cy - dx) ** 2)      # the moon drifts down: the sun breaks out above the title
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
        bloom = blur(vis, 22) * 2.0 + blur(vis, 70) * 2.0
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
                bx, by = self.cx, self.cy - R * 0.99 * side
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
        img = self.title(img, light=min(1.0, frac * 3), glint=gl, lightpos=(self.cx, self.cy - R))
        img += (blur(self.la, 6) * (0.35 * tot + 0.8 * min(1.0, frac * 3)))[..., None] * GOLD * 0.35
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([228, 196, 172], np.float32)
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


class Worm(Base):
    T_SIGN = (26, 100)     # a sand trail runs in towards the middle under the dunes
    T_RISE = (96, 150)     # the worm rises behind the title
    T_SINK = (176, 214)    # and goes back down

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
        self.parts = rng.uniform(0, 1, (900, 4)).astype(np.float32)
        # the worm: the Part Two still of its open mouth in the sand storm (TMDB backdrop), graded into the dusk
        pl = np.asarray(Image.open(os.path.join(src, "worm_plate.jpg")).convert("RGB"), np.float32)
        pw = 900; ph = round(pl.shape[0] * pw / pl.shape[1])
        pl = cv2.resize(pl, (pw, ph), interpolation=cv2.INTER_AREA)
        v, u = np.mgrid[0:ph, 0:pw].astype(np.float32)
        u /= pw; v /= ph
        r = np.sqrt(((u - 0.51) / 0.47) ** 2 + ((v - 0.47) / 0.52) ** 2)
        al = 1 - smooth((r - 0.78) / 0.24)
        al *= 1 - smooth((0.36 - np.sqrt(((u - 0.18) / 0.22) ** 2 + ((v - 0.1) / 0.17) ** 2)) / 0.3)   # the patched corner
        al *= smooth(v / 0.07)                                           # no hard top edge while it rises
        # the still is used as light and shade only: how much darker (the worm) or brighter (dust) than the haze
        lum = pl @ np.array([0.3, 0.55, 0.15], np.float32)
        haze = float(np.percentile(lum[(r > 0.8) & (r < 1.0)], 55))
        self.plate = np.clip(lum / haze, 0.04, 1.3).astype(np.float32)
        self.pal = al.astype(np.float32)
        self.pw, self.ph = pw, ph
        self.maw = (0.51 * pw, 0.47 * ph)
        self.boil = noise(ph, pw, 1.6, 41), noise(ph, pw, 1.6, 42)

    def dunes(self, img):
        for i, (y, col) in enumerate(self.ridges):
            m = smooth((self.yy - y[None, :]) / 1.5)
            shade = np.clip((self.yy - y[None, :]) / 140, 0, 1)
            lit = np.exp(-np.maximum(self.yy - y[None, :], 0) / 5) * 0.8
            c = col * (1.0 - 0.45 * shade[..., None]) + lit[..., None] * np.array([150, 90, 40], np.float32)
            c *= (0.92 + 0.16 * self.grain)[..., None]
            img = img * (1 - m[..., None]) + c * m[..., None]
        return img

    def offset(self, k):
        """how far below its resting place the worm is (px): rises with weight, creeps, sinks"""
        rise = seg(k, *self.T_RISE); sink = seg(k, *self.T_SINK)
        creep = 18 * seg(k, self.T_RISE[1], self.T_SINK[0])
        return 520 * (1 - rise) - creep + (520 + creep) * sink, rise * (1 - sink)

    def frame(self, k):
        img = self.sky.copy()
        w = np.roll(self.wind, -int(round(2 * W * k / N)), axis=1)[:, :W]
        img += (w ** 2 * smooth((self.yy - 300) / 260))[..., None] * np.array([70, 40, 20], np.float32) * 0.6
        off, up = self.offset(k)
        sx = self.cx - self.maw[0]; sy = self.cy + 30 - self.maw[1] + off
        if up > 0.001:
            # dust boiling in the still: a slow displacement that moves with the frame
            b1, b2 = self.boil
            ph = 2 * math.pi * k / N
            dxm = (np.sin(b1 * 12 + ph * 3) * 2.5).astype(np.float32)
            dym = (np.cos(b2 * 12 + ph * 3) * 2.5 - 1.0).astype(np.float32)
            v, u = np.mgrid[0:self.ph, 0:self.pw].astype(np.float32)
            pl = cv2.remap(self.plate, u + dxm, v + dym, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            M = np.float32([[1, 0, sx], [0, 1, sy]])
            ratio = cv2.warpAffine(pl, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=1.0)
            pa = cv2.warpAffine(self.pal, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
            pa *= min(1.0, up * 1.6)
            shade = 1 + (ratio ** 1.15 - 1) * pa * 0.88                      # some haze stays in front of it
            img = img * shade[..., None]
        # the trail: a plume of sand running in under the dunes towards the middle
        sp = np.zeros((H, W), np.float32)
        P = self.parts
        if self.T_SIGN[0] <= k <= self.T_SIGN[1] + 10:
            u_ = (k - self.T_SIGN[0]) / (self.T_SIGN[1] - self.T_SIGN[0])
            hx = -60 + min(1.0, u_) * (self.cx + 60)
            fade = 1 - seg(k, self.T_SIGN[1] - 6, self.T_SIGN[1] + 10)
            for i in range(0, 320):
                age = P[i, 0]
                x = hx - age * 160 + (P[i, 1] - 0.5) * 30
                if not (0 <= x < W):
                    continue
                ridge = self.ridges[0][0][int(x)]
                y = ridge - (P[i, 2] ** 1.5) * 34 * (1 - age) - age * 6 + 4
                if 0 <= y < H:
                    sp[int(y), int(x)] += 0.55 * (1 - age) * fade
        # sand pouring off the worm while it is up, a heavy fall as it sinks
        if up > 0.2:
            R = 0.42 * self.pw
            for i in range(320, 720):
                a = math.pi + P[i, 0] * math.pi
                x = self.cx + math.cos(a) * R * (0.92 + 0.08 * P[i, 3])
                y0 = self.cy + 30 + math.sin(a) * R * 1.05 + off
                fall = ((P[i, 1] + k * 0.02) % 1.0) * 260
                y = y0 + fall
                x += (P[i, 2] - 0.5) * 8 + fall * 0.04 * math.cos(a)
                if 0 <= x < W and 0 <= y < H:
                    sp[int(y), int(x)] += 0.45 * up * (1 - fall / 300)
        sink = seg(k, self.T_SINK[0], self.T_SINK[0] + 8) * (1 - seg(k, self.T_SINK[0] + 14, self.T_SINK[1] + 24))
        rise_dust = math.sin(math.pi * seg(k, self.T_RISE[0], self.T_RISE[1] + 20)) if k < self.T_RISE[1] + 20 else 0.0
        img = self.dunes(img)
        sp = blur(sp, 0.9) * 2.5 + blur(sp, 3) * 2.0
        img += np.clip(sp, 0, 1)[..., None] * np.array([200, 140, 84], np.float32) * 0.5
        # dust clouds where it breaks the surface (rising) and where it goes down (sinking)
        cloud_n = np.roll(self.wind, int(k * 3), axis=1)[:, :W]
        band = np.exp(-((self.yy - 505) / 60) ** 2) * np.exp(-((self.xx - self.cx) / 380) ** 2)
        dust = np.clip(band * (0.6 + 0.8 * cloud_n), 0, 1) * (0.55 * rise_dust + 0.75 * sink)
        img = img * (1 - dust[..., None] * 0.7) + dust[..., None] * 0.7 * np.array([168, 102, 50], np.float32)
        img = self.title(img, light=0.15 + 0.15 * sink, glint=0.25 + 0.25 * math.sin(2 * math.pi * k / N) ** 2,
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
