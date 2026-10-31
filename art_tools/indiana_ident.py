"""Indiana Jones card. The classic INDIANA JONES lettering (TMDB) and two things only these films have.

--mode map     The travel map: the red line that crosses an old map from one adventure to the next (Spielberg's way of
               skipping the travel montages in Raiders). A 1930s printed map, aged paper, inked coasts with water lining,
               the graticule; the line draws Raiders' journey (San Francisco, Honolulu, Manila, Nepal, Cairo), the
               camera following it from close, each stop named as it is reached; then the map pulls back to the whole
               route and the line fades for the cover.
--mode shadow  Indy's shadow: first his whip cracks across the lamplit plaster wall from off the frame (its shadow, a rope
               pulled by its handle and integrated, so the loop rolls out and the tip snaps), then the hat-and-whip
               silhouette (from a TMDB Raiders backdrop) walks in, stops behind the title, and leaves.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/indiana_ident.py SRC_DIR OUT_DIR [--mode map|shadow] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (INDIANA JONES cut from TMDB logo AoXnr773qvewCqQ5OnD8sSA1s0l, film 89, the subtitle removed),
           land.geojson (Natural Earth land), Cinzel.ttf, Montserrat-VF.ttf, wall_still.jpg (TMDB backdrop
           iEIB24xnHq2X8sXkRCup39KrXfF, film 85), indy_silhouette.png (from TMDB backdrop 6igbZAupOE5XKFTwpf8DLfggGLR,
           film 85)
"""
import json, math, os, sys, subprocess
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


def to_image(img, k, grain, amt=0.03):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


class Title:
    """INDIANA JONES and THE COLLECTION set where the films set their subtitles: under JONES, in yellow italics"""

    def __init__(self, src, lw=800, x0=None, y0=150):
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA")
        lh = round(lg.height * lw / lg.width)
        lg = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.x0 = (W - lw) // 2 if x0 is None else x0; self.y0 = y0; self.lw, self.lh = lw, lh
        self.rgb = np.zeros((H, W, 3), np.float32); self.a = np.zeros((H, W), np.float32)
        self.rgb[y0:y0 + lh, self.x0:self.x0 + lw] = lg[..., :3]; self.a[y0:y0 + lh, self.x0:self.x0 + lw] = lg[..., 3]
        f = ImageFont.truetype(os.path.join(src, "Montserrat-VF.ttf"), 60); f.set_variation_by_axes([800])
        txt = "THE COLLECTION"; track = 10
        tw = round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 80
        fill = Image.new("L", (tw, 120), 0); edge = Image.new("L", (tw, 120), 0)
        d1, d2 = ImageDraw.Draw(fill), ImageDraw.Draw(edge); x = 40
        for c in txt:
            d2.text((x, 90), c, font=f, fill=255, anchor="ls", stroke_width=7, stroke_fill=255)
            d1.text((x, 90), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
        sh = (1, 0.24, -14, 0, 1, 0)
        fill = fill.transform(fill.size, Image.AFFINE, sh, Image.BICUBIC); edge = edge.transform(edge.size, Image.AFFINE, sh, Image.BICUBIC)
        bb = edge.getbbox(); fill = fill.crop(bb); edge = edge.crop(bb)
        sc = 0.5
        fill = np.asarray(fill.resize((round(fill.width * sc), round(fill.height * sc)), Image.LANCZOS), np.float32) / 255
        edge = np.asarray(edge.resize((round(edge.width * sc), round(edge.height * sc)), Image.LANCZOS), np.float32) / 255
        ch, cw = fill.shape
        cx = self.x0 + int(lw * 0.70) - cw // 2; cy = y0 + int(lh * 0.70) - ch // 2
        self.col_a = np.zeros((H, W), np.float32); self.col_f = np.zeros((H, W), np.float32)
        self.col_a[cy:cy + ch, cx:cx + cw] = edge; self.col_f[cy:cy + ch, cx:cx + cw] = fill
        g = np.clip((np.arange(H, dtype=np.float32) - cy) / max(ch, 1), 0, 1)[:, None]
        self.col_rgb = (np.array([1.0, 0.93, 0.35], np.float32) * (1 - g[..., None]) + np.array([0.98, 0.62, 0.12], np.float32) * g[..., None])

    def over(self, img, light=None):
        """the title and THE COLLECTION over img; light scales them (None = as they are)"""
        lt = 1.0 if light is None else light
        a = self.a[..., None]
        img = img * (1 - a) + self.rgb * lt * a
        ca = self.col_a[..., None]; cf = self.col_f[..., None]
        img = img * (1 - ca) + np.array([0.03, 0.02, 0.01], np.float32) * ca
        img = img * (1 - cf) + self.col_rgb * lt * cf
        return img

    def mask(self):
        return np.maximum(self.a, self.col_a)


# --------------------------------------------------------------------------------------------------------- map
P = 24                                                                   # map pixels per degree
LON0, LON1, LAT0, LAT1 = -352.0, -98.0, -32.0, 76.0
ROUTE = [("SAN FRANCISCO", 37.77, -122.42), ("HONOLULU", 21.31, -157.86), ("MANILA", 14.60, 120.98 - 360),
         ("NEPAL", 27.72, 85.32 - 360), ("CAIRO", 30.04, 31.24 - 360)]
LEGS = [(14, 46), (52, 98), (104, 134), (140, 176)]
INK = np.array([0.30, 0.19, 0.10], np.float32)
RED = np.array([0.80, 0.10, 0.05], np.float32)


def mxy(lat, lon):
    return (lon - LON0) * P, (LAT1 - lat) * P


class MapMode:
    def __init__(self, src):
        self.t = Title(src, lw=800, y0=170)
        MW, MH = int((LON1 - LON0) * P), int((LAT1 - LAT0) * P)
        self.MW, self.MH = MW, MH
        land = np.zeros((MH, MW), np.uint8)
        gj = json.load(open(os.path.join(src, "land.geojson")))
        for ft in gj["features"]:
            g = ft["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for shift in (0.0, -360.0):
                    rings = []
                    for ring in poly:
                        pts = np.array([mxy(la, lo + shift) for lo, la in ring], np.float32)
                        if pts[:, 0].max() < -50 or pts[:, 0].min() > MW + 50:
                            continue
                        rings.append(np.round(pts).astype(np.int32))
                    if rings:
                        cv2.fillPoly(land, rings[:1], 255)
                        if len(rings) > 1:
                            cv2.fillPoly(land, rings[1:], 0)
        landf = land.astype(np.float32) / 255
        # paper, stains, the land a little darker, inked coast, water lining, graticule
        paper = np.dstack([np.full((MH, MW), v, np.float32) for v in (0.86, 0.78, 0.62)])
        st = cv2.resize(noise(MH // 8, MW // 8, 1.8, 3), (MW, MH)); fine = cv2.resize(noise(MH // 2, MW // 2, 1.0, 4), (MW, MH))
        paper *= (0.86 + 0.18 * st)[..., None] * (0.97 + 0.05 * fine)[..., None]
        img = paper * (1 - 0.08 * landf[..., None]) + landf[..., None] * np.array([-0.02, -0.03, -0.06], np.float32)
        sea = (land == 0).astype(np.uint8)
        d = cv2.distanceTransform(sea, cv2.DIST_L2, 5)
        wl = np.zeros((MH, MW), np.float32)
        for dd, op in ((5.0, 0.55), (11.0, 0.35), (19.0, 0.2)):
            wl = np.maximum(wl, np.exp(-((d - dd) / 0.9) ** 2) * op)
        coast = cv2.morphologyEx(land, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32) / 255
        coast = blur(coast, 0.6)
        grat = np.zeros((MH, MW), np.uint8)
        for lo in range(-350, -90, 10):
            x = int((lo - LON0) * P); cv2.line(grat, (x, 0), (x, MH), 255, 1, cv2.LINE_AA)
        for la in range(-30, 80, 10):
            y = int((LAT1 - la) * P); cv2.line(grat, (0, y), (MW, y), 255, 1, cv2.LINE_AA)
        gr = grat.astype(np.float32) / 255
        ink = np.clip(coast * 0.9 + wl * 0.5 + gr * 0.22, 0, 1)
        img = img * (1 - ink[..., None]) + INK * ink[..., None]
        # ocean names, spaced italics in the map's ink
        pim = Image.fromarray(np.zeros((MH, MW), np.uint8)); dr = ImageDraw.Draw(pim)
        fo = ImageFont.truetype(os.path.join(src, "Cinzel.ttf"), 66)
        for txt, la, lo in (("PACIFIC   OCEAN", 6, -170), ("INDIAN   OCEAN", -14, 78 - 360), ("CHINA  SEA", 14, 114 - 360)):
            x, y = mxy(la, lo); dr.text((x, y), txt, font=fo, fill=150, anchor="mm")
        ol = np.asarray(pim, np.float32) / 255
        img = img * (1 - ol[..., None] * 0.6) + INK * ol[..., None] * 0.6
        self.map = np.clip(img * 255, 0, 255).astype(np.uint8)
        self.pts = [mxy(la, lo) for _, la, lo in ROUTE]
        self.fl = ImageFont.truetype(os.path.join(src, "Cinzel.ttf"), 30)
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.66)) ** 2)
        self.vig = (1 - 0.5 * np.clip(r - 0.4, 0, 1) ** 1.2)[..., None]
        xs = [p[0] for p in self.pts]; ys = [p[1] for p in self.pts]
        self.wide = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2 + 80, W / ((max(xs) - min(xs)) * 1.18))

    def head(self, k):
        """how far the line has got: (leg index, fraction), and the head point"""
        done = 0; frac = 0.0
        for i, (a, b) in enumerate(LEGS):
            if k >= b:
                done = i + 1; frac = 0.0
            elif k >= a:
                done = i; frac = smooth((k - a) / (b - a)) * 0.85 + 0.15 * (k - a) / (b - a)
                break
            else:
                break
        if done >= len(LEGS):
            return len(LEGS), 0.0, self.pts[-1]
        p0 = np.array(self.pts[done]); p1 = np.array(self.pts[done + 1])
        return done, frac, tuple(p0 + (p1 - p0) * frac)

    def view(self, k):
        cx_w, cy_w, z_w = self.wide
        close = 0.62
        leg, frac, hp = self.head(k)
        if k < 14:
            hp = self.pts[0]
        u_in = seg(k, 2, 18); u_out = seg(k, 178, 214)
        zin = z_w + (close - z_w) * u_in
        z = zin + (z_w - zin) * u_out
        cx = cx_w + (hp[0] - cx_w) * u_in; cy = cy_w + (hp[1] + 60 / max(z, 1e-3) * 0 - cy_w) * u_in
        cx = cx + (cx_w - cx) * u_out; cy = cy + (cy_w - cy) * u_out
        return cx, cy, z

    def frame(self, k):
        k = k % N
        cx, cy, z = self.view(k)
        yc = H * (0.56 + 0.22 * seg(k, 2, 18) * (1 - seg(k, 178, 214)))   # the line runs below the title
        M = np.float32([[z, 0, W / 2 - cx * z], [0, z, yc - cy * z]])
        img = cv2.warpAffine(self.map, M, (W, H), flags=cv2.INTER_AREA if z < 1 else cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
        to_s = lambda p: (p[0] * z + M[0, 2], p[1] * z + M[1, 2])
        fade = 1 - seg(k, 212, 236)
        leg, frac, hp = self.head(k)
        line = np.zeros((H * 2, W * 2), np.uint8)
        dots = np.zeros((H * 2, W * 2), np.uint8)
        if k >= LEGS[0][0] and fade > 0:
            pts = [to_s(p) for p in self.pts[:leg + 1]] + ([to_s(hp)] if leg < len(LEGS) else [])
            arr = (np.array(pts) * 2).astype(np.int32)
            cv2.polylines(line, [arr], False, 255, max(5, int(12 * min(1.0, z / 0.62))), cv2.LINE_AA)
            for p in self.pts[:leg + 1]:
                sx, sy = to_s(p); cv2.circle(dots, (int(sx * 2), int(sy * 2)), 11, 255, -1, cv2.LINE_AA)
        line = cv2.resize(line, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * fade
        dots = cv2.resize(dots, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * fade
        img = img * (1 - line[..., None]) + RED * line[..., None]
        img = img * (1 - dots[..., None]) + INK * dots[..., None]
        # the names of the stops, as each is reached
        lab = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(lab)
        for i, (name, la, lo) in enumerate(ROUTE):
            reach = LEGS[i - 1][1] if i > 0 else LEGS[0][0]
            o = seg(k, reach, reach + 6) * fade
            if o <= 0:
                continue
            sx, sy = to_s(self.pts[i])
            if -200 < sx < W + 200:
                dr.text((sx + 16, sy - 14), name, font=self.fl, fill=int(255 * o), anchor="ld")
        la_ = np.asarray(lab, np.float32)[..., None] / 255
        img = img * (1 - la_ * 0.9) + INK * la_ * 0.9
        img = img * self.vig
        # the title stands over the map with a soft shadow
        tm = self.t.mask()
        img = img * (1 - 0.45 * blur(np.roll(np.roll(tm, 10, 0), 8, 1), 8))[..., None]
        img = self.t.over(img)
        return to_image(img, k, self.grain, 0.03)


# --------------------------------------------------------------------------------------------------------- shadow
WHIP0 = 4                                                                # the crack comes first, from off the frame


class ShadowMode:
    def __init__(self, src):
        self.t = Title(src, lw=780, x0=150, y0=180)
        # the bar's plaster: its colour taken from the film's still, its grain made to fill the frame without repeats
        st = np.asarray(Image.open(os.path.join(src, "wall_still.jpg")).convert("RGB"), np.float32)[0:330, 240:680] / 255
        tone = st.reshape(-1, 3).mean(0); tone = tone / tone.mean()
        n1 = noise(H, W, 1.9, 11); n2 = noise(H, W, 1.2, 12); n3 = noise(H, W, 0.7, 13)
        plaster = 0.62 + 0.3 * (n1 - 0.5) + 0.22 * (n2 - 0.5) + 0.1 * (n3 - 0.5)
        self.wall = (plaster[..., None] * tone * np.array([0.82, 0.70, 0.56], np.float32)).astype(np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        d = np.sqrt(((xx - 600) / 720) ** 2 + ((yy - 330) / 520) ** 2)
        self.pool = (np.clip(1.15 - d, 0, 1) ** 1.4).astype(np.float32)
        sil = cv2.imread(os.path.join(src, "indy_silhouette.png"), 0).astype(np.float32) / 255
        self.sil = sil
        self.whip = self.crack()
        self.grain = noise(H * 2, W * 2, 0.0, 7)

    def crack(self):
        """a whip cracked from off the frame (right): a rope of 50 links pulled by its handle, integrated (Verlet);
        returns, per frame, a few positions within the frame for its motion blur"""
        n, L, SUB = 56, 1000.0, 24
        sl = L / (n - 1)
        keys = [(0, (1420, 300)), (WHIP0, (1420, 300)), (WHIP0 + 6, (1620, 120)), (WHIP0 + 9, (1230, 300)),
                (WHIP0 + 12, (1225, 305)), (WHIP0 + 24, (1260, 310)), (WHIP0 + 32, (1600, 300)), (N, (1600, 300))]

        def handle(t):
            for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
                if t0 <= t <= t1:
                    u = smooth((t - t0) / max(t1 - t0, 1e-6))
                    return np.array(p0, float) + (np.array(p1, float) - np.array(p0, float)) * u
            return np.array(keys[-1][1], float)
        P = np.array([[1420 + i * sl * 0.98, 300 + i * 1.0] for i in range(n)], float); Pp = P.copy()
        g = np.array([0, 0.0015]); out = []
        for f in range(N):
            snaps = []
            for s in range(SUB):
                t = f + s / SUB
                V = (P - Pp) * 0.9985; Pp = P.copy(); P = P + V + g; P[0] = handle(t)
                for _ in range(14):
                    d = P[1:] - P[:-1]; dist = np.linalg.norm(d, axis=1) + 1e-6
                    c = d * ((dist - sl) / dist)[:, None] * 0.5
                    P[:-1] += c; P[1:] -= c; P[0] = handle(t)
                if s % 2 == 0:
                    snaps.append(P.copy())
            out.append(snaps)
        return out

    def whip_shadow(self, k):
        if not (WHIP0 <= k < WHIP0 + 40):
            return np.zeros((H, W), np.float32)
        acc = np.zeros((H * 2, W * 2), np.float32)
        snaps = self.whip[k]
        for Q in snaps:
            m = np.zeros((H * 2, W * 2), np.uint8)
            q = (Q * 2).astype(np.int32)
            for i in range(len(q) - 1):
                th = int(round(18 - 13 * i / (len(q) - 1)))             # thick at the handle, thin at the tip
                cv2.line(m, tuple(int(v) for v in q[i]), tuple(int(v) for v in q[i + 1]), 255, max(th, 2), cv2.LINE_AA)
            acc += m.astype(np.float32) / 255
        acc = np.clip(acc / len(snaps) * 2.2, 0, 1)                 # a fast whip still throws a full shadow, smeared
        return blur(cv2.resize(acc, (W, H), interpolation=cv2.INTER_AREA), 2.2)

    def place(self, k):
        """where his shadow is: x of the hat's centre, scale, softness, bob"""
        enter = seg(k, 44, 100); leave = seg(k, 172, 228)
        x = 1650 + (930 - 1650) * enter
        x = x + (1700 - x) * leave
        walking = (44 <= k < 100) or (172 <= k < 228)
        bob = 3.0 * abs(math.sin(k * 0.42)) if walking else 0.8 * math.sin(k * 0.12)
        s = 1.85 + 0.12 * seg(k, 92, 116) * (1 - seg(k, 160, 180))    # a step towards the lamp: larger, softer
        soft = 3.5 + 3.0 * seg(k, 92, 116) * (1 - seg(k, 160, 180))
        return x, s, soft, bob

    def frame(self, k):
        k = k % N
        flick = 1.0 + 0.015 * math.sin(k * 1.7) + 0.01 * math.sin(k * 4.1)
        tc = k - (WHIP0 + 18)                                            # the crack stirs the lamp's flame
        if 0 <= tc < 10:
            flick *= 1 - 0.07 * math.exp(-tc / 3) * abs(math.cos(tc * 1.6))
        x, s, soft, bob = self.place(k)
        sh = np.zeros((H, W), np.float32)
        if x < W + 400:
            sw, shh = self.sil.shape[1] * s, self.sil.shape[0] * s
            M = np.float32([[s, 0, x - sw / 2], [0, s, 30 + bob]])
            sh = cv2.warpAffine(self.sil, M, (W, H), flags=cv2.INTER_LINEAR)
            sh = blur(sh, soft)
        sh = np.maximum(sh, self.whip_shadow(k) * 0.9)
        light = self.pool * flick
        tm = self.t.mask()
        tshadow = blur(np.roll(np.roll(tm, 16, 0), 22, 1), 7)          # the title's own shadow, lamp front left
        lit = light * (1 - 0.82 * sh) * (1 - 0.5 * tshadow)
        img = self.wall * (0.05 + 1.05 * lit)[..., None] * np.array([1.0, 0.86, 0.66], np.float32)
        tl = (0.55 + 0.5 * light * (1 - 0.3 * sh))[..., None]
        img = self.t.over(img, light=np.clip(tl, 0, 1.05))
        img = img / (1 + 0.15 * img) * 1.15
        return to_image(img, k, self.grain, 0.035)


def render(src, out, mode, only=None, mp4=None):
    s = MapMode(src) if mode == "map" else ShadowMode(src)
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
    mode = a[a.index("--mode") + 1] if "--mode" in a else "map"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
