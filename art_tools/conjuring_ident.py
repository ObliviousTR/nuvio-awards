"""The Conjuring Universe card. Two modes, both from the films' own language.

--mode lecture  The Conjuring (2013) closes on a title sequence by Becker Design: a 1970s parapsychology lecture, the
                Warrens' case material laid on a still projector as printed acetate sheets, the main title in a 1970s
                mustard yellow with an extended J that seems endless as the card scrolls. Here: the mustard title card;
                a projector lamp strikes and the title becomes the shadow of its ink on an acetate, projected with the
                lamp's hot spot and fall-off, dust on the glass, scratches on the sheet; the sheet is pushed slowly up
                and the J runs on; a second sheet, the Perron house (TMDB still, black and white), is laid under it
                and lifted off again; the lamp goes out and the mustard card is back.
--mode crosses  The Conjuring 2: Valak turns the crosses on Lorraine's wall upside down. The white title stands off an
                old damask wall (the wallpaper of the film's Enfield house, from a TMDB still) among wooden crosses; one
                table lamp low on the left lights it all, its shade drawing the light's edge on the wall; each time the
                lamp falters a cross turns upside down, its shadow turning with it; when all are turned the lamp goes
                out and comes back on the cover.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/conjuring_ident.py SRC_DIR OUT_DIR [--mode lecture|crosses] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (TMDB logo 5qjvxFhRZtvm4mcV90X9QNYLZVj, film 138843), house.jpg (TMDB backdrop
           fyt21GtKZ7KZCVyuOK9UtYwS07r, film 138843), wallpaper_still.jpg (TMDB backdrop tctYYcVI3xd0I3tzvxyVERlczME,
           film 259693: its left edge is the wallpaper), Cinzel.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
MUSTARD = np.array([0.87, 0.66, 0.15], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / (b - a)))


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


def spaced(font, size, txt, track, stroke=0):
    f = ImageFont.truetype(font, size)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 40, size * 2), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls", stroke_width=stroke, stroke_fill=255); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def paste(dst, a, x, y):
    h, w = a.shape; x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 > x0 and y1 > y0:
        dst[y0:y1, x0:x1] = np.maximum(dst[y0:y1, x0:x1], a[y0 - y:y1 - y, x0 - x:x1 - x])


def warp(a, M, border=0):
    return cv2.warpAffine(a, np.float32(M), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def logo_mask(src, ext=0):
    """the title's alpha; ext rows added to the J's stem below the baseline"""
    a = np.asarray(Image.open(os.path.join(src, "logo.png")).convert("LA"), np.float32)[..., 1] / 255
    if ext > 0:
        a = np.vstack([a[:366], np.repeat(a[366:367], ext, axis=0), a[366:]])
    return a


def collection(src, size=46, track=17):
    return spaced(os.path.join(src, "Cinzel.ttf"), size, "THE COLLECTION", track, stroke=1)


def to_image(img, k, grain, amt):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


# --------------------------------------------------------------------------------------------------------- lecture
LW = 780                                                                 # title width on screen
LAMP_ON = [(3, 0.0), (4, 0.35), (5, 0.12), (6, 0.7), (7, 0.55), (8, 0.92), (10, 1.0)]
LAMP_OFF = [(204, 1.0), (206, 0.6), (207, 0.9), (209, 0.3), (210, 0.45), (213, 0.0)]


def lamp_level(k):
    if k < 3 or k >= 213:
        return 0.0
    if k >= 204:
        pts = LAMP_OFF
    elif k <= 10:
        pts = LAMP_ON
    else:
        return 1.0 + 0.012 * math.sin(k * 2.7) + 0.008 * math.sin(k * 5.3)  # the lamp breathes a little
    for (k0, v0), (k1, v1) in zip(pts, pts[1:]):
        if k0 <= k <= k1:
            return v0 + (v1 - v0) * (k - k0) / (k1 - k0)
    return pts[-1][1]


class Lecture:
    def __init__(self, src):
        self.src = src
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        s = LW / 1600.0; self.s = s
        self.base_mask = logo_mask(src)
        self.lh = round(self.base_mask.shape[0] * s)
        self.ty = 215                                                    # title top on the cover
        col = collection(src)
        self.col = np.zeros((H, W), np.float32); paste(self.col, col, (W - col.shape[1]) / 2, self.ty + self.lh + 46)
        cov = np.zeros((H, W), np.float32)
        paste(cov, cv2.resize(self.base_mask, (LW, self.lh), interpolation=cv2.INTER_AREA), (W - LW) / 2, self.ty)
        self.cover_mask = cov
        # the projected frame: hot spot, fall-off, soft edges of the gate, slightly keystoned
        r2 = ((xx - W * 0.5) / (W * 0.62)) ** 2 + ((yy - H * 0.47) / (H * 0.75)) ** 2
        field = 0.58 + 0.42 * np.exp(-r2 * 1.6)
        top_w = 1.0 + 0.03 * (1 - yy / H)                                # keystone: wider at the top
        u = (xx - W / 2) / (W / 2 - 34) / top_w; v = (yy - H / 2) / (H / 2 - 26)
        gate = smooth((1 - np.abs(u)) * 14) * smooth((1 - np.abs(v)) * 12)
        self.field = (field * blur(gate.astype(np.float32), 3))[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
        # dust on the projector glass (fixed) and on the acetate (moves with the sheet)
        rng = np.random.default_rng(5)
        glass = np.ones((H, W), np.float32)
        for _ in range(26):
            x, y = rng.uniform(60, W - 60), rng.uniform(50, H - 50); r = rng.uniform(1.2, 3.8)
            cv2.circle(glass, (int(x), int(y)), int(r), 0.0, -1, cv2.LINE_AA)
        for _ in range(1):                                               # a hair
            x, y = rng.uniform(80, W - 80), rng.uniform(60, H - 60)
            d0 = rng.uniform(-3, 3, size=2)
            pts = np.cumsum(np.array([d0 + [0.25 * math.sin(i / 4.0), 0.25 * math.cos(i / 5.0)] for i in range(14)]), 0) + [x, y]
            cv2.polylines(glass, [pts.astype(np.int32)], False, 0.0, 1, cv2.LINE_AA)
        self.glass = 1 - (1 - blur(glass, 1.4)) * 0.75
        sheet = np.ones((H + 200, W), np.float32)
        for _ in range(6):                                               # fine scratches on the acetate
            x0, y0 = rng.uniform(0, W), rng.uniform(0, H + 200); ang = rng.uniform(-0.5, 0.5) + math.pi / 2 * rng.integers(0, 2)
            L = rng.uniform(40, 220)
            cv2.line(sheet, (int(x0), int(y0)), (int(x0 + L * math.cos(ang)), int(y0 + L * math.sin(ang))), 0.0, 1, cv2.LINE_AA)
        self.sheet_tex = 1 - (1 - blur(sheet, 0.7)) * 0.2
        self.sheet_tex *= (0.96 + 0.06 * noise(H + 200, W, 1.4, 9))
        # the second sheet: the Perron house, printed on acetate (black and white, washed as projected photos are)
        h = np.asarray(Image.open(os.path.join(src, "house.jpg")).convert("L"), np.float32) / 255
        h = cv2.resize(h, (W, round(h.shape[0] * W / h.shape[1])), interpolation=cv2.INTER_AREA)
        h = np.clip((h - 0.06) / 0.9, 0, 1) ** 1.1
        self.house = 0.3 + 0.7 * h
        # printed lighter under the title, as a projected photo with type on it would be
        hh = self.house.shape[0]
        yy2, xx2 = np.mgrid[0:hh, 0:W].astype(np.float32)
        dodge = np.exp(-(((xx2 - W / 2) / 430) ** 2 + ((yy2 - 330) / 170) ** 2) * 1.5)
        self.house = 1 - (1 - self.house) * (1 - 0.5 * dodge)
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def title(self, k):
        """the title's ink on its sheet at frame k: pushed up slowly, the J running on"""
        p = seg(k, 12, 200)
        up = 64 * p
        ext = int(round(150 * p / self.s))
        m = cv2.resize(logo_mask(self.src, ext), (LW, round((self.base_mask.shape[0] + ext) * self.s)), interpolation=cv2.INTER_AREA)
        out = np.zeros((H, W), np.float32)
        # a hand on the sheet: a small nudge when the second sheet is laid on and lifted off
        nud = seg(k, 84, 96) - seg(k, 160, 176)
        dx = 3 * nud; rot = 0.5 * nud
        paste(out, m, (W - LW) / 2, self.ty - up)
        out = np.maximum(out, np.roll(self.col, -int(round(up)), axis=0))
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, 1.0); M[0, 2] += dx
        return warp(out, M), up

    def frame(self, k):
        k = k % N
        lam = lamp_level(k)
        ink, up = self.title(k)
        # second sheet: laid on from below (out of focus while it falls), lifted off from its lower edge
        lay = seg(k, 70, 94); lift = seg(k, 158, 182)
        trans = np.ones((H, W), np.float32); house_blur = 0.0
        if lay > 0 and lift < 1:
            y0 = (1 - lay) * (H + 40) + 6 * seg(k, 94, 158)
            hs = self.house[:H] if self.house.shape[0] >= H else np.pad(self.house, ((0, H - self.house.shape[0]), (0, 0)), constant_values=1)
            hs = warp(hs, [[1, 0, 0], [0, 1, y0]], border=1.0)
            house_blur = 9 * (1 - seg(k, 84, 96))
            hs = blur(hs, house_blur)
            if lift > 0:
                yl = H * (1 - lift) - 60                                 # the lifted part rises off the glass from below
                m = smooth((self.yy - yl) / 140)
                hl = bigblur(hs, 40) * 0.6 + 0.4
                hs = hs * (1 - m) + hl * m
                hs = 1 - (1 - hs) * (1 - smooth((lift - 0.55) / 0.45))
            trans = hs
        # title sheet: ink, scratches; a little soft (the lens), sharper when the hand settles it
        tex = self.sheet_tex[int(200 - round(up)): int(200 - round(up)) + H]
        t_ink = 1 - blur(ink, 0.9) * 0.93
        proj = self.field * (t_ink * tex * trans * self.glass)[..., None]
        proj = proj * lam
        # spill of the projector light into the dark room around the frame
        spill = bigblur(proj, 60) * 0.12
        img = proj + spill
        # the mustard title card (cover) before the lamp and after it
        card = 1 - seg(k, 4, 12) + seg(k, 210, 232)
        if card > 0:
            cm = np.maximum(self.cover_mask, self.col)
            img = img * (1 - card * 0.85) + (cm[..., None] * MUSTARD) * card
        img = np.clip(img, 0, 1.2)
        img = img / (1 + 0.15 * img) * 1.15
        return to_image(img, k, self.grain, 0.03 + 0.03 * min(lam, 1))


# --------------------------------------------------------------------------------------------------------- crosses
LAMP = np.array([360.0, 1000.0]); LZ = 600.0                            # lamp on screen (low left, off frame), distance off the wall
DEPTH = 18.0                                                             # the title's distance off the wall
# crosses: (x, y, height)
CROSSES = [(118, 118, 104), (262, 600, 86), (1162, 136, 96), (1036, 610, 108), (404, 82, 70), (868, 74, 78),
           (148, 470, 74), (1196, 438, 82), (640, 640, 72)]
FLIPS = [18, 40, 62, 84, 106, 128, 150, 172, 194]                       # frame of each flicker; one cross turns each time
ORDER = [2, 6, 4, 1, 8, 0, 5, 3, 7]
FLICK = [1.0, 0.45, 0.85, 0.18, 0.7, 0.35, 0.95, 1.0]


def cross_shape(h):
    """latin cross polygon around its crossing point (the nail), at 4x"""
    t = 0.13 * h; w = 0.56 * h; top = 0.3 * h
    # crossing point is at (0, 0); the long arm below
    return np.array([[-t / 2, -top], [t / 2, -top], [t / 2, -t / 2], [w / 2, -t / 2], [w / 2, t / 2], [t / 2, t / 2],
                     [t / 2, h - top], [-t / 2, h - top], [-t / 2, t / 2], [-w / 2, t / 2], [-w / 2, -t / 2], [-t / 2, -t / 2]])


class Crosses:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        # the wall: the damask of the Enfield house, its lighting taken out, mirror-tiled
        st = np.asarray(Image.open(os.path.join(src, "wallpaper_still.jpg")).convert("RGB"), np.float32)[:520, 6:250] / 255
        st = st / (bigblur(st, 60) + 1e-3) * 0.62
        st = cv2.resize(st, (round(st.shape[1] * 1.1), round(st.shape[0] * 1.1)), interpolation=cv2.INTER_CUBIC)
        row = np.hstack([st, st[:, ::-1]]); tile = np.vstack([row, row[::-1]])
        reps = (H // tile.shape[0] + 2, W // tile.shape[1] + 2)
        wall = np.tile(tile, (reps[0], reps[1], 1))[:H + 40, :W + 40]
        lum = wall.mean(2, keepdims=True)
        wall = lum + (wall - lum) * 0.55                                 # muted
        wall = wall.mean() + (wall - wall.mean()) * 0.6                # and quieter, it is only the wall
        self.wall = wall * np.array([0.92, 1.0, 0.93], np.float32) * (0.9 + 0.2 * noise(H + 40, W + 40, 1.8, 3))[..., None]
        # the title
        s = 800 / 1600.0
        m = logo_mask(src); m = cv2.resize(m, (800, round(m.shape[0] * s)), interpolation=cv2.INTER_AREA)
        self.la = np.zeros((H, W), np.float32); self.ty = 214; paste(self.la, m, (W - 800) / 2, self.ty)
        col = collection(src)
        self.col = np.zeros((H, W), np.float32); paste(self.col, col, (W - col.shape[1]) / 2, self.ty + m.shape[0] + 44)
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def irradiance(self, depth, k, lam):
        """light from the lamp onto a plane `depth` in front of the wall; the shade cuts it to an upward cone"""
        lz = LZ - depth
        dx = self.xx - LAMP[0]; up = LAMP[1] - self.yy
        d2 = dx * dx + up * up + lz * lz
        e = lz / d2 ** 1.5 * 1.0e6
        cos_up = up / np.sqrt(d2)
        cone = smooth((cos_up - 0.40) / 0.12)                            # the shade's edge on the wall
        return e * (0.06 + 0.94 * cone) * lam

    def shadow_of(self, mask, depth, soft):
        s = LZ / (LZ - depth)                                            # point light: the shadow is the shape scaled from the lamp
        M = [[s, 0, LAMP[0] * (1 - s)], [0, s, LAMP[1] * (1 - s)]]
        return blur(warp(mask, M), soft)

    def angle(self, i, k):
        """rotation of cross i at frame k (degrees): it turns over during its flicker, with a little wobble"""
        n = ORDER.index(i); k0 = FLIPS[n] + 2
        if k >= 212:
            return 0.0
        t = (k - k0) / 9.0
        if t <= 0:
            return 0.0
        a = 180 * smooth(min(t, 1.0))
        if t > 1:
            a += 6 * math.exp(-(t - 1) * 2.2) * math.sin((t - 1) * 9)
        return a

    def lamp(self, k):
        lam = 1.0 + 0.01 * math.sin(k * 1.9)
        for f0 in FLIPS:
            j = k - f0
            if 0 <= j < len(FLICK):
                lam = FLICK[j]
        # the end: the lamp goes out, comes back on the cover
        if 206 <= k < 232:
            seq = {206: 0.6, 207: 0.2, 208: 0.5, 209: 0.05}
            lam = seq.get(k, 0.0)
        if 232 <= k < 240:
            lam = [0.3, 0.0, 0.6, 0.15, 0.85, 0.7, 1.0, 1.0][k - 232]
        return lam

    def frame(self, k):
        k = k % N
        ph = 2 * math.pi * k / N
        lam = self.lamp(k)
        # the camera drifts a little: the title moves against the wall
        cx = 4 * math.sin(ph); cy = 2 * math.sin(2 * ph)
        wall = self.wall[20 + int(round(cy * 0.5)):20 + int(round(cy * 0.5)) + H, 20 + int(round(cx * 0.5)):20 + int(round(cx * 0.5)) + W]
        la = warp(self.la, [[1, 0, cx], [0, 1, cy]])
        # crosses
        cm = np.zeros((H, W), np.float32); ce = np.zeros((H, W), np.float32)
        for i, (x, y, h) in enumerate(CROSSES):
            a = math.radians(self.angle(i, k))
            P = cross_shape(h)
            R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            P = (P @ R.T + [x + cx * 0.5, y + cy * 0.5]) * 4
            big = np.zeros((H * 4 // 4, W), np.float32)
            x0, y0 = int(max(0, x - h * 1.1)), int(max(0, y - h * 1.1)); x1, y1 = int(min(W, x + h * 1.1)), int(min(H, y + h * 1.1))
            patch = np.zeros(((y1 - y0) * 4, (x1 - x0) * 4), np.uint8)
            cv2.fillPoly(patch, [(P - [x0 * 4, y0 * 4]).astype(np.int32)], 255, cv2.LINE_AA)
            small = cv2.resize(patch, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
            cm[y0:y1, x0:x1] = np.maximum(cm[y0:y1, x0:x1], small)
        # lighting
        e_wall = self.irradiance(0, k, lam)
        e_title = self.irradiance(DEPTH, k, lam)
        sh_t = self.shadow_of(la, DEPTH, 7.0)
        sh_c = self.shadow_of(cm, 14, 2.0)
        amb = np.array([0.035, 0.04, 0.05], np.float32)
        warm = np.array([1.0, 0.76, 0.48], np.float32)
        lit_wall = (e_wall * (1 - 0.75 * sh_t) * (1 - 0.85 * sh_c))[..., None] * warm
        img = wall * (amb + lit_wall)
        # crosses: dark wood, the edges toward the lamp catch it
        gx = cv2.Sobel(cm, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(cm, cv2.CV_32F, 0, 1, ksize=3)
        Ld = np.array([0.6, -0.8])
        edge = np.clip((-gx * Ld[0] - gy * Ld[1]) * 0.8, 0, 1) * cm
        wood = np.array([0.20, 0.13, 0.08], np.float32)
        cross_rgb = wood * (amb * 3 + (e_wall * 0.9)[..., None] * warm) + (edge * e_wall * 0.35)[..., None] * warm
        img = img * (1 - cm[..., None]) + cross_rgb * cm[..., None]
        # the title: white, lit by the lamp, standing off the wall
        face = 0.86 * (amb * 2.5 + e_title[..., None] * warm * 1.05)
        img = img * (1 - la[..., None]) + face * la[..., None]
        # THE COLLECTION: shade behind it, warm light grey
        img = img * (1 - 0.6 * np.clip(bigblur(self.col, 12) * 1.6, 0, 1))[..., None]
        colc = np.array([0.80, 0.74, 0.64], np.float32) * (0.35 + 0.65 * min(lam, 1.0))
        img = img * (1 - self.col[..., None]) + colc * self.col[..., None]
        img = img / (1 + 0.35 * img) * 1.35
        return to_image(img, k, self.grain, 0.035)


def render(src, out, mode, only=None, mp4=None):
    s = Lecture(src) if mode == "lecture" else Crosses(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "lecture"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
