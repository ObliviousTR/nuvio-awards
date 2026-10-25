"""MCU card, the approved comic-page ident (mcu_ident.py, --layout universe) given a world around it: the films that flip
inside CINEMATIC UNIVERSE light the dark around the frame and a black glossy floor under it, the frame stands on that
floor and its reflection lies in it, and the camera arcs slowly round it, so the box turns a little in space (the
reflection with it). The closing flash and light sweep of the first version are gone.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/mcu_light.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]
  SRC_DIR: as for mcu_ident.py (marvel-studios.svg, Oswald-VF.ttf, stills/NN_*.jpg)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import mcu_ident as mi

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
LIFT = 46                                                                # the box sits higher, the floor below it


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


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


class Scene(mi.Scene):
    def __init__(self, src):
        mi.T_FLASH = 10 ** 6; mi.T_SWEEP = (10 ** 6, 10 ** 6 + 1); mi.T_ZOOM = (10 ** 6, 10 ** 6 + 1)
        super().__init__(src, "universe", 1.0)
        self.bg = np.zeros((H, W, 3), np.float32)
        self.alpha = np.clip(np.maximum(np.maximum(self.red, self.white), self.fill), 0, 1)
        ys = np.nonzero(self.alpha.max(1) > 0.2)[0]
        self.bottom = int(ys.max()) - LIFT
        self.floor = self.bottom + 5
        self.cx, self.cy = W / 2, (ys.min() + ys.max()) / 2 - LIFT
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.X, self.Y = xx, yy
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        self.floor_tex = noise(H, W, 1.2, 4)

    def homography(self, k):
        ph = 2 * math.pi * k / N
        yaw = 0.035 * math.sin(ph)                                      # the camera arcs a little round the box
        push = 1.0 + 0.04 * (1 - math.cos(ph)) / 2
        w2, h2 = 520.0, 170.0
        src = np.float32([[self.cx - w2, self.cy - h2], [self.cx + w2, self.cy - h2], [self.cx + w2, self.cy + h2], [self.cx - w2, self.cy + h2]])
        dst = []
        for (x, y) in src:
            side = (x - self.cx) / w2
            zz = 1 + yaw * side                                          # the near side grows, the far side shrinks
            dx = (x - self.cx) * push * (1 - abs(yaw) * 0.6) + yaw * 60
            dy = (y - self.cy) * push * zz
            dst.append([self.cx + dx, self.cy + dy])
        return cv2.getPerspectiveTransform(src, np.float32(dst))

    def frame(self, k):
        k = k % N
        logo = np.asarray(super().frame(k), np.float32) / 255          # the box on black, as approved
        logo = np.roll(logo, -LIFT, axis=0); a = np.roll(self.alpha, -LIFT, axis=0)
        Hm = self.homography(k)
        logo = cv2.warpPerspective(logo, Hm, (W, H), flags=cv2.INTER_LINEAR)
        a = cv2.warpPerspective(a, Hm, (W, H), flags=cv2.INTER_LINEAR)
        # the room: dark, lit only by the box (what is playing in it) - spill on the back and on the floor
        spill = bigblur(logo, 90)
        back = np.array([0.012, 0.010, 0.012], np.float32) + spill * 1.3
        img = back.copy()
        # the floor: black gloss, the box mirrored in it, softer and fainter with distance
        below = (self.Y > self.floor).astype(np.float32)
        my = (2 * self.floor - self.Y).astype(np.float32)
        refl = cv2.remap(logo, self.X, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        dist = np.clip(self.Y - self.floor, 0, None)
        r1 = bigblur(refl, 6); r2 = bigblur(refl, 22)
        mixb = np.clip(dist / 120, 0, 1)[..., None]
        refl = r1 * (1 - mixb) + r2 * mixb
        fres = (0.32 * np.exp(-dist / 150))[..., None]
        floor = np.array([0.006, 0.006, 0.007], np.float32) + spill * 1.6 * (0.9 + 0.2 * self.floor_tex[..., None]) + refl * fres
        img = img * (1 - below[..., None]) + floor * below[..., None]
        # contact: the box sits on the floor
        img *= (1 - 0.5 * np.exp(-((self.Y - self.floor) / 6) ** 2) * (np.abs(self.X - W / 2) < 500))[..., None]
        img = img * (1 - a[..., None]) + logo
        rr = np.sqrt(((self.X - W / 2) / (W * 0.62)) ** 2 + ((self.Y - H / 2) / (H * 0.68)) ** 2)
        img *= (1 - 0.4 * np.clip(rr - 0.45, 0, 1))[..., None]
        gx = (k * 37) % W; gy = (k * 53) % H
        img = img + (self.grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * 0.02
        return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


def render(src, out, only=None, mp4=None):
    s = Scene(src)
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
