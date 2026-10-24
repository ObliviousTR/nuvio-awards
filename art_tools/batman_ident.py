"""Batman card, as a title ident: THE BATMAN (2022 title logo, red, scratched, the bat welded inside the letters)
on black in the rain, THE COLLECTION in red below it.
Hover (10 s): the lights go down and the title sinks into the dark; a road flare is lit and carried past behind it,
left to right, its red light and smoke finding the scratches in the letters. As the flare passes, the bat inside the
letters lets go - from the middle outwards - and breaks into a swarm of bats (the Batman Begins effect) that circles
the title, rim-lit by the flare, then settles back and welds into the letters again. The flare is gone, the lights
stutter back on like a bad neon and hold on the cover. The title never leaves the screen.
First frame = last frame = cover: lights fully on and no flare at both ends, the rain tiles over the whole loop.
usage: python3 art_tools/batman_ident.py SRC_DIR OUT_DIR [--frames a,b,...]
  SRC_DIR: title.png (The Batman title logo, TMDB 414906), Oswald-VF.ttf.
  title_nobat.png / title_batmask.png (the letters with the bat taken out, and the bat's mask) are built from
  title.png on the first run and kept next to it.
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 250
TW = 800                                    # title width on the card
T_DOWN = (14, 40)                           # lights go down
T_FLARE = (34, 50, 196, 214)                # flare fades in, (travels), fades out
T_TRAVEL = (34, 206)
T_SWARM = (60, 192)                         # the bat is away between these
T_UP = (200, 228)                           # lights come back ...
STUTTER = {203: 0.2, 204: 0.15, 209: 0.5, 213: 0.2, 214: 0.3, 219: 0.6}   # ... like a bad neon
NB = 210
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab; return smooth((k - a) / max(1, b - a))


def pnoise(h, w, beta, seed):
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    fq = np.sqrt(fx * fx + fy * fy); fq[0, 0] = 1
    sp = (r.normal(size=fq.shape) + 1j * r.normal(size=fq.shape)) / fq ** beta; sp[0, 0] = 0
    n = np.fft.irfft2(sp, s=(h, w)); return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


def spaced(txt, font_path, size, track, weight, fill):
    f = ImageFont.truetype(font_path, size * 2)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    m = Image.new("L", (int(sum(f.getlength(c) for c in txt) + track * 2 * len(txt)) + 40, size * 4), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 3), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track * 2
    m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
    return Image.merge("RGBA", (*[Image.new("L", m.size, v) for v in fill], m))


def prep(src):
    """Take the bat out of the title: its mask (darker red inside the letters, within a loose bat-shaped envelope)
    and the letters filled where it was (inpainted base + scratch detail borrowed from elsewhere in the letters)."""
    im = Image.open(os.path.join(src, "title.png")).convert("RGBA"); im = im.crop(im.getbbox())
    a = np.asarray(im).astype(np.float32); r, al = a[..., 0], a[..., 3]
    h, w = r.shape; k = w / 1300
    let = (al > 128).astype(np.float32)
    bl = cv2.GaussianBlur(r * let, (0, 0), 10) / np.maximum(cv2.GaussianBlur(let, (0, 0), 10), 1e-3)
    den = cv2.GaussianBlur(let, (0, 0), 10)
    env = np.zeros((h, w), np.uint8)
    P = [(0, 330), (150, 255), (390, 165), (450, 290), (560, 360), (600, 315), (650, 345), (700, 315), (760, 360),
         (870, 290), (930, 165), (1150, 250), (1300, 330), (1150, 390), (1000, 480), (760, 490), (650, 570),
         (540, 490), (300, 480), (150, 390)]
    cv2.fillPoly(env, [np.round(np.array(P) * k).astype(np.int32)], 1)
    m = ((bl < 170) & (den > 0.15) & (env > 0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    f = np.zeros_like(m); cv2.drawContours(f, [c for c in cs if cv2.contourArea(c) > 20000], -1, 1, -1)
    f = cv2.dilate(f, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    soft = cv2.GaussianBlur(f.astype(np.float32), (0, 0), 3)
    sm = cv2.resize(a[..., :3], (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    ms = (cv2.resize(f, (w // 4, h // 4), interpolation=cv2.INTER_NEAREST) > 0) | (cv2.resize(1 - let, (w // 4, h // 4)) > 0.5)
    ms = cv2.dilate(ms.astype(np.uint8), np.ones((3, 3), np.uint8))
    base = cv2.resize(cv2.inpaint(sm.astype(np.uint8), ms, 15, cv2.INPAINT_TELEA).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    base = cv2.GaussianBlur(base, (0, 0), 6)
    lo = cv2.GaussianBlur(a[..., :3] * let[..., None], (0, 0), 6) / np.maximum(cv2.GaussianBlur(let, (0, 0), 6), 1e-3)[..., None]
    hf = (a[..., :3] - lo) * cv2.erode(let, np.ones((15, 15), np.uint8))[..., None] * (1 - cv2.dilate(f, np.ones((25, 25), np.uint8)))[..., None]
    hf = np.roll(hf, (380, -310), (0, 1))
    rgb = a[..., :3] * (1 - soft[..., None]) + np.clip(base + hf, 0, 255) * soft[..., None]
    Image.fromarray(np.dstack([rgb, al]).astype(np.uint8)).save(os.path.join(src, "title_nobat.png"))
    Image.fromarray((soft * 255).astype(np.uint8)).save(os.path.join(src, "title_batmask.png"))


def bat_pts(flap):
    w = 0.6 * flap
    return np.array([(-1.0, -0.2 - w), (-0.66, 0.0 - w * 0.5), (-0.5, -0.06), (-0.3, 0.1), (-0.14, -0.04), (-0.09, -0.24),
                     (0.0, -0.13), (0.09, -0.24), (0.14, -0.04), (0.3, 0.1), (0.5, -0.06), (0.66, 0.0 - w * 0.5),
                     (1.0, -0.2 - w), (0.72, 0.16), (0.36, 0.22), (0.0, 0.36), (-0.36, 0.22), (-0.72, 0.16)])


class Scene:
    def __init__(self, src):
        if not os.path.exists(os.path.join(src, "title_nobat.png")):
            prep(src)
        t = Image.open(os.path.join(src, "title.png")).convert("RGBA"); box = t.getbbox(); t = t.crop(box)
        self.th = round(t.height * TW / t.width)
        self.tx, self.ty = (W - TW) // 2, 300 - self.th // 2

        def place(im):
            arr = np.asarray(im.resize((TW, self.th), Image.LANCZOS), np.float32) / 255
            out = np.zeros((H, W) + arr.shape[2:], np.float32)
            out[self.ty:self.ty + self.th, self.tx:self.tx + TW] = arr
            return out
        self.tb = place(t)
        self.tbn = place(Image.open(os.path.join(src, "title_nobat.png")).convert("RGBA"))
        self.bm = place(Image.open(os.path.join(src, "title_batmask.png")).convert("L"))
        self.scr = np.clip((self.tb[..., 0] - np.clip(cv2.GaussianBlur(self.tb[..., 0], (0, 0), 5), 0, 1)) * 6, 0, 1)
        self.sub = spaced("THE COLLECTION", os.path.join(src, "Oswald-VF.ttf"), 22, 18, 500, (214, 52, 44))
        self.suby = self.ty + self.th + 28
        # rain, tiling the frame both ways (it moves a whole number of frames over the loop)
        rain = np.zeros((H * 4, W * 4), np.float32); r = np.random.default_rng(4)
        for _ in range(1500):
            x0, y0, L = r.uniform(0, W), r.uniform(0, H), r.uniform(16, 40)
            for dx in (-W, 0, W):
                for dy in (-H, 0, H):
                    cv2.line(rain, (int((x0 + dx) * 4), int((y0 + dy) * 4)), (int((x0 + dx - L * 0.15) * 4), int((y0 + dy + L) * 4)),
                             float(r.uniform(0.2, 0.8)), 4, cv2.LINE_AA)
        self.rain = cv2.resize(rain, (W, H), interpolation=cv2.INTER_AREA)
        self.smk = pnoise(512, 1024, 1.5, 21)
        # the swarm: every bat starts and ends on a point of the welded bat
        r = np.random.default_rng(5)
        ys, xs = np.nonzero(self.bm > 0.7)
        pk = r.choice(len(xs), NB, replace=False)
        self.home = np.stack([xs[pk], ys[pk]], -1).astype(np.float64)
        big = r.random(NB) < 0.1
        self.q = dict(r=r.uniform(150, 640, NB), th=r.uniform(0, 2 * math.pi, NB), sp=r.uniform(0.8, 1.3, NB),
                      ph=r.uniform(0, 2 * math.pi, NB), sz=r.uniform(9, 17, NB) * np.where(big, 2.6, 1.0),
                      dl=r.uniform(0, 0.1, NB), lift=r.uniform(-100, 80, NB), big=big)
        dis = cv2.GaussianBlur(r.random((H, W)).astype(np.float32), (0, 0), 6); dis = (dis - dis.min()) / (dis.max() - dis.min())
        dc = np.sqrt(((xx - W / 2) / (TW / 2)) ** 2 + ((yy - (self.ty + self.th * 0.55)) / (self.th / 2)) ** 2)
        self.order = np.clip(1 - dc / 1.2, 0, 1) * 0.6 + dis * 0.4

    def frame(self, k):
        on = min(1.0, 1 - seg(k, T_DOWN) + seg(k, T_UP)) * STUTTER.get(k, 1.0)
        fl = seg(k, T_FLARE[:2]) * (1 - seg(k, T_FLARE[2:]))
        fx = -80 + (W + 160) * smooth((k - T_TRAVEL[0]) / (T_TRAVEL[1] - T_TRAVEL[0]))
        fy = 610 + 12 * math.sin(k * 0.29)
        flick = 0.85 + 0.15 * math.sin(k * 2.3) * math.sin(k * 0.7 + 1)
        light = np.exp(-(((xx - fx) / 300) ** 2 + ((yy - fy) / 220) ** 2)) * fl * flick
        img = np.zeros((H, W, 3), np.float32) + np.array([5, 3, 3], np.float32)
        # smoke drifting up from the flare, lit red
        u = (xx * 0.8 - fx * 0.6) % 1024; v = (yy * 0.7 + k * 5) % 512
        sm = cv2.remap(self.smk, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        smoke = np.clip((sm - 0.45) * 2.5, 0, 1) * np.exp(-(((xx - fx) / 440) ** 2 + ((yy - fy + 170) / 330) ** 2)) * fl
        img += smoke[..., None] * np.array([120, 18, 12], np.float32) * flick
        img += light[..., None] * np.array([160, 30, 15], np.float32)
        core = np.exp(-(((xx - fx) / 10) ** 2 + ((yy - fy) / 10) ** 2)) * fl
        img += core[..., None] * np.array([255, 195, 160], np.float32)
        img += cv2.GaussianBlur(core, (0, 0), 26)[..., None] * np.array([255, 60, 30], np.float32) * 1.6
        # the bat lets go of the letters (middle first) and comes back
        q = self.q
        tt = np.clip((k / (N - 1) - T_SWARM[0] / (N - 1) - q["dl"] * 0.5) / ((T_SWARM[1] - T_SWARM[0]) / (N - 1) - 0.05), 0, 1)
        env = np.sin(np.pi * tt) ** 1.2
        away = float(np.clip(np.sin(np.pi * np.clip((k - T_SWARM[0] + 6) / (T_SWARM[1] - T_SWARM[0]), 0, 1)) * 1.3, 0, 1))
        gone = np.clip((away * 1.15 - (1 - self.order)) / 0.08 + 0.5, 0, 1) * self.bm
        src = self.tb * (1 - gone[..., None]) + self.tbn * gone[..., None]
        a = self.tb[..., 3]
        lit = 0.2 + 0.8 * on + 2.0 * light
        col = src[..., :3] * 255 * np.clip(lit, 0, 1.6)[..., None]
        col += (self.scr * light * 2.5)[..., None] * np.array([255, 120, 90], np.float32)
        img = img * (1 - a[..., None]) + col * a[..., None]
        # swarm
        ang = q["th"] + 2 * math.pi * tt * q["sp"] * 1.2
        px = self.home[:, 0] * (1 - env) + (W / 2 + np.cos(ang) * q["r"]) * env
        py = self.home[:, 1] * (1 - env) + (self.ty + self.th * 0.5 + np.sin(ang) * q["r"] * 0.42 + q["lift"]) * env
        S2 = 2
        lay = np.zeros((H * S2, W * S2), np.uint8); rim = np.zeros((H * S2, W * S2), np.uint8)
        for i in np.argsort(q["sz"]):
            if env[i] < 0.03:
                continue
            flap = math.sin(k * 1.1 * q["sp"][i] + q["ph"][i])
            sz = q["sz"][i] * (0.45 + 0.85 * env[i])
            pts = bat_pts(flap) * sz * np.array([1 if math.cos(ang[i]) < 0 else -1, 1]) + np.array([px[i], py[i]])
            cv2.fillPoly(lay, [np.round(pts * S2 * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
            cv2.polylines(rim, [np.round((pts + [0, 1.2]) * S2 * 16).astype(np.int32)], True, 200, 2, cv2.LINE_AA, 4)
        lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        rim = cv2.resize(rim, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * (1 - lay)
        img = img * (1 - lay[..., None]) + np.array([12, 4, 4], np.float32) * lay[..., None]
        img += rim[..., None] * np.array([255, 70, 45], np.float32) * np.clip(0.25 + light * 2.5, 0, 1.2)[..., None]
        # rain (6 passes down, 1 across over the loop)
        rr = np.roll(np.roll(self.rain, (k * 6 * H // N) % H, axis=0), (-k * W // N) % W, axis=1)
        img += rr[..., None] * np.array([70, 40, 40], np.float32) * (0.4 + 0.8 * light[..., None] + 0.3 * on)
        # vignette
        d = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.4 * np.clip(d - 0.45, 0, 1) ** 1.3)[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        s = self.sub.copy(); s.putalpha(s.getchannel("A").point(lambda v: round(v * (0.3 + 0.7 * on))))
        out.alpha_composite(s, (round(W / 2 - s.width / 2), self.suby))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
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
    render(sys.argv[1], sys.argv[2], only)
