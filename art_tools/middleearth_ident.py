"""Middle-earth card, as a title ident: the title in gold inside the One Ring's inscription, THE COLLECTION under it.
Hover (10 s): as if the Ring were in the fire, the inscription heats letter by letter round the circle until it burns
orange and gold, embers rise, the heat shimmers and the title takes the warm light; then it cools back to dark gold.
The title never leaves the screen. First frame = last frame = cover.
Titles (--title):
  lotr   - The Lord of the Rings film title logo (TMDB, film 120), its subtitle removed
  game   - MIDDLE-EARTH set like the Middle-earth game series header (spaced Cinzel between ruled ornaments)
  ring   - MIDDLE-EARTH in Ringbearer (the films' lettering), chiselled in the gold of the film title (me_wordmark)
usage: python3 art_tools/middleearth_ident.py SRC_DIR OUT_DIR --title lotr|game|ring [--frames a,b] [--scale s] [--mp4 p]
  SRC_DIR: inscription.png (the Ring inscription, TMDB film 120 logo), lotr_title.png, cinzel.ttf, ringbearer.ttf
  (Ringbearer is freeware, not redistributed: dafont.com/ringbearer.font, RINGM___.TTF)
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

GW, GH, MS, N = 512, 288, 40, 250
T_HEAT = (16, 150)          # the heat runs round the circle
T_HOLD = (150, 180)
T_COOL = (176, 228)
BG = np.array([9, 6, 4], np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def sarr(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab; return smooth((k - a) / max(1, b - a))


def gold_ramp(src):
    """the film title's gold, as a colour per height (top to bottom)"""
    g = np.asarray(Image.open(os.path.join(src, "lotr_title.png")).convert("RGBA"), np.float32)
    a = g[..., 3] > 200
    rows = [g[y, :, :3][a[y]].mean(0) if a[y].sum() > 50 else None for y in range(g.shape[0])]
    ys = [i for i, r in enumerate(rows) if r is not None]
    top, bot = int(g.shape[0] * 0.18), int(g.shape[0] * 0.78)
    pts = np.array([rows[y] for y in ys if top <= y <= bot])
    return cv2.resize(pts[None], (1, 256), interpolation=cv2.INTER_LINEAR)[:, 0]


def bevel_light(mask, r):
    m = (mask > 0.5).astype(np.uint8)
    d = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    h = cv2.GaussianBlur(np.clip(d / r, 0, 1) ** 0.7, (0, 0), 0.8)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    return np.clip(0.75 - (gx + gy) * 1.6, 0.35, 1.35).astype(np.float32)


def text_mask(txt, font, size, track):
    f = ImageFont.truetype(font, size * 2)
    try:
        f.set_variation_by_axes([600])
    except Exception:
        pass
    ws = [f.getlength(c) for c in txt]
    im = Image.new("L", (round(sum(ws) + track * 2 * len(txt)) + 60, size * 4), 0)
    d = ImageDraw.Draw(im); x = 30
    for c, w in zip(txt, ws):
        d.text((x, size * 3), c, font=f, fill=255, anchor="ls"); x += w + track * 2
    im = im.crop(im.getbbox())
    return np.asarray(im.resize((im.width // 2, im.height // 2), Image.LANCZOS), np.float32) / 255


class Scene:
    def __init__(self, src, title, sc=1.0):
        W, H = self.W, self.H = round(1280 * sc), round(720 * sc)
        self.sc = sc
        ramp = gold_ramp(src)
        # the title
        if title == "lotr":
            g = np.asarray(Image.open(os.path.join(src, "lotr_title.png")).convert("RGBA"), np.float32) / 255
            tw = round(780 * sc); th = round(g.shape[0] * tw / g.shape[1])
            g = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA)
            trgb, ta = g[..., :3] * 255, g[..., 3]
        else:
            if title == "ring":
                from me_wordmark import wordmark
                wm = wordmark(os.path.join(src, "ringbearer.ttf"), os.path.join(src, "lotr_title.png"), height=round(112 * sc))
                g = np.asarray(wm, np.float32) / 255
                m = None
            else:
                m = text_mask("MIDDLE-EARTH", os.path.join(src, "cinzel.ttf"), round(74 * sc), round(16 * sc))
                # the game header's ruled ornaments either side
                pad = round(110 * sc); h0 = m.shape[0]
                mm = np.zeros((h0, m.shape[1] + 2 * pad), np.float32); mm[:, pad:pad + m.shape[1]] = m
                cy = h0 // 2
                orn = Image.new("L", (mm.shape[1] * 4, h0 * 4), 0); d = ImageDraw.Draw(orn)
                for side in (-1, 1):
                    x_in = (pad - round(24 * sc)) if side < 0 else (pad + m.shape[1] + round(24 * sc))
                    x_out = round(6 * sc) if side < 0 else mm.shape[1] - round(6 * sc)
                    d.line([(x_out * 4, cy * 4), (x_in * 4, cy * 4)], fill=255, width=max(4, round(2.2 * sc * 4)))
                    for xd in (x_in + side * round(-10 * sc), x_out + side * round(-14 * sc)):
                        r = 6 * sc
                        d.polygon([((xd - r) * 4, cy * 4), (xd * 4, (cy - r) * 4), ((xd + r) * 4, cy * 4), (xd * 4, (cy + r) * 4)], fill=255)
                orn = np.asarray(orn.resize((mm.shape[1], h0), Image.LANCZOS), np.float32) / 255
                m = np.maximum(mm, orn)
            if m is None:
                th, tw = g.shape[:2]; trgb, ta = g[..., :3] * 255, g[..., 3]
            else:
                th, tw = m.shape
                rows = ramp[np.clip((np.arange(th) / th * 255).astype(int), 0, 255)]
                light = bevel_light(m, 3 * sc)
                trgb = rows[:, None, :] * light[..., None]
                ta = m
        self.cx, self.cy = W / 2, round(318 * sc)
        tx, ty = round(self.cx - tw / 2), round(self.cy - th / 2)
        self.trgb = np.zeros((H, W, 3), np.float32); self.ta = np.zeros((H, W), np.float32)
        self.trgb[ty:ty + th, tx:tx + tw] = trgb; self.ta[ty:ty + th, tx:tx + tw] = ta
        self.tbox = (tx, ty, tw, th)
        # the inscription round it
        ins = Image.open(os.path.join(src, "inscription.png")).convert("RGBA")
        D = round(560 * sc)
        ins = np.asarray(ins.resize((D, round(ins.height * D / ins.width)), Image.LANCZOS), np.float32) / 255
        ih, iw = ins.shape[:2]
        self.ia = np.zeros((H, W), np.float32)
        ix, iy = round(self.cx - iw / 2), round(self.cy - ih / 2)
        y0, y1 = max(0, iy), min(H, iy + ih); x0, x1 = max(0, ix), min(W, ix + iw)
        self.ia[y0:y1, x0:x1] = ins[y0 - iy:y1 - iy, x0 - ix:x1 - ix, 3]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.yy, self.xx = yy, xx
        ang = (np.arctan2(yy - self.cy, xx - self.cx) + math.pi / 2) % (2 * math.pi) / (2 * math.pi)   # 0 at top, clockwise
        self.ang = ang
        self.ilight = bevel_light(self.ia, 1.5 * sc)
        # THE COLLECTION
        sub = text_mask("THE COLLECTION", os.path.join(src, "cinzel.ttf"), round(20 * sc), round(11 * sc))
        sh, sw = sub.shape
        self.sub = np.zeros((H, W), np.float32)
        sy = ty + th + round(30 * sc) if title != "lotr" else ty + th + round(22 * sc)
        self.sub[sy:sy + sh, round(self.cx - sw / 2):round(self.cx - sw / 2) + sw] = sub
        self.subcol = ramp[150] * 0.95
        # embers
        r = np.random.default_rng(9)
        self.ne = 140
        self.ea = r.uniform(0, 2 * math.pi, self.ne); self.er = r.uniform(0.85, 1.05, self.ne) * D / 2
        self.ev = r.uniform(0.6, 1.4, self.ne); self.eph = r.uniform(0, 1, self.ne); self.esz = r.uniform(0.8, 2.2, self.ne) * sc
        d = np.sqrt(((xx - self.cx) / (W * 0.5)) ** 2 + ((yy - self.cy) / (H * 0.55)) ** 2)
        self.bg = BG + np.exp(-(d / 0.55) ** 2)[..., None] * np.array([34, 20, 10], np.float32)
        vg = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        self.vig = 1 - 0.5 * np.clip(vg - 0.4, 0, 1) ** 1.3
        self.haze = None

    def frame(self, k):
        W, H, sc = self.W, self.H, self.sc
        front = (k - T_HEAT[0]) / (T_HEAT[1] - T_HEAT[0])                     # 0..1 round the circle
        heat_on = np.clip((front * 1.15 - self.ang) / 0.15, 0, 1) if front > 0 else np.zeros_like(self.ang)
        cool = 1 - seg(k, T_COOL)
        heat = sarr(heat_on) * cool
        if k >= T_HEAT[1]:
            heat = np.full_like(self.ang, cool)
        flick = 0.88 + 0.12 * np.sin(self.ang * 40 + k * 0.6) * math.sin(k * 0.37 + 1)
        H_ = heat * flick
        total = float(heat.mean())
        img = self.bg * (1 + 0.6 * total)
        # the inscription: dark gold, then red-hot to gold-white
        cold = np.array([96, 70, 34], np.float32) * self.ilight[..., None]
        hot = np.array([255, 150, 50], np.float32) * (1 - H_[..., None] * 0.3) + np.array([255, 235, 170], np.float32) * (H_[..., None] * 0.6)
        icol = cold * (1 - H_[..., None]) + hot * H_[..., None]
        a = self.ia[..., None]
        glow = cv2.GaussianBlur(self.ia * H_, (0, 0), 8 * sc)[..., None] * np.array([255, 110, 25], np.float32) * 1.4 \
            + cv2.GaussianBlur(self.ia * H_, (0, 0), 26 * sc)[..., None] * np.array([255, 90, 20], np.float32) * 0.9
        img = img + glow
        img = img * (1 - a) + icol * a
        # embers rising from the ring while it burns
        if total > 0.01:
            lay = np.zeros((H, W), np.float32)
            for i in range(self.ne):
                t = (k / N * 3 * self.ev[i] + self.eph[i]) % 1.0
                ex = self.cx + math.cos(self.ea[i]) * self.er[i] + 18 * sc * math.sin(t * 9 + i)
                ey = self.cy + math.sin(self.ea[i]) * self.er[i] - t * 220 * sc
                b = float(heat.flat[min(H * W - 1, int(np.clip(self.cy + math.sin(self.ea[i]) * self.er[i], 0, H - 1)) * W
                                     + int(np.clip(self.cx + math.cos(self.ea[i]) * self.er[i], 0, W - 1)))]) * (1 - t)
                if b > 0.02 and 0 <= ex < W and 0 <= ey < H:
                    cv2.circle(lay, (int(ex * 4), int(ey * 4)), max(1, int(self.esz[i] * 4)), b, -1, cv2.LINE_AA, 2)
            img += cv2.GaussianBlur(lay, (0, 0), 1.5 * sc)[..., None] * np.array([255, 160, 60], np.float32) * 1.6
        # heat shimmer over the whole picture while it burns
        if total > 0.05:
            sh = (np.sin(self.yy / (9 * sc) + k * 0.9) * np.cos(self.xx / (23 * sc) - k * 0.4)) * 1.6 * sc * total
            img = cv2.remap(img.astype(np.float32), (self.xx + sh).astype(np.float32), (self.yy - abs(sh) * 0.5).astype(np.float32),
                            cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # the title, taking the warm light
        warm = 1 + 0.35 * total
        tcol = self.trgb * warm + total * np.array([30, 12, 0], np.float32) * self.ta[..., None]
        ta = self.ta[..., None]
        shadow = cv2.GaussianBlur(self.ta, (0, 0), 6 * sc)[..., None]
        img = img * (1 - 0.6 * shadow)
        img = img * (1 - ta) + tcol * ta
        s_ = self.sub[..., None]
        img = img * (1 - s_) + (self.subcol * (1 + 0.3 * total))[None, None, :] * s_
        img *= self.vig[..., None]
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def render(src, out, title, only=None, sc=1.0, mp4=None):
    s = Scene(src, title, sc)
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
    render(a[1], a[2], a[a.index("--title") + 1], only, sc, mp4)
