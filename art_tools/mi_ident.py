"""Mission: Impossible card: the red MISSION: IMPOSSIBLE of Dead / Final Reckoning, on screen for the whole hover.

The fuse runs under the title from left to right - a single hot point of light with a long anamorphic streak, no
particles - and where it has passed the red letters open onto the series' signature stunts, film by film (the
Langley vault, the aquarium, the Burj Khalifa, the A400M door, the HALO jump, the helicopter, the rooftop leap, the
cliff jump, the paraglider, the biplane), cut on the beat, each pushing in slowly; the rest of the still shows dimly
around the letters. The fuse runs back from right to left and the title is red again.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/mi_ident.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]
  SRC_DIR: title.png (the Final Reckoning title logo on TMDB, film 575265; only the MISSION: IMPOSSIBLE line is used),
           stills/NN_*.jpg (official TMDB backdrops, in order), BarlowCondensed-Medium.ttf
"""
import glob, math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
# where the subject of each still is (share of width, height): it is placed on the title
FOCUS = [(0.42, 0.48), (0.55, 0.42), (0.48, 0.4), (0.38, 0.36), (0.5, 0.45), (0.6, 0.58), (0.6, 0.5),
         (0.76, 0.45), (0.53, 0.55), (0.52, 0.5), (0.43, 0.55)]
T_IN = (3, 30)               # the fuse runs left to right
T_OUT = (204, 231)           # and back
CUT0, CUTLEN = 30, 16        # the cuts


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def bigblur(a, s):
    h, w = a.shape[:2]
    sm = cv2.resize(a, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), s / 4)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)


def text_layer(font, size, txt, track, shear=0.0):
    f = ImageFont.truetype(font, size)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 80, size * 2), 0)
    d = ImageDraw.Draw(m); x = 40
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    if shear:
        m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * m.height * 0.75, 0, 1, 0), Image.BICUBIC)
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


class Scene:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        a = np.asarray(Image.open(os.path.join(src, "title.png")).convert("RGBA"), np.float32)[:540]
        ys, xs = np.where(a[..., 3] > 10); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        lw = 1080; lh = round(a.shape[0] * lw / a.shape[1])
        a = cv2.resize(a, (lw, lh), interpolation=cv2.INTER_AREA)
        self.top = 296 - lh // 2; self.x0 = (W - lw) // 2; self.lw, self.lh = lw, lh
        self.la = np.zeros((H, W), np.float32); self.red = np.zeros((H, W, 3), np.float32)
        self.la[self.top:self.top + lh, self.x0:self.x0 + lw] = a[..., 3] / 255
        self.red[self.top:self.top + lh, self.x0:self.x0 + lw] = a[..., :3]
        m = (self.la > 0.5).astype(np.uint8)
        self.rim = blur(np.clip(self.la - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1), 0.6)
        self.cy = self.top + lh / 2
        sub = text_layer(os.path.join(src, "BarlowCondensed-Medium.ttf"), 58, "THE COLLECTION", 40, shear=0.2)
        self.sub = np.zeros((H, W), np.float32)
        sy = self.top + lh + 22; sx = (W - sub.shape[1]) // 2
        self.sub[sy:sy + sub.shape[0], sx:sx + sub.shape[1]] = sub
        self.fy = self.top + lh + 10                                        # the fuse runs just under the title
        self.stills = []
        for i, f in enumerate(sorted(glob.glob(os.path.join(src, "stills", "*.jpg")))):
            im = np.asarray(Image.open(f).convert("RGB"), np.float32)
            s = max(W * 1.22 / im.shape[1], H * 1.22 / im.shape[0])
            im = cv2.resize(im, (round(im.shape[1] * s), round(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
            fx, fy = FOCUS[i % len(FOCUS)]
            ox = float(np.clip(fx * im.shape[1] - W / 2, 0, im.shape[1] - W))
            oy = float(np.clip(fy * im.shape[0] - self.cy, 0, im.shape[0] - H))
            im = np.clip((im - 128) * 1.08 + 128, 0, 255).astype(np.float32)
            self.stills.append((im, ox, oy))
        self.n = len(self.stills)
        self._cache = {}

    def still(self, k):
        if k in self._cache:
            return self._cache[k]
        i = min(self.n - 1, max(0, (k - CUT0) // CUTLEN))
        t = max(0.0, ((k - CUT0) - i * CUTLEN) / CUTLEN)
        im, ox, oy = self.stills[i]
        z = 1.0 + 0.06 * min(1.8, t)                                        # slow push in
        cx, cy = W / 2, self.cy
        M = np.float32([[z, 0, -ox * z + cx * (1 - z)], [0, z, -oy * z + cy * (1 - z)]])
        out = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        self._cache = {k: out}
        return out

    def fuse(self, k):
        for (a, b), rev in ((T_IN, False), (T_OUT, True)):
            if a <= k <= b:
                v = (k - a) / (b - a)
                u = 0.85 * v + 0.15 * float(smooth(v))
                x = self.x0 - 40 + u * (self.lw + 80)
                return (self.x0 + self.lw + self.x0 - x) if rev else x
        return None

    def frame(self, k):
        hx = self.fuse(k)
        if hx is not None:
            openm = smooth((hx - self.xx) / 18)
        elif T_IN[1] < k < T_OUT[0]:
            openm = np.ones((H, W), np.float32)
        else:
            openm = np.zeros((H, W), np.float32)
        img = np.zeros((H, W, 3), np.float32) + np.array([5, 4, 4], np.float32)
        img += (bigblur(self.la, 40) * 0.5)[..., None] * np.array([90, 8, 4], np.float32) * (1 - openm[..., None])
        st = self.still(k) if openm.max() > 0 else None
        if st is not None:
            if T_IN[0] <= k <= T_IN[1]:
                g = float(smooth((k - T_IN[0]) / (T_IN[1] - T_IN[0])))
            elif T_OUT[0] <= k <= T_OUT[1]:
                g = 1 - float(smooth((k - T_OUT[0]) / (T_OUT[1] - T_OUT[0])))
            else:
                g = 1.0
            img = img * (1 - 0.9 * g) + st * (0.16 * g)                     # a dim memory around (fades, no wipe)
            img += bigblur(st * (self.la * openm)[..., None], 26) * 0.3                    # light from the letters
        a = self.la[..., None]
        letters = self.red * (1 - openm[..., None])
        if st is not None:
            fill = 255 * (st / 255) ** 1.12 * 0.95                           # a touch deeper inside the letters
            letters = letters + fill * openm[..., None] + (self.rim * openm * 0.8)[..., None] * np.array([230, 30, 20], np.float32)
        img = img * (1 - a) + letters * a
        if hx is not None:                                                  # the fuse's head
            fl = 0.9 + 0.1 * math.sin(k * 2.3)
            d2 = (self.xx - hx) ** 2 + (self.yy - self.fy) ** 2
            core = np.exp(-d2 / (2 * 2.2 ** 2)); halo = np.exp(-d2 / (2 * 18.0 ** 2)); wide = np.exp(-d2 / (2 * 120.0 ** 2))
            streak = np.exp(-((self.yy - self.fy) / 1.6) ** 2) * np.exp(-np.abs(self.xx - hx) / 380)
            img += ((core * 3.0 + halo * 0.9) * fl)[..., None] * np.array([255, 236, 210], np.float32)
            img += ((wide * 0.35 + streak * 0.9) * fl)[..., None] * np.array([255, 120, 50], np.float32)
            under = np.exp(-((self.xx - hx) / 90) ** 2) * self.la * smooth((self.yy - self.top - self.lh * 0.4) / (self.lh * 0.6))
            img += (under * 0.8 * fl)[..., None] * np.array([255, 170, 110], np.float32)
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([238, 236, 232], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.45 * np.clip(rr - 0.4, 0, 1))[..., None]
        img += np.random.default_rng(900 + k).normal(size=(H, W)).astype(np.float32)[..., None] * 1.5
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


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
