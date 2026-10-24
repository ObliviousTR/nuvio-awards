"""Middle-earth card: the One Ring over the dark, MIDDLE-EARTH in chiselled gold below it and THE COLLECTION.
Hover: the inscription on the ring heats up and glows, the ring turns towards us and we pass through it - inside,
a journey from the Shire to Mordor - then it pulls back, cools and settles on the cover. Seamless loop.
The ring is ray-marched (a band with rounded edges), the inscription is the Ring Verse in Alcarin Tengwar (OFL),
the title is Ringbearer coloured with the gold of the Fellowship title logo; stills are official backdrops (TMDB).
usage: python3 art_tools/middleearth_ring.py SRC_DIR OUT_DIR [--frames a,b,c]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
from me_wordmark import wordmark, gold_ramp, chisel, grit_field

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 250
R, A, B = 1.0, 0.075, 0.13          # ring radius, radial half-thickness, axial half-width
SS = 2                              # supersampling for the ring
JOURNEY = ["movie49051_bd3.jpg", "movie57158_bd4.jpg", "movie120_bd7.jpg", "movie120_bd5.jpg", "movie122_bd2.jpg",
           "movie122_bd7.jpg"]      # Shire, Erebor, the Fellowship on the ridge, Argonath, Minas Tirith, Barad-dur


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return smooth((k - a) / max(1, b - a))


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def sdf(p):
    q = np.sqrt(p[:, 0] ** 2 + p[:, 2] ** 2) - R
    k = 2.6
    e = (np.abs(q) / A) ** k + (np.abs(p[:, 1]) / B) ** k
    return (e ** (1 / k) - 1) * min(A, B)


class Ring:
    """ray-marched band; returns per-pixel hit, normal, view dir, ring coords and the hole mask"""

    def march(self, w, h, tilt, scale, cx, cy):
        D = 7.0
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        px = (x + 0.5 - cx) / scale; py = -(y + 0.5 - cy) / scale
        dirs = np.stack([px / D, py / D, -np.ones_like(px)], -1).reshape(-1, 3)
        dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
        M = rot_x(tilt).T
        o = M @ np.array([0, 0, D], np.float32)
        d = dirs @ M.T
        n_px = d.shape[0]
        # the hole: where the ray crosses the ring plane inside the band
        with np.errstate(divide="ignore", invalid="ignore"):
            tp = -o[1] / d[:, 1]
        pp = o[None, :] + d * tp[:, None]
        rp = np.sqrt(pp[:, 0] ** 2 + pp[:, 2] ** 2)
        hole = np.clip(((R - A * 0.6) - rp) * scale / SS * 1.0 + 0.5, 0, 1)
        hole[~np.isfinite(tp)] = 0
        # slab |y| <= B: march only there
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (-B - 0.01 - o[1]) / d[:, 1]; t2 = (B + 0.01 - o[1]) / d[:, 1]
        t0 = np.nan_to_num(np.minimum(t1, t2), nan=0, posinf=1e9, neginf=-1e9)
        te = np.nan_to_num(np.maximum(t1, t2), nan=0, posinf=1e9, neginf=-1e9)
        t0 = np.maximum(t0, 0); te = np.minimum(te, D + 3)
        cand = np.nonzero(te > t0)[0]
        # quick reject: radial distance at the slab middle far from the band
        tm = (t0[cand] + te[cand]) / 2
        pm = o[None, :] + d[cand] * tm[:, None]
        rm = np.sqrt(pm[:, 0] ** 2 + pm[:, 2] ** 2)
        span = (te[cand] - t0[cand]) * np.sqrt(d[cand, 0] ** 2 + d[cand, 2] ** 2) / 2
        keep = np.abs(rm - R) < A + span + 0.02
        cand = cand[keep]
        t = t0[cand].copy(); hit = np.zeros(n_px, bool); tt = np.zeros(n_px, np.float32)
        act = np.arange(len(cand))
        for _ in range(80):
            if not len(act): break
            idx = cand[act]
            p = o[None, :] + d[idx] * t[act][:, None]
            dist = sdf(p)
            t[act] += dist * 0.85
            done = dist < 5e-4
            hit[idx[done]] = True; tt[idx[done]] = t[act][done]
            act = act[~done & (t[act] < te[idx] + 0.01)]
        p = o[None, :] + d * tt[:, None]
        e = 1e-3; ex, ey, ez = (np.array(v, np.float32) for v in ([e, 0, 0], [0, e, 0], [0, 0, e]))
        hi = np.nonzero(hit)[0]
        ph = p[hi]
        nl = np.stack([sdf(ph + ex) - sdf(ph - ex), sdf(ph + ey) - sdf(ph - ey), sdf(ph + ez) - sdf(ph - ez)], -1)
        nl /= np.linalg.norm(nl, axis=-1, keepdims=True) + 1e-9
        return dict(hit=hit, hi=hi, n=nl @ M, d=d[hi] @ M, u=np.arctan2(ph[:, 2], ph[:, 0]), ay=ph[:, 1],
                    rq=np.sqrt(ph[:, 0] ** 2 + ph[:, 2] ** 2) - R, hole=hole, shape=(h, w))


def inscription_strip(font_path, lines, tw=6144, th=200):
    f = ImageFont.truetype(font_path, 150, layout_engine=ImageFont.Layout.RAQM)
    txt = "  ".join(lines) + "  "
    m = Image.new("L", (round(f.getlength(txt)) + 40, 260), 0)
    ImageDraw.Draw(m).text((20, 205), txt, font=f, fill=255, anchor="ls")
    m = m.crop((0, 20, m.width, 250))
    m = m.resize((tw, th), Image.LANCZOS)
    return np.asarray(m, np.float32) / 255


class Scene:
    def __init__(self, src):
        self.src = src
        self.ring = Ring()
        lines = [l.strip() for l in open(os.path.join(src, "alcarin-samples.txt"), encoding="utf-8").read().split("\n")[1:7]
                 if l.strip() and any(ord(c) >= 0xE000 for c in l)]
        tf = os.path.join(src, "alcarin-bold.ttf")
        self.outer = inscription_strip(tf, lines[:2])
        self.inner = inscription_strip(tf, lines[2:4])
        self.wm = wordmark(os.path.join(src, "ringbearer.ttf"), os.path.join(src, "movie120_logo0.png"), height=104)
        self.sub = self.subtitle(os.path.join(src, "cinzel.ttf"), os.path.join(src, "movie120_logo0.png"))
        self.bg = self.background()
        self.stills = [self.load_still(os.path.join(src, f)) for f in JOURNEY]
        rng = np.random.default_rng(11)
        self.embers = [(rng.uniform(0, W), rng.uniform(0, H), rng.integers(1, 3), rng.uniform(0.6, 2.4), rng.uniform(0, 1),
                        rng.uniform(8, 40)) for _ in range(70)]

    def subtitle(self, font_path, logo_path, size=24, track=13):
        """THE COLLECTION in Cinzel (a Trajan-like capital, as on the film subtitles), same gold"""
        f = ImageFont.truetype(font_path, size * 2); f.set_variation_by_axes([600])
        txt = "THE COLLECTION"
        ws = [f.getlength(c) for c in txt]
        m = Image.new("L", (round(sum(ws) + track * 2 * len(txt)) + 40, size * 4), 0); d = ImageDraw.Draw(m); x = 20
        for c, w in zip(txt, ws):
            d.text((x, size * 3), c, font=f, fill=255, anchor="ls"); x += w + track * 2
        m = m.crop(m.getbbox())
        img = chisel(m, gold_ramp(logo_path), depth=2.6, grit=grit_field((m.height, m.width), 5))
        return img.resize((img.width // 2, img.height // 2), Image.LANCZOS)

    def background(self):
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / W * 1.4) ** 2 + ((y - 290) / H * 1.6) ** 2)
        glow = np.exp(-(d / 0.36) ** 2)
        base = np.array([9, 6, 5], np.float32)
        c = base + glow[..., None] * np.array([58, 30, 12], np.float32)
        return c

    def load_still(self, path):
        im = Image.open(path).convert("RGB")
        k = max(W * 1.12 / im.width, H * 1.12 / im.height)
        return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)

    def still_frame(self, i, p):
        """still i with a slow drift, p 0..1"""
        im = self.stills[i]
        dx = (im.width - W) * (0.2 + 0.6 * p); dy = (im.height - H) * 0.5
        return np.asarray(im.crop((round(dx), round(dy), round(dx) + W, round(dy) + H)), np.float32)

    # ---------------------------------------------------------------- shading
    def shade_ring(self, g, heat, spin):
        n, d = g["n"], g["d"]
        refl = d - 2 * (d * n).sum(-1, keepdims=True) * n
        rx, ry = refl[:, 0], refl[:, 1]
        env = 0.07 + 1.15 * np.exp(-((ry - 0.72) / 0.2) ** 2) + 0.75 * np.exp(-((rx + 0.8) / 0.16) ** 2) \
            + 0.5 * np.exp(-((rx - 0.85) / 0.2) ** 2) * np.clip(ry + 0.5, 0, 1)
        fire = np.clip(-ry - 0.15, 0, 1) ** 1.4 * (0.75 + 0.9 * heat)
        col = env[:, None] * np.array([1.0, 0.93, 0.78]) + fire[:, None] * np.array([1.0, 0.42, 0.10])
        gold = np.array([1.0, 0.72, 0.30])
        fres = 0.75 + 0.25 * (1 - np.abs((n * -d).sum(-1))) ** 4
        col = col * gold * fres[:, None]
        col = 1 - np.exp(-col * 1.6)
        # inscription: outer and inner faces, the verse once around each
        tw = self.outer.shape[1]; th = self.outer.shape[0]
        u = (g["u"] + math.pi) / (2 * math.pi)
        ty = np.clip((g["ay"] / (B * 0.66) * 0.5 + 0.5) * (th - 1), 0, th - 1).astype(int)
        side_o = np.clip((g["rq"] / A - 0.55) / 0.3, 0, 1); side_i = np.clip((-g["rq"] / A - 0.55) / 0.3, 0, 1)
        txo = (((-u + spin) % 1) * (tw - 1)).astype(int); txi = (((u + spin * 0.7) % 1) * (tw - 1)).astype(int)
        ins = self.outer[th - 1 - ty, txo] * side_o + self.inner[th - 1 - ty, txi] * side_i
        emit = ins * heat
        return col, emit

    def frame(self, k):
        # ---- timeline
        heat = seg(k, 14, 66) * (1 - seg(k, 200, 238))
        z = seg(k, 66, 108) * (1 - seg(k, 188, 226))                     # 0 = cover pose, 1 = through the ring
        tilt = math.radians(22 + 62 * z)
        scale = 205 * (1 + 0.12 * seg(k, 14, 66) * (1 - seg(k, 200, 238))) * (1 + 5.2 * z ** 2.2)
        cy = 252 + (360 - 252) * z
        title_a = (1 - seg(k, 34, 64)) + seg(k, 206, 240)
        title_a = min(1.0, title_a)
        spin = 0.05 * math.sin(2 * math.pi * k / N)
        # ---- background + embers
        img = self.bg.copy()
        ember_amt = 0.35 + 0.65 * heat
        # ---- journey through the hole
        g = self.ring.march(W * SS, H * SS, tilt, scale * SS, W * SS / 2, cy * SS)
        hole = g["hole"].reshape(H * SS, W * SS)
        hole = hole.reshape(H, SS, W, SS).mean((1, 3))
        jt = np.clip((k - 70) / (182 - 70), 0, 1)                        # 0..1 across the journey
        if 66 <= k <= 226:
            n = len(self.stills); pos = jt * (n - 1)
            i0 = min(int(pos), n - 1); f = pos - i0
            fade = smooth((f - 0.62) / 0.38)
            kk = k - k % 2                                              # the drift moves on every other frame (smaller file)
            pos2 = np.clip((kk - 70) / (182 - 70), 0, 1) * (n - 1); f2 = pos2 - min(int(pos2), n - 1)
            st = self.still_frame(i0, f2 * 0.5 + 0.25) if i0 < n - 1 else self.still_frame(i0, 0.25 + 0.5 * seg(kk, 182, 226))
            if fade > 0 and i0 + 1 < n:
                st = st * (1 - fade) + self.still_frame(i0 + 1, 0.25 * fade) * fade
            vis = seg(k, 66, 84) * (1 - seg(k, 206, 224))
            img = img * (1 - hole[..., None] * vis) + st * hole[..., None] * vis
        # embers (periodic: whole number of trips per loop)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        for (x0, y0, r, sp, ph, sway) in self.embers:
            trips = max(1, round(sp))
            y = (y0 - k / N * H * trips) % H
            x = x0 + sway * math.sin(2 * math.pi * (k / N * trips + ph))
            fl = 0.55 + 0.45 * math.sin(2 * math.pi * (k / N * 3 * trips + ph * 5))
            a = int(255 * ember_amt * fl * (0.35 + 0.65 * (1 - y / H)))
            dl.ellipse((x - r, y - r, x + r, y + r), fill=(255, 150 + int(60 * fl), 60, a))
        lay = lay.filter(ImageFilter.GaussianBlur(0.8))
        la = np.asarray(lay, np.float32)
        img = img * (1 - la[..., 3:] / 255) + la[..., :3] * (la[..., 3:] / 255)
        # ---- ring
        col, emit = self.shade_ring(g, heat, spin)
        big = np.zeros((H * SS * W * SS, 3), np.float32); cov = np.zeros(H * SS * W * SS, np.float32)
        em = np.zeros(H * SS * W * SS, np.float32)
        big[g["hi"]] = col * 255; cov[g["hi"]] = 1; em[g["hi"]] = emit
        big = big.reshape(H, SS, W, SS, 3).mean((1, 3)); cov = cov.reshape(H, SS, W, SS).mean((1, 3))
        em = em.reshape(H, SS, W, SS).mean((1, 3))
        # under the glowing letters the gold is burned dark, the glyphs themselves are fire
        burn = em[..., None]
        ringc = big * (1 - 0.55 * burn) + burn * np.array([255, 120, 30]) * 1.15
        img = img * (1 - cov[..., None]) + ringc * cov[..., None]
        if heat > 0.01:
            glow = ndimage.gaussian_filter(em, 5) * 1.6 + ndimage.gaussian_filter(em, 16) * 1.2
            img = img + glow[..., None] * np.array([255, 110, 25]) * heat
            # warm light on the scene around the ring
            amb = ndimage.gaussian_filter(cov, 40) * heat * 0.6
            img = img + amb[..., None] * np.array([70, 28, 6])
        # ---- title
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        if title_a > 0.001:
            ty = 452 + 30 * (1 - title_a) * (1 if k < N / 2 else -1) * 0
            for im, y in ((self.wm, 448), (self.sub, 448 + self.wm.height + 26)):
                t = im.copy(); t.putalpha(t.getchannel("A").point(lambda v: round(v * title_a)))
                out.alpha_composite(t, (round(W / 2 - im.width / 2), round(y)))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
    os.makedirs(out, exist_ok=True)
    ks = only if only else range(N)
    frames = []
    for k in ks:
        frames.append(sc.frame(k))
        if only:
            frames[-1].save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
    if only:
        return
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=70)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for m, i in enumerate(range(0, N, N // 16)):
        if m < 16:
            sheet.paste(frames[i].resize((320, 180)), ((m % 4) * 320, (m // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", N, "seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    only = None
    if "--frames" in sys.argv:
        only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]
    render(sys.argv[1], sys.argv[2], only)
