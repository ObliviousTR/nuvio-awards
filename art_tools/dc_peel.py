"""DC card, as the DC "peel" ident (DC Entertainment, Landor 2012; used on the films 2012-2016): the steel D with its
corner peeled back over the dark C beneath, DC UNIVERSE and THE COLLECTION under it, on a deep night blue.
Hover (10 s): light rises behind the logo and shines through the C; the peel lifts further back and stays lifted,
breathing, while the C underneath shows the heroes one after another - Superman, Batman, Wonder Woman, Green Lantern,
The Flash - their emblems embossed in the steel, as in the character versions of the peel; then the peel settles
back, the light goes down and the card is the cover again. The logo never leaves the screen.
The peel is modelled, not traced: the D (a box and a circle), the C (the D minus a round counter and a mouth), a fold
line, and the flap as the peeled part folded back over the fold and foreshortened by the curl. The geometry is
measured from the DC Entertainment logo, in its pixels (D from x 14 to 277, y 5 to 295).
usage: python3 art_tools/dc_peel.py SRC_DIR OUT_DIR [--frames a,b] [--scale s] [--mp4 path]
  SRC_DIR: Montserrat-VF.ttf
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

GW, GH, MS, N = 512, 288, 40, 250
X0, Y0, Y1 = 14.0, 5.0, 295.0
CX, CY, R = 133.3, 150.0, 143.9
KX, KY, KR = 121.0, 152.5, 81.0
MY0, MY1 = 136.0, 168.0
F0 = np.array([100.0, 5.0]); F1 = np.array([207.0, 270.0])
CURL, SHEAR = 0.75, -0.25
T_LIFT = (18, 52); T_DROP = (196, 228)
T_LIGHT = (12, 50); T_DARK = (200, 234)
T_EMB = (50, 196)
NAVY = np.array([5, 8, 17], np.float32)
EMBLEMS = ["superman", "batman", "wonderwoman", "lantern", "flash"]


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab; return smooth((k - a) / max(1, b - a))


def d_mask(xx, yy):
    inside = (yy >= Y0) & (yy <= Y1) & (xx >= X0)
    return inside & ((xx <= CX) | ((xx - CX) ** 2 + (yy - CY) ** 2 <= R * R))


def c_mask(xx, yy):
    m = d_mask(xx, yy) & ((xx - KX) ** 2 + (yy - KY) ** 2 > KR * KR)
    return m & ~((yy > MY0) & (yy < MY1) & (xx > KX))


def emblem_canvas(name, font):
    """a hero's emblem as a filled silhouette, in the D's own pixels (4x), centred in the open part of the counter"""
    S = 4; W, H = 300 * S, 310 * S
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    cx, cy = 172 * S, 152 * S
    P = lambda pts, s=1.0: [(cx + x * s * S, cy + y * s * S) for x, y in pts]
    g = 0.31
    if name == "superman":
        shield = [(-120, -78), (120, -78), (150, -38), (0, 128), (-150, -38)]
        d.polygon(P(shield, g), fill=255)
        f = ImageFont.truetype(font, round(150 * g) * S); f.set_variation_by_axes([900])
        t = Image.new("L", (W, H), 0); ImageDraw.Draw(t).text((cx, cy - 6 * S), "S", font=f, fill=255, anchor="mm")
        t = t.transform(t.size, Image.AFFINE, (1, 0.2, -0.2 * cy, 0, 1, 0), Image.BICUBIC)
        im = Image.fromarray(np.clip(np.asarray(im, np.int16) - np.asarray(t, np.int16), 0, 255).astype(np.uint8))
    elif name == "batman":
        # the classic bat: wings with three scallops below, short ears
        bat = [(0, -22), (8, -40), (14, -18), (40, -26), (78, -44), (150, -40), (118, -20), (110, 8), (88, 0), (70, 22), (46, 10),
               (24, 34), (0, 64), (-24, 34), (-46, 10), (-70, 22), (-88, 0), (-110, 8), (-118, -20), (-150, -40), (-78, -44),
               (-40, -26), (-14, -18), (-8, -40)]
        d.polygon(P(bat, g * 1.05), fill=255)
    elif name == "wonderwoman":
        w = [(-150, -60), (-100, -60), (-64, 46), (-34, -40), (0, -40), (34, -40), (64, 46), (100, -60), (150, -60), (84, 100),
             (46, 100), (17, 22), (0, 64), (-17, 22), (-46, 100), (-84, 100)]
        d.polygon(P(w, g), fill=255)
        d.polygon(P([(-176, -60), (176, -60), (150, -36), (-150, -36)], g), fill=255)
    elif name == "lantern":
        r1, r2 = 82 * g, 56 * g
        d.ellipse([cx - r1 * S, cy - r1 * S, cx + r1 * S, cy + r1 * S], fill=255)
        d.ellipse([cx - r2 * S, cy - r2 * S, cx + r2 * S, cy + r2 * S], fill=0)
        for y0 in (-118, 82):
            d.rectangle([cx - 120 * g * S, cy + y0 * g * S, cx + 120 * g * S, cy + (y0 + 36) * g * S], fill=255)
    elif name == "flash":
        bolt = [(-128, -64), (36, -24), (8, -6), (150, 38), (-20, 4), (6, -12)]
        d.polygon(P(bolt, g * 1.1), fill=255)
    a = np.asarray(im, np.float32) / 255
    return cv2.GaussianBlur(a, (0, 0), 1.2)


class Scene:
    def __init__(self, src, sc=1.0):
        self.sc = sc
        W, H = self.W, self.H = round(1280 * sc), round(720 * sc)
        font = os.path.join(src, "Montserrat-VF.ttf")
        self.k = 1.16 * sc                                  # screen px per D pixel (D 336 px tall on the cover)

        def text(t, size, wght, track):
            f = ImageFont.truetype(font, size * 2); f.set_variation_by_axes([wght])
            ws = [f.getlength(c) for c in t]
            im = Image.new("L", (round(sum(ws) + track * 2 * len(t)) + 40, size * 3), 0)
            d = ImageDraw.Draw(im); x = 20
            for c, w in zip(t, ws):
                d.text((x, size * 2.4), c, font=f, fill=255, anchor="ls"); x += w + track * 2
            im = im.crop(im.getbbox()); return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        self.t1 = text("DC UNIVERSE", round(56 * sc), 700, round(1 * sc))
        self.t2 = text("THE COLLECTION", round(21 * sc), 600, round(9 * sc))
        dw = (277 - X0) * self.k; dh = (Y1 - Y0) * self.k
        gap1, gap2 = round(26 * sc), round(14 * sc)
        block_w = max(dw, self.t1.width, self.t2.width)
        block_h = dh + gap1 + self.t1.height + gap2 + self.t2.height
        self.bx = (W - block_w) / 2; self.by = (H - block_h) / 2 + 6 * sc
        self.ox = self.bx - X0 * self.k; self.oy = self.by - Y0 * self.k
        self.t1y = self.by + dh + gap1; self.t2y = self.t1y + self.t1.height + gap2
        # the logo's region on screen, sampled at 2x
        pad = 40 * sc
        self.rx0 = int(self.ox + (X0 - 40) * self.k); self.ry0 = int(self.oy + (Y0 - 40) * self.k)
        self.rw = int((277 - X0 + 80) * self.k); self.rh = int((Y1 - Y0 + 80) * self.k)
        SS = 2
        gy, gx = np.mgrid[0:self.rh * SS, 0:self.rw * SS].astype(np.float32)
        self.px = (self.rx0 + (gx + 0.5) / SS - self.ox) / self.k          # D pixels
        self.py = (self.ry0 + (gy + 0.5) / SS - self.oy) / self.k
        self.SS = SS
        self.D = d_mask(self.px, self.py); self.C = c_mask(self.px, self.py)
        r = np.random.default_rng(3)
        brush = cv2.GaussianBlur(r.normal(size=(self.rh * SS, self.rw * SS)).astype(np.float32), (0, 0), sigmaX=40, sigmaY=0.8)
        self.brush = brush / (np.abs(brush).max() + 1e-6)
        self.emb = {}
        for n in EMBLEMS:
            a = emblem_canvas(n, font)
            m = cv2.remap(a, self.px * 4, self.py * 4, cv2.INTER_LINEAR)
            self.emb[n] = m
        # background: rays from behind the counter of the C
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.ccx = self.ox + (KX + 30) * self.k; self.ccy = self.oy + KY * self.k
        ang = np.arctan2(yy - self.ccy, xx - self.ccx); dist = np.hypot(xx - self.ccx, yy - self.ccy)
        ray = np.zeros_like(ang)
        for i, (f, ph, w) in enumerate([(7, 0.3, 0.5), (13, 1.7, 0.35), (23, 4.1, 0.25), (41, 2.2, 0.15)]):
            ray += w * np.cos(ang * f + ph)
        ray = np.clip(ray * 0.5 + 0.55, 0, 1) ** 2.2
        self.ang, self.dist = ang, dist
        self.rays_static = ray
        self.glow = np.exp(-(dist / (260 * sc)) ** 2)
        vg = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        self.vig = 1 - 0.45 * np.clip(vg - 0.4, 0, 1) ** 1.3
        self.yy, self.xx = yy, xx

    def background(self, k, light):
        rot = 0.002 * k
        ray = np.zeros_like(self.ang)
        for f, ph, w in [(7, 0.3, 0.5), (13, 1.7, 0.35), (23, 4.1, 0.25), (41, 2.2, 0.15)]:
            ray += w * np.cos((self.ang + rot * (1 if f % 2 else -1)) * f + ph)
        ray = np.clip(ray * 0.5 + 0.55, 0, 1) ** 2.2
        fall = np.exp(-(self.dist / (380 * self.sc)) ** 1.5) * 0.55
        img = np.zeros((self.H, self.W, 3), np.float32) + NAVY
        img += (self.glow * (0.12 + 0.88 * light))[..., None] * np.array([18, 34, 70], np.float32)
        img += (ray * fall * light)[..., None] * np.array([90, 140, 220], np.float32)
        return img

    def logo(self, k, lift):
        """the D region (2x), RGBA float"""
        sc, SS = self.sc, self.SS
        breathe = 4 * math.sin(k * 0.21) * lift
        f0 = F0 + np.array([-44 * lift + breathe, 0]); f1 = F1 + np.array([-6 * lift + breathe * 0.2, 0])
        curl = CURL + 0.08 * lift
        d = (f1 - f0) / np.linalg.norm(f1 - f0); n = np.array([d[1], -d[0]])
        rx, ry = self.px - f0[0], self.py - f0[1]
        t = rx * n[0] + ry * n[1]; s = rx * d[0] + ry * d[1]
        right = t > 0
        tt = -t / curl; s2 = s + SHEAR * tt
        sx = f0[0] + s2 * d[0] + tt * n[0]; sy = f0[1] + s2 * d[1] + tt * n[1]
        flap = (t < 0) & d_mask(sx, sy)
        u = np.clip(tt / 150, 0, 1)
        D, C = self.D, self.C
        base = D & ~right; rev = D & right
        h, w = self.px.shape
        col = np.zeros((h, w, 3), np.float32); alpha = np.zeros((h, w), np.float32)
        # brushed steel D
        v = 150 - 55 * np.clip((self.py - Y0) / (Y1 - Y0), 0, 1) + 14 * self.brush
        steel = v[..., None] * np.array([0.92, 0.97, 1.06], np.float32)
        col[base] = steel[base]; alpha[base] = 1
        # the C beneath: dark gunmetal, and the hero's emblem embossed in it
        cm = rev & C
        gv = 1.0 - 0.3 * np.clip((self.py - Y0) / (Y1 - Y0), 0, 1)
        gun = (gv[..., None] * np.array([50, 66, 102], np.float32)) + (10 * self.brush)[..., None]
        return col, alpha, cm, gun, flap, u, rev, t

    def frame(self, k):
        sc, SS = self.sc, self.SS
        W, H = self.W, self.H
        lift = seg(k, T_LIFT) * (1 - seg(k, T_DROP))
        light = seg(k, T_LIGHT) * (1 - seg(k, T_DARK))
        img = self.background(k, light)
        col, alpha, cm, gun, flap, u, rev, t = self.logo(k, lift)
        col[cm] = gun[cm]; alpha[cm] = 1
        # through the holes of the C: the light behind, and in it the hero's emblem as a dark silhouette
        holes = rev & ~self.C
        dd = np.hypot(self.px - 172, self.py - KY)
        core = np.exp(-(dd / 70) ** 2)
        sil = np.zeros_like(core)
        span = (T_EMB[1] - T_EMB[0]) / len(EMBLEMS)
        for i, nme in enumerate(EMBLEMS):
            a0 = T_EMB[0] + i * span
            vis = smooth((k - a0) / 7) * (1 - smooth((k - (a0 + span - 3)) / 7))
            if i == len(EMBLEMS) - 1:
                vis = smooth((k - a0) / 7) * (1 - seg(k, (T_DROP[0] - 6, T_DROP[0] + 8)))
            if vis > 0.001:
                sil = np.maximum(sil, self.emb[nme] * vis)
        pulse = sum(math.exp(-((k - (T_EMB[0] + i * span + 3)) / 4.0) ** 2) for i in range(len(EMBLEMS)))
        lightc = (core * (0.75 + 0.25 * pulse) + 0.15)[..., None] * np.array([200, 225, 255], np.float32) * light
        lightc = lightc * (1 - 0.92 * sil[..., None])
        hl = holes & (light > 0.001)
        col[hl] = lightc[hl]; alpha[hl] = np.clip(light * 1.4, 0, 1)
        # rim light where the C meets the holes, from the light behind
        hole_glow = cv2.GaussianBlur(holes.astype(np.float32), (0, 0), 3 * SS * sc)
        col += (hole_glow * cm * light)[..., None] * np.array([60, 100, 170], np.float32)
        # the flap's shadow on what lies under it, then the flap: polished, bright at the fold, a dark lip at the curl
        shadow = cv2.GaussianBlur(np.roll(np.roll(flap.astype(np.float32), int(6 * SS * sc), 0), int(-4 * SS * sc), 1), (0, 0), 6 * SS * sc)
        col *= (1 - 0.55 * shadow * (alpha > 0))[..., None]
        fv = 246 - 110 * u ** 0.7 + 10 * self.brush + 18 * np.exp(-((u - 0.18) / 0.06) ** 2)
        lip = np.exp(-((-t) / (5.0)) ** 2)
        fv = fv - 70 * lip * np.clip(1 - (self.py - Y0) / 80, 0, 1)
        fcol = fv[..., None] * np.array([0.95, 0.98, 1.04], np.float32)
        col[flap] = fcol[flap]; alpha[flap] = 1
        # down to screen size and over the background
        h2, w2 = self.rh, self.rw
        col = cv2.resize(col * alpha[..., None], (w2, h2), interpolation=cv2.INTER_AREA)
        al = cv2.resize(alpha, (w2, h2), interpolation=cv2.INTER_AREA)
        y0, x0 = self.ry0, self.rx0
        reg = img[y0:y0 + h2, x0:x0 + w2]
        img[y0:y0 + h2, x0:x0 + w2] = reg * (1 - al[..., None]) + col
        img *= self.vig[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        for im, y, c in ((self.t1, self.t1y, (236, 239, 245)), (self.t2, self.t2y, (170, 182, 205))):
            lay = Image.merge("RGBA", (Image.new("L", im.size, c[0]), Image.new("L", im.size, c[1]), Image.new("L", im.size, c[2]), im))
            out.alpha_composite(lay, (round(self.bx), round(y)))
        return out.convert("RGB")


def render(src, out, only=None, sc=1.0, mp4=None):
    s = Scene(src, sc)
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
    render(a[1], a[2], only, sc, mp4)
