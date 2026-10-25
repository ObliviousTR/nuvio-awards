"""Godzilla & Kong card, the approved storm (gk_calm.py: gk_ident.py --mode storm with the title on its own plane and the
thunder shake) beat for beat, finished better:
- the bolts are real channels: a thick bright trunk that thins towards the ground, forks that fade, a hot core and a
  wide glow, and each flash lights the cloud base it comes out of;
- the clouds have volume: a flash lights their sides that face it and leaves the rest dark;
- the steel answers each flash with a glint along the bevels that face it;
- the rain has depth: a fine far layer and a sparse near layer, both lit by the flash;
- the charge after the last strike runs through the letters with fewer, softer arcs.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/gk_storm2.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]   (SRC_DIR as for gk_ident.py)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import gk_ident as gk
import gk_calm

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
smooth, seg, blur = gk.smooth, gk.seg, gk.blur
NAVY, CYAN, ICE = gk.NAVY, gk.CYAN, gk.ICE


def bigblur(a, s):
    h, w = a.shape[:2]
    sm = cv2.resize(a, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), s / 4)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)


def channel(canvas, pts, w0, w1, val, S):
    """Draw a path on a supersampled canvas with its width tapering from w0 to w1 (output pixels)."""
    n = len(pts) - 1
    for i in range(n):
        w = w0 + (w1 - w0) * i / max(1, n - 1)
        a = np.round(pts[i] * S).astype(int); b = np.round(pts[i + 1] * S).astype(int)
        cv2.line(canvas, tuple(a), tuple(b), val, max(1, int(round(w * S))), cv2.LINE_AA)


def bolt2(p0, p1, seed, branches=5, trunk=3.2):
    """A lightning channel: tapered trunk, fading forks and sub-forks. Returns the core at frame size."""
    S = 3
    rng = np.random.default_rng(seed)
    can = np.zeros((H * S, W * S), np.float32)
    main = gk.bolt_path(p0, p1, rng, 0.2, 7)
    total = np.linalg.norm(np.array(p1, float) - np.array(p0, float))
    for _ in range(branches):
        i = int(rng.uniform(0.12, 0.7) * len(main))
        d = main[min(i + 8, len(main) - 1)] - main[i]; d /= np.linalg.norm(d) + 1e-6
        ang = rng.choice([-1, 1]) * rng.uniform(0.35, 0.95)
        d = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang)])
        q = main[i] + d * total * rng.uniform(0.14, 0.34)
        br = gk.bolt_path(main[i], q, rng, 0.25, 5)
        f = 1 - i / len(main)
        channel(can, br, 1.5 * f + 0.6, 0.5, 0.42 + 0.25 * f, S)
        for _ in range(int(rng.integers(0, 3))):                         # sub-forks off the fork
            j = int(rng.uniform(0.2, 0.8) * len(br))
            e = br[min(j + 4, len(br) - 1)] - br[j]; e /= np.linalg.norm(e) + 1e-6
            a2 = rng.choice([-1, 1]) * rng.uniform(0.4, 1.0)
            e = np.array([e[0] * math.cos(a2) - e[1] * math.sin(a2), e[0] * math.sin(a2) + e[1] * math.cos(a2)])
            r2 = br[j] + e * total * rng.uniform(0.05, 0.12)
            channel(can, gk.bolt_path(br[j], r2, rng, 0.3, 4), 0.6, 0.4, 0.22, S)
    channel(can, main, trunk, trunk * 0.45, 1.0, S)
    return cv2.resize(can, (W, H), interpolation=cv2.INTER_AREA)


def make_rain_near(seed=19, count=170):
    rng = np.random.default_rng(seed)
    lay = np.zeros((H, W), np.float32)
    for _ in range(count):
        x, y = rng.uniform(0, W), rng.uniform(0, H); L = rng.uniform(60, 110); b = rng.uniform(0.3, 0.8)
        for dx in (-W, 0, W):
            for dy in (-H, 0, H):
                p0 = (x + dx, y + dy); p1 = (x + dx - L * 0.22, y + dy + L)
                cv2.line(lay, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), b, 2, cv2.LINE_AA, 2)
    return blur(lay, 1.3)


def near_at(rain, k):
    return np.roll(np.roll(rain, (k * 14 * H // N) % H, axis=0), (-k * 4 * W // N) % W, axis=1)


def normals(la):
    m = (la > 0.5).astype(np.uint8)
    bw = 4.5
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    hgt = blur(smooth(dt / bw).astype(np.float32), 0.7)
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8 * bw
    gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8 * bw
    n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n.astype(np.float32)


class Storm(gk_calm.Storm):
    def __init__(self, src):
        super().__init__(src)
        t = self.t
        self.bolts = [bolt2((x + 40, -20), (x - 30, ye), s, 5, 3.0 if ti else 2.2) for _, x, ye, s, _, ti in self.events]
        self.strike = bolt2((t.xm + 18, -20), (t.xm, t.xm_top + 4), 31, 4, 4.0)
        self.near = make_rain_near()
        self.bolt_top = [(x + 40) for _, x, *_ in self.events]

    def cloud_relief(self, cl, x, y):
        """How much of the cloud faces a flash at (x, y): the side of each billow towards it."""
        g = bigblur(cl, 14.0)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        dx = x - self.xx; dy = y - self.yy; d = np.sqrt(dx * dx + dy * dy) + 1e-3
        return np.clip(0.75 + 90.0 * (gx * dx + gy * dy) / d, 0.4, 1.4)

    def glint(self, flashes):
        """The steel catches each flash on the bevels that face it."""
        t = self.t
        n = normals(t.la)
        out = np.zeros((H, W), np.float32)
        for f, x, y in flashes:
            L = np.dstack([x - self.xx, y - self.yy, np.full_like(self.xx, 520.0)])
            L /= np.linalg.norm(L, axis=2, keepdims=True)
            Hh = L + np.array([0, 0, 1], np.float32); Hh /= np.linalg.norm(Hh, axis=2, keepdims=True)
            out += np.clip((n * Hh).sum(2), 0, 1) ** 60 * f
        return out * t.la

    def frame(self, k):
        self.place_title(k)
        im = self.storm_frame(k)
        sx, sy = self.shake(k)
        if abs(sx) + abs(sy) > 0.05:
            a = np.asarray(im, np.float32)
            a = cv2.warpAffine(a, np.float32([[1, 0, sx], [0, 1, sy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
            im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        return im

    def storm_frame(self, k):
        t = self.t
        c = gk.drift(self.cloud, k, 2.6); c2 = gk.drift(self.cloud2, k, 4.5)
        cl = np.clip(c * 0.75 + c2 * 0.35, 0, 1)
        sky = 1 - smooth((self.yy - H * 0.2) / (H * 0.9)) * 0.45
        img = NAVY + ((cl ** 1.5) * sky)[..., None] * np.array([44, 52, 70], np.float32)
        light = np.zeros((H, W), np.float32); amb = 0.0
        extra = np.zeros((H, W, 3), np.float32)
        sil = []; flashes = []; cores = np.zeros((H, W), np.float32)
        for (k0, x, ye, s, st, ti), bl, tt in zip(self.events, self.bolts, self.titans):
            f = self.flick(k, k0) * st
            if f <= 0:
                continue
            cy = H * 0.55 if tt else H * 0.2
            L = np.exp(-((self.xx - x) / (W * 0.24)) ** 2 - ((self.yy - cy) / (H * 0.5)) ** 2)
            base = np.exp(-((self.xx - (x + 40)) / (W * 0.16)) ** 2 - ((self.yy + 10) / (H * 0.22)) ** 2)   # the cloud it leaves
            light += f * (L * self.cloud_relief(cl, x, H * 0.25) + base * 1.4)
            amb += f * (0.2 if tt else 0.12)
            cores = np.maximum(cores, bl * f)
            side = np.clip(t.nx * (1 if x > W / 2 else -1), 0, 1)
            extra += ((side * 1.6 + 0.18) * f)[..., None] * np.array([190, 205, 240], np.float32)
            flashes.append((f, x, H * 0.25))
            if tt:
                sil.append((tt, f))
        E = np.zeros((H, W), np.float32); Eg = 0.0; band = E
        pl = 0.0
        if k >= self.T_STRIKE:
            fs = self.flick(k, self.T_STRIKE)
            kk = k - self.T_STRIKE
            fade = 1 - seg(k, (self.T_STRIKE + 14, 240))
            light += fs * 1.3 * np.exp(-((self.xx - t.xm) / (W * 0.35)) ** 2 - ((self.yy - H * 0.15) / (H * 0.6)) ** 2) * self.cloud_relief(cl, t.xm, H * 0.2)
            light += fs * 1.6 * np.exp(-((self.xx - t.xm) / (W * 0.18)) ** 2 - ((self.yy + 10) / (H * 0.22)) ** 2)
            pl = (fs * 0.8 + 0.45 * fade * float(kk >= 1))
            for p in self.pair:
                light += pl * np.exp(-((self.xx - p.cx) / (W * 0.16)) ** 2 - ((self.yy - H * 0.62) / (H * 0.35)) ** 2)
            amb += fs * 0.35
            cores = np.maximum(cores, self.strike * fs)
            flashes.append((fs * 1.4, t.xm, t.y0 - 40))
            r = (kk - 1) / 15.0 * (t.lw / 2 + 60)
            dx = np.abs(self.xx - t.xm)
            band = np.exp(-((dx - r) / 28) ** 2) * (1 - seg(kk, (14, 22))) * 1.3 * (kk >= 1)
            E = (smooth((r - dx) / 30) * 0.9 + band) * fade
            Eg = 0.9 * fade * float(kk >= 1)
            spot = np.exp(-(((self.xx - t.xm) ** 2 + (self.yy - t.ym) ** 2) / (2 * 22.0 ** 2)))
            img += (spot * (fs * 2.5 + 0.8 * fade))[..., None] * CYAN
        img += (light * cl ** 1.1)[..., None] * np.array([170, 185, 225], np.float32) + amb * np.array([26, 30, 44], np.float32)
        img += (light * 0.14)[..., None] * np.array([120, 135, 175], np.float32)
        if cores.max() > 0:                                              # the channels: hot core, tight and wide glow
            img += (bigblur(cores, 46) * 1.6)[..., None] * np.array([110, 120, 190], np.float32)
            img += (blur(cores, 6) * 1.1 + blur(cores, 2) * 1.0)[..., None] * np.array([150, 175, 245], np.float32)
            img += np.clip(cores * 1.3, 0, 1)[..., None] * np.array([245, 248, 255], np.float32)
        for tt, f in sil:
            img = self.silhouette(img, tt, f, np.array([190, 205, 240], np.float32))
        if k >= self.T_STRIKE:
            for p in self.pair:
                img = self.silhouette(img, p, pl, CYAN * 0.6 + np.array([90, 90, 90], np.float32) * fs)
        img = t.charge_light(img, E, Eg)
        if flashes:
            g = self.glint(flashes)
            extra = extra + (g * 120)[..., None] * np.array([0.95, 0.97, 1.0], np.float32)
        img = t.composite(img, E, Eg, 0.0, extra)
        if flashes:
            img += (blur(g, 3) * 45)[..., None] * np.array([0.8, 0.88, 1.0], np.float32)
        if Eg > 0.05:
            w = band[t.pts[:, 1].astype(int), t.pts[:, 0].astype(int)] * 3 + E[t.pts[:, 1].astype(int), t.pts[:, 0].astype(int)] * 0.3
            arc = blur(t.arcs(k, w, int(2 + 5 * Eg), 16), 0.6)
            img += (arc * 0.6)[..., None] * ICE + (blur(arc, 2) * 1.6 + blur(arc, 7) * 1.2)[..., None] * CYAN
        lit = 0.17 + 0.8 * min(1.0, amb * 2)
        img += (gk.rain_at(self.rain, k) * lit)[..., None] * np.array([150, 160, 185], np.float32) * 0.45
        img += (near_at(self.near, k) * lit * 0.9)[..., None] * np.array([150, 160, 185], np.float32) * 0.35
        return gk.finish(img, self.xx, self.yy, self.sub, self.sub_y)


def render(src, out, only=None, mp4=None):
    s = Storm(src)
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
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], only, mp4)
