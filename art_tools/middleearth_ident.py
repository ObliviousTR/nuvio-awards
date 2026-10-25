"""Middle-earth card, as a title ident: the title in gold inside the One Ring's inscription, THE COLLECTION under it.
Hover (10 s): as if the Ring were in the fire, the inscription heats letter by letter round the circle until it burns
orange and gold (starting in its gap, not in a word), embers rise, the heat shimmers and the title takes the warm
light and comes forward, waits and goes back; then the inscription cools back to dark gold.
The title never leaves the screen. First frame = last frame = cover.
Titles (--title):
  lotr    - The Lord of the Rings film title logo (TMDB, film 120), its subtitle removed
  stacked - the same title's own letters set in three lines (THE LORD / OF THE / RINGS), inside the ring
  game   - MIDDLE-EARTH set like the Middle-earth game series header (spaced Cinzel between ruled ornaments)
  split  - MIDDLE / THE COLLECTION / EARTH, set across the ring like the stacked title
  ring   - MIDDLE-EARTH in Ringbearer (the films' lettering), chiselled in the gold of the film title (me_wordmark)
usage: python3 art_tools/middleearth_ident.py SRC_DIR OUT_DIR --title lotr|stacked|game|ring|split [--frames a,b] [--scale s] [--mp4 p]
  SRC_DIR: inscription.png (the Ring inscription, TMDB film 120 logo), lotr_title.png, lotr_stacked.png, cinzel.ttf, ringbearer.ttf
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
T_ZOOM = (58, 94, 128, 170)  # the lockup comes forward, waits, goes back
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
        # the lockup (title + THE COLLECTION) is built once at its largest size and scaled per frame: it sits inside
        # the ring on the cover and comes forward (to the size of a full-width title) while the ring burns, then goes back
        D = round(684 * sc)                                   # the inscription's diameter
        inner = D * 0.63                                      # its inner diameter: the lockup fits inside on the cover
        self.zmax = 1.6
        Z = self.zmax
        sub_m = text_mask("THE COLLECTION", os.path.join(src, "cinzel.ttf"), round(18 * sc * Z), round(9 * sc * Z))
        subcol = ramp[150] * 0.95

        def rgba_from_mask(m, col):
            return np.dstack([np.ones_like(m)[..., None] * col[None, None, :], m[..., None]]).astype(np.float32)

        def rgba_from_img(im):
            g = np.asarray(im, np.float32); g[..., :3] = g[..., :3]; g[..., 3] /= 255; return g

        def fit(g, w):
            f = w / g.shape[1]
            return cv2.resize(g, (max(1, round(g.shape[1] * f)), max(1, round(g.shape[0] * f))), interpolation=cv2.INTER_AREA)

        def stack(parts, gap, align="c"):
            """parts: [(rgba, align)] top to bottom"""
            wmax = max(p[0].shape[1] for p in parts)
            hsum = sum(p[0].shape[0] for p in parts) + gap * (len(parts) - 1)
            out = np.zeros((hsum, wmax, 4), np.float32); y = 0
            for g, al in parts:
                h, w = g.shape[:2]
                x = 0 if al == "l" else (wmax - w if al == "r" else (wmax - w) // 2)
                out[y:y + h, x:x + w] = np.where(g[..., 3:4] > out[y:y + h, x:x + w, 3:4], g, out[y:y + h, x:x + w])
                y += h + gap
            return out
        sub = rgba_from_mask(sub_m, subcol)
        if title in ("lotr", "stacked"):
            g = rgba_from_img(Image.open(os.path.join(src, "lotr_title.png" if title == "lotr" else "lotr_stacked.png")).convert("RGBA"))
            g = fit(g, inner * (0.86 if title == "lotr" else 0.72) * Z)
            block = stack([(g, "c"), (sub, "c")], round(24 * sc * Z))
        elif title in ("ring", "split"):
            from me_wordmark import wordmark
            rb, lt = os.path.join(src, "ringbearer.ttf"), os.path.join(src, "lotr_title.png")
            if title == "ring":
                wm = rgba_from_img(wordmark(rb, lt, height=round(112 * sc * Z)))
                wm = fit(wm, inner * 0.86 * Z)
                block = stack([(wm, "c"), (sub, "c")], round(26 * sc * Z))
            else:
                mid = rgba_from_img(wordmark(rb, lt, height=round(112 * sc * Z), words=("MIDDLE",)))
                ear = rgba_from_img(wordmark(rb, lt, height=round(112 * sc * Z), words=("EARTH",)))
                k_ = inner * 0.60 * Z / mid.shape[1]
                mid = fit(mid, mid.shape[1] * k_); ear = fit(ear, ear.shape[1] * k_)
                # THE COLLECTION between them, with a fine rule either side
                rule = round(46 * sc * Z); pad = round(14 * sc * Z)
                sh_, sw_ = sub_m.shape
                row = np.zeros((sh_, sw_ + 2 * (rule + pad)), np.float32)
                row[:, rule + pad:rule + pad + sw_] = sub_m
                cyr = sh_ // 2; t_ = max(1, round(1.3 * sc * Z))
                row[cyr - t_ // 2:cyr - t_ // 2 + t_, :rule] = 0.85
                row[cyr - t_ // 2:cyr - t_ // 2 + t_, -rule:] = 0.85
                mid_row = rgba_from_mask(row, subcol)
                wtot = max(mid.shape[1], ear.shape[1], mid_row.shape[1]) + round(inner * 0.16 * Z)
                def place(g, al):
                    out = np.zeros((g.shape[0], wtot, 4), np.float32)
                    x = 0 if al == "l" else (wtot - g.shape[1] if al == "r" else (wtot - g.shape[1]) // 2)
                    out[:, x:x + g.shape[1]] = g; return out
                block = stack([(place(mid, "l"), "c"), (place(mid_row, "c"), "c"), (place(ear, "r"), "c")], round(10 * sc * Z))
        else:
            m = text_mask("MIDDLE-EARTH", os.path.join(src, "cinzel.ttf"), round(74 * sc * Z), round(16 * sc * Z))
            rows = ramp[np.clip((np.arange(m.shape[0]) / m.shape[0] * 255).astype(int), 0, 255)]
            g = np.dstack([rows[:, None, :] * bevel_light(m, 3 * sc * Z)[..., None], m[..., None]]).astype(np.float32)
            g = fit(g, inner * 0.86 * Z)
            block = stack([(g, "c"), (sub, "c")], round(26 * sc * Z))
        self.block = block
        # the inscription round it
        ins = Image.open(os.path.join(src, "inscription.png")).convert("RGBA")
        ins = np.asarray(ins.resize((D, round(ins.height * D / ins.width)), Image.LANCZOS), np.float32) / 255
        ih, iw = ins.shape[:2]
        self.ia = np.zeros((H, W), np.float32)
        self.cx, self.cy = W / 2, H / 2
        # the circle's true centre in the inscription picture (a least-squares circle through its letters), which is a
        # little right of and below the picture's middle: put that on the card's centre, not the picture's middle
        al_ = ins[..., 3]; ys_, xs_ = np.nonzero(al_ > 0.4)
        Dl, El, Fl = np.linalg.lstsq(np.c_[xs_, ys_, np.ones_like(xs_)], -(xs_ ** 2 + ys_ ** 2).astype(np.float64), rcond=None)[0]
        ccx, ccy = -Dl / 2, -El / 2
        ix, iy = round(self.cx - ccx), round(self.cy - ccy)
        y0, y1 = max(0, iy), min(H, iy + ih); x0, x1 = max(0, ix), min(W, ix + iw)
        self.ia[y0:y1, x0:x1] = ins[y0 - iy:y1 - iy, x0 - ix:x1 - ix, 3]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.yy, self.xx = yy, xx
        ang = (np.arctan2(yy - self.cy, xx - self.cx) + math.pi / 2) % (2 * math.pi) / (2 * math.pi)   # 0 at top, clockwise
        ang = (ang - 0.158) % 1.0                             # start where the inscription has its gap (about 2 o'clock)
        self.ang = ang
        self.ilight = bevel_light(self.ia, 1.5 * sc)
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
        if total > 0.05 and getattr(self, 'shimmer', True):
            sh = (np.sin(self.yy / (9 * sc) + k * 0.9) * np.cos(self.xx / (23 * sc) - k * 0.4)) * 1.6 * sc * total
            img = cv2.remap(img.astype(np.float32), (self.xx + sh).astype(np.float32), (self.yy - abs(sh) * 0.5).astype(np.float32),
                            cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # the lockup, taking the warm light; it comes forward while the ring burns, waits, and goes back
        z = 1 + (self.zmax - 1) * seg(k, T_ZOOM[:2]) * (1 - seg(k, T_ZOOM[2:]))
        f = z / self.zmax
        g = self.block if abs(f - 1) < 1e-6 else cv2.resize(self.block, (max(1, round(self.block.shape[1] * f)), max(1, round(self.block.shape[0] * f))),
                                                            interpolation=cv2.INTER_AREA)
        bh, bw = g.shape[:2]
        x0, y0 = round(self.cx - bw / 2), round(self.cy - bh / 2)
        lay = np.zeros((H, W, 4), np.float32)
        sx0, sy0 = max(0, -x0), max(0, -y0); dx0, dy0 = max(0, x0), max(0, y0)
        ww, hh = min(bw - sx0, W - dx0), min(bh - sy0, H - dy0)
        lay[dy0:dy0 + hh, dx0:dx0 + ww] = g[sy0:sy0 + hh, sx0:sx0 + ww]
        ta = lay[..., 3:4]
        warm = 1 + 0.35 * total
        tcol = lay[..., :3] * warm + total * np.array([30, 12, 0], np.float32) * ta
        shadow = cv2.GaussianBlur(lay[..., 3], (0, 0), 6 * sc * z)[..., None]
        img = img * (1 - 0.6 * shadow)
        img = img * (1 - ta) + tcol * ta
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
