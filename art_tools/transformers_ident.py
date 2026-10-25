"""Transformers card. The 2007 metal TRANSFORMERS (TMDB) and the series' own idea: the title is a machine.

--mode transform  After Imaginary Forces' 2006 teaser title (the logo reconfigures itself, panels open, expand and
                  contract like a giant jigsaw puzzle, and the structure becomes the Autobot insignia): the title comes
                  apart into heavy metal panels; they lift, cast their shadows, slide along one axis then the other,
                  turn over and build the Autobot insignia, which locks with a jolt and catches the light; then the
                  insignia comes apart the same way and the title locks back on the cover.
--mode allspark   The AllSpark: the title before a dark metal plate cut with angular channels (the Cube's surface,
                  the circuit lines of Transformers One); the Cube's blue energy runs along the channels from the
                  edges to the title, the title's edges take the charge, then it drains away.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/transformers_ident.py SRC_DIR OUT_DIR [--mode transform|allspark] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (TMDB logo 8nx4OwqxY7NtS9Llu6Oi23ViGB, film 1858), insignia.png (the films' metal Autobot
           insignia, marketing art, cut out), BarlowCondensed-Medium.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linear_sum_assignment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / (b - a)))


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0.05 else a


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


def spaced(font, size, txt, track):
    f = ImageFont.truetype(font, size)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 40, size * 2), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def to_image(img, k, grain, amt=0.03):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


def load_rgba(path, w=None, h=None):
    im = Image.open(path).convert("RGBA")
    if w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    elif h:
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


class Stage:
    def __init__(self, src):
        lg = load_rgba(os.path.join(src, "logo.png"), w=1010)
        self.lh, self.lw = lg.shape[:2]
        self.lx0 = (W - self.lw) // 2; self.ly0 = 300 - self.lh // 2
        self.logo = np.zeros((H, W, 4), np.float32)
        self.logo[self.ly0:self.ly0 + self.lh, self.lx0:self.lx0 + self.lw] = lg
        col = spaced(os.path.join(src, "BarlowCondensed-Medium.ttf"), 44, "THE COLLECTION", 22)
        self.col = np.zeros((H, W), np.float32)
        cy = self.ly0 + self.lh + 92; cx = (W - col.shape[1]) // 2
        self.col[cy:cy + col.shape[0], cx:cx + col.shape[1]] = col
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.44) / (H * 0.66)) ** 2)
        self.bg = (np.clip(1 - r, 0, 1) ** 1.6)[..., None] * np.array([0.05, 0.065, 0.085], np.float32) + np.array([0.006, 0.008, 0.011], np.float32)
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def finish(self, img, k, jolt=(0.0, 0.0)):
        img = img * (1 - 0.55 * np.clip(bigblur(self.col, 10) * 1.6, 0, 1))[..., None]
        img = img * (1 - self.col[..., None]) + np.array([0.74, 0.79, 0.86], np.float32) * self.col[..., None]
        if abs(jolt[0]) + abs(jolt[1]) > 0.02:
            img = cv2.warpAffine(img, np.float32([[1, 0, jolt[0]], [0, 1, jolt[1]]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        return to_image(img, k, self.grain)


# --------------------------------------------------------------------------------------------------------- transform
def panels(alpha, x0, y0, w, h, seed, smin=16, smax=46):
    """cut a box into rectangular plates (a random binary split), keep those that carry metal"""
    rng = np.random.default_rng(seed)
    out = []

    def split(x, y, ww, hh, depth):
        if (ww <= smax and hh <= smax and (rng.random() < 0.55 or ww < smin * 2 or hh < smin * 2)) or depth > 12:
            cov = alpha[y:y + hh, x:x + ww].mean() if ww > 0 and hh > 0 else 0
            if cov > 0.06:
                out.append((x, y, ww, hh))
            return
        if (ww >= hh and ww >= 2 * smin) or hh < 2 * smin:
            c = int(rng.uniform(0.35, 0.65) * ww); split(x, y, c, hh, depth + 1); split(x + c, y, ww - c, hh, depth + 1)
        else:
            c = int(rng.uniform(0.35, 0.65) * hh); split(x, y, ww, c, depth + 1); split(x, y + c, ww, hh - c, depth + 1)

    split(x0, y0, w, h, 0)
    return out


TO_START, BACK_START = 1, 122


class Transform(Stage):
    def __init__(self, src):
        super().__init__(src)
        ins = load_rgba(os.path.join(src, "insignia.png"), h=258)
        # the insignia in the title's steel: same blue-grey, a little brighter
        lum = ins[..., :3].mean(2, keepdims=True)
        tint = self.logo[..., :3][self.logo[..., 3] > 0.9].mean(0) / max(float(self.logo[..., :3][self.logo[..., 3] > 0.9].mean()), 1e-3)
        ins[..., :3] = np.clip(lum * tint * 1.25, 0, 1)
        ih, iw = ins.shape[:2]
        self.ix0 = (W - iw) // 2; self.iy0 = 300 - ih // 2 - 18
        self.ins = np.zeros((H, W, 4), np.float32); self.ins[self.iy0:self.iy0 + ih, self.ix0:self.ix0 + iw] = ins
        tp = panels(self.logo[..., 3], self.lx0, self.ly0, self.lw, self.lh, 3, 28, 64)
        ip = panels(self.ins[..., 3], self.ix0, self.iy0, iw, ih, 5, 26, 58)
        ct = np.array([(x + w / 2, y + h / 2) for x, y, w, h in tp]); ci = np.array([(x + w / 2, y + h / 2) for x, y, w, h in ip])
        # pair the title's plates with the insignia's: each travels to the nearest free place (by columns)
        a = (ct[:, None, 0] - W / 2) / self.lw * 2; b = (ci[None, :, 0] - W / 2) / iw * 2
        cost = (a - b) ** 2 * 4 + ((ct[:, None, 1] - ci[None, :, 1]) / 300) ** 2
        r, c = linear_sum_assignment(cost)
        pairs = list(zip(r, c))
        used_t = set(r); used_i = set(c)
        for t in range(len(tp)):                                         # extra title plates fold under a neighbour
            if t not in used_t:
                pairs.append((t, int(np.argmin(cost[t])) + 10000))
        for i in range(len(ip)):                                         # extra insignia plates open out from under one
            if i not in used_i:
                pairs.append((int(np.argmin(cost[:, i])) + 10000, i))
        rng = np.random.default_rng(9)
        self.moves = []
        for t, i in pairs:
            extra_t = t >= 10000; extra_i = i >= 10000
            tt = t - 10000 if extra_t else t; ii = i - 10000 if extra_i else i
            src_box = tp[tt]; dst_box = ip[ii]
            stag = abs(src_box[0] + src_box[2] / 2 - W / 2) / (self.lw / 2) * 18 + rng.uniform(0, 1.5)   # from the middle out
            stag_b = (1 - abs(dst_box[0] + dst_box[2] / 2 - W / 2) / (iw / 2)) * 12 + rng.uniform(0, 1.5)
            self.moves.append(dict(s=src_box, d=dst_box, horiz=True, rot=int(rng.choice([0, 0, 0, 2])),
                                   stag=stag, stag_b=stag_b, fade_t=extra_i, fade_i=extra_t))
        self.tp, self.ip = tp, ip
        self.arr1 = TO_START + max(m["stag"] for m in self.moves) + 44
        self.arr2 = BACK_START + max(m["stag_b"] for m in self.moves) + 44
        self.go1 = TO_START + min(m["stag"] for m in self.moves)
        self.go2 = BACK_START + min(m["stag_b"] for m in self.moves)

    def patch(self, img, box):
        x, y, w, h = box
        return img[y:y + h, x:x + w].copy()

    def state(self, m, k):
        """where plate m is at frame k: centre, size, angle, flip (-1..1), texture (0 title / 1 insignia), lift"""
        def leg(t0):
            u = k - t0
            lift = ease(u / 6) - 0.0
            u1 = ease((u - 6) / 15); u2 = ease((u - 21) / 17); settle = ease((u - 38) / 6)
            return lift, u1, u2, settle
        out = None
        for start, frm, to, stag, tex0 in ((TO_START, m["s"], m["d"], m["stag"], 0), (BACK_START, m["d"], m["s"], m["stag_b"], 1)):
            t0 = start + stag
            lift, u1, u2, settle = leg(t0)
            if k < t0 and start == BACK_START:
                break
            fx, fy = frm[0] + frm[2] / 2, frm[1] + frm[3] / 2; tx, ty = to[0] + to[2] / 2, to[1] + to[3] / 2
            if m["horiz"]:
                cx = fx + (tx - fx) * u1; cy = fy + (ty - fy) * u2
            else:
                cy = fy + (ty - fy) * u1; cx = fx + (tx - fx) * u2
            w = frm[2] + (to[2] - frm[2]) * u2; h = frm[3] + (to[3] - frm[3]) * u2
            ang = 90 * m["rot"] * u2
            flip = math.cos(math.pi * u2)                                 # turns over during the second leg
            tex = tex0 if u2 < 0.5 else 1 - tex0
            lifted = lift * (1 - settle)
            out = (cx, cy, w, h, ang, flip, tex, lifted, u2, tex0)
        return out

    def frame(self, k):
        k = k % N
        img = self.bg.copy()
        # at rest: draw the whole title or the whole insignia (no seams)
        resting_ins = self.arr1 <= k < self.go2
        if k < self.go1 or k >= self.arr2 or resting_ins:
            src = self.ins if resting_ins else self.logo
            a = src[..., 3:4]
            # shadow
            sh = blur(np.roll(np.roll(src[..., 3], 8, 0), 4, 1), 6)
            img = img * (1 - 0.55 * sh)[..., None]
            face = src[..., :3]
            if resting_ins:                                              # the insignia catches the light once
                u = (k - self.arr1 - 10) / 22.0
                band = np.exp(-(((self.xx + 0.5 * self.yy) - (380 + u * 520)) / 60) ** 2)
                face = np.clip(face + band[..., None] * 0.35 * a, 0, 1)
            img = img * (1 - a) + face * a
            jolt = self.jolt(k)
            return self.finish(img, k, jolt)
        # in motion: every plate on its own
        layers = []
        for m in self.moves:
            st = self.state(m, k)
            if st is None:
                continue
            cx, cy, w, h, ang, flip, tex, lifted, u2, tex0 = st
            box = m["s"] if tex == 0 else m["d"]
            p = self.patch(self.logo if tex == 0 else self.ins, box)
            a_mul = 1.0
            if tex == 0 and m["fade_i"] and ((tex0 == 0 and u2 > 0.4) or (tex0 == 1 and u2 < 0.6)):
                a_mul = 0.0
            if tex == 1 and m["fade_t"] and ((tex0 == 1 and u2 > 0.4) or (tex0 == 0 and u2 < 0.6)):
                a_mul = 0.0
            if a_mul == 0.0:
                continue
            layers.append((lifted, cx, cy, w, h, ang, flip, p))
        layers.sort(key=lambda t: t[0])
        for lifted, cx, cy, w, h, ang, flip, p in layers:
            ph, pw = p.shape[:2]
            sx = max(abs(flip), 0.04) * (w / pw) * (1 + 0.06 * lifted); sy = (h / ph) * (1 + 0.06 * lifted)
            c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            M = np.array([[c * sx, -s * sy, 0], [s * sx, c * sy, 0]], np.float32)
            M[:, 2] = [cx, cy] - M[:, :2] @ np.array([pw / 2, ph / 2], np.float32)
            R = int(max(w, h) * 0.9 + 14)
            x0, y0 = int(max(cx - R, 0)), int(max(cy - R, 0)); x1, y1 = int(min(cx + R, W)), int(min(cy + R, H))
            if x1 <= x0 or y1 <= y0:
                continue
            Ml = M.copy(); Ml[:, 2] -= [x0, y0]
            q = cv2.warpAffine(p, Ml, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
            a = q[..., 3:4]
            # its shadow on what is below, further off when lifted
            off = 3 + 9 * lifted
            Ms = Ml.copy(); Ms[:, 2] += [off * 0.5, off]
            sa = blur(cv2.warpAffine(p[..., 3], Ms, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR), 2 + 4 * lifted)
            roi = img[y0:y1, x0:x1]
            roi *= (1 - (0.35 + 0.3 * lifted) * sa)[..., None]
            shade = 0.55 + 0.45 * abs(flip)                              # turned edge-on it goes dark
            edge = np.clip(cv2.Sobel(q[..., 3], cv2.CV_32F, 0, 1, ksize=3) * -0.6, 0, 0.4)[..., None]
            roi[:] = roi * (1 - a) + (q[..., :3] * shade + edge * 0.6) * a
        return self.finish(img, k, self.jolt(k))

    def jolt(self, k):
        dx = dy = 0.0
        for k0 in (self.arr1 - 4, self.arr2 - 4):
            t = k - k0
            if 0 <= t < 12:
                dy += 5.0 * math.exp(-t / 2.5) * math.cos(t * 2.0)
        return dx, dy


# --------------------------------------------------------------------------------------------------------- allspark
class AllSpark(Stage):
    def __init__(self, src):
        super().__init__(src)
        rng = np.random.default_rng(21)
        keep_out = cv2.dilate((self.logo[..., 3] > 0.3).astype(np.uint8), np.ones((40, 40), np.uint8))
        keep_out |= cv2.dilate((self.col > 0.2).astype(np.uint8), np.ones((30, 30), np.uint8))
        G = 16
        dist = np.full((H, W), np.inf, np.float32)
        chan = np.zeros((H, W), np.uint8)
        dirs = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
        tc = np.array([W / 2, 300.0])
        self.ends = []
        for n in range(64):
            side = rng.integers(4)
            if side == 0:
                p = np.array([rng.integers(1, W // G) * G, 0.0])
            elif side == 1:
                p = np.array([rng.integers(1, W // G) * G, (H // G) * G])
            elif side == 2:
                p = np.array([0.0, rng.integers(1, H // G) * G])
            else:
                p = np.array([(W // G) * G, rng.integers(1, H // G) * G])
            d0 = rng.uniform(0, 160)                                     # not all start together
            L = d0; pts = [p.copy()]
            for step in range(140):
                to = tc - p; ang = math.atan2(to[1], to[0])
                best = min(range(8), key=lambda i: abs((math.atan2(dirs[i][1], dirs[i][0]) - ang + math.pi) % (2 * math.pi) - math.pi)
                           + rng.uniform(0, 1.3))
                q = p + np.array(dirs[best]) * G
                if not (0 <= q[0] < W and 0 <= q[1] < H):
                    break
                if keep_out[int(q[1]), int(q[0])]:
                    self.ends.append((int(p[0]), int(p[1]), L)); break
                pts.append(q.copy()); p = q
            for a, b in zip(pts, pts[1:]):
                seg_len = float(np.hypot(*(b - a)))
                nn = int(seg_len)
                for j in range(nn + 1):
                    x = int(a[0] + (b[0] - a[0]) * j / max(nn, 1)); y = int(a[1] + (b[1] - a[1]) * j / max(nn, 1))
                    for oy in range(-2, 3):
                        for ox in range(-2, 3):
                            yy, xx = y + oy, x + ox
                            if 0 <= yy < H and 0 <= xx < W:
                                dist[yy, xx] = min(dist[yy, xx], L + j)
                L += seg_len
            m = np.zeros((H, W), np.uint8)
            cv2.polylines(m, [np.array(pts, np.int32)], False, 1, 4, cv2.LINE_AA)
            if len(pts) > 1:
                cv2.circle(m, (int(pts[-1][0]), int(pts[-1][1])), 6, 1, -1, cv2.LINE_AA)
            chan |= m
        self.chan = blur(chan.astype(np.float32), 0.7)
        self.dist = np.where(np.isfinite(dist), dist, 1e6).astype(np.float32)
        # the plate: dark brushed metal, the channels cut into it (lit from the top left)
        n1 = noise(H, W, 1.6, 4); brushed = blur(noise(H, W, 0.4, 5), 0.6)
        brushed = cv2.resize(cv2.resize(brushed, (W // 8, H)), (W, H))
        self.plate = (0.07 + 0.04 * n1 + 0.02 * brushed)[..., None] * np.array([0.85, 0.93, 1.05], np.float32)
        gy = cv2.Sobel(self.chan, cv2.CV_32F, 0, 1, ksize=3); gx = cv2.Sobel(self.chan, cv2.CV_32F, 1, 0, ksize=3)
        self.groove_hi = np.clip((gx + gy) * 0.4, 0, 1); self.groove_lo = np.clip(-(gx + gy) * 0.4, 0, 1)
        sol = (self.logo[..., 3] > 0.5).astype(np.uint8)
        outer = cv2.dilate(sol, np.ones((5, 5), np.uint8)) - sol
        inner = sol - cv2.erode(sol, np.ones((5, 5), np.uint8))
        self.rim = blur((outer | inner).astype(np.float32), 1.2)
        self.maxL = float(self.dist[self.dist < 1e5].max())

    def frame(self, k):
        k = k % N
        speed = 6.0
        front = (k - 6) * speed
        drain = seg(k, 150, 200)
        energy = np.zeros((H, W), np.float32)
        if front > 0:
            d = self.dist
            head = np.exp(-((d - front) / 26) ** 2)
            tail = np.where(d < front, np.exp(-np.clip(front - d, 0, 1e4) / 260), 0.0)
            energy = (head * 1.2 + tail * 0.45) * self.chan * (1 - drain)
        arrived = float(np.clip((front - min(e[2] for e in self.ends) - 40) / 260, 0, 1)) * (1 - drain)
        blue = np.array([0.35, 0.72, 1.0], np.float32)
        img = self.plate * (1 - 0.35 * self.chan[..., None]) + (self.groove_hi * 0.05)[..., None] - (self.groove_lo * 0.03)[..., None]
        img = img * (1 - np.clip(self.chan, 0, 1)[..., None] * 0.3)
        img += energy[..., None] * blue * 0.9
        img += bigblur(energy, 10)[..., None] * blue * 0.35            # the light spills a little onto the plate
        a = self.logo[..., 3:4]
        sh = blur(np.roll(np.roll(self.logo[..., 3], 9, 0), 5, 1), 7)
        img = img * (1 - 0.6 * sh)[..., None]
        face = self.logo[..., :3] * (1 + 0.25 * arrived * np.array([0.6, 0.9, 1.2], np.float32))
        img = img * (1 - a) + face * a
        pulse = 0.75 + 0.25 * math.sin(k * 0.5)
        img += (self.rim * arrived * pulse)[..., None] * blue * 0.9
        img += bigblur(self.rim * arrived, 14)[..., None] * blue * 0.25
        return self.finish(img, k)


def render(src, out, mode, only=None, mp4=None):
    s = Transform(src) if mode == "transform" else AllSpark(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "transform"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
