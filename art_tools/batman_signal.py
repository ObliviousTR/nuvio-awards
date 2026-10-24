"""Batman card: a cloudy Gotham night, the Bat-Signal (the 1989 emblem's bat, from the title logo on TMDB) thrown on the
clouds by a searchlight beam, the skyline below, BATMAN and THE COLLECTION between them.
Hover: the title fades and the searchlight loses its mark - the beam swings off across the clouds as a plain, unfocused
pool of light and searches the sky for a while, then finds its place again and the bat snaps into focus. The camera
moves in on the signal (no dive: clouds stay around it) and the bat becomes a window: the Batmen of every era slide by
inside it, one after another, unhurried - West, Keaton, the Phantasm, Kilmer, Clooney, Bale, Affleck, Pattinson. The
last one fades back into the dark bat before the camera pulls out, and the title returns. Seamless loop (first frame =
cover).
Everything but the stills and the title is drawn analytically in cover coordinates.
usage: python3 art_tools/batman_signal.py SRC_DIR OUT_DIR [--frames a,b]
  SRC_DIR: bat.json (bat outline + emblem ellipse in logo pixels), title.png, Oswald-VF.ttf,
           stills/NN_*.jpg (optional stills/NN_*.json: {"cx": 0.5, "cy": 0.4, "zoom": 1.0} framing inside the bat)
"""
import glob, json, math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
SIG_C, SIG_W = (640.0, 222.0), 370.0          # signal centre and width on the cover
ZOOM = 2.75                                    # camera scale once it has moved in on the signal

# timeline (frames of 40 ms)
T_TITLE_OUT = (8, 26)
T_UNLOCK = (12, 34)                            # the bat blurs away as the light starts to move
T_SEARCH = (22, 112)                           # the pool of light wanders over the clouds
T_FOCUS = (108, 130)                           # back on its mark, the bat comes into focus
T_PUSH = (134, 168)
T_IN = (166, 184)                              # first still fades into the bat
HOLD, SLIDE = 22, 16                           # per still: rest, then slide to the next
T_OUT_LEN = 18                                 # last still fades back to the dark bat
PULL_LEN = 36
TITLE_IN_LEN = 22


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab
    return smooth((k - a) / max(1, b - a))


rng0 = np.random.default_rng(5)
PERM = rng0.permutation(256)
VALS = rng0.random(256).astype(np.float32)


def vnoise(x, y):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)

    def h(i, j):
        return VALS[PERM[(PERM[i & 255] + j) & 255]]
    a, b, c, d = h(xi, yi), h(xi + 1, yi), h(xi, yi + 1), h(xi + 1, yi + 1)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, octaves=5):
    t, amp, f, norm = 0, 1.0, 1.0, 0
    for _ in range(octaves):
        t = t + amp * vnoise(x * f, y * f); norm += amp
        amp *= 0.5; f *= 2.03
    return t / norm


# where the light goes while it searches (cover coords); the ends are the signal's own place
PATH = [SIG_C, (560, 200), (380, 168), (300, 214), (352, 250), (520, 150), (760, 126), (930, 176), (968, 236),
        (880, 262), (760, 238), SIG_C]


def catmull(pts, t):
    """Point at t in [0,1] along a Catmull-Rom curve through pts, eased so it starts and stops gently."""
    n = len(pts) - 1
    u = smooth(t) * n
    i = min(n - 1, int(u)); f = u - i
    p0, p1, p2, p3 = (np.array(pts[max(0, i - 1)]), np.array(pts[i]), np.array(pts[i + 1]), np.array(pts[min(n, i + 2)]))
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)


class Scene:
    def __init__(self, src):
        d = json.load(open(os.path.join(src, "bat.json")))
        ex, ey, erx, ery = d["ellipse"]
        self.k = SIG_W / (2 * erx)
        self.erx, self.ery = erx * self.k, ery * self.k
        self.bat = np.array(d["bat"], np.float64)
        self.bat = np.stack([(self.bat[:, 0] - ex) * self.k + SIG_C[0], (self.bat[:, 1] - ey) * self.k + SIG_C[1]], -1)
        tl = Image.open(os.path.join(src, "title.png")).convert("RGBA"); tl = tl.crop(tl.getbbox())
        tw = 400; self.title = tl.resize((tw, round(tl.height * tw / tl.width)), Image.LANCZOS)
        f = ImageFont.truetype(os.path.join(src, "Oswald-VF.ttf"), 44); f.set_variation_by_axes([400])
        txt = "THE COLLECTION"; tr = 26
        m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 20, 80), 0)
        dd = ImageDraw.Draw(m); x = 10
        for c in txt:
            dd.text((x, 60), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); self.sub = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        # stills, framed for the window the bat makes once the camera has moved in
        self.iw = round(2 * self.erx * ZOOM * 1.04); self.ih = round(2 * self.ery * ZOOM * 1.08)
        self.stills = []
        for fp in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            fr = {"cx": 0.5, "cy": 0.45, "zoom": 1.0}
            jp = os.path.splitext(fp)[0] + ".json"
            if os.path.exists(jp):
                fr.update(json.load(open(jp)))
            im = Image.open(fp).convert("RGB")
            kk = max(self.iw / im.width, self.ih / im.height) * fr["zoom"] * 1.06     # 6% spare for the slow push
            im = im.resize((math.ceil(im.width * kk), math.ceil(im.height * kk)), Image.LANCZOS)
            self.stills.append((np.asarray(im, np.float32), fr))
        self.n = len(self.stills)
        self.t_slides = T_IN[1] + HOLD
        self.t_out = self.t_slides + (self.n - 1) * (HOLD + SLIDE) + HOLD
        self.t_pull = (self.t_out + T_OUT_LEN, self.t_out + T_OUT_LEN + PULL_LEN)
        self.t_title_in = (self.t_pull[1] - 12, self.t_pull[1] - 12 + TITLE_IN_LEN)
        self.N = self.t_title_in[1] + 10
        # skyline: a hazy far row and a dark near row of buildings, and lit windows on the near row (cover pixels)
        rng = np.random.default_rng(12)
        self.far, self.buildings, self.windows = [], [], []
        for layer, (hmin, hmax, wmin, wmax) in (("far", (120, 260, 30, 80)), ("near", (50, 170, 24, 66))):
            x = -20
            while x < W + 20:
                bw = rng.uniform(wmin, wmax); bh = rng.uniform(hmin, hmax) * (1.3 if rng.random() < 0.1 else 1)
                top = H - bh
                poly = [(x, H + 5), (x, top), (x + bw, top), (x + bw, H + 5)]
                r = rng.random()
                if r < 0.22:                                          # a spire
                    cxm = x + bw / 2; poly = [(x, H + 5), (x, top), (cxm - bw * 0.16, top), (cxm, top - rng.uniform(24, 70)),
                                              (cxm + bw * 0.16, top), (x + bw, top), (x + bw, H + 5)]
                elif r < 0.4:                                         # a stepped crown
                    st = bw * 0.22; h2 = rng.uniform(14, 30)
                    poly = [(x, H + 5), (x, top), (x + st, top), (x + st, top - h2), (x + bw - st, top - h2),
                            (x + bw - st, top), (x + bw, top), (x + bw, H + 5)]
                (self.far if layer == "far" else self.buildings).append(np.array(poly))
                if layer == "near":
                    dens = rng.uniform(0.02, 0.16)
                    for wy in np.arange(top + 8, H, 9):
                        for wx in np.arange(x + 4, x + bw - 5, 7):
                            if rng.random() < dens:
                                self.windows.append((wx, wy))
                x += bw + rng.uniform(-8, 3)
        self.windows = np.array(self.windows)

    def poly_mask(self, polys, tf, ss=2):
        m = np.zeros((H * ss, W * ss), np.uint8)
        pts = [np.round(np.clip(tf(p) * ss, -1e6, 1e6) * 16).astype(np.int32) for p in polys]
        cv2.fillPoly(m, pts, 255, lineType=cv2.LINE_AA, shift=4)
        return cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255

    # ---- the stills strip, in screen pixels, centred on the signal
    def strip(self, k, ecx, ecy):
        img = np.zeros((H, W, 3), np.float32) + np.array([10, 12, 18], np.float32)
        gap = 40
        pitch = self.iw + gap
        t = k - self.t_slides
        if t < 0:
            pos = 0.0
        else:
            j = int(t // (HOLD + SLIDE)); r = t - j * (HOLD + SLIDE)
            pos = j + smooth((r - HOLD) / SLIDE) if r > HOLD else float(j)
            pos = min(pos, self.n - 1)
        for j in range(self.n):
            off = (j - pos) * pitch
            if abs(off) > W:
                continue
            arr, fr = self.stills[j]
            # slow push on each still while it is on screen
            life = (k - (self.t_slides + (j - 1) * (HOLD + SLIDE))) / (2 * (HOLD + SLIDE) + HOLD)
            z = 1.0 + 0.045 * min(1.0, max(0.0, life))
            ah, aw = arr.shape[:2]
            cw, ch = self.iw / z, self.ih / z                     # crop size in the pre-sized still
            cx = min(max(fr["cx"] * aw, cw / 2), aw - cw / 2); cy = min(max(fr["cy"] * ah, ch / 2), ah - ch / 2)
            x0, y0 = int(cx - cw / 2), int(cy - ch / 2)                 # only the crop, so a still never spills
            sub = np.ascontiguousarray(arr[y0:min(ah, y0 + math.ceil(ch) + 2), x0:min(aw, x0 + math.ceil(cw) + 2)])
            M = np.float32([[z, 0, ecx + off - self.iw / 2 - (cx - cw / 2 - x0) * z],
                            [0, z, ecy - self.ih / 2 - (cy - ch / 2 - y0) * z]])
            lay = cv2.warpAffine(sub, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(-1, -1, -1))
            ok = lay[..., 0] >= 0
            xl, xr = ecx + off - self.iw / 2, ecx + off + self.iw / 2
            ok[:, :max(0, math.ceil(xl))] = False; ok[:, max(0, int(xr)):] = False
            img[ok] = lay[ok]
        return img

    def frame(self, k):
        N = self.N
        # where the light is, and how sharp the bat in it is
        search = seg(k, T_SEARCH)
        C = np.array(SIG_C) if (k < T_SEARCH[0] or k > T_SEARCH[1]) else catmull(PATH, search)
        blur = seg(k, T_UNLOCK) * (1 - seg(k, T_FOCUS))
        flare = math.exp(-((k - T_FOCUS[1]) / 9.0) ** 2)
        # camera
        push = seg(k, T_PUSH) * (1 - seg(k, self.t_pull))
        s = math.exp(math.log(ZOOM) * push)
        A = np.array(SIG_C)
        c = (A[0] + (W / 2 - A[0]) * push, A[1] + (H / 2 - A[1]) * push)
        tf = lambda p: np.stack([c[0] + (p[:, 0] - A[0]) * s, c[1] + (p[:, 1] - A[1]) * s], -1)
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        px = A[0] + (xs - c[0]) / s; py = A[1] + (ys - c[1]) / s
        # sky
        t = np.clip(py / H, 0, 1)
        img = np.array([8, 11, 20], np.float32) * (1 - t[..., None]) + np.array([30, 30, 40], np.float32) * t[..., None]
        img += np.clip((py - 420) / 300, 0, 1)[..., None] * np.array([34, 20, 10], np.float32)       # city glow
        # clouds, drifting back and forth over the loop
        sway = 18 * math.sin(2 * math.pi * k / N)
        cl = fbm((px + sway) / 230, py / 150 + 3.1)
        cl2 = fbm((px - sway * 0.6) / 90 + 7.7, py / 70)
        cloud = np.clip((cl * 0.75 + cl2 * 0.35 - 0.42) * 2.2, 0, 1) * np.clip(1.15 - py / 640, 0, 1)
        img = img * (1 - 0.6 * cloud[..., None]) + cloud[..., None] * np.array([46, 52, 66], np.float32) * 0.9
        # searchlight beam from below the skyline to wherever the light is
        P0 = np.array([905.0, 760.0]); ax = C - P0; L = np.linalg.norm(ax); ax /= L
        rx, ry = px - P0[0], py - P0[1]
        along = rx * ax[0] + ry * ax[1]; across = np.abs(-rx * ax[1] + ry * ax[0])
        wdt = 7 + (self.erx * 0.55 - 7) * np.clip(along / L, 0, 1)
        beam = np.clip(1 - across / wdt, 0, 1) ** 1.5 * np.clip(along / 40, 0, 1) * np.clip((L + 10 - along) / 60, 0, 1)
        beam *= (0.16 + 0.05 * blur + 0.1 * flare) * (0.7 + 0.6 * cloud)
        img += beam[..., None] * np.array([255, 236, 190], np.float32)
        # the pool of light on the clouds: soft edge, softer still while it is out of focus
        e = np.sqrt(((px - C[0]) / self.erx) ** 2 + ((py - C[1]) / self.ery) ** 2)
        edge = (0.06 + 0.22 * blur) * self.erx * s
        oval = np.clip((1 - e) * self.erx * s / max(edge, 1) + 0.5, 0, 1)
        halo = np.exp(-np.clip(e - 1, 0, None) / (0.35 + 0.3 * blur)) * (e > 0.98 - 0.2 * blur)
        lit = (0.55 + 0.6 * cloud) * (0.92 + 0.22 * flare) * (1 - 0.18 * blur)
        sigcol = np.array([255, 238, 186], np.float32)
        img = img * (1 - oval[..., None]) + (sigcol * lit[..., None]) * oval[..., None]
        img += halo[..., None] * np.array([90, 80, 60], np.float32) * (0.5 + 0.5 * cloud[..., None]) * (0.8 + 0.5 * flare)
        # the bat: sharp on its mark, a faint smudge while the light searches; a window onto the films later on
        d = C - np.array(SIG_C)
        bm = self.poly_mask([self.bat + d], tf)
        if blur > 0.001:
            sig = 1 + 26 * blur * s
            bb = cv2.GaussianBlur(bm, (0, 0), sig)
            bm = bm * (1 - blur) + bb * blur * (1 - 0.75 * blur)
        dark = np.array([12, 14, 22], np.float32) * (0.9 + 0.2 * cloud[..., None])
        f_in = seg(k, T_IN) * (1 - seg(k, (self.t_out, self.t_out + T_OUT_LEN)))
        if f_in > 0.001:
            ecx, ecy = tf(np.array([SIG_C]))[0]
            films = self.strip(k, ecx, ecy)
            inner = cv2.GaussianBlur(bm, (0, 0), 16)                   # a soft shadow just inside the bat's edge
            films = films * (0.45 + 0.55 * np.clip(inner * 1.6 - 0.3, 0, 1))[..., None]
            inside = dark * (1 - f_in) + films * f_in
        else:
            inside = dark
        img = img * (1 - bm[..., None]) + inside * bm[..., None]
        # skyline and windows
        if s < 6:
            fk = self.poly_mask(self.far, tf)
            img = img * (1 - fk[..., None]) + np.array([20, 22, 32], np.float32) * fk[..., None]
            sk = self.poly_mask(self.buildings, tf)
            img = img * (1 - sk[..., None]) + np.array([5, 6, 10], np.float32) * sk[..., None]
            lay = Image.new("L", (W, H), 0); dl = ImageDraw.Draw(lay)
            wp = tf(self.windows)
            for i, (wx, wy) in enumerate(wp):
                if wy > H + 4:
                    continue
                if hash((i, (k + i * 7) // 37 % 7)) % 23:               # a few windows blink
                    dl.rectangle((wx, wy, wx + 2.2 * s, wy + 3 * s), fill=210)
            wl = np.asarray(lay, np.float32)[..., None] / 255
            img = img * (1 - wl * 0.9) + wl * 0.9 * np.array([255, 196, 110], np.float32)
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        ta = min(1.0, (1 - seg(k, T_TITLE_OUT)) + seg(k, self.t_title_in))
        if ta > 0.001:
            for im, y in ((self.title, 392), (self.sub, 392 + self.title.height + 18)):
                t2 = im.copy() if im.mode == "RGBA" else Image.merge("RGBA", (*[Image.new("L", im.size, 236)] * 3, im))
                t2.putalpha(t2.getchannel("A").point(lambda v: round(v * ta)))
                out.alpha_composite(t2, (round(W / 2 - t2.width / 2), y))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
    print("stills", sc.n, "frames", sc.N, "seconds", round(sc.N * MS / 1000, 1))
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            sc.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    N = sc.N
    frames = [sc.frame(k) for k in range(N)]
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for m in range(16):
        sheet.paste(frames[m * N // 16].resize((320, 180)), ((m % 4) * 320, (m // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")] if "--frames" in sys.argv else None
    render(sys.argv[1], sys.argv[2], only)
