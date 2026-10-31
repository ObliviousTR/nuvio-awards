"""Wizarding World card, rebuilt on the franchise's own mark: Pentagram's Wizarding World logo, a book whose fanned
pages are nine wands (Voldemort, Ron, Hermione, Harry, Dumbledore's Elder Wand in the centre, Newt, Tina, Queenie,
Grindelwald), gold, over the Harry Beast lettering. The art is the official gold logo itself, cut from its black.

--mode book  The cover is WIZARDING WORLD and THE COLLECTION alone, centred. On hover the lettering moves down, the
             book's line draws out from the spine and the book opens as in the franchise's logo animation: its wands
             turn over one by one like pages and stand in their fan, each settling with a small swing and catching the
             light; Dumbledore's wand in the middle brings the light up. Then the book closes (the wands fall back
             flat), the line draws back in and the lettering rises to the cover.
--mode map   The Marauder's Map: the mark is inked on blank parchment; the wand's touch wakes the map and its ink runs
             out from the mark through the castle plan; a pair of footprints walks round the mark and away; the ink
             withdraws ("mischief managed") and the parchment is blank again.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/wizarding_ident.py SRC_DIR OUT_DIR [--mode book|map] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.jpg (the official gold Wizarding World logo on black), mark_flat.png (the same mark, flat, one colour),
           map.jpg (the Marauder's Map prop art),
           footprints.png (shoe prints), Cinzel.ttf
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
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls", stroke_width=1, stroke_fill=255); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def to_image(img, k, grain, amt=0.025):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


class Mark:
    """the logo on screen: its gold, its alpha, the nine wands apart from the rest"""

    def __init__(self, src, lh=500, top=46):
        im = np.asarray(Image.open(os.path.join(src, "logo.jpg")).convert("RGB"), np.float32) / 255
        lum = im.max(2)
        a = np.clip((lum - 0.035) / 0.16, 0, 1)
        ys, xs = np.nonzero(a > 0.3)
        y0, y1, x0, x1 = ys.min() - 8, ys.max() + 8, xs.min() - 8, xs.max() + 8
        im, a = im[y0:y1, x0:x1], a[y0:y1, x0:x1]
        rgb = im / np.maximum(a[..., None], 1e-3)
        s = lh / a.shape[0]
        lw = round(a.shape[1] * s)
        a = cv2.resize(a, (lw, lh), interpolation=cv2.INTER_AREA); rgb = cv2.resize(np.clip(rgb, 0, 1), (lw, lh), interpolation=cv2.INTER_AREA)
        self.x0 = (W - lw) // 2; self.y0 = top
        self.a = np.zeros((H, W), np.float32); self.rgb = np.zeros((H, W, 3), np.float32)
        self.a[top:top + lh, self.x0:self.x0 + lw] = a; self.rgb[top:top + lh, self.x0:self.x0 + lw] = rgb
        # the wands: the pieces above the book's line
        solid = (self.a > 0.45).astype(np.uint8)
        rows = solid.sum(1)
        book_y = top + int(np.argmax(rows[top:top + lh // 2 + 60]))       # the long page line
        self.book_y = book_y
        top_part = solid.copy(); top_part[book_y - 6:] = 0
        n, lab, st, cc = cv2.connectedComponentsWithStats(top_part)
        wands = [i for i in range(1, n) if st[i, 4] > 900 and st[i, 3] > 60]
        cxm = float(np.mean([cc[i][0] for i in wands]))
        self.pivot = np.array([cxm, book_y - 4.0])
        self.wand_a, self.wand_ang = [], []
        taken = np.zeros((H, W), np.float32)
        for i in sorted(wands, key=lambda i: math.atan2(-(cc[i][1] - self.pivot[1]), cc[i][0] - self.pivot[0]), reverse=True):
            m = cv2.dilate((lab == i).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
            m[book_y - 6:] = 0
            wa = self.a * m
            self.wand_a.append(wa); taken = np.maximum(taken, wa)
            self.wand_ang.append(math.degrees(math.atan2(-(cc[i][1] - self.pivot[1]), cc[i][0] - self.pivot[0])))
        self.rest_a = np.clip(self.a - taken, 0, 1)
        # left to right: wand 0 is Voldemort's (largest angle)
        col = spaced(os.path.join(src, "Cinzel.ttf"), 40, "COLLECTION", 16)
        self.col = np.zeros((H, W), np.float32)
        cy = top + lh + 22; cx = (W - col.shape[1]) // 2
        self.col[cy:cy + col.shape[0], cx:cx + col.shape[1]] = col


# --------------------------------------------------------------------------------------------------------- book
FLAT = 176.0                                                             # a wand lying on the left page
DOWN = (4, 30); UP = (212, 240)                                          # the lettering moves down to make room / back
BOOK_IN = (16, 40); BOOK_OUT = (196, 216)                                # the book's line draws out / back in
TURN0, TURN_GAP, TURN_LEN = 38, 11, 22                                   # pages (wands) turn one by one
CLOSE = (178, 196)                                                       # the book closes: the wands fall back flat


class Book:
    """the cover is the lettering alone, centred; the hover brings the book of wands up over it and closes it again"""

    def __init__(self, src):
        self.m = m = Mark(src)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.42) / (H * 0.7)) ** 2)
        self.sky_n = cv2.resize(noise(H // 2, W, 2.1, 5), (W * 2, H))
        self.vig = np.clip(1 - r, 0, 1) ** 1.3
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        # split what is not a wand into the book (line and arch) and the lettering below it
        cut = m.book_y + 12
        self.book_a = m.rest_a.copy(); self.book_a[cut:] = 0
        self.let_a = m.rest_a.copy(); self.let_a[:cut] = 0
        ys = np.nonzero(np.maximum(self.let_a, m.col).max(1) > 0.3)[0]
        self.dy_cover = H / 2 - (ys.min() + ys.max()) / 2                # the lettering centred on the cover
        xs = np.nonzero(self.book_a.max(0) > 0.3)[0]
        self.bx0, self.bx1 = xs.min(), xs.max()
        n = len(m.wand_a)
        order = list(range(n))[::-1]                                     # the right-most page turns first
        self.start = {i: TURN0 + j * TURN_GAP for j, i in enumerate(order)}

    def angle(self, i, k):
        a1 = self.m.wand_ang[i]
        close = seg(k, *CLOSE)
        t = (k - self.start[i]) / TURN_LEN
        if t <= 0:
            return FLAT, 0.0, 0.0
        if t < 1:
            return FLAT + (a1 - FLAT) * smooth(t), 0.0, t
        settle = 5.0 * math.exp(-(t - 1) * 3.0) * math.sin((t - 1) * 9.0)
        glint = max(0.0, 1 - (t - 1) * 1.5)
        a = a1 + settle
        return a + (FLAT - a) * close, glint * (1 - close), 1.0

    def frame(self, k):
        k = k % N
        m = self.m
        ph = 2 * math.pi * k / N
        sh = int(40 + 30 * math.sin(ph))
        sky = self.sky_n[:, sh:sh + W]
        img = np.array([0.015, 0.03, 0.05], np.float32) + (self.vig * (0.10 + 0.06 * sky))[..., None] * np.array([0.32, 0.55, 0.72], np.float32)
        # the lettering: centred on the cover, down under the book while it is open
        dy = self.dy_cover * (1 - seg(k, *DOWN) + seg(k, *UP))
        T = np.float32([[1, 0, 0], [0, 1, dy]])
        let_a = cv2.warpAffine(self.let_a, T, (W, H)); col = cv2.warpAffine(m.col, T, (W, H))
        rgb_l = cv2.warpAffine(m.rgb * self.let_a[..., None], T, (W, H))
        # the book's line draws out from the spine and back
        bk = seg(k, *BOOK_IN) * (1 - seg(k, *BOOK_OUT))
        half = (self.bx1 - self.bx0) / 2 * bk
        cx = m.pivot[0]
        reveal = smooth((half - np.abs(self.xx - cx)) / 6.0)
        book_a = self.book_a * reveal
        layer_a = np.maximum(let_a, book_a)
        layer_rgb = rgb_l * (1 - book_a[..., None]) + m.rgb * book_a[..., None]
        # the wands: pages that lie flat on the left page, turn over one by one, stand, and fall back as it closes
        stack = seg(k, BOOK_IN[0] + 12, BOOK_IN[1]) * (1 - seg(k, CLOSE[1], BOOK_OUT[0] + 8))
        mid = len(m.wand_a) // 2
        lift = seg(k, self.start[mid] + TURN_LEN - 4, self.start[mid] + TURN_LEN + 18) * (1 - seg(k, *CLOSE))
        gain = 1.0 + 0.18 * lift
        glints = np.zeros((H, W), np.float32)
        for i, wa in enumerate(m.wand_a):
            ang, glint, prog = self.angle(i, k)
            vis = stack if prog <= 0 or k >= CLOSE[1] else 1.0
            if vis <= 0.001:
                continue
            d = m.wand_ang[i] - ang
            M = cv2.getRotationMatrix2D((float(m.pivot[0]), float(m.pivot[1])), -d, 1.0)
            w_a = cv2.warpAffine(wa, M, (W, H), flags=cv2.INTER_LINEAR) * vis
            w_rgb = cv2.warpAffine(m.rgb * wa[..., None], M, (W, H), flags=cv2.INTER_LINEAR) * vis
            turning = 0 < prog < 1
            if turning:
                w_rgb = w_rgb * (1 - 0.3 * abs(math.sin(math.radians((ang - FLAT) * 0.5))))
            layer_rgb = layer_rgb * (1 - w_a[..., None]) + w_rgb
            layer_a = np.maximum(layer_a, w_a)
            if glint > 0:
                glints = np.maximum(glints, w_a * glint)
        img = img * (1 - 0.35 * bigblur(layer_a, 14))[..., None]
        face = layer_rgb * gain + (glints[..., None] * np.array([1.0, 0.85, 0.55], np.float32) * 0.45) * layer_a[..., None]
        img = img * (1 - layer_a[..., None]) + face
        img += bigblur(glints, 10)[..., None] * np.array([1.0, 0.8, 0.45], np.float32) * 0.18
        img += (bigblur(layer_a, 30) * 0.06 * lift)[..., None] * np.array([1.0, 0.8, 0.45], np.float32)
        img = img * (1 - col[..., None]) + np.array([0.86, 0.72, 0.46], np.float32) * gain * col[..., None]
        return to_image(img, 0, self.grain, 0.012)                     # still grain: it is the same film every frame


# --------------------------------------------------------------------------------------------------------- map
WAKE = (8, 70); SLEEP = (196, 236)


class Map:
    def __init__(self, src):
        self.m = Mark(src, lh=470, top=60)
        mp = Image.open(os.path.join(src, "map.jpg")).convert("RGB")
        mp = mp.crop((1790, 0, 2950, mp.height))                        # the castle plan, right of the title panel
        s = W / mp.width
        mp = np.asarray(mp.resize((W, round(mp.height * s)), Image.LANCZOS), np.float32) / 255
        y0 = (mp.shape[0] - H) // 2
        mp = mp[y0:y0 + H]
        lum = mp.mean(2)
        blank = cv2.medianBlur((mp * 255).astype(np.uint8), 21).astype(np.float32) / 255
        blank = cv2.GaussianBlur(blank, (0, 0), 3)
        self.blank = np.maximum(blank, mp)                               # the lines lifted out: the parchment itself
        self.inked = mp
        self.ink = np.array([0.25, 0.12, 0.07], np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        cx, cy = W / 2, self.m.y0 + 300
        self.dist = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.25) ** 2) + noise(H, W, 1.4, 9) * 160
        self.dmax = float(self.dist.max())
        fp = np.asarray(Image.open(os.path.join(src, "footprints.png")).convert("RGBA"), np.float32)[..., 3] / 255
        grp = cv2.dilate((fp > 0.5).astype(np.uint8), np.ones((25, 25), np.uint8))   # a sole and its heel together
        n, lab, st, cc = cv2.connectedComponentsWithStats(grp)
        i0 = max(range(1, n), key=lambda i: st[i, 4])
        x, y, w, h, _ = st[i0]
        one = fp[y:y + h, x:x + w] * (lab[y:y + h, x:x + w] == i0)
        self.print = cv2.resize(one, (int(w * 0.26), int(h * 0.26)), interpolation=cv2.INTER_AREA)
        # the walk: round the mark below it and away to the right
        pts = []
        for j in range(26):
            t = j / 25
            ang = math.pi * (0.95 - 1.25 * t)
            px = W / 2 + 470 * math.cos(ang); py = 470 + 150 * math.sin(ang) + 40 * t
            pts.append((px, py))
        self.steps = pts
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        fl = np.asarray(Image.open(os.path.join(src, "mark_flat.png")).convert("LA"), np.float32)[..., 1] / 255
        ys, xs = np.nonzero(fl > 0.5); fl = fl[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        sa = np.nonzero(self.m.a > 0.5); ty0, ty1 = sa[0].min(), sa[0].max(); tx0, tx1 = sa[1].min(), sa[1].max()
        fl = cv2.resize(fl, (int(tx1 - tx0 + 1), int(ty1 - ty0 + 1)), interpolation=cv2.INTER_AREA)
        self.flat = np.zeros((H, W), np.float32); self.flat[ty0:ty1 + 1, tx0:tx1 + 1] = fl
        mm = np.maximum(self.flat, self.m.col)
        self.keep = np.clip(bigblur(cv2.dilate(mm, np.ones((31, 31), np.uint8)), 24) * 1.6, 0, 1) * 0.85

    def frame(self, k):
        k = k % N
        m = self.m
        wake = seg(k, *WAKE) * (1 - seg(k, *SLEEP))
        front = wake * (self.dmax + 120)
        rev = smooth((front - self.dist) / 90)
        rev = rev * (1 - self.keep)                                       # the ink keeps clear of the mark
        img = self.blank * (1 - rev[..., None]) + self.inked * rev[..., None]
        # footprints, each appears and fades (one step every 4 frames, left and right)
        fpm = np.zeros((H, W), np.float32)
        for j, (px, py) in enumerate(self.steps):
            t0 = 70 + j * 4
            o = seg(k, t0, t0 + 2) * (1 - seg(k, t0 + 26, t0 + 40))
            if o <= 0:
                continue
            if j + 1 < len(self.steps):
                dx, dy = self.steps[j + 1][0] - px, self.steps[j + 1][1] - py
            else:
                dx, dy = px - self.steps[j - 1][0], py - self.steps[j - 1][1]
            ang = math.degrees(math.atan2(dy, dx))
            side = 9 if j % 2 else -9
            nx, ny = -dy, dx; nn = math.hypot(nx, ny) + 1e-6
            qx, qy = px + nx / nn * side, py + ny / nn * side
            p = self.print
            M = cv2.getRotationMatrix2D((p.shape[1] / 2, p.shape[0] / 2), -ang, 1.0)
            M[:, 2] += [qx - p.shape[1] / 2, qy - p.shape[0] / 2]
            fpm = np.maximum(fpm, cv2.warpAffine(p, M, (W, H)) * o)
        img = img * (1 - 0.85 * fpm[..., None]) + self.ink * 0.85 * fpm[..., None]
        # the mark, inked into the parchment; THE COLLECTION in the same ink
        ink_a = self.flat                                                 # the flat mark (the gold art's glints are not ink)
        tex = 0.85 + 0.15 * self.blank.mean(2, keepdims=True)
        img = img * (1 - ink_a[..., None] * 0.92) + self.ink * tex * ink_a[..., None] * 0.92
        img = img * (1 - m.col[..., None] * 0.9) + self.ink * m.col[..., None] * 0.9
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img *= (1 - 0.35 * np.clip(rr - 0.45, 0, 1))[..., None]
        return to_image(img, k, self.grain, 0.02)


def render(src, out, mode, only=None, mp4=None):
    s = Book(src) if mode == "book" else Map(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "book"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
