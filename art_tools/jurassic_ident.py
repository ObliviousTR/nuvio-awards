"""Jurassic card. The 1993 JURASSIC PARK badge (TMDB vector) and two moments of the first film.

--mode tremor  The impact tremor: the T. rex is announced by rings in a cup of water. Here the badge stands over still
               night water before the far tree line (the film's own palm silhouette, TMDB), its reflection below. Each
               heavy footfall sends rings out through the reflection and jolts the frame; the steps come closer, the
               rings grow; after the nearest one the water settles back to the cover.
--mode power   The power goes down: the badge on the park's gate (TMDB artwork of the gates) under three floodlights.
               They fail one by one; in the dark only a dim red emergency light; the generator comes in and the lamps
               strike and warm up again one by one.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/jurassic_ident.py SRC_DIR OUT_DIR [--mode tremor|power] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.svg (TMDB logo djIhZiHr974aA5Cyprgal4YAJDl, film 329), treeline.jpg (TMDB backdrop
           9REZLLxUbLSl2HyrDLev6fbe8HT, film 329), gate.jpg (TMDB backdrop 7NDGk4jdMjHnfolFVxBZQAIohM4, film 329),
           Oswald-VF.ttf
"""
import io, math, os, sys, subprocess
import numpy as np
import cv2
import cairosvg
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / (b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0.05 else a


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


def badge(src, width):
    png = cairosvg.svg2png(url=os.path.join(src, "logo.svg"), output_width=width * 2)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    return a[..., :3], a[..., 3]


def collection(src, size=40, track=16):
    f = ImageFont.truetype(os.path.join(src, "Oswald-VF.ttf"), size)
    f.set_variation_by_axes([400])
    txt = "THE COLLECTION"
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 40, size * 2), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def place(rgb, a, x0, y0):
    R = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32)
    h, w = a.shape
    R[y0:y0 + h, x0:x0 + w] = rgb; A[y0:y0 + h, x0:x0 + w] = a
    return R, A


def to_image(img, k, grain, amt=0.03):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


# --------------------------------------------------------------------------------------------------------- tremor
STEPS = [(12, 0.35), (54, 0.5), (88, 0.66), (116, 0.84), (138, 1.0)]    # footfalls: frame, strength
YW = 452                                                                 # the waterline


class Tremor:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        rgb, a = badge(src, 452)
        self.lx0 = (W - a.shape[1]) // 2; self.ly0 = 48
        self.lrgb, self.la = place(rgb, a, self.lx0, self.ly0)
        col = collection(src)
        self.col = np.zeros((H, W), np.float32)
        cy = self.ly0 + a.shape[0] + 22; cx = (W - col.shape[1]) // 2
        self.col[cy:cy + col.shape[0], cx:cx + col.shape[1]] = col
        # the night above the water: sky, and the film's palm line as the far shore
        gl = smooth((yy - 60) / (YW - 60)) ** 1.6
        sky = np.dstack([0.012 + 0.11 * gl, 0.02 + 0.14 * gl, 0.04 + 0.19 * gl]).astype(np.float32)
        t = np.asarray(Image.open(os.path.join(src, "treeline.jpg")).convert("RGB"), np.float32) / 255
        t = cv2.resize(t, (W, round(t.shape[0] * W / t.shape[1])), interpolation=cv2.INTER_AREA)
        dark = (t.max(2) < 0.12).astype(np.float32)                      # the palms are the black in the still
        dark = blur(dark, 0.8)
        trees = np.zeros((H, W), np.float32)
        strip = dark[int(t.shape[0] * 0.20):int(t.shape[0] * 0.70)]     # the palm crowns and the dark below them
        strip = cv2.resize(strip, (W, round(strip.shape[0] * 0.5)), interpolation=cv2.INTER_AREA)
        hs = strip.shape[0]
        trees[YW - hs + 6:YW + 6] = strip[:hs]
        trees[YW - 8:YW + 6] = 1.0
        self.above = sky * (1 - trees[..., None]) + np.array([0.006, 0.009, 0.012], np.float32) * trees[..., None]
        self.amb_n1 = noise(H, W * 2, 2.2, 21); self.amb_n2 = noise(H, W * 2, 2.0, 22)
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        # the ring centre: under the badge's reflection; the water seen at a grazing angle
        self.cx, self.cy = W / 2, 2 * YW - (self.ly0 + a.shape[0] / 2) + 20
        dyw = (yy - self.cy) / 0.24
        self.r = np.sqrt((xx - self.cx) ** 2 + dyw ** 2)

    def scene_above(self, k, dy):
        img = self.above.copy()
        face = self.lrgb * 0.92
        img = img * (1 - self.la[..., None]) + face * self.la[..., None]
        img = img * (1 - self.col[..., None]) + np.array([0.85, 0.84, 0.80], np.float32) * self.col[..., None]
        if abs(dy) > 0.02:
            img = cv2.warpAffine(img, np.float32([[1, 0, 0], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        return img

    def height(self, k):
        h = np.zeros((H, W), np.float32)
        for k0, s in STEPS:
            t = k - k0
            if t <= 0:
                continue
            front = 13.0 * t
            env = np.exp(-((self.r - front + 50) / 90) ** 2) * np.exp(-t / 30) * smooth((front + 60 - self.r) / 30)
            h += s * env * np.sin(2 * math.pi * (self.r - front) / 64)
        # a breath of wind on the water all along (loops)
        ph = 2 * math.pi * k / N
        o1 = int((math.sin(ph) * 0.5 + 0.5) * W); o2 = int((math.cos(ph) * 0.5 + 0.5) * W)
        h += (self.amb_n1[:, o1:o1 + W] - 0.5) * 0.08 + (self.amb_n2[:, o2:o2 + W] - 0.5) * 0.06
        return h

    def jolt(self, k):
        dy = 0.0
        for k0, s in STEPS:
            t = k - k0
            if 0 <= t < 16:
                dy += s * 6.0 * math.exp(-t / 3.5) * math.cos(t * 1.9)
        return dy

    def frame(self, k):
        k = k % N
        dy = self.jolt(k)
        above = self.scene_above(k, dy)
        h = self.height(k)
        gy, gx = np.gradient(h)
        # the reflection: the scene mirrored about the waterline, bent by the slope of the water
        my = (2 * YW - self.yy) + gy * 70 + dy
        mx = self.xx + gx * 30
        refl = cv2.remap(above, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        dist = np.clip((self.yy - YW) / (H - YW), 0, 1)
        refl = blur(refl, 1.2) * (1 - dist[..., None]) + blur(refl, 3.0) * dist[..., None]
        fres = 0.5 - 0.2 * dist
        water = refl * (fres[..., None] * np.array([0.82, 0.92, 1.0], np.float32)) + np.array([0.004, 0.008, 0.012], np.float32)
        # crests catch the faint sky
        sheen = np.clip(-gy * 14, 0, 1) * (1 - 0.6 * dist) * 0.22
        water += sheen[..., None] * np.array([0.5, 0.65, 0.9], np.float32)
        below = (self.yy > YW + dy).astype(np.float32)[..., None]
        img = above * (1 - below) + water * below
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.68)) ** 2)
        img *= (1 - 0.45 * np.clip(rr - 0.45, 0, 1))[..., None]
        return to_image(img, k, self.grain, 0.03)


# --------------------------------------------------------------------------------------------------------- power
LIGHTS = [(250.0, 285.0), (640.0, 260.0), (1030.0, 285.0)]               # where each floodlight's pool sits
OFF = {2: 6, 0: 24, 1: 42}                                               # light -> frame it fails
ON = {1: 150, 0: 166, 2: 180}                                            # light -> frame it strikes again
STRIKE = [0.0, 0.5, 0.05, 0.7, 0.2, 0.35]
FAIL = [1.0, 1.25, 0.3, 0.9, 0.08, 0.45, 0.02]


def light_level(i, k):
    """brightness and warm-up (0 cold .. 1 full white) of floodlight i"""
    if k < OFF[i]:
        return 1.0, 1.0
    t = k - OFF[i]
    if k < ON[i]:
        if t < len(FAIL):
            return FAIL[t], 1.0
        return 0.12 * math.exp(-(t - len(FAIL)) / 3.0), 0.0              # the glass glows a moment after the arc dies
    t = k - ON[i]
    if t < len(STRIKE):
        return STRIKE[t], 0.0
    u = smooth((t - len(STRIKE)) / 34.0)                                 # a discharge lamp warms up
    return 0.25 + 0.75 * u, u


class Power:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        g = np.asarray(Image.open(os.path.join(src, "gate.jpg")).convert("RGB"), np.float32) / 255
        g = g[30:380, 330:950]                                           # the doors between the torches
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
        g = g / (bigblur(g, 140) + 0.02)                                 # its painted light taken out
        lum = g.mean(2, keepdims=True)
        g = 0.5 * g + 0.5 * lum * np.array([1.25, 0.95, 0.72], np.float32)   # weathered wood, not green
        self.wall = np.clip(0.3 * (0.6 + 0.4 * g), 0, 1)
        rgb, a = badge(src, 470)
        self.lx0 = (W - a.shape[1]) // 2; self.ly0 = 70
        self.lrgb, self.la = place(rgb, a, self.lx0, self.ly0)
        col = collection(src)
        self.col = np.zeros((H, W), np.float32)
        cy = self.ly0 + a.shape[0] + 26; cx = (W - col.shape[1]) // 2
        self.col[cy:cy + col.shape[0], cx:cx + col.shape[1]] = col
        self.pools = []
        for (px, py) in LIGHTS:
            d = np.sqrt(((xx - px) / 330) ** 2 + ((yy - py) / 400) ** 2)
            pool = (1 - smooth((d - 0.55) / 0.5)) * (0.75 + 0.45 * np.exp(-d * d * 3))
            pool *= smooth((yy + 60) / 200)
            self.pools.append(pool.astype(np.float32))
        self.red = (np.exp(-(((xx - 120) / 520) ** 2 + ((yy - 760) / 420) ** 2))).astype(np.float32)
        # the badge is a plate off the gate: it shadows the gate below it (lights are above)
        self.shadow = blur(np.roll(self.la, 20, axis=0), 9)
        self.plate = noise(H, W, 1.6, 31)
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def frame(self, k):
        k = k % N
        light = np.zeros((H, W, 3), np.float32)
        for i, pool in enumerate(self.pools):
            lv, warm = light_level(i, k)
            if lv <= 0.001:
                continue
            c = np.array([0.55, 0.85, 1.0], np.float32) * (1 - warm) + np.array([1.0, 0.98, 0.94], np.float32) * warm
            light += pool[..., None] * c * lv
        emerg = seg(k, 66, 74) * (1 - seg(k, 170, 200))
        light += (self.red * emerg * 0.32)[..., None] * np.array([1.0, 0.1, 0.06], np.float32)
        amb = np.array([0.012, 0.015, 0.02], np.float32)
        lit = light * (1 - 0.7 * self.shadow)[..., None]
        img = self.wall * (amb + lit * 1.15)
        face = self.lrgb * (0.93 + 0.07 * self.plate[..., None]) * (amb * 3 + light * 1.05)
        img = img * (1 - self.la[..., None]) + face * self.la[..., None]
        # THE COLLECTION: painted on the gate, lit as the gate is
        img = img * (1 - 0.6 * np.clip(bigblur(self.col, 10) * 1.6, 0, 1))[..., None]
        ll = np.clip(light.max(2, keepdims=True) * 1.3, 0.12, 1.0)
        colc = np.array([0.95, 0.9, 0.8], np.float32) * ll
        img = img * (1 - self.col[..., None]) + colc * self.col[..., None]
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.68)) ** 2)
        img *= (1 - 0.4 * np.clip(rr - 0.5, 0, 1))[..., None]
        img = img / (1 + 0.25 * img) * 1.25
        return to_image(img, k, self.grain, 0.03)


def render(src, out, mode, only=None, mp4=None):
    s = Tremor(src) if mode == "tremor" else Power(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "tremor"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
