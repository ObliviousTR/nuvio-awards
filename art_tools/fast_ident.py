"""Fast & Furious card. The chrome FAST & FURIOUS (the series' title since 2009, TMDB) and the films' night racing.

--mode night  A night run: the only light on the chrome is the street lamps passing over the car, their reflections
              running across the letters from front to back. The car gathers speed, the lamps come quicker; the NOS
              kicks in: the light turns blue, the reflections stop being lamps and stream as one line, the title's own
              speed streaks draw out, the kick shakes the camera; the car eases off and the cover is back.
--mode rev    The cars' electroluminescent gauges: a big tachometer glows out of focus behind the title, its light on
              the chrome. The needle climbs through the gears and drops at each shift; at the red line the NOS light
              comes on, the dial turns blue, the streaks draw out; the needle falls back to idle.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/fast_ident.py SRC_DIR OUT_DIR [--mode night|rev] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (TMDB logo 1HQxOYKdA0IfsMJT6TNClFU23Hb, film 13804), Montserrat-VF.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
SODIUM = np.array([1.0, 0.70, 0.36], np.float32)
NOS = np.array([0.42, 0.66, 1.0], np.float32)
EL = np.array([0.30, 1.0, 0.86], np.float32)


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


def disc_blur(a, r):
    k = np.zeros((2 * r + 1, 2 * r + 1), np.float32)
    cv2.circle(k, (r, r), r, 1.0, -1, cv2.LINE_AA); k /= k.sum()
    return cv2.filter2D(a, -1, k)


def hstreak(a, length):
    """motion blur trailing to the left (the title moves right)"""
    if length < 1:
        return a
    L = int(length)
    k = np.zeros((1, 2 * L + 1), np.float32); k[0, L:] = np.linspace(1.0, 0.15, L + 1)
    k /= k.sum()
    return cv2.filter2D(a, -1, k)


def collection(src):
    f = ImageFont.truetype(os.path.join(src, "Montserrat-VF.ttf"), 44)
    f.set_variation_by_axes([700])
    txt = "THE COLLECTION"; track = 14
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 80, 110), 0)
    d = ImageDraw.Draw(m); x = 40
    for c in txt:
        d.text((x, 80), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.transform(m.size, Image.AFFINE, (1, 0.2, -16, 0, 1, 0), Image.BICUBIC)   # italic, like the title
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


class Title:
    """the chrome title on the frame, with what its relief needs for moving reflections"""

    def __init__(self, src, lw=820, top=196):
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA")
        lh = round(lg.height * lw / lg.width)
        lg = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.x0 = (W - lw) // 2 + 14; self.top = top; self.lw, self.lh = lw, lh
        self.a = np.zeros((H, W), np.float32); self.rgb = np.zeros((H, W, 3), np.float32)
        self.a[top:top + lh, self.x0:self.x0 + lw] = lg[..., 3]; self.rgb[top:top + lh, self.x0:self.x0 + lw] = lg[..., :3]
        solid = (self.a > 0.92).astype(np.uint8)
        dist = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
        hgt = np.clip(dist / 5.0, 0, 1)
        hgt = blur(hgt, 1.2)
        self.nx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3); self.ny = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3)
        self.solid = blur(solid.astype(np.float32), 0.6) * self.a
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # where a reflection sits on the chrome: along the slant of the letters, bent by the bevels
        self.u = xx - 0.32 * (yy - (top + lh / 2)) + 34 * self.nx
        self.v = yy + 26 * self.ny
        col = collection(src)
        self.col = np.zeros((H, W), np.float32)
        cy = top + lh + 40; cx = (W - col.shape[1]) // 2
        self.col[cy:cy + col.shape[0], cx:cx + col.shape[1]] = col


def to_image(img, k, grain, amt=0.03):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


def shake(k, k0, amp=6.0, dur=18):
    t = k - k0
    if t < 0 or t >= dur:
        return 0.0, 0.0
    rng = np.random.default_rng(4000 + k)
    e = (1 - t / dur) ** 2 * amp
    return rng.normal() * e, rng.normal() * e * 0.6


# --------------------------------------------------------------------------------------------------------- night
NOS_ON, NOS_OFF = 140, 186


def speed(k):
    """lamps per frame: cruising, gathering speed, the NOS, easing off"""
    base = 0.05 + 0.13 * smooth((k - 10) / 120) + 0.25 * smooth((k - NOS_ON) / 6) - 0.36 * smooth((k - NOS_OFF) / 50)
    return max(base, 0.05)


class Night:
    def __init__(self, src):
        self.t = Title(src)
        sp = np.array([speed(k) for k in range(N)])
        self.phase = np.concatenate([[0], np.cumsum(sp)])[:N]
        tot = self.phase[-1] + sp[-1]
        self.phase *= round(tot) / tot                                   # a whole number of lamps per loop
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy

    def frame(self, k):
        k = k % N
        t = self.t
        ph = self.phase[k]; sp = speed(k)
        nos = seg(k, NOS_ON, NOS_ON + 6) * (1 - seg(k, NOS_OFF, NOS_OFF + 30))
        lamp_col = SODIUM * (1 - nos) + NOS * nos
        span = t.lw + 700; xr = t.x0 + t.lw + 300
        # each lamp's reflection runs right to left across the chrome; at speed it smears into a line
        refl = np.zeros((H, W), np.float32); spill = np.zeros((H, W), np.float32)
        wid = 14 + 560 * sp
        for n in range(int(ph) - 4, int(ph) + 3):
            p = xr - (ph - n) * span * 0.55
            if p < t.x0 - 600 or p > xr + 300:
                continue
            band = np.exp(-((t.u - p) / wid) ** 2)
            refl += band
            spill += np.exp(-((self.xx - p) / 360) ** 2)
        refl = np.clip(refl, 0, 1.6)
        # the reflection is brightest on faces turned up and on the upper bevels (lamps are overhead)
        up = np.clip(-t.ny * 1.6 + 0.55, 0, 1.3)
        hl = refl * up * t.a
        # the title: chrome in the dark keeps a little of its own reflection; the lamps add theirs
        base = t.rgb * (0.42 + 0.06 * nos)
        img = np.zeros((H, W, 3), np.float32)
        # the street: nothing but the lamps' light passing over the dark
        img += (spill * (0.08 + 0.05 * nos))[..., None] * lamp_col * smooth((self.yy - 40) / 500)[..., None]
        streak = 260 * nos
        a = t.a; rgb = base + (hl[..., None] * lamp_col) * 2.1
        if streak > 1:
            a2 = hstreak(a, streak); rgb2 = hstreak(rgb * a[..., None], streak)
            a = np.maximum(a, a2 * 0.75); rgb = np.where(a[..., None] > 1e-3, (rgb * t.a[..., None] + rgb2 * 0.75) / np.maximum(a[..., None], 1e-3), rgb)
        img = img * (1 - a[..., None]) + np.clip(rgb, 0, 2) * a[..., None]
        img += bigblur(hl, 10)[..., None] * lamp_col * 0.18
        img = img * (1 - t.col[..., None]) + np.array([0.80, 0.83, 0.88], np.float32) * t.col[..., None]
        sx, sy = shake(k, NOS_ON + 1, 7.0, 22)
        if abs(sx) + abs(sy) > 0.05:
            img = cv2.warpAffine(img, np.float32([[1, 0, sx], [0, 1, sy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        img = img / (1 + 0.3 * img) * 1.3
        return to_image(img, k, self.grain)


# --------------------------------------------------------------------------------------------------------- rev
RPM_KEYS = [(0, 0.9), (6, 0.9), (30, 6.8), (34, 4.4), (66, 7.0), (70, 4.8), (104, 7.2), (108, 5.2), (138, 8.4),
            (150, 8.6), (186, 8.4), (226, 0.9), (250, 0.9)]


def rpm(k):
    for (k0, v0), (k1, v1) in zip(RPM_KEYS, RPM_KEYS[1:]):
        if k0 <= k <= k1:
            u = (k - k0) / max(k1 - k0, 1)
            u = u if v1 >= v0 and (k1 - k0) > 6 else smooth(u)
            return v0 + (v1 - v0) * u + (0.06 * math.sin(k * 3.1) if v1 > 6 else 0)
    return 0.9


class Rev:
    CX, CY, R = 640, 770, 640                                            # the dial, big and low behind the title
    A0, A1 = math.radians(160), math.radians(20)                          # 0 .. 9 (x1000 rpm), clockwise

    def ang(self, r):
        return self.A0 + (self.A1 - self.A0) * r / 9.0

    def __init__(self, src):
        self.t = Title(src, top=170)
        S = 2
        dial = np.zeros((H * S, W * S), np.float32); red = np.zeros_like(dial)
        cx, cy, R = self.CX * S, self.CY * S, self.R * S
        for i in range(0, 91):
            r = i / 10.0; a = self.ang(r)
            major = i % 10 == 0
            l0 = R * (0.86 if major else 0.91); l1 = R * 0.97
            p0 = (int(cx + l0 * math.cos(a)), int(cy - l0 * math.sin(a))); p1 = (int(cx + l1 * math.cos(a)), int(cy - l1 * math.sin(a)))
            tgt = red if r >= 7 else dial
            cv2.line(tgt, p0, p1, 1.0, (9 if major else 4), cv2.LINE_AA)
        # the arc
        cv2.ellipse(dial, (cx, cy), (int(R * 0.99), int(R * 0.99)), 0, -220, 40 - 360 + 360 * 0, 0.0, 1)
        pts = [(int(cx + R * 0.995 * math.cos(self.ang(r))), int(cy - R * 0.995 * math.sin(self.ang(r)))) for r in np.linspace(0, 7, 120)]
        cv2.polylines(dial, [np.array(pts, np.int32)], False, 0.8, 5, cv2.LINE_AA)
        pts = [(int(cx + R * 0.995 * math.cos(self.ang(r))), int(cy - R * 0.995 * math.sin(self.ang(r)))) for r in np.linspace(7, 9, 40)]
        cv2.polylines(red, [np.array(pts, np.int32)], False, 1.0, 9, cv2.LINE_AA)
        # numerals
        im = Image.new("L", (W * S, H * S), 0); d = ImageDraw.Draw(im)
        f = ImageFont.truetype(os.path.join(src, "Montserrat-VF.ttf"), 64); f.set_variation_by_axes([600])
        for i in range(10):
            a = self.ang(i); rr = R * 0.76
            d.text((cx + rr * math.cos(a), cy - rr * math.sin(a)), str(i), font=f, fill=255 if i < 7 else 0, anchor="mm")
        dial = np.maximum(dial, np.asarray(im, np.float32) / 255)
        imr = Image.new("L", (W * S, H * S), 0); d = ImageDraw.Draw(imr)
        for i in (7, 8, 9):
            a = self.ang(i); rr = R * 0.76
            d.text((cx + rr * math.cos(a), cy - rr * math.sin(a)), str(i), font=f, fill=255, anchor="mm")
        red = np.maximum(red, np.asarray(imr, np.float32) / 255)
        self.dial = cv2.resize(dial, (W, H), interpolation=cv2.INTER_AREA)
        self.red = cv2.resize(red, (W, H), interpolation=cv2.INTER_AREA)
        # out of focus: a real lens, not a glow
        self.dial_b = disc_blur(self.dial, 9); self.red_b = disc_blur(self.red, 9)
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy

    def needle(self, r):
        m = np.zeros((H * 2, W * 2), np.float32)
        a = self.ang(r); cx, cy, R = self.CX * 2, self.CY * 2, self.R * 2
        p0 = (int(cx - 0.12 * R * math.cos(a)), int(cy + 0.12 * R * math.sin(a)))
        p1 = (int(cx + 0.93 * R * math.cos(a)), int(cy - 0.93 * R * math.sin(a)))
        cv2.line(m, p0, p1, 1.0, 10, cv2.LINE_AA)
        cv2.circle(m, (cx, cy), int(0.07 * R), 0.6, -1, cv2.LINE_AA)
        return disc_blur(cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA), 8)

    def frame(self, k):
        k = k % N
        t = self.t
        r = rpm(k)
        nos = seg(k, 138, 144) * (1 - seg(k, 186, 214))
        col = EL * (1 - nos) + NOS * nos
        redc = np.array([1.0, 0.18, 0.12], np.float32)
        needle = self.needle(r)
        hot = smooth((r - 6.6) / 1.4)                                    # the red zone lights as the needle reaches it
        img = (self.dial_b[..., None] * col * (0.55 + 0.2 * nos) + self.red_b[..., None] * redc * (0.35 + 0.45 * hot)
               + needle[..., None] * np.array([1.0, 0.45, 0.2], np.float32) * 1.1)
        glow = bigblur(img, 50)
        img = img + glow * 0.6
        # the gauge's light on the chrome: the bevels facing down catch it
        facing = np.clip(t.ny * 1.4 + 0.25, 0, 1.2)
        lightc = glow.mean(axis=(0, 1)) / (glow.mean() + 1e-4)
        env = bigblur(img, 30)
        hl = (facing * t.a)[..., None] * env * 2.6
        base = t.rgb * (0.5 + 0.08 * nos)
        rgb = base + hl
        a = t.a
        streak = 240 * nos
        if streak > 1:
            a2 = hstreak(a, streak); rgb2 = hstreak(rgb * a[..., None], streak)
            a = np.maximum(a, a2 * 0.75)
            rgb = np.where(a[..., None] > 1e-3, (rgb * t.a[..., None] + rgb2 * 0.75) / np.maximum(a[..., None], 1e-3), rgb)
        img = img * (1 - 0.85 * bigblur(t.a, 14))[..., None]               # the title stands in front of the dial
        img = img * (1 - a[..., None]) + np.clip(rgb, 0, 2) * a[..., None]
        img = img * (1 - 0.7 * np.clip(bigblur(t.col, 12) * 1.6, 0, 1))[..., None]
        img = img * (1 - t.col[..., None]) + np.array([0.82, 0.85, 0.9], np.float32) * t.col[..., None]
        sx, sy = shake(k, 139, 6.0, 20)
        if abs(sx) + abs(sy) > 0.05:
            img = cv2.warpAffine(img, np.float32([[1, 0, sx], [0, 1, sy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        img = img / (1 + 0.3 * img) * 1.3
        return to_image(img, k, self.grain)


def render(src, out, mode, only=None, mp4=None):
    s = Night(src) if mode == "night" else Rev(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "night"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
