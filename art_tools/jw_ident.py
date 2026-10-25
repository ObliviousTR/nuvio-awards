"""John Wick card: idents with the title on screen for the whole hover.

modes
  neon  the JOHN WICK neon of Chapter 4 as a sign over a wet street at night, rain falling, the sign's light on the
        rain and in the puddles below. The power dips and the letters come back one by one, buzzing; muzzle flashes
        from a fight off screen light the street in red bursts, a round hits the sign and the I shorts out in sparks
        and comes back; the red light of the Chapter 4 title sweeps across, and the sign hums on.
  coin  the JOHN WICK title in brushed gold on black. A Continental gold coin spins through the dark behind it,
        catching the light, drops and wobbles flat behind the title, its lion lit by a sweep of light, then sinks
        back into the dark.
Both: 250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/jw_ident.py SRC_DIR OUT_DIR --mode neon|coin [--frames a,b] [--mp4 path]
  SRC_DIR: neon.png (the Chapter 4 neon title logo on TMDB), solid.svg (the Chapter 4 title logo, vector, for the
           letter shapes), title_2014.png (the John Wick title logo on TMDB), coin.jpg (a photo of the Continental
           coin replica), BarlowCondensed-Medium.ttf, cinzel.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
NEON = np.array([255, 120, 30], np.float32)
RED = np.array([255, 40, 20], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / max(1, b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta; spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


def text_layer(font, size, txt, track, shear=0.0, var=None):
    f = ImageFont.truetype(font, size)
    if var:
        f.set_variation_by_axes(var)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 80, size * 2), 0)
    d = ImageDraw.Draw(m); x = 40
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    if shear:
        m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * m.height * 0.75, 0, 1, 0), Image.BICUBIC)
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def put(layer, cx, top):
    out = np.zeros((H, W), np.float32)
    h, w = layer.shape
    x0 = int(round(cx - w / 2))
    out[top:top + h, x0:x0 + w] = layer
    return out


def make_rain(seed=9, count=1300):
    rng = np.random.default_rng(seed)
    lay = np.zeros((H, W), np.float32)
    for _ in range(count):
        x, y = rng.uniform(0, W), rng.uniform(0, H); L = rng.uniform(12, 30); b = rng.uniform(0.25, 1)
        for dx in (-W, 0, W):
            for dy in (-H, 0, H):
                p0 = (x + dx, y + dy); p1 = (x + dx - L * 0.12, y + dy + L)
                cv2.line(lay, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), b, 1, cv2.LINE_AA, 2)
    return lay


class Neon:
    LETTERS = 8                                  # J O H N W I C K
    T_DIP = (18, 28)
    T_RELIGHT = (30, 84)
    T_FIGHT = (92, 160)
    T_HIT = 126
    HIT_LETTER = 5                               # the I
    T_SWEEP = (168, 198)

    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        a = np.asarray(Image.open(os.path.join(src, "neon.png")).convert("RGBA"), np.float32)
        a = a[:1050]                                                        # the CHAPTER 4 line is left out
        lw = 860; s = lw / a.shape[1]; lh = round(a.shape[0] * s)
        a = cv2.resize(a, (lw, lh), interpolation=cv2.INTER_AREA)
        self.top = 236 - lh // 2
        x0 = (W - lw) // 2
        self.neon = np.zeros((H, W, 3), np.float32); self.na = np.zeros((H, W), np.float32)
        self.neon[self.top:self.top + lh, x0:x0 + lw] = a[..., :3]
        self.na[self.top:self.top + lh, x0:x0 + lw] = a[..., 3] / 255
        lum = self.neon.max(2) * self.na
        self.tube = smooth((lum - 170) / 60)                                 # the glass tubes
        # letter shapes from the vector logo, fitted onto the tubes by their bounding boxes
        import cairosvg
        from io import BytesIO
        sv = Image.open(BytesIO(cairosvg.svg2png(url=os.path.join(src, "solid.svg"), output_width=3000))).getchannel("A")
        sa = np.asarray(sv, np.float32) / 255
        n, lab, st, cen = cv2.connectedComponentsWithStats((sa > 0.5).astype(np.uint8))
        rows = [i for i in range(1, n) if st[i][1] < sa.shape[0] * 0.6 and st[i][4] > 1000]
        rows.sort(key=lambda i: st[i][0])
        sx0 = min(st[i][0] for i in rows); sx1 = max(st[i][0] + st[i][2] for i in rows)
        sy0 = min(st[i][1] for i in rows); sy1 = max(st[i][1] + st[i][3] for i in rows)
        ys, xs = np.where(self.tube > 0.5)
        tx0, tx1, ty0, ty1 = xs.min(), xs.max(), ys.min(), ys.max()
        M = np.float32([[(tx1 - tx0) / (sx1 - sx0), 0, tx0 - sx0 * (tx1 - tx0) / (sx1 - sx0)],
                        [0, (ty1 - ty0) / (sy1 - sy0), ty0 - sy0 * (ty1 - ty0) / (sy1 - sy0)]])
        self.w = []
        for i in rows:
            li = cv2.warpAffine((lab == i).astype(np.float32), M, (W, H))
            self.w.append(blur(cv2.dilate(li, np.ones((9, 9), np.uint8)), 10) + 1e-4)
        self.wsum = sum(self.w)
        self.letter_c = [((cv2.warpAffine((lab == i).astype(np.float32), M, (W, H)) * self.xx).sum()
                          / max(1, cv2.warpAffine((lab == i).astype(np.float32), M, (W, H)).sum())) for i in rows]
        self.mid_y = (ty0 + ty1) / 2
        sub = text_layer(os.path.join(src, "BarlowCondensed-Medium.ttf"), 64, "THE COLLECTION", 34, shear=0.2)
        self.sub = put(sub, W / 2, self.top + lh + 18)
        # the street: bokeh, a wet ground, rain
        rng = np.random.default_rng(5)
        bk = np.zeros((H, W, 3), np.float32)
        for _ in range(60):
            x, y = rng.uniform(0, W), rng.uniform(H * 0.25, H * 0.7)
            r = rng.uniform(6, 22); c = [np.array([255, 120, 40]), np.array([255, 60, 40]), np.array([80, 120, 255]),
                                       np.array([255, 200, 120])][rng.integers(0, 4)] * rng.uniform(0.15, 0.5)
            cv2.circle(bk, (int(x), int(y)), int(r), c.tolist(), -1, cv2.LINE_AA)
        self.bokeh = blur(bk, 5)
        self.horizon = 512
        self.rain = make_rain()
        self.ripple = noise(256, 2 * W, 1.1, 7)
        self.puddle = noise(H, W, 1.5, 8)
        rng = np.random.default_rng(11)
        # the gunfight: flashes from left and right off screen
        self.flashes = []
        k = self.T_FIGHT[0]
        while k < self.T_FIGHT[1]:
            self.flashes.append((k, rng.choice([-1, 1]), rng.uniform(0.5, 1.0)))
            k += int(rng.choice([2, 3, 3, 5, 9, 14]))
        self.sparks = rng.uniform(0, 1, (160, 4)).astype(np.float32)

    def letters(self, k):
        """brightness of each letter at frame k"""
        b = np.ones(self.LETTERS)
        rng = np.random.default_rng(900 + k)
        if self.T_DIP[0] <= k < self.T_RELIGHT[0]:
            b[:] = [0.15, 0.7, 0.0, 0.0, 0.0, 0.0][min(5, k - self.T_DIP[0])] if k - self.T_DIP[0] < 6 else 0.0
        if self.T_RELIGHT[0] <= k < self.T_RELIGHT[1]:
            span = self.T_RELIGHT[1] - self.T_RELIGHT[0]
            for i in range(self.LETTERS):
                t0 = self.T_RELIGHT[0] + i * span / self.LETTERS
                dt = k - t0
                if dt < 0:
                    b[i] = 0.0
                elif dt < 5:
                    b[i] = [0.9, 0.1, 0.0, 1.0, 0.3][int(dt)]                 # the stutter as a tube strikes
                else:
                    b[i] = 1.0
        if self.T_HIT <= k < self.T_HIT + 26:
            dt = k - self.T_HIT
            b[self.HIT_LETTER] = 0.0 if dt < 18 else (1.0 if dt % 3 else 0.2)
            if dt < 18 and rng.random() < 0.25:
                b[self.HIT_LETTER] = 0.6
        b *= 0.97 + 0.03 * math.sin(k * 1.7)                                # mains hum
        return b

    def frame(self, k):
        b = self.letters(k)
        f = sum(wi * bi for wi, bi in zip(self.w, b)) / self.wsum
        lit = self.neon * (self.na * f)[..., None]
        glow = blur(lit, 18) * 0.9 + blur(lit, 60) * 0.9
        level = float(np.mean(b))
        img = np.zeros((H, W, 3), np.float32) + np.array([6, 7, 10], np.float32)
        img += self.bokeh * (0.6 + 0.2 * level)
        img += glow * 0.28
        # muzzle flashes
        fl = 0.0; side = 1
        for kf, sd, st in self.flashes:
            if 0 <= k - kf < 2:
                fl = max(fl, st * (1.0 if k == kf else 0.35)); side = sd
        if fl > 0:
            lx = W + 60 if side > 0 else -60
            L = np.exp(-np.abs(self.xx - lx) / 520) * (0.6 + 0.4 * smooth((self.yy - 200) / 400))
            img += (L * fl)[..., None] * np.array([255, 120, 50], np.float32) * 0.9
        # the hit: sparks spraying from the I
        if self.T_HIT <= k < self.T_HIT + 22:
            dt = k - self.T_HIT
            sp = np.zeros((H, W), np.float32)
            cx = self.letter_c[self.HIT_LETTER]; cy = self.mid_y - 30
            for (a0, v, life, j) in self.sparks:
                t = dt / (8 + 14 * life)
                if t > 1:
                    continue
                ang = -math.pi * (0.1 + 0.8 * a0)
                vx, vy = math.cos(ang) * (60 + 220 * v), math.sin(ang) * (60 + 220 * v)
                x = cx + vx * t * 0.6; y = cy + vy * t * 0.6 + 260 * t * t
                x2 = x - vx * 0.03; y2 = y - (vy + 520 * t) * 0.03
                cv2.line(sp, (int(x * 4), int(y * 4)), (int(x2 * 4), int(y2 * 4)), float(1 - t), 1, cv2.LINE_AA, 2)
            img += (sp * 1.4)[..., None] * np.array([255, 210, 140], np.float32) + blur(sp, 4)[..., None] * NEON * 1.2
            if dt < 3:
                img += (np.exp(-((self.xx - cx) ** 2 + (self.yy - cy) ** 2) / (2 * 30.0 ** 2)) * (1 - dt / 3) * 2)[..., None] * np.array([255, 220, 170], np.float32)
        # the sign: dark glass where it is off, lit neon where it is on
        unlit = (self.tube * (1 - f))[..., None] * np.array([46, 30, 26], np.float32)
        img = img * (1 - (self.tube * 0.85)[..., None]) + unlit + lit
        # the wet street: the sign mirrored in the puddles, broken by rain
        gh = H - self.horizon
        rip = np.roll(self.ripple, -int(k * 4), axis=1)[:, :W]
        rip = cv2.resize(rip, (W, gh))
        src_y = (2 * self.horizon - self.yy[self.horizon:] - 30).astype(np.float32)
        src_x = (self.xx[self.horizon:] + (rip - 0.5) * 14).astype(np.float32)
        refl = cv2.remap((img + glow * 0.4).astype(np.float32), src_x, src_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        refl = cv2.blur(blur(refl, 1.5), (3, 29))                           # wet asphalt smears it downwards
        wet = (0.45 + 0.35 * smooth((self.puddle[self.horizon:] - 0.4) / 0.25))[..., None]
        fade = np.exp(-(self.yy[self.horizon:] - self.horizon) / 160)[..., None]
        ground = np.array([10, 10, 12], np.float32) + refl * wet * fade * 0.8
        ground += (fl * 0.4 * np.exp(-(self.yy[self.horizon:] - self.horizon) / 120))[..., None] * np.array([120, 50, 20], np.float32)
        bl = smooth((self.yy[self.horizon:] - self.horizon) / 14)[..., None]
        img[self.horizon:] = img[self.horizon:] * (1 - bl) * 0.6 + ground * bl + ground * (1 - bl) * 0.4
        # rain, lit by the sign and the flashes
        r = np.roll(np.roll(self.rain, (k * 9 * H // N) % H, axis=0), (-k * W // N) % W, axis=1)
        light = 0.2 + blur(f * self.na, 50) * 3 * level + fl * 0.8
        img += (r * light)[..., None] * np.array([200, 150, 120], np.float32) * 0.45
        # the Chapter 4 red light: a hot line sweeping left to right behind and across the title
        if self.T_SWEEP[0] <= k <= self.T_SWEEP[1]:
            u = (k - self.T_SWEEP[0]) / (self.T_SWEEP[1] - self.T_SWEEP[0])
            sx = -200 + u * (W + 400)
            amp = math.sin(math.pi * u)
            line = np.exp(-((self.yy - self.mid_y) / 3.0) ** 2) * np.exp(-np.abs(self.xx - sx) / 420)
            core = np.exp(-((self.xx - sx) ** 2 / (2 * 60.0 ** 2) + (self.yy - self.mid_y) ** 2 / (2 * 40.0 ** 2)))
            img += ((line * 1.6 + blur(line, 6) * 1.2 + core * 0.9) * amp)[..., None] * RED
            img += (core * amp * 0.6)[..., None] * np.array([255, 200, 150], np.float32)
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([236, 236, 236], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img *= (1 - 0.45 * np.clip(rr - 0.45, 0, 1))[..., None]
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


class Coin:
    T_FLY = (26, 112)       # spinning through the dark behind the title
    T_SETTLE = (112, 150)   # wobbling down flat
    T_SWEEP = (150, 186)
    T_GONE = (196, 232)

    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        lg = Image.open(os.path.join(src, "title_2014.png")).getchannel("A")
        lw = 760; lh = round(lg.height * lw / lg.width)
        a = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.top = 300 - lh // 2
        self.la = put(a, W / 2, self.top)
        m = (self.la > 0.5).astype(np.uint8)
        bw = 3.5
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        hg = blur(smooth(dt / bw).astype(np.float32), 0.6)
        gx = cv2.Sobel(hg, cv2.CV_32F, 1, 0, ksize=3) / 8 * bw; gy = cv2.Sobel(hg, cv2.CV_32F, 0, 1, ksize=3) / 8 * bw
        n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
        self.n = n
        g = np.clip((yy - self.top) / lh, 0, 1)[..., None]
        self.gold = np.array([246, 214, 140], np.float32) * (1 - g) + np.array([168, 118, 52], np.float32) * g
        rng = np.random.default_rng(2)
        br = cv2.GaussianBlur(rng.normal(size=(H, W)).astype(np.float32), (0, 0), sigmaX=22, sigmaY=0.6)
        self.brush = 1 + 0.06 * br / (np.abs(br).max() + 1e-6)
        sub = text_layer(os.path.join(src, "cinzel.ttf"), 44, "THE COLLECTION", 22)
        self.sub = put(sub, W / 2, self.top + lh + 30)
        # the coin: cut from the photo by its rim
        c = np.asarray(Image.open(os.path.join(src, "coin.jpg")).convert("RGB"), np.float32)
        lum = c.mean(2)
        mask = (lum > 60).astype(np.uint8)
        mask[int(c.shape[0] * 0.87):] = 0                                     # the caption under it
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cmax = max(cs, key=cv2.contourArea)
        (ccx, ccy), cr = cv2.minEnclosingCircle(cmax)
        cr *= 0.985
        R = 170
        x0, y0 = int(ccx - cr), int(ccy - cr)
        crop = c[max(0, y0):int(ccy + cr), max(0, x0):int(ccx + cr)]
        crop = cv2.resize(crop, (2 * R, 2 * R), interpolation=cv2.INTER_AREA)
        v, u = np.mgrid[0:2 * R, 0:2 * R].astype(np.float32)
        d = np.sqrt((u - R) ** 2 + (v - R) ** 2)
        self.coin = crop; self.calpha = smooth((R - d) / 1.5); self.R = R
        self.dust = noise(H, W, 1.6, 4)

    def coin_state(self, k):
        """centre, scale, spin angle (rad, around the vertical axis), tilt flatness, visibility"""
        if k < self.T_FLY[0] or k >= self.T_GONE[1]:
            return None
        if k < self.T_FLY[1]:
            u = (k - self.T_FLY[0]) / (self.T_FLY[1] - self.T_FLY[0])
            x = -120 + u * (W / 2 + 120) + 140 * math.sin(u * math.pi) * (1 - u)
            y = 120 + 180 * u - 160 * math.sin(u * math.pi)
            spin = u * 10 * math.pi
            return x, y + 20, 0.55 + 0.45 * u, spin, 1.0
        if k < self.T_SETTLE[1]:
            u = (k - self.T_SETTLE[0]) / (self.T_SETTLE[1] - self.T_SETTLE[0])
            spin = 10 * math.pi + 0.45 * math.pi * (1 - u) ** 2 * math.cos(u * 14)     # wobbles down onto its face
            return W / 2, 320, 1.0, spin, 1.0
        vis = 1 - seg(k, *self.T_GONE)
        return W / 2, 320, 1.0 + 0.04 * seg(k, *self.T_GONE), 10 * math.pi, vis

    def frame(self, k):
        img = np.zeros((H, W, 3), np.float32) + np.array([7, 6, 5], np.float32)
        img += (self.dust ** 3)[..., None] * np.array([30, 22, 10], np.float32)
        st = self.coin_state(k)
        sweep = 0.0
        if self.T_SWEEP[0] <= k <= self.T_SWEEP[1]:
            sweep = (k - self.T_SWEEP[0]) / (self.T_SWEEP[1] - self.T_SWEEP[0])
        if st is not None:
            cx, cy, sc, spin, vis = st
            cw = abs(math.cos(spin))                                       # the coin turns edge-on and back
            face = math.cos(spin) >= 0
            R = self.R
            coin = self.coin if face else self.coin[:, ::-1] * 0.55             # the back: darker, mirrored
            sx = max(0.04, cw) * sc; sy = sc
            M = np.float32([[sx, 0, cx - R * sx], [0, sy, cy - R * sy]])
            cimg = cv2.warpAffine(coin, M, (W, H), flags=cv2.INTER_LINEAR)
            ca = cv2.warpAffine(self.calpha, M, (W, H), flags=cv2.INTER_LINEAR)
            # the edge of the coin when it is nearly edge-on
            edge = np.exp(-((self.xx - cx) / max(1.0, 3 * sc)) ** 2) * (np.abs(self.yy - cy) < R * sc) * (1 - cw) ** 4
            lightband = 0.6 + 0.8 * max(0.0, math.sin(spin * 2)) ** 8               # glints as it turns
            dim = 0.5 if k >= self.T_SETTLE[0] else 0.75
            if sweep > 0:
                sb = np.exp(-((self.xx - (cx - R + sweep * 2 * R) + (self.yy - cy) * 0.5) / 40) ** 2)
                cimg = cimg * (1 + 1.4 * sb[..., None] * math.sin(math.pi * sweep))
            img = img * (1 - (ca * vis)[..., None]) + cimg * (ca * vis * dim * lightband)[..., None]
            img += (edge * vis)[..., None] * np.array([200, 160, 80], np.float32)
            img += (blur(ca, 30) * vis * 0.25 * lightband)[..., None] * np.array([120, 80, 30], np.float32)
        # the title: brushed gold, lit from above; the light sweep crosses it too
        L = np.array([-0.3, -0.85, 0.45]); L /= np.linalg.norm(L)
        diff = np.clip(self.n @ L, 0, 1)
        face = self.gold * (0.45 + 0.75 * diff)[..., None] * self.brush[..., None]
        if sweep > 0:
            sxp = -100 + sweep * (W + 200)
            band = np.exp(-((self.xx - sxp + (self.yy - 300) * 0.5) / 50) ** 2) * math.sin(math.pi * sweep)
            face = face + band[..., None] * np.array([255, 230, 170], np.float32) * 0.8
        a = self.la[..., None]
        img = img * (1 - a) + face * a
        img += blur(self.la, 10)[..., None] * np.array([60, 40, 12], np.float32) * 0.3
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([214, 178, 108], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img *= (1 - 0.45 * np.clip(rr - 0.45, 0, 1))[..., None]
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


MODES = {"neon": Neon, "coin": Coin}


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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "neon"
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
