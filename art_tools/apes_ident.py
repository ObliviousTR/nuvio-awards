"""Planet of the Apes card. Two modes, both built from the franchise's own material, no stills behind or inside the title.

--mode titles  The franchise names itself: [RISE / DAWN / WAR / KINGDOM] OF THE PLANET OF THE APES. War for the Planet of
               the Apes opens on a text that picks RISE, DAWN and WAR out of its lines; here the stacked PLANET OF THE
               APES stays and the four words come up over it in turn, each in its own film's title lettering (TMDB
               logos), each with its film's colour in the light behind (its backdrop reduced to colour by a very wide
               blur), a light sweep across the letters as each word settles.
--mode window  Caesar's window. The round attic window of Rise (a circle crossed by four arcs) became the apes' sign. The
               stone PLANET OF THE APES hangs in front of a dark plaster wall in an attic; the only light is the sun
               through that window. Its patch, crossed by the shadows of the arcs, travels across the wall and the
               letters as the sun moves; the letters' relief and the plaster catch it; the title throws its shadow into
               the patch; midway the patch sits behind the title and the sign reads on the wall. A cloud takes the sun
               at the end and gives it back where it started.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/apes_ident.py SRC_DIR OUT_DIR [--mode titles|window] [--frames a,b] [--mp4 path]
  SRC_DIR: kingdom.png (TMDB logo gLi5qaqxZbVj2PXQYrah0AFgqkB, film 653346), rise.png (13KoNbLM9HvuE8Jt5a6Sp90QX7R, 61791),
           dawn.png (bLIyaaCoHkeiRrDs8nWz5ClMP5X, 119450), war.png (ieaqf457LniUZCIEmSsuBbiVTkX, 281338),
           stone.png (6MBp6uyDB8dVW2w70ETfIDVpiXA, film 869), field_{rise,dawn,war,kingdom}.jpg (one backdrop of each
           film, TMDB), Montserrat-VF.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / (b - a)))


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


def spaced(font, size, txt, track, var=None):
    f = ImageFont.truetype(font, size)
    if var:
        f.set_variation_by_axes(var)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 40, size * 2), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def alpha(path):
    return np.asarray(Image.open(path).convert("RGBA"), np.float32)[..., 3] / 255


def tight(a):
    ys, xs = np.nonzero(a > 0.05)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def paste(dst, a, x, y):
    """add mask a into dst at integer (x, y), clipped"""
    h, w = a.shape; x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 > x0 and y1 > y0:
        dst[y0:y1, x0:x1] = np.maximum(dst[y0:y1, x0:x1], a[y0 - y:y1 - y, x0 - x:x1 - x])


def shift(a, dx, dy):
    return cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR)


def collection(src, size=46, track=17):
    return spaced(os.path.join(src, "Montserrat-VF.ttf"), size, "THE COLLECTION", track, [600])


# --------------------------------------------------------------------------------------------------------- titles
# word timing: (name, rise start, sink start); rises take 16 frames, sinks 12
WORDS = [("rise", 8, 56), ("dawn", 70, 116), ("war", 130, 176), ("kingdom", 190, 226)]


class Titles:
    def __init__(self, src):
        kd = alpha(os.path.join(src, "kingdom.png"))                    # 3223 x 1688: KINGDOM OF THE / PLANET / OF THE APES
        LW = kd.shape[1]; LINE = 347; BASE0 = 400                        # word line rows 0..347, the stacked title from row 400
        self.s = s = 660 / LW
        base = kd[BASE0:]
        kword = tight(kd[:LINE + 2, :2515]); of_the = tight(kd[:LINE + 2, 2515:])
        wt = kword.shape[0]                                              # word height in logo units (KINGDOM's)
        war = alpha(os.path.join(src, "war.png"))
        words = {"kingdom": kword,
                 "rise": tight(alpha(os.path.join(src, "rise.png"))[:906]),
                 "dawn": tight(alpha(os.path.join(src, "dawn.png"))[:262]),
                 "war": tight(war[:218])}
        for_the = tight(war[224:320, :93])
        oh = of_the.shape[0]
        sc = lambda a, h: cv2.resize(a, (max(1, round(a.shape[1] * h / a.shape[0])), h), interpolation=cv2.INTER_AREA)
        res = lambda a: cv2.resize(a, (max(1, round(a.shape[1] * s)), max(1, round(a.shape[0] * s))), interpolation=cv2.INTER_AREA)
        self.lines = {}
        for k, wa in words.items():
            wa = sc(wa, wt)
            small = for_the if k == "war" else of_the
            small = sc(small, round(oh * 2.15) if k == "war" else oh)
            line = np.zeros((LINE + 2, LW), np.float32)
            paste(line, wa, 0, LINE + 1 - wt)
            paste(line, small, wa.shape[1] + 26, LINE + 1 - small.shape[0])
            # word and the small words separately, the small ones follow a little behind
            ln_w = np.zeros_like(line); paste(ln_w, wa, 0, LINE + 1 - wt)
            self.lines[k] = (res(ln_w), res(line - ln_w))
        self.base = res(base)
        self.X0 = (W - self.base.shape[1]) // 2
        self.base_dy = BASE0 * s                                         # word line top above the title's top
        self.col = collection(src)
        # light behind: each film's backdrop reduced to its colour
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - H * 0.44) / (H * 0.6)) ** 2)
        self.vig = np.clip(1 - 0.78 * r ** 1.5, 0.12, 1)[..., None]
        self.fields = {"none": np.dstack([np.full((H, W), v, np.float32) for v in (0.085, 0.09, 0.105)]) * self.vig}
        for k in words:
            im = np.asarray(Image.open(os.path.join(src, f"field_{k}.jpg")).convert("RGB"), np.float32) / 255
            fw, fh = int(W * 1.16), int(H * 1.16)
            sc2 = max(fw / im.shape[1], fh / im.shape[0])
            im = cv2.resize(im, (round(im.shape[1] * sc2), round(im.shape[0] * sc2)), interpolation=cv2.INTER_AREA)
            y0 = (im.shape[0] - fh) // 2; x0 = (im.shape[1] - fw) // 2
            im = bigblur(bigblur(im[y0:y0 + fh, x0:x0 + fw], 70), 50)
            lum = im.mean(2, keepdims=True)
            im = np.clip(lum + (im - lum) * 1.9, 0, None)                 # keep its colour, not its detail
            im = im * (0.23 / max(float(im.mean()), 1e-3))
            mx = im.max(2, keepdims=True); im = np.where(mx > 0.42, im * 0.42 / mx, im)   # no hot spots behind white letters
            self.fields[k] = im
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def field(self, k):
        ph = 2 * math.pi * k / N
        ws = {"none": 1 - seg(k, 4, 24) + seg(k, 226, 249)}
        edges = [(4, 24), (60, 80), (120, 140), (180, 200), (226, 249)]
        for i, (name, _, _) in enumerate(WORDS):
            ws[name] = seg(k, *edges[i]) - seg(k, *edges[i + 1])
        out = np.zeros((H, W, 3), np.float32)
        z = 1.0 + 0.035 * (1 - math.cos(ph)) / 2
        for name, w in ws.items():
            if w <= 0.001:
                continue
            f = self.fields[name]
            if name != "none":
                fh, fw = f.shape[:2]
                dx = 18 * math.sin(ph + len(name)); dy = 8 * math.cos(ph * 2 + len(name))
                M = np.float32([[z, 0, W / 2 - fw / 2 * z + dx], [0, z, H / 2 - fh / 2 * z + dy]])
                f = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) * self.vig
            out += f * w
        return out

    def frame(self, k):
        k = k % N
        d = seg(k, 0, 16) * (1 - seg(k, 230, 249))                       # the title moves down to make room for the word
        yb = 201 + 41 * d
        base = np.zeros((H, W), np.float32); paste(base, self.base, self.X0, yb)
        word = np.zeros((H, W), np.float32)
        clip_y = int(round(yb - 3))
        settle = []
        for name, r0, s0 in WORDS:
            for part, delay in ((0, 0), (1, 3)):
                rise = 1 - (1 - np.clip((k - r0 - delay) / 16, 0, 1)) ** 3
                sink = np.clip((k - s0 - delay) / 12, 0, 1) ** 3
                o = rise - sink
                if o <= 0:
                    continue
                m = self.lines[name][part]
                # a short motion blur while it moves
                vel = abs(rise - (1 - (1 - np.clip((k - 1 - r0 - delay) / 16, 0, 1)) ** 3)) + abs(sink - np.clip((k - 1 - s0 - delay) / 12, 0, 1) ** 3)
                acc = np.zeros((H, W), np.float32); n = 4 if vel > 0.02 else 1
                for j in range(n):
                    oj = o + (vel * (j / max(n - 1, 1) - 0.5) if n > 1 else 0)
                    t = np.zeros((H, W), np.float32)
                    paste(t, m, self.X0, yb - self.base_dy + 84 * (1 - oj))
                    acc += t / n
                word = np.maximum(word, acc)
            settle.append(r0 + 14)
        word[clip_y:] = 0
        letters = np.maximum(base, word)
        col = np.zeros((H, W), np.float32)
        paste(col, self.col, (W - self.col.shape[1]) / 2, yb + self.base.shape[0] + 36)
        img = self.field(k)
        # the letters stand off the light behind: soft shadow
        sh = bigblur(shift(letters, 0, 9), 16)
        img *= (1 - 0.55 * sh)[..., None]
        img *= (1 - 0.35 * bigblur(col, 10))[..., None]
        # letters: white, a little shade toward the bottom, tinted by the light around them
        yy = np.arange(H, dtype=np.float32)[:, None]
        g = np.clip(1.0 - 0.1 * (yy - (yb - 90)) / 420, 0.86, 1.0)
        env = bigblur(img, 40) / (bigblur(img, 40).mean() + 1e-3)
        face = (0.9 * g)[..., None] * (0.93 + 0.07 * np.clip(env, 0, 2))
        # the sweep: one band of light across the letters as each word settles
        xx = np.arange(W, dtype=np.float32)[None, :] + 0.45 * yy
        sweep = np.zeros((H, W), np.float32)
        for st in settle:
            u = (k - st) / 24.0
            if 0 <= u <= 1:
                xs = self.X0 - 260 + u * (self.base.shape[1] + 700)
                sweep = np.maximum(sweep, np.exp(-((xx - xs) / 70) ** 2) * math.sin(math.pi * u))
        face = face + sweep[..., None] * 0.35
        img = img * (1 - letters[..., None]) + np.clip(face, 0, 1.05) * letters[..., None]
        img = img * (1 - col[..., None]) + np.array([0.86, 0.86, 0.88], np.float32) * col[..., None]
        gx = (k * 37) % W; gy = (k * 53) % H
        img += (self.grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * 0.035
        return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


# --------------------------------------------------------------------------------------------------------- window
T = 1000                                                                 # window light texture, radius 1 = T/2/1.1
SUN = np.array([1.0, 0.80, 0.57], np.float32)
A_SRC = np.array([640.0, -1100.0]); A_Z = 1600.0; DEPTH = 80.0           # where the light comes from; title's distance off the wall


def window_light():
    """the light that passes the window: a disc crossed by four arcs (centres on the diagonals, radius 1)"""
    k = T / 2 / 1.1
    yy, xx = (np.mgrid[0:T, 0:T].astype(np.float32) - T / 2) / k
    r = np.sqrt(xx ** 2 + yy ** 2)
    m = (r < 0.965).astype(np.float32)
    wid = 0.068
    for sx in (-1, 1):
        for sy in (-1, 1):
            dd = np.abs(np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2) - 1.0)
            m *= (dd > wid / 2)
    # old glass: the panes pass a little more or less, and the glass itself is uneven
    lab = np.zeros((T, T), np.int32)
    lab[(np.sqrt((xx - 1) ** 2 + (yy - 1) ** 2) < 1)] = 1; lab[(np.sqrt((xx + 1) ** 2 + (yy - 1) ** 2) < 1)] = 2
    lab[(np.sqrt((xx - 1) ** 2 + (yy + 1) ** 2) < 1)] = 3; lab[(np.sqrt((xx + 1) ** 2 + (yy + 1) ** 2) < 1)] = 4
    pane = np.array([1.0, 0.93, 0.97, 0.9, 0.95], np.float32)[lab]
    glass = 0.9 + 0.2 * noise(T, T, 1.6, 41)
    return blur(m * pane * glass, 8.0)


class Window:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        self.tex = window_light()
        # the wall: old plaster, its relief only shows where the light rakes it
        n1 = cv2.resize(noise(H // 2, W // 2, 1.5, 11), (W, H)); n2 = noise(H, W, 1.7, 12); n3 = noise(H, W, 1.25, 13)
        self.walb = np.dstack([0.42 * (0.8 + 0.35 * n1) * (0.96 + 0.06 * n3)] * 3) * np.array([1.0, 0.97, 0.92], np.float32)
        hw = n2 * 9.0 + blur(n3, 1.2) * 1.4
        self.wnx = cv2.Sobel(hw, cv2.CV_32F, 1, 0, ksize=3); self.wny = cv2.Sobel(hw, cv2.CV_32F, 0, 1, ksize=3)
        # the title: stone
        lg = Image.open(os.path.join(src, "stone.png")).convert("RGBA")
        lw = 650; lh = round(lg.height * lw / lg.width)
        lg = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.top = 132
        x0 = (W - lw) // 2
        self.la = np.zeros((H, W), np.float32); self.la[self.top:self.top + lh, x0:x0 + lw] = lg[..., 3]
        self.alb = np.zeros((H, W, 3), np.float32); self.alb[self.top:self.top + lh, x0:x0 + lw] = lg[..., :3]
        lum = self.alb.mean(2)
        dist = cv2.distanceTransform((self.la > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        hl = np.clip(dist / 7, 0, 1) * 5 + (blur(lum, 1.0) - blur(lum, 5)) * 9
        self.lnx = cv2.Sobel(hl, cv2.CV_32F, 1, 0, ksize=3) * 0.5; self.lny = cv2.Sobel(hl, cv2.CV_32F, 0, 1, ksize=3) * 0.5
        self.alb = self.alb / max(float(lum[self.la > 0.5].mean()), 1e-3) * 0.55
        self.col = np.zeros((H, W), np.float32)
        c = collection(src); paste(self.col, c, (W - c.shape[1]) / 2, self.top + lh + 52)
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def sun(self, k):
        """patch centre on the wall and the sun's strength (a cloud at the end)"""
        u = k / 196.0
        p = u + 0.35 / (2 * math.pi) * math.sin(2 * math.pi * u)
        x = 300 + (1000 - 300) * p
        inten = (1 - seg(k, 192, 212)) + seg(k, 226, 249)
        if k > 214:
            x = 300.0
        y = 318 + 34 * ((x - 640) / 360) ** 2
        return np.array([x, y]), float(np.clip(inten, 0, 1))

    def patch(self, c, v):
        k = T / 2 / 1.1; R = 268
        M = np.array([[R, R * v[0] / v[1] * 0.55], [0, R * 1.1]]) / k
        b = c - M @ np.array([T / 2, T / 2])
        return cv2.warpAffine(self.tex, np.float32(np.hstack([M, b[:, None]])), (W, H), flags=cv2.INTER_LINEAR)

    def frame(self, k):
        k = k % N
        ph = 2 * math.pi * k / N
        c, inten = self.sun(k)
        v = (c - A_SRC) / A_Z                                            # the light's travel per unit of depth
        L = np.array([-v[0], -v[1], 0.75]); L /= np.linalg.norm(L)
        # camera drifts a little: the title moves against the wall
        dl = 5 * math.sin(ph); dlx, dly = dl, 1.5 * math.sin(2 * ph)
        la = shift(self.la, dlx, dly); alb = cv2.warpAffine(self.alb, np.float32([[1, 0, dlx], [0, 1, dly]]), (W, H))
        lnx, lny = shift(self.lnx, dlx, dly), shift(self.lny, dlx, dly)
        pw = self.patch(c, v) * inten                                    # on the wall
        pl = self.patch(c - v * DEPTH + np.array([dlx, dly]), v) * inten  # on the title, a plane in front
        shadow = bigblur(shift(la, v[0] * DEPTH, v[1] * DEPTH), 5)
        shadow = blur(np.clip(shadow, 0, 1), 3)
        pw_s = pw * (1 - shadow)
        # wall shading
        nz = 1.0
        ndl_w = np.clip((-self.wnx * L[0] - self.wny * L[1] + nz * L[2]) / np.sqrt(self.wnx ** 2 + self.wny ** 2 + 1), 0, 1.4)
        bounce = bigblur(pw_s, 110) * 0.55
        amb_w = np.array([0.15, 0.17, 0.21], np.float32)
        wall = self.walb * (amb_w + (pw_s * ndl_w * 1.35)[..., None] * SUN + bounce[..., None] * SUN * 0.8)
        # title shading
        ndl_l = np.clip((-lnx * L[0] - lny * L[1] + L[2]) / np.sqrt(lnx ** 2 + lny ** 2 + 1), 0, 1.4)
        amb_l = np.array([0.33, 0.35, 0.40], np.float32)
        face = alb * (amb_l + (pl * ndl_l * 1.3)[..., None] * SUN + bounce[..., None] * SUN * 0.9)
        img = wall * (1 - la[..., None]) + face * la[..., None]
        img = img * (1 - 0.68 * np.clip(bigblur(self.col, 14) * 1.6, 0, 1))[..., None]
        img = img * (1 - self.col[..., None]) + np.array([0.80, 0.77, 0.72], np.float32) * self.col[..., None]
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img *= (1 - 0.4 * np.clip(rr - 0.45, 0, 1))[..., None]
        img = img / (1 + 0.3 * img) * 1.3
        gx = (k * 37) % W; gy = (k * 53) % H
        img += (self.grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * 0.03
        return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


def render(src, out, mode, only=None, mp4=None):
    s = Titles(src) if mode == "titles" else Window(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "titles"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
