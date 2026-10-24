"""Star Trek card, as the franchise ident: STAR, the Starfleet delta, TREK in chrome on deep space, THE COLLECTION
under it (the franchise logo of the Star Trek Universe, 2016-).
Hover (10 s): a light comes up behind the delta and draws out into a long anamorphic flare; the stars begin to stretch
away from the delta, faster and faster, into warp streaks; a flash as the ship jumps to warp, the streaks pour past,
a light sweep runs over the chrome; then the streaks slow and shrink back into stars, the flare goes down and the card
is the cover again. The logo never leaves the screen. First frame = last frame = cover: the starfield travels a whole
number of depth cycles over the loop.
The letters are the TOS wordmark on TMDB (Star Trek, 1966) set upright; the delta is drawn here; both get the same
chrome (a bevel from the shape's distance field, lit, with a horizon band reflected in it).
usage: python3 art_tools/startrek_delta.py SRC_DIR OUT_DIR [--frames a,b] [--scale s] [--mp4 path]
  SRC_DIR: wordmark.png, Antonio.ttf
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

GW, GH, MS, N = 512, 288, 40, 250
T_FLARE = (14, 60, 170, 222)       # flare up .. down
T_WARP = (40, 92, 150, 205)        # stars stretch, full warp, slow down, stars again
T_JUMP = 90                        # the flash
T_SWEEP = (100, 142)
NAVY = np.array([3, 5, 12], np.float32)
ICE = np.array([150, 200, 255], np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab; return smooth((k - a) / max(1, b - a))


def env4(k, t):
    return seg(k, t[:2]) * (1 - seg(k, t[2:]))


def bez(p0, p1, p2, n=90):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)


def delta_mask(h):
    w = int(h * 0.86); S = 4
    im = Image.new("L", (w * S, h * S), 0); d = ImageDraw.Draw(im)
    cx, sc = w * S / 2, h * S
    P = lambda pts: [(cx + x * sc, (y + 0.5) * sc) for x, y in pts]
    left = bez((0, -0.5), (-0.27, -0.12), (-0.41, 0.5)); bottom = bez((-0.41, 0.5), (0, 0.10), (0.41, 0.5))
    right = bez((0.41, 0.5), (0.27, -0.12), (0, -0.5))
    d.polygon(P(np.vstack([left, bottom, right])), fill=255)
    # the star: four points joined by inward curves
    c0 = np.array([0.0, 0.1])
    tips = [c0 + (0, -0.17), c0 + (0.115, 0), c0 + (0, 0.17), c0 + (-0.115, 0)]
    st = []
    for i in range(4):
        p0, p1 = tips[i], tips[(i + 1) % 4]
        ctrl = c0 + (p0 + p1 - 2 * c0) * 0.02
        st.append(bez(p0, ctrl, p1, 30))
    d.polygon(P(np.vstack(st)), fill=0)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255


def chrome(mask, bevel):
    m = (mask > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    h = np.clip(dist / bevel, 0, 1) ** 0.6; h = cv2.GaussianBlur(h, (0, 0), 1.0)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=5)
    nz = np.ones_like(h) * 6; nx, ny = -gx, -gy; ln = np.sqrt(nx * nx + ny * ny + nz * nz); nx, ny, nz = nx / ln, ny / ln, nz / ln
    L = np.array([-0.45, -0.65, 0.62]); L /= np.linalg.norm(L)
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 28
    yy = np.linspace(0, 1, mask.shape[0])[:, None] * np.ones((1, mask.shape[1]), np.float32)
    env = 1.0 - 0.55 * np.exp(-((yy - 0.55) / 0.06) ** 2) + 0.08 * (yy > 0.6) - 0.15 * yy
    return np.clip(0.12 + 0.95 * diff * env + 1.0 * spec, 0, 1.3).astype(np.float32)


class Scene:
    def __init__(self, src, sc=1.0):
        self.sc = sc
        W, H = self.W, self.H = round(1280 * sc), round(720 * sc)
        # the wordmark, set upright, split into STAR and TREK
        wm = np.asarray(Image.open(os.path.join(src, "wordmark.png")).convert("RGBA"), np.float32)[..., 3] / 255
        pad = 80; wm = np.pad(wm, ((0, 0), (pad, pad)))
        hh, ww = wm.shape
        wm = cv2.warpAffine(wm, np.array([[1, 0.22, -0.22 * hh], [0, 1, 0]], np.float32), (ww, hh), flags=cv2.INTER_CUBIC)
        cols = np.nonzero(wm.max(0) > 0.5)[0]
        gaps = [(cols[i], cols[i + 1]) for i in range(len(cols) - 1) if cols[i + 1] - cols[i] > 15]
        g0, g1 = max(gaps, key=lambda g: g[1] - g[0])
        star = wm[:, cols[0]:g0 + 1]; trek = wm[:, g1:cols[-1] + 1]
        LH = round(128 * sc)
        rs = lambda m: cv2.resize(m, (max(1, round(m.shape[1] * LH / m.shape[0])), LH), interpolation=cv2.INTER_AREA)
        star, trek = rs(star), rs(trek)
        DH = round(236 * sc)
        delta = delta_mask(DH)
        gap = round(16 * sc)
        total = star.shape[1] + gap + delta.shape[1] + gap + trek.shape[1]
        x0 = (W - total) // 2; cy = round(300 * sc)
        self.mask = np.zeros((H, W), np.float32); self.lum = np.zeros((H, W), np.float32)

        def put(m, x, y, bevel):
            h, w = m.shape; y = int(y); x = int(x)
            self.mask[y:y + h, x:x + w] = np.maximum(self.mask[y:y + h, x:x + w], m)
            self.lum[y:y + h, x:x + w] = np.where(m > 0.01, chrome(m, bevel), self.lum[y:y + h, x:x + w])
        put(star, x0, cy - LH / 2, 5 * sc)
        dx = x0 + star.shape[1] + gap
        put(delta, dx, cy - DH / 2 + 8 * sc, 6 * sc)
        put(trek, dx + delta.shape[1] + gap, cy - LH / 2, 5 * sc)
        self.dcx, self.dcy = dx + delta.shape[1] / 2, cy + 8 * sc
        self.dmask = np.zeros((H, W), np.float32)
        self.dmask[int(cy - DH / 2 + 8 * sc):int(cy - DH / 2 + 8 * sc) + DH, int(dx):int(dx) + delta.shape[1]] = delta
        self.l0, self.l1 = x0, x0 + total
        self.bot = cy + DH / 2 + 8 * sc
        # THE COLLECTION
        f = ImageFont.truetype(os.path.join(src, "Antonio.ttf"), round(24 * sc) * 2)
        try:
            f.set_variation_by_axes([500])
        except Exception:
            pass
        txt = "THE COLLECTION"; tr = round(14 * sc) * 2
        m = Image.new("L", (int(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 40, round(24 * sc) * 4), 0)
        d = ImageDraw.Draw(m); x = 20
        for c in txt:
            d.text((x, round(24 * sc) * 3), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        self.sub = m; self.suby = round(self.bot + 26 * sc)
        # stars: a 3-D field flying out of the delta
        r = np.random.default_rng(7)
        n = 900
        self.sx = r.uniform(-1, 1, n) * 1.6; self.sy = r.uniform(-1, 1, n) * 0.95
        self.sz0 = r.uniform(0, 1, n); self.sb = r.uniform(0.35, 1.0, n)
        v = np.array([env4(k, T_WARP) ** 1.6 for k in range(N + 1)])
        cum = np.concatenate([[0], np.cumsum(v[:-1])])
        cycles = 3
        self.travel = cum / cum[-1] * cycles                       # whole cycles over the loop
        self.speed = v / cum[-1] * cycles
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        vg = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        self.vig = 1 - 0.4 * np.clip(vg - 0.45, 0, 1) ** 1.3

    def stars(self, k):
        W, H, sc = self.W, self.H, self.sc
        z = (self.sz0 - self.travel[k]) % 1.0
        z = 0.06 + z * 0.94
        f = 0.5 * W
        px = self.dcx + self.sx / z * f * 0.35; py = self.dcy + self.sy / z * f * 0.35
        sp = self.speed[k] * 0.94
        z2 = np.minimum(1.0, z + sp * 9)                            # the tail: where the star was a moment ago
        qx = self.dcx + self.sx / z2 * f * 0.35; qy = self.dcy + self.sy / z2 * f * 0.35
        lay = np.zeros((H * 2, W * 2), np.float32)
        b = self.sb * np.clip(1.15 - z, 0.15, 1)
        warp = env4(k, T_WARP)
        for i in range(len(z)):
            if not (-50 < px[i] < W + 50 and -50 < py[i] < H + 50):
                continue
            th = max(1, int(round((1.8 - z[i]) * sc * 2)))
            c = float(b[i] * (0.55 + 0.45 * warp))
            p1 = (int(px[i] * 2 * 4), int(py[i] * 2 * 4)); p0 = (int(qx[i] * 2 * 4), int(qy[i] * 2 * 4))
            if abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) < 6:
                cv2.circle(lay, (p1[0], p1[1]), th * 4 // 2 + 2, c, -1, cv2.LINE_AA, 2)
            else:
                cv2.line(lay, p0, p1, c, th, cv2.LINE_AA, 2)
        lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_AREA)
        return lay

    def frame(self, k):
        W, H, sc = self.W, self.H, self.sc
        flare = env4(k, T_FLARE)
        jump = math.exp(-((k - T_JUMP) / 4.5) ** 2)
        img = np.zeros((H, W, 3), np.float32) + NAVY
        st = self.stars(k)
        img += st[..., None] * np.array([200, 220, 255], np.float32)
        img += cv2.GaussianBlur(st, (0, 0), 3 * sc)[..., None] * ICE * 0.6
        # light behind the delta and the anamorphic flare
        dx = self.xx - self.dcx; dy = self.yy - self.dcy
        glow = np.exp(-(dx * dx + dy * dy) / (2 * (90 * sc) ** 2))
        line = np.exp(-(dy / (2.2 * sc)) ** 2) * np.exp(-np.abs(dx) / (520 * sc))
        halo = np.exp(-(dy / (18 * sc)) ** 2) * np.exp(-np.abs(dx) / (300 * sc))
        fl = flare * (0.75 + 0.25 * math.sin(k * 0.5) * math.sin(k * 0.17)) + 1.4 * jump
        img += (glow * fl)[..., None] * np.array([70, 120, 210], np.float32)
        img += (halo * fl * 0.6)[..., None] * np.array([90, 150, 255], np.float32)
        img += (line * fl)[..., None] * np.array([210, 235, 255], np.float32)
        img += (jump * 70 * np.exp(-(dx * dx + dy * dy) / (2 * (420 * sc) ** 2)))[..., None]
        # the logo in chrome, lit by the flare from behind and swept by a light
        lum = self.lum.copy()
        sw = seg(k, T_SWEEP)
        if 0 < sw < 1:
            sx = self.l0 - 120 * sc + (self.l1 - self.l0 + 240 * sc) * sw
            lum += 0.6 * np.exp(-(((self.xx - sx) + (self.yy - self.dcy) * 0.35) / (26 * sc)) ** 2)
        lit = 1 + 0.35 * flare * np.exp(-np.abs(dx) / (400 * sc)) + 0.6 * jump
        tint = np.clip((self.yy - (self.dcy - 10 * sc)) / (80 * sc), 0, 1)[..., None]          # the lower half reflects the blue of space
        col = (lum * lit)[..., None] * (np.array([0.97, 0.99, 1.03], np.float32) * (1 - tint) + np.array([0.78, 0.88, 1.05], np.float32) * tint) * 245
        rim = cv2.GaussianBlur(self.dmask, (0, 0), 2 * sc) - self.dmask
        img += (np.clip(rim, 0, 1) * (flare * 0.8 + jump))[..., None] * np.array([150, 200, 255], np.float32) * 2.5
        a = self.mask[..., None]
        img = img * (1 - a) + col * a
        # a thin line of the flare also crosses in front, faintly
        img += (line * fl * 0.25)[..., None] * np.array([210, 235, 255], np.float32)
        img *= self.vig[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        lay = Image.merge("RGBA", (Image.new("L", self.sub.size, 190), Image.new("L", self.sub.size, 206), Image.new("L", self.sub.size, 228), self.sub))
        out.alpha_composite(lay, (round(W / 2 - self.sub.width / 2), self.suby))
        return out.convert("RGB")


def render(src, out, only=None, sc=1.0, mp4=None):
    s = Scene(src, sc)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            s.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [s.frame(k) for k in range(N)]
    if mp4:
        import subprocess
        p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{s.W}x{s.H}",
                              "-r", "25", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", mp4], stdin=subprocess.PIPE)
        for _ in range(2):
            for f in frames:
                p.stdin.write(f.tobytes())
        p.stdin.close(); p.wait()
    if sc == 1.0:
        frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
        encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
        print("kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2))


if __name__ == "__main__":
    a = sys.argv
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    sc = float(a[a.index("--scale") + 1]) if "--scale" in a else 1.0
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], only, sc, mp4)
