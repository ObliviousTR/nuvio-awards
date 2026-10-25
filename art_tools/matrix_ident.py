"""Matrix card: THE MATRIX title over the digital rain, the title on screen for the whole hover.

modes
  code    (the 1999 opening, where the title forms out of the code) the title glows pale green. Code columns fall into
          the letters one by one and the letters turn into running code - the title is made of falling glyphs for a
          while, the rain behind wakes up - then the glyphs lock, column by column from left to right, each with a
          flash, and the title is solid again.
  mirror  (Neo touching the mirror) the title is dark chrome reflecting the green rain. A touch lands in the middle of
          it and a ripple runs out through the letters like liquid mirror, bending the rain behind; a second smaller
          touch on the X; the surface settles.
Both: 250 frames at 40 ms, first frame = last frame = cover; every rain column falls a whole number of times per loop.
usage: python3 art_tools/matrix_ident.py SRC_DIR OUT_DIR --mode code|mirror [--frames a,b] [--mp4 path]
  SRC_DIR: logo.svg (The Matrix title logo on TMDB, vector), MPLUS1Code.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
from matrix_rain import Rain

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
GREEN = np.array([70, 255, 110], np.float32)
PALE = np.array([214, 255, 222], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / max(1, b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def code_layer(rain, k, cs):
    """the rain at cell size cs over the whole frame: glyph brightness and the bright heads"""
    A = rain.atlas(cs)
    R, C = H // cs + 2, W // cs + 2
    b, g, hd = rain.field(k, 0, R, 0, C)
    lum = (A[g] * b[..., None, None]).transpose(0, 2, 1, 3).reshape(R * cs, C * cs)[:H, :W]
    heads = (A[g] * hd[..., None, None]).transpose(0, 2, 1, 3).reshape(R * cs, C * cs)[:H, :W]
    return lum, heads


class Base:
    def __init__(self, src, lw=820, cy=322):
        import cairosvg
        png = cairosvg.svg2png(url=os.path.join(src, "logo.svg"), output_width=lw * 3)
        from io import BytesIO
        lg = Image.open(BytesIO(png)).convert("RGBA")
        lg = lg.crop(lg.getchannel("A").getbbox())
        lh = round(lg.height * lw / lg.width)
        a = np.asarray(lg.getchannel("A").resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.x0, self.y0, self.lw, self.lh = (W - lw) // 2, cy - lh // 2, lw, lh
        self.la = np.zeros((H, W), np.float32); self.la[self.y0:self.y0 + lh, self.x0:self.x0 + lw] = a
        self.rain = Rain(os.path.join(src, "MPLUS1Code.ttf"))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        f = ImageFont.truetype(os.path.join(src, "MPLUS1Code.ttf"), 46); f.set_variation_by_axes([500])
        txt, tr = "THE COLLECTION", 24
        m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 20, 70), 0)
        d = ImageDraw.Draw(m); x = 10
        for c in txt:
            d.text((x, 52), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        self.sub = np.zeros((H, W), np.float32)
        sx, sy = (W - m.width) // 2, self.y0 + lh + 30
        self.sub[sy:sy + m.height, sx:sx + m.width] = np.asarray(m, np.float32) / 255
        pocket = blur(cv2.dilate(np.maximum(self.la, self.sub), np.ones((15, 15), np.uint8)), 24)
        self.pocket = np.clip(pocket * 1.7, 0, 1)

    def background(self, k, bright):
        lum, heads = code_layer(self.rain, k, 18)
        img = lum[..., None] * GREEN * bright + heads[..., None] * np.array([150, 120, 140], np.float32) * bright
        img += blur(lum, 2.2)[..., None] * GREEN * 0.45 * bright
        img *= (1 - 0.82 * self.pocket)[..., None]
        return img

    def finish(self, img, sub_a=1.0):
        img = img * (1 - self.sub * sub_a)[..., None] + (self.sub * sub_a)[..., None] * np.array([120, 255, 150], np.float32)
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


class Code(Base):
    T_IN = (24, 64)          # columns start falling into the letters
    T_LOCK = (150, 186)      # glyphs lock, left to right

    def __init__(self, src):
        super().__init__(src)
        self.inner = Rain(os.path.join(src, "MPLUS1Code.ttf"), seed=11)
        rng = np.random.default_rng(5)
        self.inner.m = rng.integers(3, 7, self.inner.cols)            # faster than the rain behind
        self.inner.L = rng.integers(24, 60, self.inner.cols)          # long trails: the letters stay full
        self.inner.P = self.inner.rows // 4 + self.inner.L + rng.integers(0, 10, self.inner.cols)
        cs = 9; ncol = W // cs + 2
        t0 = rng.uniform(*self.T_IN, ncol)
        col = (self.xx // cs).astype(int)
        self.t_in = t0[col] + np.clip((self.yy - self.y0) / self.lh, 0, 1) * 14
        self.t_out = self.T_LOCK[0] + np.clip((self.xx - self.x0) / self.lw, 0, 1) * (self.T_LOCK[1] - self.T_LOCK[0] - 6)
        m = (self.la > 0.5).astype(np.uint8)
        self.rim = blur(np.clip(self.la - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1), 0.6)
        self.g1, self.g2 = blur(self.la, 4), blur(self.la, 16)

    def frame(self, k):
        wake = seg(k, 60, 96) * (1 - seg(k, 160, 200))
        img = self.background(k, 0.45 + 0.4 * wake)
        C = smooth((k - self.t_in) / 6) * (1 - smooth((k - self.t_out) / 5))
        flash = np.exp(-((k - self.t_out - 2) / 2.4) ** 2) * (np.abs(k - self.t_out - 2) < 9)
        lum, heads = code_layer(self.inner, k, 9)
        code = (lum * 1.5 + 0.2)[..., None] * GREEN + heads[..., None] * np.array([200, 120, 200], np.float32)
        code = np.clip(code, 0, 255)
        solid = PALE
        a = self.la[..., None]
        Cc = C[..., None]
        pulse = 0.0 if k < 180 else math.exp(-((k - 190) / 8.0) ** 2)
        glow = (self.g1 * 0.9 + self.g2 * 0.6) * (1 - C * 0.75) * (1 + 1.2 * pulse)
        img += glow[..., None] * GREEN * 0.55
        letter = solid * (1 - Cc) + code * Cc
        img = img * (1 - a) + letter * a
        img += (self.rim * C * 0.9)[..., None] * GREEN
        img += ((self.la * 0.9 + self.g1 * 0.8) * flash)[..., None] * np.array([230, 255, 235], np.float32)
        return self.finish(img)


class Mirror(Base):
    TOUCHES = [(44, 0.5, 1.0, 112), (126, 0.93, 0.55, 90)]      # frame, x along the title, strength, life

    def __init__(self, src):
        super().__init__(src)
        m = (self.la > 0.5).astype(np.uint8)
        bw = 2.6
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        self.hgt = blur(smooth(dt / bw).astype(np.float32), 0.6)
        self.bw = bw
        self.gy_v = np.clip((self.yy - self.y0) / self.lh, 0, 1)

    def ripple(self, k):
        h = np.zeros((H, W), np.float32)
        for k0, fx, st, life in self.TOUCHES:
            t = k - k0
            if t < 0 or t > life:
                continue
            cx, cy = self.x0 + fx * self.lw, self.y0 + self.lh * 0.55
            r = np.sqrt((self.xx - cx) ** 2 + ((self.yy - cy) * 1.15) ** 2)
            front = 11.0 * t
            env = smooth((front - r) / 30) * np.exp(-r / 260) * (1 - seg(t, life * 0.45, life)) * smooth(t / 3)
            h += st * env * np.sin(2 * math.pi * (r - front) / 46.0)
        return h

    def frame(self, k):
        h = self.ripple(k)
        gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8
        D = 34.0
        mapx = self.xx - gx * D; mapy = self.yy - gy * D
        bg = self.background(k, 0.45)
        bg = cv2.remap(bg.astype(np.float32), self.xx - gx * D * 0.6, self.yy - gy * D * 0.6, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        bg *= (1 + 0.35 * np.clip(h, -1, 1))[..., None]                 # the rain catches the ripple faintly
        # chrome: bevel normals + the ripple's slope, reflecting the rain and a soft sky
        la = cv2.remap(self.la, mapx, mapy, cv2.INTER_LINEAR)
        hg = cv2.remap(self.hgt, mapx, mapy, cv2.INTER_LINEAR)
        nx = -cv2.Sobel(hg, cv2.CV_32F, 1, 0, ksize=3) / 8 * self.bw - gx * 16
        ny = -cv2.Sobel(hg, cv2.CV_32F, 0, 1, ksize=3) / 8 * self.bw - gy * 16
        nz = np.ones_like(nx); nn = np.sqrt(nx * nx + ny * ny + 1); nx, ny, nz = nx / nn, ny / nn, nz / nn
        lum, _ = code_layer(self.rain, k, 18)
        env = blur(lum, 3)
        ex = self.xx + nx * 90; ey = self.yy + ny * 90 - 40
        refl = cv2.remap(env, ex, ey, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        sky = np.clip(0.5 - ny * 0.9, 0, 1) ** 2
        L = np.array([-0.35, -0.8, 0.5]); L /= np.linalg.norm(L)
        spec = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1) ** 28
        g = cv2.remap(self.gy_v, mapx, mapy, cv2.INTER_LINEAR)
        # classic chrome: a bright sky above a dark horizon band, a lighter floor below; the ripple bends the horizon
        v = np.clip(g + ny * 0.9 + nx * 0.15, -0.5, 1.5)
        top = np.array([200, 236, 218], np.float32); hor = np.array([16, 34, 30], np.float32)
        flo = np.array([96, 150, 128], np.float32)
        a1 = smooth((v - 0.22) / 0.3)[..., None]; a2 = smooth((v - 0.62) / 0.3)[..., None]
        base = top * (1 - a1) + hor * a1
        base = base * (1 - a2) + flo * a2
        chrome = base * 0.85 + refl[..., None] * np.array([60, 230, 120], np.float32) * 0.7 \
            + sky[..., None] * np.array([40, 60, 55], np.float32) + spec[..., None] * np.array([235, 255, 240], np.float32)
        glow = blur(la, 5)
        bg += glow[..., None] * GREEN * 0.22
        img = bg * (1 - la[..., None]) + chrome * la[..., None]
        for k0, fx, st, life in self.TOUCHES:                       # the touch itself: a small glint
            t = k - k0
            if 0 <= t < 14:
                cx, cy = self.x0 + fx * self.lw, self.y0 + self.lh * 0.55
                spot = np.exp(-(((self.xx - cx) ** 2 + (self.yy - cy) ** 2) / (2 * (6 + 1.5 * t) ** 2)))
                img += (spot * st * (1 - t / 14) * 0.9)[..., None] * np.array([200, 255, 210], np.float32)
        return self.finish(img)


MODES = {"code": Code, "mirror": Mirror}


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
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=70)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print(mode, "seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    a = sys.argv
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mode = a[a.index("--mode") + 1] if "--mode" in a else "code"
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
