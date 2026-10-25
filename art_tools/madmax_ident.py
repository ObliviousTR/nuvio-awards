"""Mad Max card: the rusted MAD MAX of the Fury Road era in front of the film's own sandstorm.

Behind the title: the Fury Road still of the War Rig driving into the storm (TMDB backdrop), thrown slightly out of
focus and graded. Its lightning is not drawn: the bolts are taken out of the still for the dark state and given back
for the flashes, so every flash is the film's own lightning and the light it throws on the clouds. Lightning strikes
in short strobes from the first second; the camera pushes in slowly; the wind moves the dust; the title catches each
flash on its edges.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/madmax_ident.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (the Mad Max title logo on TMDB, film 9659, Fury Road style), storm.jpg (the Mad Max: Fury Road
           backdrop on TMDB, film 76341), dust.jpg (another Fury Road backdrop: the dust clouds), BarlowCondensed-Medium.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
# strikes: (frame, strobe pattern)
STRIKES = [(6, [1.0, 0.25, 0.9, 0.1, 0.55, 0.0, 0.25]), (74, [0.8, 0.1, 1.0, 0.35, 0.05]),
           (132, [1.0, 0.2, 0.15, 0.85, 0.3, 0.6, 0.1]), (196, [0.9, 0.3, 1.0, 0.1, 0.4])]


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


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


def split_lightning(a):
    """the still with its lightning taken out, and the lightning mask"""
    h, w = a.shape[:2]
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35))
    op = blur(cv2.morphologyEx(a, cv2.MORPH_OPEN, k), 6)
    lum = a.astype(np.float32).mean(2); lop = op.astype(np.float32).mean(2)
    sat = a.max(2).astype(np.float32) - a.min(2)
    raw = ((lum - lop) > 14) & (sat < 70) & (lum > 150)
    raw[int(h * 0.6):] = False
    raw = cv2.morphologyEx(raw.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, l, st, c = cv2.connectedComponentsWithStats(raw)
    keep = np.zeros((h, w), np.uint8)
    for i in range(1, n):
        x, y, ww, hh, ar = st[i]
        if hh > 120 and ar > 800 and ar / (ww * hh) < 0.35:
            keep[l == i] = 1
    keep[int(h * 0.44):, int(w * 0.52):int(w * 0.69)] = 0                  # not the War Rig
    bolt = np.clip(blur(cv2.dilate(keep, np.ones((11, 11))).astype(np.float32), 4) * 1.6, 0, 1)
    nob = a * (1 - bolt[..., None]) + op * bolt[..., None]
    return nob.astype(np.float32), bolt


class Scene:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        a = np.asarray(Image.open(os.path.join(src, "storm.jpg")).convert("RGB")); a_src = a
        nob, bolt = split_lightning(a)
        BW, BH = int(W * 1.3), int(H * 1.3)
        s = max(BW / a.shape[1], BH / a.shape[0])
        size = (round(a.shape[1] * s), round(a.shape[0] * s))
        lit = cv2.resize(a.astype(np.float32), size, interpolation=cv2.INTER_AREA)
        dark = cv2.resize(nob, size, interpolation=cv2.INTER_AREA)
        bolt = cv2.resize(bolt, size, interpolation=cv2.INTER_AREA)
        ox = (size[0] - BW) // 2 + int(size[0] * 0.04); oy = 0                 # the War Rig sits under the title
        crop = lambda im: im[oy:oy + BH, ox:ox + BW]
        lit, dark, bolt = crop(lit), crop(dark), crop(bolt)
        # a slight lens blur: the title is in focus, the storm is not
        r = 3
        disc = np.zeros((2 * r + 1, 2 * r + 1), np.float32); cv2.circle(disc, (r, r), r, 1.0, -1, cv2.LINE_AA); disc /= disc.sum()
        lb = lambda im: (cv2.filter2D((im / 255) ** 2.2, -1, disc) ** (1 / 2.2)) * 255
        lit, dark = lb(lit), lb(dark)
        # grade: Fury Road's orange and teal; the dark state is the storm between strikes
        def grade(im, expo):
            im = im / 255 * expo
            lum = im.mean(2, keepdims=True)
            warm = np.array([1.12, 0.92, 0.72], np.float32); cool = np.array([0.72, 0.9, 1.0], np.float32)
            t = np.clip(lum * 1.4, 0, 1)
            im = im * (cool * (1 - t) + warm * t)
            return np.clip(im, 0, 1.4) * 255
        glow = bigblur(bolt, 120); glow /= glow.max() + 1e-6
        self.dark = grade(dark * (1 - 0.35 * glow[..., None]), 0.55)
        self.lit = grade(lit, 1.05)
        self.bw, self.bh = BW, BH
        self.wind = noise(BH, 2 * BW, 1.2, 5)
        # title
        lg = np.asarray(Image.open(os.path.join(src, "logo.png")).convert("RGBA"), np.float32)
        lw = 900; lh = round(lg.shape[0] * lw / lg.shape[1])
        lg = cv2.resize(lg, (lw, lh), interpolation=cv2.INTER_AREA)
        self.top = 250 - lh // 2; x0 = (W - lw) // 2
        self.la = np.zeros((H, W), np.float32); self.rgb = np.zeros((H, W, 3), np.float32)
        self.la[self.top:self.top + lh, x0:x0 + lw] = lg[..., 3] / 255
        self.rgb[self.top:self.top + lh, x0:x0 + lw] = lg[..., :3]
        m = (self.la > 0.5).astype(np.uint8)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        hg = blur(smooth(dt / 3.0).astype(np.float32), 0.6)
        self.gx = cv2.Sobel(hg, cv2.CV_32F, 1, 0, ksize=3) / 8; self.gy = cv2.Sobel(hg, cv2.CV_32F, 0, 1, ksize=3) / 8
        self.edge = np.clip(np.sqrt(self.gx ** 2 + self.gy ** 2) * 3, 0, 1)
        f = ImageFont.truetype(os.path.join(src, "BarlowCondensed-Medium.ttf"), 56)
        txt, tr = "THE COLLECTION", 40
        mm = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 80, 120), 0)
        d = ImageDraw.Draw(mm); x = 40
        for c in txt:
            d.text((x, 90), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        mm = mm.crop(mm.getbbox()); mm = mm.resize((mm.width // 2, mm.height // 2), Image.LANCZOS)
        sub = np.asarray(mm, np.float32) / 255
        self.sub = np.zeros((H, W), np.float32)
        sy = self.top + lh + 26; sx = (W - sub.shape[1]) // 2
        self.sub[sy:sy + sub.shape[0], sx:sx + sub.shape[1]] = sub
        self.bolt_x = W * 0.66                                              # where the light comes from
        # dust gusts in front of the title: the storm's own dust (the still's cloud texture, as a matte), tiled
        cl = cv2.cvtColor(np.asarray(Image.open(os.path.join(src, "dust.jpg")).convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
        hh, ww = cl.shape
        patch = cl[int(hh * 0.02):int(hh * 0.62), int(ww * 0.02):int(ww * 0.62)]      # billowing dust, nothing else
        patch = cv2.resize(patch, (W, int(W * patch.shape[0] / patch.shape[1])))
        hp = blur(patch, 3) - blur(patch, 90)
        m = np.clip(hp / (hp.std() * 2.5) + 0.35, 0, 1) ** 1.5
        tile = np.concatenate([m, m[:, ::-1]], 1)                            # seamless across
        tile = cv2.resize(tile, (2 * W, H))
        self.gust = blur(tile, 2.5)
        self.gust_env = noise(4, 2 * W, 1.0, 17)[2]                          # where along the tile the gusts are thick

    def flash(self, k):
        f = 0.0
        for k0, pat in STRIKES:
            i = k - k0
            if 0 <= i < len(pat):
                f = max(f, pat[i])
            elif len(pat) <= i < len(pat) + 8:                                # the clouds glow on a moment
                f = max(f, 0.12 * (1 - (i - len(pat)) / 8))
        return f

    def thunder(self, k):
        """camera shake a few frames after each strike, decaying"""
        amp = 0.0
        for k0, pat in STRIKES:
            t = k - (k0 + 3)
            if 0 <= t < 16:
                amp = max(amp, (1 - t / 16) ** 2 * 5.0 * max(pat))
        rng = np.random.default_rng(3000 + k)
        return rng.normal() * amp, rng.normal() * amp * 0.6

    def frame(self, k):
        f = self.flash(k)
        ph = 2 * math.pi * k / N
        z = 1.0 + 0.04 * (1 - math.cos(ph)) / 2
        cx, cy = self.bw / 2, self.bh / 2
        # the wind: the dust in the still moves a little (loops: displacement on a tiling noise)
        wn = np.roll(self.wind, -int(round(2 * self.bw * k / N)), axis=1)[:, :self.bw]
        wn2 = np.roll(self.wind, -int(round(2 * self.bw * k / N)) + self.bw // 3, axis=1)[:, :self.bw]
        dx = (wn - 0.5) * 7; dy = (wn2 - 0.5) * 3
        yy, xx = np.mgrid[0:self.bh, 0:self.bw].astype(np.float32)
        bg = self.dark * (1 - f) + self.lit * f
        bg = cv2.remap(bg.astype(np.float32), xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        z0 = W / self.bw * 1.06                                              # the plate is bigger than the frame
        M = np.float32([[z * z0, 0, W / 2 - cx * z * z0], [0, z * z0, H / 2 - (cy - 30) * z * z0]])
        img = cv2.warpAffine(bg, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # the title moves on its own plane: it comes forward more than the storm behind it (parallax)
        zl = 1.0 + 0.075 * (1 - math.cos(ph)) / 2
        tcy = self.top + 60
        ML = np.float32([[zl, 0, W / 2 * (1 - zl)], [0, zl, tcy * (1 - zl)]])
        wp = lambda im: cv2.warpAffine(im, ML, (W, H), flags=cv2.INTER_LINEAR)
        la, gx, gy, sub = wp(self.la), wp(self.gx), wp(self.gy), wp(self.sub)
        rgb = wp(self.rgb)
        # it casts a shadow into the dust when the lightning strikes behind it (light from above right)
        sh = cv2.warpAffine(la, np.float32([[1, 0, -22], [0, 1, 26]]), (W, H))
        img *= (1 - 0.42 * bigblur(la, 18) - 0.55 * np.clip(bigblur(sub, 12) * 2.5, 0, 1) - 0.5 * f * blur(sh, 7))[..., None]
        # the title: rust in the storm's dark, lit hard by each strike; its edges facing the bolt flare
        L = np.dstack([self.bolt_x - self.xx, -400 - self.yy]); L /= np.linalg.norm(L, axis=2, keepdims=True) + 1e-6
        facing = np.clip(-(gx * L[..., 0] + gy * L[..., 1]) * 6, 0, 1)
        face = rgb * (0.84 + 0.2 * f)
        face = face + (facing * f * 1.3)[..., None] * np.array([235, 230, 255], np.float32)
        a = la[..., None]
        img = img * (1 - a) + face * a
        img += (bigblur(la, 30) * f * 0.35)[..., None] * np.array([255, 200, 140], np.float32)
        img = img * (1 - sub[..., None]) + sub[..., None] * np.array([236, 220, 196], np.float32)
        # gusts of the storm's dust blow across in front of everything, two depths
        for spd, op, sc in ((3, 0.24, 1.0), (5, 0.16, 1.6)):
            sx = (k * spd * 2 * W // N) % (2 * W)
            g = np.roll(self.gust, -sx, axis=1)[:, :W]
            env = np.roll(self.gust_env, -sx)[:W]
            if sc != 1.0:
                g = cv2.resize(cv2.resize(g, (int(W / sc), int(H / sc))), (W, H))
            g = g * np.clip((env[None, :] - 0.35) * 2.2, 0, 1) * op
            dust_col = np.array([150, 104, 76], np.float32) * (0.55 + 0.8 * f)
            img = img * (1 - g[..., None]) + dust_col * g[..., None]
        sxk, syk = self.thunder(k)
        if abs(sxk) + abs(syk) > 0.05:
            img = cv2.warpAffine(img.astype(np.float32), np.float32([[1, 0, sxk], [0, 1, syk]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.45 * np.clip(rr - 0.4, 0, 1))[..., None]
        img += np.random.default_rng(900 + k).normal(size=(H, W)).astype(np.float32)[..., None] * 2.0
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
