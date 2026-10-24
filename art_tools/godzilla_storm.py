"""Godzilla & Kong card: night, a storm over the open sea; Godzilla and Kong face each other far out in the water, dark
against the clouds, Godzilla's dorsal plates faintly blue; GODZILLA x KONG and THE COLLECTION above them.
Hover (10 s): the title fades and the camera starts to track sideways along the sea, steadily, like a film strip.
The Titans of every era stand in the water at different distances and slide past - dorsal plates breaking the surface
close by, King Kong (1933), Godzilla (1954), Heisei Godzilla, Shin Godzilla, Godzilla Minus One, Kong of Skull Island,
the MonsterVerse Godzilla - each lit for a moment by lightning in the clouds behind it as we pass. The camera eases to
a stop on Godzilla and Kong again; Godzilla's plates light up from tail to head, the charge floods the clouds blue, and
the title returns. First frame = last frame = cover: the track runs from one copy of the pair to an identical one, and
the sea, the clouds and the rain all tile exactly over that distance.
usage: python3 art_tools/godzilla_storm.py SRC_DIR OUT_DIR [--frames a,b] [--font barlow|stencil]
  SRC_DIR: logo.png, BarlowCondensed-Medium.ttf / BigShouldersStencil.ttf, elements/*.png (cut-outs)
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 250
F = 640.0
YH = 470.0                                      # horizon (px)
CAM_H = 1.0                                     # camera height above the water (world units)
D = 1000.0                                      # track length: pair -> ... -> pair
T_MOVE = (10, 200)                              # camera moves, easing in and out
T_TITLE_OUT, T_TITLE_IN = (6, 18), (214, 234)
T_CHARGE = (194, 216)                           # plates light tail -> head
T_BURST = 216                                   # the charge floods the clouds
NAVY = np.array([9, 13, 24], np.float32)

# name, world X along the track, depth z, height above the water (world), waterline (share of the image height)
ELEMENTS = [
    ("pair", 0.0, 160.0, 66.0, 0.80),
    ("fins", 70.0, 40.0, 16.0, 0.30),
    ("kong1933", 150.0, 120.0, 70.0, 0.86),
    ("godzilla1954", 262.0, 170.0, 98.0, 0.84),
    ("godzilla_heisei", 372.0, 110.0, 76.0, 0.86),
    ("shin", 478.0, 190.0, 118.0, 0.88),
    ("minusone", 588.0, 125.0, 80.0, 0.84),
    ("kong_skull", 700.0, 160.0, 84.0, 0.84),
    ("godzilla_kotm", 806.0, 115.0, 78.0, 0.86),
]
REVEAL = {"kong1933", "godzilla1954", "godzilla_heisei", "shin", "minusone", "kong_skull", "godzilla_kotm"}


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    return smooth((k - ab[0]) / max(1, ab[1] - ab[0]))


def periodic_noise(h, w, beta, seed):
    """Fractal noise that tiles in both directions (FFT with a 1/f^beta spectrum), normalised to 0..1."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta
    spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    n = (n - n.min()) / (n.max() - n.min())
    return n.astype(np.float32)


def cam_x(k):
    """Camera position along the track: rest, ease in, steady, ease out, rest."""
    a, b = T_MOVE
    if k <= a:
        return 0.0
    if k >= b:
        return D
    t = (k - a) / (b - a)
    e = 0.16                                                       # share of the move spent easing at each end
    if t < e:
        u = t * t / (2 * e)
    elif t > 1 - e:
        u = (1 - e) - (1 - t) ** 2 / (2 * e)
    else:
        u = e / 2 + (t - e)
    return D * u / (1 - e)


class Scene:
    def __init__(self, src, font="barlow"):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        # textures that tile over one loop
        self.cloud_t = periodic_noise(256, 1024, 1.7, 3)
        self.cloud_d = periodic_noise(256, 1024, 1.3, 4)
        self.water_t = periodic_noise(256, 2048, 1.35, 5)
        self.rain_t = self.make_rain()
        # sea geometry: depth of each row below the horizon
        rows = np.arange(H, dtype=np.float32)
        self.zrow = np.where(rows > YH + 0.5, F * CAM_H / np.maximum(rows - YH, 0.5), 1e9)
        # elements
        self.els = []
        for name, X, z, hw, wl in ELEMENTS:
            im = Image.open(os.path.join(src, "elements", f"{name}.png")).convert("RGBA")
            a = np.asarray(im, np.float32)
            rgb, al = a[..., :3], a[..., 3] / 255
            hh = al.shape[0]
            cut = int(hh * wl)                                    # below the waterline is in the sea
            rgb, al = rgb[:cut], al[:cut]
            lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32)) / 255
            tex = NAVY * 1.4 + (np.array([170, 186, 214], np.float32) - NAVY * 1.4) * np.clip(lum, 0, 1)[..., None] ** 1.1
            # rim: the outline, lit from behind by the clouds
            m = (al > 0.5).astype(np.uint8)
            er = cv2.erode(m, np.ones((7, 7), np.uint8))
            edge = cv2.GaussianBlur((m - er).astype(np.float32), (0, 0), 1.8)
            gy = cv2.Sobel(cv2.GaussianBlur(al, (0, 0), 4), cv2.CV_32F, 0, 1, ksize=5)
            up = np.clip(gy / (np.abs(gy).max() * 0.25 + 1e-6), 0, 1)        # outline that faces the sky
            rim = edge * (0.25 + 0.75 * up) * al
            el = dict(name=name, X=X, z=z, h=hw, rgb=tex.astype(np.float32), al=al.astype(np.float32),
                      rim=rim.astype(np.float32), lum=lum.astype(np.float32))
            if name == "pair":
                el["plates"] = self.plates(al)
            self.els.append(el)
        # flashes: one as each era crosses the middle, a double flicker
        self.flashes = []
        for e in self.els:
            if e["name"] in REVEAL:
                k = self.k_at(e["X"])
                self.flashes.append((k, e["X"], e["z"]))
        # title
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA")
        lw = 760; lg = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
        a = np.asarray(lg, np.float32)
        g = np.linspace(0, 1, a.shape[0])[:, None, None]
        steel = np.array([236, 242, 250], np.float32) * (1 - g) + np.array([150, 170, 198], np.float32) * g
        a[..., :3] = steel
        self.logo = Image.fromarray(a.astype(np.uint8), "RGBA")
        lgl = np.asarray(self.logo.getchannel("A"), np.float32) / 255
        self.logo_glow = cv2.GaussianBlur(np.pad(lgl, 60), (0, 0), 14)            # padded: no box edge
        fp = os.path.join(src, "BigShouldersStencil.ttf" if font == "stencil" else "BarlowCondensed-Medium.ttf")
        f = ImageFont.truetype(fp, 62)
        if font == "stencil":
            try:
                f.set_variation_by_axes([700, 24])
            except Exception:
                pass
        txt, tr = "THE COLLECTION", 30
        m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 20, 130), 0)
        d = ImageDraw.Draw(m); x = 10
        for c in txt:
            d.text((x, 100), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        self.sub = Image.merge("RGBA", (Image.new("L", m.size, 196), Image.new("L", m.size, 212),
                                        Image.new("L", m.size, 236), m))
        self.ty = 70

    def k_at(self, X):
        ks = np.arange(N * 4) / 4
        cx = np.array([cam_x(k) for k in ks])
        return float(ks[np.argmin(np.abs(cx - X))])

    def make_rain(self):
        rng = np.random.default_rng(9)
        lay = np.zeros((H, W), np.float32)
        for _ in range(1500):
            x, y = rng.uniform(0, W), rng.uniform(0, H); L = rng.uniform(14, 34); b = rng.uniform(0.25, 1)
            for dx in (-W, 0, W):
                for dy in (-H, 0, H):
                    p0 = (x + dx, y + dy); p1 = (x + dx - L * 0.22, y + dy + L)
                    cv2.line(lay, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), b, 1, cv2.LINE_AA, 2)
        return lay

    def plates(self, al):
        """Where Godzilla's dorsal plates are on the pair cut-out: the outline band on the back (upper-left) of the
        left-hand figure, with how far up it is (tail 0 .. head 1)."""
        h, w = al.shape
        m = (al > 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        band = ((dist > 0) & (dist < max(4, w * 0.03))).astype(np.float32)
        gx = cv2.Sobel(al, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(al, cv2.CV_32F, 0, 1, ksize=5)
        gx = cv2.GaussianBlur(gx, (0, 0), 6); gy = cv2.GaussianBlur(gy, (0, 0), 6)
        back = np.clip((gx + gy) / (np.abs(gx) + np.abs(gy) + 1e-3), 0, 1)        # outline faces up-left
        left = np.clip((0.56 - np.arange(w) / w) / 0.08, 0, 1)[None, :]
        band = cv2.GaussianBlur(band * back * left, (0, 0), 2.0) * al
        up = 1 - np.arange(h, dtype=np.float32)[:, None] / h
        return dict(band=band.astype(np.float32), up=np.broadcast_to(up, (h, w)).astype(np.float32))

    def flash_at(self, k):
        """Lightning: (intensity, screen x of the bolt) for each live flash."""
        out = []
        for kf, X, z in self.flashes:
            t = k - kf
            X = X + D * round((cam_x(k) - X) / D) if abs(cam_x(k) - X) > D / 2 else X
            a = math.exp(-((t + 1) / 1.6) ** 2) + 0.75 * math.exp(-((t - 3) / 1.3) ** 2)
            if a > 0.01:
                out.append((a, W / 2 + (X - cam_x(k)) * F / z))
        return out

    def bolts(self, k):
        out = []
        for i, (kf, X, z) in enumerate(self.flashes):
            t = k - kf
            a = 1.0 if -1 <= t <= 0 else 0.6 if 2 <= t <= 3 else 0.0
            if a:
                Xs = X + D * round((cam_x(k) - X) / D) if abs(cam_x(k) - X) > D / 2 else X
                out.append((a, W / 2 + (Xs - cam_x(k)) * F / z + (90 if i % 2 else -110), 31 + i))
        return out

    def bolt(self, sx, seed, a):
        """A forked bolt from the cloud base down towards the horizon, behind the Titans."""
        rng = np.random.default_rng(seed)
        lay = np.zeros((H, W), np.float32)
        def branch(x, y, y1, width, b):
            pts = [(x, y)]
            while y < y1:
                y += rng.uniform(10, 22); x += rng.normal(0, 9); pts.append((x, y))
                if rng.random() < 0.08 and width > 1:
                    branch(x, y, y + rng.uniform(60, 150), 1, b * 0.6)
            p = np.array(pts) * 4
            cv2.polylines(lay, [p.astype(np.int32)], False, b, width, cv2.LINE_AA, 2)
        branch(sx, rng.uniform(20, 80), YH - rng.uniform(20, 70), 2, 1.0)
        glow = cv2.GaussianBlur(lay, (0, 0), 6) * 2.5 + cv2.GaussianBlur(lay, (0, 0), 24) * 4
        return (lay * 1.0 + glow)[..., None] * np.array([200, 215, 255], np.float32) * a

    def frame(self, k):
        cx = cam_x(k)
        flashes = self.flash_at(k)
        charge = seg(k, T_CHARGE)
        burst = math.exp(-((k - T_BURST) / 4.5) ** 2)
        glow_level = 0.22 + 0.78 * charge * (1 - seg(k, (T_BURST, T_BURST + 26))) + 0.0
        glow_level = max(glow_level, 0.22)
        if k < T_CHARGE[0] and k > T_MOVE[0]:
            glow_level = 0.22 * (1 - seg(k, (T_MOVE[0], T_MOVE[0] + 20))) + 0.22 * seg(k, (T_CHARGE[0] - 30, T_CHARGE[0]))
        # ---- sky
        sky_y = np.clip(self.yy / YH, 0, 1)
        img = NAVY * (0.55 + 0.6 * sky_y[..., None])
        off = cx / D * 1024                                               # one cloud tile per loop
        mu = ((self.xx * 0.42 + off) % 1024).astype(np.float32); mv = np.clip(self.yy * 0.24 + 8, 0, 255).astype(np.float32)
        c1 = cv2.remap(self.cloud_t, mu, mv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        mu2 = ((self.xx * 0.8 + off * 2.0) % 1024).astype(np.float32); mv2 = np.clip(self.yy * 0.4 + 40, 0, 255).astype(np.float32)
        c2 = cv2.remap(self.cloud_d, mu2, mv2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        cloud = np.clip((c1 * 0.85 + c2 * 0.3 - 0.5) * 2.0, 0, 1) * (self.yy < YH + 2)
        cloud = cloud * cloud * (3 - 2 * cloud)
        img = img + cloud[..., None] * np.array([30, 36, 50], np.float32)
        # a pale band of storm light low on the horizon, behind the Titans
        hb = np.exp(-((self.yy - (YH - 60)) / 110) ** 2) * (self.yy < YH + 2)
        img = img + (hb * (0.6 + 0.6 * cloud))[..., None] * np.array([30, 38, 56], np.float32)
        light = np.zeros((H, W), np.float32)
        for a, sx in flashes:
            g = np.exp(-(((self.xx - sx) / 380) ** 2 + ((self.yy - 170) / 210) ** 2))
            light += a * g * (0.75 + 0.9 * cloud)
        bl = 0.0
        if burst > 0.01 or charge > 0.01:
            bl = burst * 1.0 + charge * 0.25 * (1 - seg(k, (T_BURST, T_BURST + 26)))
            px = W / 2 - 120
            g = np.exp(-(((self.xx - px) / 520) ** 2 + ((self.yy - 240) / 300) ** 2))
            img += (g * (0.25 + 1.2 * cloud) * bl)[..., None] * np.array([60, 130, 255], np.float32)
        img += light[..., None] * np.array([150, 162, 190], np.float32)
        for a, sx, seed in self.bolts(k):
            img += self.bolt(sx, seed, a)
        # ---- sea
        below = self.yy > YH
        z = self.zrow[:, None] * np.ones((1, W), np.float32)
        wx = cx + (self.xx - W / 2) * z / F
        uu = ((wx / D * 2048 * 2.0) % 2048).astype(np.float32)
        vv = ((np.log(np.maximum(z, 1)) * 60 + k * 256 / N * 3) % 256).astype(np.float32)
        wt = cv2.remap(self.water_t, uu, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        fade = np.clip((self.yy - YH) / 250, 0, 1)
        swell = np.clip((wt - 0.46) * 3.4, 0, 1) ** 1.4
        sea = NAVY * (0.55 + 0.25 * fade[..., None]) * (0.7 + 0.6 * wt[..., None])
        sea = sea + (swell * (1 - 0.7 * fade) * 1.2)[..., None] * np.array([28, 34, 50], np.float32)   # sky on the swells
        sea = sea + (np.exp(-((self.yy - YH) / 40) ** 2) * swell * 1.4)[..., None] * np.array([30, 38, 56], np.float32)
        refl = np.zeros((H, W), np.float32)
        for a, sx in flashes:
            refl += a * np.exp(-((self.xx - sx) / 300) ** 2) * swell * (0.4 + 0.6 * (1 - fade))
        sea = sea + refl[..., None] * np.array([120, 132, 160], np.float32)
        if bl > 0.01:
            sea = sea + (bl * swell * np.exp(-((self.xx - (W / 2 - 120)) / 420) ** 2))[..., None] * np.array([30, 80, 190], np.float32)
        img = np.where(below[..., None], sea, img)
        # horizon haze
        img = img + np.exp(-((self.yy - YH) / 16) ** 2)[..., None] * np.array([12, 15, 24], np.float32)
        # ---- Titans, far first
        # the world repeats every D along the track (that is what makes the loop seamless), so each Titan is also
        # drawn one track length ahead and behind
        placed = [(e, e["X"] + o) for e in self.els for o in (-D, 0.0, D)]
        for e, X in sorted(placed, key=lambda t: -t[0]["z"]):
            s = (e["h"] * F / e["z"]) / e["al"].shape[0]
            wp, hp = e["al"].shape[1] * s, e["al"].shape[0] * s
            sx = W / 2 + (X - cx) * F / e["z"]
            base = YH + CAM_H * F / e["z"] + 1
            if sx + wp / 2 < -20 or sx - wp / 2 > W + 20:
                continue
            M = np.float32([[s, 0, sx - wp / 2], [0, s, base - hp]])
            fl = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
            al = cv2.warpAffine(e["al"], M, (W, H), flags=fl)
            rim = cv2.warpAffine(e["rim"], M, (W, H), flags=fl)
            haze = np.clip((e["z"] - 60) / 300, 0, 0.5)
            dark = NAVY * (0.32 + 0.9 * haze) + np.array([12, 15, 22], np.float32) * haze
            col = np.broadcast_to(dark, (H, W, 3)).astype(np.float32).copy()
            lit = sum(a * math.exp(-((sx - fx) / 260) ** 2) for a, fx in flashes)
            lit = min(1.0, lit)
            if lit > 0.01 and e["name"] in REVEAL:
                tex = cv2.warpAffine(e["rgb"], M, (W, H), flags=fl)
                col = col * (1 - 0.45 * lit) + tex * 0.5 * lit
            amb = 0.16 + 1.3 * lit
            col = col + rim[..., None] * np.array([150, 168, 205], np.float32) * amb * (1 - haze * 0.6)
            if "plates" in e:
                p = e["plates"]
                band = cv2.warpAffine(p["band"], M, (W, H), flags=fl)
                up = cv2.warpAffine(p["up"], M, (W, H), flags=fl)
                on = np.clip((charge * 1.25 - up) / 0.12, 0, 1) * (k >= T_CHARGE[0])
                lvl = np.maximum(on, glow_level if k < T_CHARGE[0] or k > T_BURST else on)
                if k > T_BURST:
                    lvl = np.maximum(glow_level, on * (1 - seg(k, (T_BURST, T_BURST + 26))))
                gl = band * lvl
                halo = cv2.GaussianBlur(gl, (0, 0), 7)
                col = col + (gl * 1.6 + halo * 1.2)[..., None] * np.array([70, 160, 255], np.float32)
                img = img + (halo * (1 - al) * 1.4)[..., None] * np.array([40, 110, 255], np.float32)
            img = img * (1 - al[..., None]) + col * al[..., None]
            # foam where it stands in the water
            foam_y = base
            fm = np.exp(-((self.yy - foam_y) / (2 + 6 * F / e["z"] / 10)) ** 2) * (np.abs(self.xx - sx) < wp * 0.42)
            fm = cv2.GaussianBlur(fm.astype(np.float32), (0, 0), 3) * (0.25 + 0.6 * lit) * (1 - haze)
            img = img + fm[..., None] * np.array([90, 100, 120], np.float32)
        # ---- rain (loops: whole number of tile passes)
        shift_y = (k * 6 * H // N) % H; shift_x = (-k * 2 * W // N) % W
        r = np.roll(np.roll(self.rain_t, shift_y, axis=0), shift_x, axis=1)
        amb = 0.16 + 0.8 * min(1.0, sum(a for a, _ in flashes)) + 0.3 * bl
        img = img + r[..., None] * np.array([150, 160, 185], np.float32) * amb * 0.55
        # vignette
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img = img * (1 - 0.42 * np.clip(rr - 0.4, 0, 1) ** 1.3)[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        ta = min(1.0, (1 - seg(k, T_TITLE_OUT)) + seg(k, T_TITLE_IN))
        if ta > 0.001:
            lx = round(W / 2 - self.logo.width / 2)
            glow = np.zeros((H, W), np.float32)
            gh, gw = self.logo_glow.shape
            y0, x0 = self.ty - 60, lx - 60
            glow[max(0, y0):y0 + gh, max(0, x0):x0 + gw] = self.logo_glow[max(0, -y0):, max(0, -x0):][:H - max(0, y0), :W - max(0, x0)]
            o = np.asarray(out, np.float32)
            o[..., :3] += (glow * ta * (0.25 + 0.5 * glow_level))[..., None] * np.array([40, 90, 200], np.float32)
            out = Image.fromarray(np.clip(o, 0, 255).astype("uint8"), "RGBA")
            for im, y in ((self.logo, self.ty), (self.sub, self.ty + self.logo.height + 26)):
                t2 = im.copy(); t2.putalpha(t2.getchannel("A").point(lambda v: round(v * ta)))
                out.alpha_composite(t2, (round(W / 2 - t2.width / 2), y))
        return out.convert("RGB")


def render(src, out, only=None, font="barlow"):
    sc = Scene(src, font)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            sc.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [sc.frame(k) for k in range(N)]
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=70)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")] if "--frames" in sys.argv else None
    font = sys.argv[sys.argv.index("--font") + 1] if "--font" in sys.argv else "barlow"
    render(sys.argv[1], sys.argv[2], only, font)
