"""John Wick card: idents with the title on screen for the whole hover.

modes
  neon  the JOHN WICK neon of Chapter 4 in the Parabellum colours (blue, violet, magenta) on a dark violet ground,
        haze drifting in its light. The sign hums; WICK stutters once; later the power sags and the tubes strike
        back on with the neon flicker; the camera breathes slowly in and out.
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
    """the Chapter 4 neon title, recoloured to the Parabellum palette (blue through violet to magenta), on a dark
    violet ground with slow haze; the sign hums, WICK stutters once, later the power sags and the tubes strike back."""
    T_STUTTER = (40, 54)
    T_SAG = (122, 138)
    T_STRIKE = (138, 160)

    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        a = np.asarray(Image.open(os.path.join(src, "neon.png")).convert("RGBA"), np.float32)
        a = a[:1050]                                                        # the CHAPTER 4 line is left out
        lw = 840; s = lw / a.shape[1]; lh = round(a.shape[0] * s)
        a = cv2.resize(a, (lw, lh), interpolation=cv2.INTER_AREA)
        self.top = 300 - lh // 2 - 26
        x0 = (W - lw) // 2
        al = np.zeros((H, W), np.float32); rgb = np.zeros((H, W, 3), np.float32)
        al[self.top:self.top + lh, x0:x0 + lw] = a[..., 3] / 255
        rgb[self.top:self.top + lh, x0:x0 + lw] = a[..., :3]
        pm = rgb * al[..., None]
        inten = pm.max(2) / 255                                             # how bright the original neon is here
        core = smooth((pm[..., 1] / 255 - 0.42) / 0.4)                      # the yellow-white heart of the tubes
        # Parabellum palette across the title: blue, violet, magenta
        u = np.clip((xx - x0) / lw, 0, 1)
        stops = np.array([0.0, 0.5, 1.0]); cols = np.array([[70, 110, 255], [150, 86, 255], [255, 70, 196]], np.float32)
        grad = np.stack([np.interp(u, stops, cols[:, c]) for c in range(3)], -1).astype(np.float32)
        self.grad = grad
        self.lit = grad * (inten ** 1.5)[..., None] * 1.05 + core[..., None] * np.array([235, 225, 255], np.float32) * 0.85
        self.tube = smooth((inten - 0.55) / 0.3) * core.clip(0.3, 1)
        self.x0, self.lw, self.lh = x0, lw, lh
        # word masks (JOHN | WICK) for the stutter: the gap between the words in the original (x 1642..1664 of 3218),
        # slanted like the italic
        split = x0 + 1653 * s
        midy = self.top + lh / 2
        self.wick = blur(smooth((xx - split + 0.2 * (yy - midy)) / 6), 4)
        sub = text_layer(os.path.join(src, "BarlowCondensed-Medium.ttf"), 60, "THE COLLECTION", 34, shear=0.2)
        self.sub = put(sub, W / 2, self.top + lh + 16)
        # the room: dark violet, a little lighter behind the sign; haze that drifts and loops
        d = np.sqrt(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - self.top - lh / 2) / (H * 0.5)) ** 2)
        self.room = (np.array([9, 6, 20], np.float32) + np.exp(-d * 1.6)[..., None] * np.array([26, 14, 52], np.float32))
        self.haze = noise(H, 2 * W, 1.6, 21)
        self.haze2 = noise(H, 2 * W, 1.3, 22)

    def level(self, k):
        """(JOHN, WICK) brightness"""
        hum = 0.985 + 0.015 * math.sin(2 * math.pi * 7 * k / N)
        j = w = 1.0
        if self.T_STUTTER[0] <= k < self.T_STUTTER[1]:
            w = [1, 0.25, 1, 1, 0.1, 0.1, 0.9, 1, 0.35, 1, 1, 1, 0.6, 1][k - self.T_STUTTER[0]]
        if self.T_SAG[0] <= k < self.T_STRIKE[1]:
            if k < self.T_SAG[1]:
                v = 1 - 0.8 * seg(k, self.T_SAG[0], self.T_SAG[1])
            else:
                dt = k - self.T_STRIKE[0]
                pat = [0.2, 0.2, 0.9, 0.25, 0.25, 1.0, 0.5, 1.0, 1.0, 0.8, 1.0]
                v = pat[dt] if dt < len(pat) else 0.2 + 0.8 * seg(k, self.T_STRIKE[0] + len(pat), self.T_STRIKE[1])
                v = max(v, 0.2)
            j *= v; w *= v
        return j * hum, w * hum

    def drift(self, tex, k, v):
        t = k / N
        a = np.roll(tex, -int(round(v * k)), axis=1)[:, :W]
        b = np.roll(tex, -int(round(v * k - v * N)), axis=1)[:, :W]
        m = float(tex.mean())
        return np.clip(m + ((1 - t) * a + t * b - m) / math.sqrt((1 - t) ** 2 + t ** 2), 0, 1)

    def frame(self, k):
        jl, wl = self.level(k)
        f = jl * (1 - self.wick) + wl * self.wick
        lit = self.lit * f[..., None]
        glow = blur(lit, 14) * 0.45 + blur(lit, 46) * 0.6 + blur(lit, 120) * 0.5
        img = self.room.copy() + glow * 0.8
        # haze in the light of the sign
        hz = self.drift(self.haze, k, 1.2) * 0.6 + self.drift(self.haze2, k, -0.8) * 0.4
        lightc = blur(lit, 90) * 2.2 + 6
        img += (np.clip(hz - 0.35, 0, 1) * 0.9)[..., None] * lightc * 0.6
        # glass tubes, faint when the power sags
        dark = np.clip(1 - f, 0, 1)
        img = img * (1 - (self.tube * 0.6 * dark)[..., None]) + (self.tube * dark)[..., None] * np.array([40, 30, 58], np.float32)
        img += lit
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([228, 222, 246], np.float32) * (0.85 + 0.15 * (jl + wl) / 2)
        # a slow push in and back
        z = 1 + 0.03 * (1 - math.cos(2 * math.pi * k / N)) / 2
        M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
        img = cv2.warpAffine(img.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.5 * np.clip(rr - 0.4, 0, 1))[..., None]
        g = np.random.default_rng(700 + k).normal(size=(H, W)).astype(np.float32) * 2.0        # a little film grain
        img += g[..., None]
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
