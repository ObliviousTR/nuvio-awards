"""Mission: Impossible card: idents with the title on screen for the whole hover.

modes
  fuse   the 1996 MISSION: IMPOSSIBLE title in the dark. A match strikes off screen and the fuse burns in from the
         left under the title: a white-hot head throwing sparks that arc and fall, a thin smoke trail, the burnt cord
         glowing and going to ash behind it. The spark lights the letters from below as it passes and runs up into
         the last letter; the title flashes, embers fall, and the light dies back to the cover.
  ember  the red MISSION: IMPOSSIBLE of Dead / Final Reckoning. Heat runs through the letters from left to right -
         their edges and a moving grain inside them glow like coals - with heat haze above and embers rising; a long
         orange light opens behind the title, then the letters cool back to red.
Both: 250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/mi_ident.py SRC_DIR OUT_DIR --mode fuse|ember [--frames a,b] [--mp4 path]
  SRC_DIR: l1.png (the Mission: Impossible (1996) title logo on TMDB), l3.png (the Final Reckoning title logo on TMDB),
           Oswald-VF.ttf, BarlowCondensed-Medium.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
FPS = 25.0


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / max(1, b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


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


def blackbody(t):
    """0..1 temperature -> colour: dark red, red, orange, yellow, white"""
    stops = np.array([0.0, 0.25, 0.5, 0.75, 1.0], np.float32)
    cols = np.array([[30, 2, 0], [170, 20, 4], [255, 90, 10], [255, 190, 70], [255, 245, 220]], np.float32)
    t = np.clip(t, 0, 1)
    return np.stack([np.interp(t, stops, cols[:, c]) for c in range(3)], -1).astype(np.float32)


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


def bevel_normals(la, bw=2.5):
    m = (la > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    hg = blur(smooth(dt / bw).astype(np.float32), 0.6)
    gx = cv2.Sobel(hg, cv2.CV_32F, 1, 0, ksize=3) / 8 * bw; gy = cv2.Sobel(hg, cv2.CV_32F, 0, 1, ksize=3) / 8 * bw
    n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n


class Fuse:
    T_START, T_END = 4, 150        # the head enters the frame, reaches the last letter
    T_FADE = 214

    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        lg = Image.open(os.path.join(src, "l1.png")).convert("RGBA")
        lw = 820; lh = round(lg.height * lw / lg.width)
        a = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32)
        self.top = 300 - lh // 2
        self.la = put(a[..., 3] / 255, W / 2, self.top)
        self.x0, self.lw, self.lh = (W - lw) // 2, lw, lh
        self.n = bevel_normals(self.la)
        g = np.clip((yy - self.top) / lh, 0, 1)[..., None]
        self.face = np.array([244, 244, 240], np.float32) * (1 - 0.1 * g)
        sub = text_layer(os.path.join(src, "Oswald-VF.ttf"), 40, "THE COLLECTION", 30, var=[400])
        self.sub = put(sub, W / 2, self.top + lh + 30)
        # the fuse's path: in from the left under the title, curving up into the bottom of the last letter
        pts = np.array([[-60, 640], [220, 560], [500, 520], [800, 512], [1010, 470], [self.x0 + lw - 22, self.top + lh + 2]], np.float32)
        t = np.linspace(0, 1, 2000)
        # Catmull-Rom through the points
        P = np.concatenate([pts[:1], pts, pts[-1:]])
        seg_n = len(pts) - 1
        curve = []
        for i in range(seg_n):
            p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
            for u in np.linspace(0, 1, 400, endpoint=False):
                curve.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
        curve.append(pts[-1])
        self.curve = np.array(curve, np.float32)
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.curve, axis=0), axis=1))]
        self.arclen = d
        # head position per frame: steady burn with sputters
        rng = np.random.default_rng(7)
        speed = 1 + 0.45 * (noise(4, 256, 1.0, 9)[2] - 0.5) * 2
        prog = np.zeros(N + 1, np.float32)
        span = self.T_END - self.T_START
        acc = 0.0
        for k in range(N + 1):
            if self.T_START <= k <= self.T_END:
                acc += speed[k % 256]
            prog[k] = acc
        prog /= max(prog.max(), 1e-6)
        self.s = prog * d[-1]
        # precompute sparks and smoke for every frame (the simulation runs once, frames read from it)
        self.sim = self.simulate(rng)
        self.smoke_tex = noise(64, 128, 1.4, 5)

    def head(self, k):
        s = self.s[min(k, N)]
        i = int(np.searchsorted(self.arclen, s))
        i = min(i, len(self.curve) - 1)
        tng = self.curve[min(i + 3, len(self.curve) - 1)] - self.curve[max(i - 3, 0)]
        tng /= np.linalg.norm(tng) + 1e-6
        return self.curve[i], tng, i

    def simulate(self, rng):
        parts = []                                     # x, y, vx, vy, age, life, heat
        frames = []
        smoke = []                                     # x, y, age, size, seed
        g = 520.0 / FPS / FPS
        for k in range(N):
            burning = self.T_START <= k <= self.T_END
            if burning:
                (hx, hy), tng, _ = self.head(k)
                for _ in range(int(rng.integers(26, 44))):
                    ang = rng.normal(-math.pi / 2, 1.0) + rng.normal(0, 0.3)
                    sp = rng.uniform(60, 330) / FPS
                    vx, vy = math.cos(ang) * sp - tng[0] * 40 / FPS, math.sin(ang) * sp
                    parts.append([hx, hy, vx, vy, 0.0, rng.uniform(0.18, 0.75) * FPS, rng.uniform(0.75, 1.0)])
                if k % 2 == 0:
                    smoke.append([hx, hy - 4, 0.0, rng.uniform(6, 10), rng.integers(0, 1000)])
            if k == self.T_END:                                         # it reaches the title: a burst
                (hx, hy), _, _ = self.head(k)
                for _ in range(380):
                    ang = rng.uniform(-math.pi, 0) + rng.normal(0, 0.2)
                    sp = rng.uniform(80, 520) / FPS
                    parts.append([hx, hy, math.cos(ang) * sp, math.sin(ang) * sp, 0.0, rng.uniform(0.3, 1.3) * FPS, 1.0])
            segs = []
            alive = []
            for p in parts:
                x0, y0 = p[0], p[1]
                p[2] *= 0.985; p[3] = p[3] * 0.985 + g
                p[0] += p[2]; p[1] += p[3]; p[4] += 1
                if p[4] < p[5] and p[1] < H + 20:
                    alive.append(p)
                    segs.append((x0, y0, p[0], p[1], p[4] / p[5], p[6]))
            parts = alive
            sm_alive = []
            sm_now = []
            for s_ in smoke:
                s_[2] += 1
                if s_[2] < 1.8 * FPS:
                    sm_alive.append(s_)
                    t = s_[2] / FPS
                    sm_now.append((s_[0] + 6 * t, s_[1] - 26 * t - 6 * t * t, s_[3] + 22 * t, (1 - t / 1.8) ** 1.5, s_[4]))
            smoke = sm_alive
            frames.append((segs, sm_now))
        return frames

    def frame(self, k):
        img = np.zeros((H, W, 3), np.float32) + np.array([4, 4, 5], np.float32)
        segs, sm = self.sim[k]
        burning = self.T_START <= k <= self.T_END
        # the spark light: flickering point light at the head
        light = np.zeros((H, W), np.float32)
        hx = hy = None
        if burning:
            (hx, hy), _, idx = self.head(k)
            fl = 0.85 + 0.3 * np.random.default_rng(2000 + k).random()
            d2 = (self.xx - hx) ** 2 + (self.yy - hy) ** 2
            light = fl / (1 + d2 / 140.0 ** 2)
        burst = math.exp(-max(0, k - self.T_END) / 6.0) if k >= self.T_END else 0.0
        if burst > 0:
            (bx, by), _, _ = self.head(self.T_END)
            d2 = (self.xx - bx) ** 2 + (self.yy - by) ** 2
            light = np.maximum(light, 2.2 * burst / (1 + d2 / 260.0 ** 2))
        warm = np.array([255, 170, 90], np.float32)
        img += (light * 10)[..., None] * warm / 255 * 3                     # a faint bounce off the dark
        # the cord: dark, seen only in the spark's light; burnt part glows then goes to ash; nothing before T_START
        cord = np.zeros((H, W), np.float32); ember = np.zeros((H, W), np.float32)
        if burning:
            pts = self.curve[idx:]
            cv2.polylines(cord, [np.round(pts * 4).astype(np.int32)], False, 1.0, 3, cv2.LINE_AA, 2)
            back = self.curve[max(0, idx - 160):idx + 1]
            if len(back) > 1:
                for j in range(len(back) - 1):
                    t = j / max(1, len(back) - 1)
                    cv2.line(ember, tuple((back[j] * 4).astype(int)), tuple((back[j + 1] * 4).astype(int)), float(t ** 3), 2, cv2.LINE_AA, 2)
        img += (cord * light)[..., None] * np.array([70, 62, 54], np.float32)
        img += (blur(ember, 0.7) * 1.2)[..., None] * np.array([255, 110, 30], np.float32) + blur(ember, 4)[..., None] * np.array([255, 80, 20], np.float32) * 0.8
        # smoke: soft wisps, lit warm near the spark
        if sm:
            smk = np.zeros((H, W), np.float32)
            for x, y, r, a, sd in sm:
                if 0 <= x < W and 0 <= y < H:
                    cv2.circle(smk, (int(x), int(y)), int(r), float(a * 0.08), -1, cv2.LINE_AA)
            smk = blur(smk, 6)
            tex = cv2.resize(np.roll(self.smoke_tex, -k, axis=0), (W, H))
            smk *= 0.6 + 0.8 * tex
            img += smk[..., None] * (np.array([70, 70, 74], np.float32) + light[..., None] * warm * 0.6)
        # the title, lit from below by the spark
        L = np.dstack([(hx if hx is not None else W / 2) - self.xx, (hy if hy is not None else H) - self.yy,
                       np.full_like(self.xx, 60)])
        L /= np.linalg.norm(L, axis=2, keepdims=True)
        diff = np.clip((self.n * L).sum(2), 0, 1)
        lit_face = self.face * (0.9 + 0.1 * diff)[..., None] + (light * diff * 1.4)[..., None] * warm
        after = 0.35 * (1 - seg(k, self.T_END, 236)) * (k >= self.T_END)
        hot = (burst + after) * smooth(1 - np.sqrt((self.xx - (self.x0 + self.lw)) ** 2 + (self.yy - self.top - self.lh) ** 2) / 420)
        lit_face = lit_face * (1 - (hot * 0.5)[..., None]) + (hot * 0.5)[..., None] * np.array([255, 200, 140], np.float32)
        a = self.la[..., None]
        img = img * (1 - a) + lit_face * a
        img += (bigblur(self.la * (light + hot), 12) * 0.9)[..., None] * warm
        # sparks: motion-blurred streaks, white-hot when young, orange-red as they cool
        sp = np.zeros((H, W, 3), np.float32)
        if segs:
            lay = {}
            for x0, y0, x1, y1, age, heat in segs:
                temp = heat * (1 - age) ** 0.8
                col = tuple(float(c) for c in blackbody(np.array(0.35 + 0.65 * temp)) / 255 * (0.6 + 0.8 * temp))
                cv2.line(sp, (int(x0 * 4), int(y0 * 4)), (int(x1 * 4), int(y1 * 4)), col, 1, cv2.LINE_AA, 2)
        img += sp * 255 * 1.2 + bigblur(sp, 6) * 255 * 2.0
        if burning:
            core = np.exp(-((self.xx - hx) ** 2 + (self.yy - hy) ** 2) / (2 * 3.0 ** 2))
            img += (core * 3 + blur(core, 10) * 18)[..., None] * np.array([255, 230, 190], np.float32)
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([214, 214, 210], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.5 * np.clip(rr - 0.4, 0, 1))[..., None]
        img += np.random.default_rng(900 + k).normal(size=(H, W)).astype(np.float32)[..., None] * 1.6
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


class Ember:
    T_HEAT = (14, 70)       # heat runs in, left to right
    T_COOL = (150, 214)     # and out again

    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        a = np.asarray(Image.open(os.path.join(src, "l3.png")).convert("RGBA"), np.float32)[:520]   # the red title only
        al0 = a[..., 3]
        ys, xs = np.where(al0 > 10); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        lw = 880; lh = round(a.shape[0] * lw / a.shape[1])
        a = cv2.resize(a, (lw, lh), interpolation=cv2.INTER_AREA)
        self.top = 300 - lh // 2 - 10
        self.x0, self.lw, self.lh = (W - lw) // 2, lw, lh
        self.la = put(a[..., 3] / 255, W / 2, self.top)
        rgb = np.zeros((H, W, 3), np.float32); rgb[self.top:self.top + lh, self.x0:self.x0 + lw] = a[..., :3]
        self.red = rgb
        m = (self.la > 0.5).astype(np.uint8)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        self.edge = np.exp(-dt / 3.5) * self.la                          # heat gathers at the edges
        self.n = bevel_normals(self.la, 3.0)
        sub = text_layer(os.path.join(src, "BarlowCondensed-Medium.ttf"), 60, "THE COLLECTION", 36, shear=0.2)
        self.sub = put(sub, W / 2, self.top + lh + 22)
        self.grain = noise(H, W, 1.1, 31); self.grain2 = noise(H, W, 1.5, 32)
        self.haze = noise(H, W, 1.3, 33)
        rng = np.random.default_rng(3)
        self.emb = rng.uniform(0, 1, (170, 5)).astype(np.float32)
        self.dust = noise(H, W, 1.6, 34)

    def heat(self, k):
        u0 = (k - self.T_HEAT[0]) / (self.T_HEAT[1] - self.T_HEAT[0])
        front = self.x0 - 60 + u0 * (self.lw + 160)
        on = smooth((front - self.xx) / 90) if k >= self.T_HEAT[0] else np.zeros_like(self.xx)
        u1 = (k - self.T_COOL[0]) / (self.T_COOL[1] - self.T_COOL[0])
        back = self.x0 - 60 + u1 * (self.lw + 160)
        off = smooth((back - self.xx) / 110) if k >= self.T_COOL[0] else 0.0
        pulse = 0.9 + 0.1 * math.sin(k * 0.37) * math.sin(k * 0.11)
        return on * (1 - off) * pulse

    def frame(self, k):
        Hm = self.heat(k)
        level = float(Hm[self.top + self.lh // 2, self.x0:self.x0 + self.lw].mean())
        img = np.zeros((H, W, 3), np.float32) + np.array([6, 4, 4], np.float32)
        img += (self.dust ** 3)[..., None] * np.array([26, 12, 6], np.float32)
        # the long light behind the title (Final Reckoning)
        cy = self.top + self.lh * 0.5
        band = np.exp(-((self.yy - cy) / 70) ** 2) * np.exp(-((self.xx - W / 2) / 520) ** 2)
        streak = np.exp(-((self.yy - cy) / 5) ** 2) * np.exp(-np.abs(self.xx - W / 2) / 600)
        img += ((band * 0.9 + streak * 0.6) * (0.25 + 0.75 * level))[..., None] * np.array([255, 110, 30], np.float32)
        # heat haze: the scene above the letters wavers where they are hot
        hz = np.roll(self.haze, -int(k * 3), axis=0)
        amp = bigblur(Hm * self.la, 18) * 6
        dx = (hz - 0.5) * amp * 2; dy = (np.roll(self.haze, 37, axis=1) - 0.5) * amp
        # the letters: red at rest; hot, their edges and a moving grain glow like coals
        g1 = np.roll(self.grain, -int(k * 1.6), axis=0); g2 = np.roll(self.grain2, -int(k * 0.7), axis=0)
        cracks = np.clip((g1 * 0.6 + g2 * 0.4 - 0.42) * 3.2, 0, 1)
        temp = Hm * (0.12 + 0.62 * cracks ** 1.6 + 0.5 * self.edge)
        coal = blackbody(temp)
        shade = 0.85 + 0.25 * np.clip(self.n[..., 1] * -1 + 0.4, 0, 1)
        face = self.red * shade[..., None]
        char = np.array([46, 8, 4], np.float32)                           # the letter darkens as it heats, then glows
        face = face * (1 - Hm[..., None] * 0.8) + char * Hm[..., None] * 0.8
        face = face + coal * smooth((temp - 0.08) / 0.5)[..., None] * 1.1
        a = self.la[..., None]
        img = img * (1 - a) + face * a
        img += (bigblur(temp * self.la, 8) * 1.6 + bigblur(temp * self.la, 30) * 1.2)[..., None] * np.array([255, 120, 30], np.float32)
        img = cv2.remap(img.astype(np.float32), self.xx + dx, self.yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # embers: rise from the hot letters, drift, wink out
        sp = np.zeros((H, W), np.float32)
        for e in self.emb:
            x = self.x0 + e[0] * self.lw
            base_h = float(Hm[int(self.top + self.lh * 0.3), int(np.clip(x, 0, W - 1))])
            if base_h < 0.05:
                continue
            life = 1.2 + 1.6 * e[1]
            t = ((k / FPS + e[2] * life) % life) / life
            y = self.top + self.lh * (0.2 + 0.6 * e[3]) - t * (90 + 160 * e[4])
            x += math.sin(t * 6 + e[2] * 9) * 14 + t * 30
            b = base_h * math.sin(math.pi * t) * (0.4 + 0.6 * e[4])
            if 0 <= x < W and 0 <= y < H:                                 # a short streak: they move fast
                vy = (90 + 160 * e[4]) / life / FPS
                cv2.line(sp, (int(x * 4), int(y * 4)), (int((x - 1.5) * 4), int((y + vy * 1.2) * 4)), float(b), 1 + int(2 * e[1]), cv2.LINE_AA, 2)
        img += (sp * 1.4)[..., None] * np.array([255, 190, 110], np.float32) + bigblur(sp, 5)[..., None] * np.array([255, 110, 30], np.float32) * 2.5
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([236, 232, 228], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.5 * np.clip(rr - 0.4, 0, 1))[..., None]
        img += np.random.default_rng(900 + k).normal(size=(H, W)).astype(np.float32)[..., None] * 1.6
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


MODES = {"fuse": Fuse, "ember": Ember}


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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "fuse"
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
