"""Batman card, lit the way The Batman (2022) is lit: dark but readable, the image carried by single sources of light.
The title (TMDB) and THE COLLECTION are those of the approved card (batman_ident.py); nothing is drawn but light.

--mode hallway  The hallway: the power is cut and the only light is the gunfire. The red title goes dark; short hard
                bursts from off the frame (never the flashes themselves, only their light) strike it from one side then
                another, catching the edges of the letters and the bat, throwing the title's shadow on the concrete
                behind; between bursts it is black and the camera has stepped closer; then the light comes back.
--mode signal   The signal: the film's own shot of the Bat-Signal on the clouds over Gotham (TMDB backdrop), the signal
                taken out of the clouds for the dark state. The projector strikes, the signal comes up in the clouds
                over the title, its light catches the title's edges from behind and the bat in the title answers; it
                goes out and the cover is back.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/batman_light.py SRC_DIR OUT_DIR [--mode hallway|signal] [--frames a,b] [--mp4 path]
  SRC_DIR: title.png, title_batmask.png (as for batman_ident.py), Oswald-VF.ttf, signal.jpg (TMDB backdrop
           4evjdaPnAimHieQzQR0wgTbqc4M, film 414906)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
TW = 800


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


def spaced(txt, font_path, size, track, weight):
    f = ImageFont.truetype(font_path, size * 2)
    f.set_variation_by_axes([weight])
    m = Image.new("L", (int(sum(f.getlength(c) for c in txt) + track * 2 * len(txt)) + 40, size * 4), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 3), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track * 2
    m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
    return np.asarray(m, np.float32) / 255


def to_image(img, k, grain, amt=0.03):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


class Title:
    def __init__(self, src, cy=300):
        t = Image.open(os.path.join(src, "title.png")).convert("RGBA"); box = t.getbbox(); t = t.crop(box)
        self.th = round(t.height * TW / t.width)
        self.tx, self.ty = (W - TW) // 2, cy - self.th // 2
        arr = np.asarray(t.resize((TW, self.th), Image.LANCZOS), np.float32) / 255
        self.rgb = np.zeros((H, W, 3), np.float32); self.a = np.zeros((H, W), np.float32)
        self.rgb[self.ty:self.ty + self.th, self.tx:self.tx + TW] = arr[..., :3]
        self.a[self.ty:self.ty + self.th, self.tx:self.tx + TW] = arr[..., 3]
        bm = Image.open(os.path.join(src, "title_batmask.png")).convert("L").crop(box).resize((TW, self.th), Image.LANCZOS)
        self.bat = np.zeros((H, W), np.float32); self.bat[self.ty:self.ty + self.th, self.tx:self.tx + TW] = np.asarray(bm, np.float32) / 255
        sub = spaced("THE COLLECTION", os.path.join(src, "Oswald-VF.ttf"), 22, 18, 500)
        self.sub = np.zeros((H, W), np.float32)
        sy = self.ty + self.th + 28; sx = (W - sub.shape[1]) // 2
        self.sub[sy:sy + sub.shape[0], sx:sx + sub.shape[1]] = sub
        self.subc = np.array([214, 52, 44], np.float32) / 255
        # the letters as thin plates: the relief that catches a raking light
        solid = (self.a > 0.5).astype(np.uint8)
        hgt = blur(np.clip(cv2.distanceTransform(solid, cv2.DIST_L2, 5) / 4.0, 0, 1), 0.8)
        lum = self.rgb.mean(2)
        hgt = hgt + (lum - blur(lum, 2.0)) * 1.2                          # the scratches of the print
        self.nx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3); self.ny = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3)
        self.mask = np.maximum(self.a, self.sub)


# --------------------------------------------------------------------------------------------------------- hallway
# bursts: (start frame, light position (x, y, z in front of the title), strobe pattern)
BURSTS = [(16, (-260, 420, 260), [1.0, 0.15, 0.85, 0.0, 0.6]),
          (44, (1560, 260, 300), [0.9, 0.0, 1.0, 0.25, 0.8, 0.0, 0.5]),
          (70, (300, 980, 240), [1.0, 0.3, 0.7]),
          (94, (1500, 640, 220), [0.8, 0.0, 1.0, 0.1, 0.9, 0.2]),
          (120, (-200, 120, 300), [1.0, 0.1, 0.8, 0.0, 0.7, 0.0, 0.4]),
          (148, (980, 1000, 200), [1.0, 0.2, 0.9, 0.1, 1.0, 0.3, 0.6, 0.0, 0.4])]
DARK0, LIGHT0 = 10, 186                                                  # the power goes / comes back
DEPTH = 46.0


class Hallway:
    def __init__(self, src):
        self.t = Title(src)
        n1 = noise(H, W, 1.8, 3); n2 = noise(H, W, 1.1, 4); n3 = noise(H, W, 0.5, 5)
        self.wall = (0.5 + 0.28 * (n1 - 0.5) + 0.16 * (n2 - 0.5) + 0.08 * (n3 - 0.5))[..., None] * np.array([0.9, 0.9, 0.92], np.float32)
        hw = n2 * 1.2 + blur(n3, 1.0) * 0.3
        self.wnx = cv2.Sobel(hw, cv2.CV_32F, 1, 0, ksize=3); self.wny = cv2.Sobel(hw, cv2.CV_32F, 0, 1, ksize=3)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def flash(self, k):
        for k0, pos, pat in BURSTS:
            j = k - k0
            if 0 <= j < len(pat):
                return pat[j], np.array(pos, np.float32), k0
        return 0.0, None, None

    def zoom(self, k):
        steps = sum(1 for k0, _, _ in BURSTS if k >= k0 + 6)
        z = 1.0 + 0.022 * steps
        return 1.0 + (z - 1.0) * (1 - seg(k, LIGHT0 + 4, LIGHT0 + 50))

    def frame(self, k):
        k = k % N
        t = self.t
        f, pos, _ = self.flash(k)
        room = 1.0 - seg(k, DARK0, DARK0 + 3) * (1 - seg(k, LIGHT0, LIGHT0 + 14))
        # the light coming back: a fluorescent tube that catches on the second try
        if LIGHT0 <= k < LIGHT0 + 14:
            room = [0.0, 0.5, 0.1, 0.0, 0.0, 0.7, 0.35, 0.85, 0.9, 1.0, 1.0, 1.0, 1.0, 1.0][k - LIGHT0]
        base = t.rgb * (0.04 + 0.96 * room)
        img = np.zeros((H, W, 3), np.float32) + np.array([0.003, 0.003, 0.004], np.float32)
        warm = np.array([1.0, 0.86, 0.66], np.float32)
        if f > 0:
            # irradiance on the wall and on the title from a point source in front
            for plane in ("wall", "title"):
                z = pos[2] + (0 if plane == "wall" else -DEPTH)
                dx = self.xx - pos[0]; dy = self.yy - pos[1]
                d2 = dx * dx + dy * dy + z * z; d = np.sqrt(d2)
                L = np.dstack([-dx / d, -dy / d, z / d])
                if plane == "wall":
                    nx, ny = self.wnx * 0.4, self.wny * 0.4
                else:
                    nx, ny = t.nx, t.ny
                nn = np.sqrt(nx * nx + ny * ny + 1)
                ndl = np.clip((-nx * L[..., 0] - ny * L[..., 1] + L[..., 2]) / nn, 0, 1.2)
                E = ndl * (z / d) * 9.0e5 / d2 * f
                if plane == "wall":
                    # the title's shadow on the wall: the title's mask pushed away from the light
                    sx = (W / 2 - pos[0]) / pos[2] * DEPTH; sy = ((t.ty + t.th / 2) - pos[1]) / pos[2] * DEPTH
                    sh = blur(cv2.warpAffine(t.mask, np.float32([[1, 0, sx], [0, 1, sy]]), (W, H)), 4)
                    img = img + self.wall * 0.38 * (E * (1 - 0.92 * sh))[..., None] * warm
                else:
                    Et = E
            lit = t.rgb * (Et[..., None] * warm * 1.6)
            # edges facing the source flare (the print's varnish)
            rim = np.clip((-t.nx * L[..., 0] - t.ny * L[..., 1]) * 1.6, 0, 1) * np.clip(Et, 0, 1.5) * 0.45
            lit = lit + rim[..., None] * warm
        else:
            lit = 0.0
        face = base + lit
        a = t.a[..., None]
        img = img * (1 - a) + face * a
        sub = t.sub[..., None]
        subl = 0.04 + 0.96 * room + (f * 0.9 if f > 0 else 0)
        img = img * (1 - sub) + t.subc * min(subl, 1.4) * sub
        z = self.zoom(k)
        if z > 1.0005:
            M = cv2.getRotationMatrix2D((W / 2, t.ty + t.th / 2), 0, z)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        img = img / (1 + 0.3 * img) * 1.3
        return to_image(img, k, self.grain, 0.03 + 0.02 * (1 - room))


# --------------------------------------------------------------------------------------------------------- signal
SIG_ON, SIG_OFF = 10, 196
STRIKE = [0.0, 0.55, 0.1, 0.0, 0.75, 0.4, 0.9]


class Signal:
    def __init__(self, src):
        self.t = Title(src, cy=372)
        a = Image.open(os.path.join(src, "signal.jpg")).convert("RGB")
        k0 = 1280 / a.width
        a = np.asarray(a.resize((1280, round(a.height * k0)), Image.LANCZOS), np.float32) / 255   # work at 1280 wide
        h, w = a.shape[:2]
        # the signal's glow taken out of the clouds for the dark state
        cx, cy = 410, 285
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        rr = np.sqrt(((xx - cx) / 175) ** 2 + ((yy - cy) / 150) ** 2)
        m = (rr < 1).astype(np.uint8)
        off = cv2.inpaint((a * 255).astype(np.uint8), m, 25, cv2.INPAINT_TELEA).astype(np.float32) / 255
        off = blur(off, 0) * 1.0
        feather = smooth((1.25 - rr) / 0.35)[..., None]
        off = a * (1 - feather) + blur(off, 6) * feather
        glow = np.clip(a - off, 0, None)
        # place the plate: the signal over the title, a little left of centre, the spire on the right
        s = 1.38
        self.plate_s = s
        size = (round(w * s), round(h * s))
        full = np.asarray(Image.open(os.path.join(src, "signal.jpg")).convert("RGB").resize(size, Image.LANCZOS), np.float32) / 255
        up = lambda x: cv2.resize(x, size, interpolation=cv2.INTER_CUBIC)
        self.lit = full
        self.glow = np.clip(up(glow), 0, None)
        self.off = np.clip(full - self.glow, 0, 1)
        self.ox = 560 - cx * s; self.oy = 120 - cy * s
        self.sig = np.array([560.0, 120.0])
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy

    def level(self, k):
        if k < SIG_ON:
            return 0.0
        j = k - SIG_ON
        if j < len(STRIKE):
            return STRIKE[j]
        if k >= SIG_OFF:
            return 1.0 - seg(k, SIG_OFF, SIG_OFF + 30)
        return 1.0 + 0.02 * math.sin(k * 0.7)

    def frame(self, k):
        k = k % N
        t = self.t
        lv = self.level(k)
        ph = 2 * math.pi * k / N
        drift = 14 * (1 - math.cos(ph)) / 2                              # the clouds move; the camera drifts with them
        z = 1.0 + 0.03 * (1 - math.cos(ph)) / 2
        M = np.float32([[z, 0, self.ox - drift], [0, z, self.oy]])
        plate = self.off + self.glow * lv
        bg = cv2.warpAffine(plate, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # grade: night, blue-grey, the signal's light warm
        lum = bg.mean(2, keepdims=True)
        bg = lum * np.array([0.62, 0.68, 0.80], np.float32) * 0.55 + (bg - lum) * 0.3
        sx, sy = M[0, 0] * 410 + M[0, 2], M[1, 1] * 285 + M[1, 2]
        warmglow = np.exp(-(((self.xx - sx) / 230) ** 2 + ((self.yy - sy) / 190) ** 2)) * lv
        bg = bg + warmglow[..., None] * np.array([0.10, 0.08, 0.05], np.float32)
        img = bg
        # the title in front: dark, red, its edges toward the signal catch the light from behind
        a = t.a[..., None]
        img = img * (1 - 0.6 * blur(t.mask, 10))[..., None]
        L = np.array([sx, sy]); dx = self.xx - L[0]; dy = self.yy - L[1]; d = np.sqrt(dx * dx + dy * dy) + 1
        facing = np.clip((t.nx * dx + t.ny * dy) / d * 1.8, 0, 1)
        rim = facing ** 1.5 * np.exp(-d / 420) * lv * 0.55
        face = t.rgb * (0.88 + 0.12 * lv) + rim[..., None] * np.array([1.0, 0.9, 0.75], np.float32)
        face = face * (1 + (t.bat * lv * 0.35)[..., None])             # the bat in the title answers the signal
        img = img * (1 - a) + face * a
        sub = t.sub[..., None]
        img = img * (1 - sub) + t.subc * sub
        img = img / (1 + 0.2 * img) * 1.2
        return to_image(img, k, self.grain, 0.035)


def render(src, out, mode, only=None, mp4=None):
    s = Hallway(src) if mode == "hallway" else Signal(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "hallway"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
