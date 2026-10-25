"""Star Trek card, redone without the stacked effects of startrek_delta.py: one light event per hover, the 2016
franchise logo (its own glow and light line) as it is, THE COLLECTION always readable.

--mode orbit  Orbit: below the logo the night side of a planet, its limb a thin line of atmosphere; the sun rises over
              the limb to the right of the delta, the atmosphere lights from deep orange at the surface to blue above,
              the sun throws one anamorphic streak (the films' lenses) and the chrome letters catch it on their lower
              edges; the orbit carries the sun back under the limb for the cover.
--mode warp   Warp, once: the stars begin to stretch away from the delta, the ship goes to warp and the streaks pour
              past, then it drops out of warp and the streaks shrink back into stars; nothing else moves but the logo's
              own glow, which follows the speed.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/startrek_orbit.py SRC_DIR OUT_DIR [--mode orbit|warp] [--frames a,b] [--mp4 path]
  SRC_DIR: logo_plate.jpg (the franchise logo on black), Antonio.ttf (as for startrek_delta.py)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import startrek_delta as sd

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / (b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0.05 else a


def noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta; spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


class Base(sd.Scene):
    def __init__(self, src):
        super().__init__(src, 1.0)
        rng = np.random.default_rng(3)
        n = 1400
        self.fx = rng.uniform(0, W, n); self.fy = rng.uniform(0, H, n); self.fb = rng.uniform(0.15, 1.0, n) ** 2
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def still_stars(self, dx=0.0, mask=None):
        lay = np.zeros((H * 2, W * 2), np.float32)
        for x, y, b in zip(self.fx, self.fy, self.fb):
            x = (x + dx) % W
            cv2.circle(lay, (int(x * 2 * 4), int(y * 2 * 4)), 4 + int(4 * b), float(b), -1, cv2.LINE_AA, 2)
        lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_AREA)
        return lay

    def logo(self, img, gain=1.0, light=None):
        res = self.res * gain
        if light is not None:
            res = res + light
        img = img * (1 - self.pa[..., None]) + self.glow_img * gain + res
        return img

    def collection(self, img):
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        lay = Image.merge("RGBA", (Image.new("L", self.sub.size, 196), Image.new("L", self.sub.size, 212), Image.new("L", self.sub.size, 232), self.sub))
        x = round(W / 2 - self.sub.width / 2)
        sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
        a = np.zeros((H, W), np.float32); a[self.suby:self.suby + self.sub.height, x:x + self.sub.width] = np.asarray(self.sub, np.float32) / 255
        a = np.clip(cv2.GaussianBlur(a, (0, 0), 14) * 3.0, 0, 1) * 0.9
        base = np.asarray(out, np.float32)[..., :3] * (1 - a[..., None])
        out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        out.alpha_composite(lay, (x, self.suby))
        return np.asarray(out.convert("RGB"), np.float32)

    def finish(self, img, k, amt=0.025):
        img = img * self.vig[..., None]
        img = self.collection(img)
        gx = (k * 37) % W; gy = (k * 53) % H
        img = img + (self.grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * 255 * amt
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


# --------------------------------------------------------------------------------------------------------- orbit
RISE = (16, 100); SET = (176, 236)


class Orbit(Base):
    def __init__(self, src):
        super().__init__(src)
        self.R = 1900.0; self.pcx = 560.0; self.pcy = 618 + self.R          # the limb at y ~ 618, curving away
        d = np.sqrt((self.xx - self.pcx) ** 2 + (self.yy - self.pcy) ** 2)
        self.h = d - self.R                                                  # height above the limb (px), < 0 = surface
        self.ang = np.arctan2(self.xx - self.pcx, -(self.yy - self.pcy))      # angle along the limb
        cl = noise(H, W * 2, 1.6, 8)
        self.clouds = cv2.resize(cl, (W * 2, H))
        self.sun_x = 930.0

    def sun(self, k):
        u = seg(k, *RISE) * (1 - seg(k, *SET))
        return u

    def frame(self, k):
        k = k % N
        u = self.sun(k)
        ph = 2 * math.pi * k / N
        drift = 10 * math.sin(ph)                                           # the orbit: the planet turns a little under us
        sx = self.sun_x + drift
        sy = self.pcy - math.sqrt(self.R ** 2 - (sx - self.pcx) ** 2) + 10 - 26 * u   # just over the limb                      # the sun climbs over the limb
        img = np.zeros((H, W, 3), np.float32) + sd.NAVY * 0.8
        st = self.still_stars(dx=drift * 0.2)
        img += st[..., None] * np.array([190, 210, 245], np.float32) * (1 - 0.6 * u)   # the sun dims the stars
        # the planet: night side, a faint cloud deck seen where the sun begins to light it
        surf = (self.h < 0).astype(np.float32)
        surf = blur(surf, 1.0)
        dsun = np.sqrt((self.xx - sx) ** 2 + ((self.yy - sy) * 2.2) ** 2)
        cl = self.clouds[:, int(400 + drift * 3):int(400 + drift * 3) + W]
        lit_surf = np.exp(-dsun / 260) * u * (0.4 + 0.6 * cl) * np.exp(self.h / 140)
        planet = np.array([4, 7, 14], np.float32) + lit_surf[..., None] * np.array([150, 160, 175], np.float32)
        img = img * (1 - surf[..., None]) + planet * surf[..., None]
        # the atmosphere: a thin shell above the limb, orange low, blue high, strongest towards the sun
        hh = np.clip(self.h, 0, None)
        shell = (self.h > -2) * np.exp(-hh / 16.0)
        along = np.exp(-((self.xx - sx) / 420) ** 2)
        base_rim = 0.10 + 0.9 * along * u
        low = np.exp(-hh / 6.0); high = np.exp(-hh / 26.0) - low * 0.5
        atm = (low[..., None] * np.array([255, 150, 70], np.float32) * along[..., None] * u
               + np.clip(high, 0, None)[..., None] * np.array([70, 140, 255], np.float32))
        img += atm * (shell * base_rim)[..., None] * 1.8
        img += np.exp(-np.clip(self.h, 0, None) / 60)[..., None] * (self.h > 0)[..., None] * along[..., None] * u * np.array([10, 22, 45], np.float32)
        # the sun: a small hard disc on the limb, a soft bloom, one anamorphic streak (the films' lenses)
        dx = self.xx - sx; dy = self.yy - sy
        core = np.exp(-(dx * dx + dy * dy) / (2 * 7.0 ** 2)) * (self.h > -4)
        bloom = np.exp(-np.sqrt(dx * dx + dy * dy) / 55)
        streak = np.exp(-(dy / 2.0) ** 2) * np.exp(-np.abs(dx) / 520)
        img += (core * 255 * 2.0 * u)[..., None]
        img += (bloom * u * 0.8)[..., None] * np.array([255, 225, 190], np.float32)
        img += (streak * u * 0.75)[..., None] * np.array([150, 200, 255], np.float32)
        # the chrome catches the sunrise on the lower edges of its letters
        gy = cv2.Sobel(self.pa, cv2.CV_32F, 0, 1, ksize=3)
        lower = np.clip(-gy * 1.4, 0, 1) * self.lm
        near = np.exp(-((self.xx - sx) / 420) ** 2)
        light = (lower * near * u)[..., None] * np.array([255, 205, 160], np.float32) * 0.7
        light += (self.lm * near * u * 0.12)[..., None] * np.array([255, 220, 190], np.float32)
        img = self.logo(img, gain=1.0 + 0.06 * u, light=light)
        return self.finish(img, k)


# --------------------------------------------------------------------------------------------------------- warp
T_W = (12, 74, 128, 190)


def env(k, t):
    a, b, c, d = t
    return seg(k, a, b) * (1 - seg(k, c, d))


class Warp(Base):
    def __init__(self, src):
        super().__init__(src)
        v = np.array([env(k, T_W) ** 1.6 for k in range(N + 1)]) + 0.002
        cum = np.concatenate([[0], np.cumsum(v[:-1])])
        cycles = 3
        self.travel = cum / cum[-1] * cycles
        self.speed = v / cum[-1] * cycles
        self._env = env

    def frame(self, k):
        k = k % N
        w = env(k, T_W)
        img = np.zeros((H, W, 3), np.float32) + sd.NAVY
        sd_env = sd.env4
        sd.env4 = lambda kk, t: env(kk, T_W)
        st = self.stars(k)
        sd.env4 = sd_env
        img += st[..., None] * np.array([200, 220, 255], np.float32) * (0.75 + 0.25 * w)
        img += cv2.GaussianBlur(st, (0, 0), 2.5)[..., None] * sd.ICE * 0.35 * w
        img = self.logo(img, gain=1.0 + 0.12 * w)
        return self.finish(img, k)


def render(src, out, mode, only=None, mp4=None):
    s = Orbit(src) if mode == "orbit" else Warp(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "orbit"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
