"""Mission: Impossible card: the red MISSION: IMPOSSIBLE of Dead / Final Reckoning, on screen for the whole hover.

The fuse runs under the title from left to right - a single hot point of light with a long anamorphic streak, no
particles - and where it has passed the red letters open onto the series' signature stunts, film by film (the
Langley vault, the aquarium, the Burj Khalifa, the A400M door, the HALO jump, the helicopter, the rooftop leap, the
cliff jump, the paraglider, the biplane), cut on the beat, each pushing in slowly; the film plays only inside the
letters. Behind, a dark red dot-matrix world map drifts like an IMF screen; each stunt pings its place on it
(Langley, Prague, Dubai ... South Africa) and a route draws from the last one. The fuse runs back from right to left and the title is red again.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/mi_ident.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]
  SRC_DIR: title.png (the Final Reckoning title logo on TMDB, film 575265; only the MISSION: IMPOSSIBLE line is used),
           stills/NN_*.jpg (official TMDB backdrops, in order), BarlowCondensed-Medium.ttf,
           land.geojson (Natural Earth 1:110m land, public domain)
"""
import glob, math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
# where the subject of each still is (share of width, height): it is placed on the title
FOCUS = [(0.42, 0.48), (0.55, 0.42), (0.48, 0.4), (0.38, 0.36), (0.5, 0.45), (0.6, 0.58), (0.6, 0.5),
         (0.76, 0.45), (0.53, 0.55), (0.52, 0.5), (0.43, 0.55)]
# where each stunt was set (lon, lat, label): pinged on the map while it plays in the letters
PLACES = [(-77.15, 38.95, "LANGLEY"), (14.42, 50.08, "PRAGUE"), (55.27, 25.2, "DUBAI"), (27.56, 53.9, "MINSK"),
          (2.35, 48.86, "PARIS"), (74.8, 34.08, "KASHMIR"), (-0.1, 51.51, "LONDON"), (11.4, 47.3, "THE ALPS"),
          (11.4, 47.3, "THE ALPS"), (18.4, -33.9, "SOUTH AFRICA"), (18.4, -33.9, "SOUTH AFRICA")]
LON0, LAT0, DEG = -125.0, 75.0, 260.0 / 1280     # the map's view: left edge, top edge, degrees per pixel
T_IN = (3, 30)               # the fuse runs left to right
T_OUT = (204, 231)           # and back
CUT0, CUTLEN = 30, 16        # the cuts


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def bigblur(a, s):
    h, w = a.shape[:2]
    sm = cv2.resize(a, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), s / 4)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)


def text_layer(font, size, txt, track, shear=0.0):
    f = ImageFont.truetype(font, size)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 80, size * 2), 0)
    d = ImageDraw.Draw(m); x = 40
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    if shear:
        m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * m.height * 0.75, 0, 1, 0), Image.BICUBIC)
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


class Scene:
    def __init__(self, src):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        a = np.asarray(Image.open(os.path.join(src, "title.png")).convert("RGBA"), np.float32)[:540]
        ys, xs = np.where(a[..., 3] > 10); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        lw = 1080; lh = round(a.shape[0] * lw / a.shape[1])
        a = cv2.resize(a, (lw, lh), interpolation=cv2.INTER_AREA)
        self.top = 296 - lh // 2; self.x0 = (W - lw) // 2; self.lw, self.lh = lw, lh
        self.la = np.zeros((H, W), np.float32); self.red = np.zeros((H, W, 3), np.float32)
        self.la[self.top:self.top + lh, self.x0:self.x0 + lw] = a[..., 3] / 255
        self.red[self.top:self.top + lh, self.x0:self.x0 + lw] = a[..., :3]
        m = (self.la > 0.5).astype(np.uint8)
        self.rim = blur(np.clip(self.la - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1), 0.6)
        self.cy = self.top + lh / 2
        sub = text_layer(os.path.join(src, "BarlowCondensed-Medium.ttf"), 58, "THE COLLECTION", 40, shear=0.2)
        self.sub = np.zeros((H, W), np.float32)
        sy = self.top + lh + 22; sx = (W - sub.shape[1]) // 2
        self.sub[sy:sy + sub.shape[0], sx:sx + sub.shape[1]] = sub
        self.fy = self.top + lh + 10                                        # the fuse runs just under the title
        self.stills = []
        for i, f in enumerate(sorted(glob.glob(os.path.join(src, "stills", "*.jpg")))):
            im = np.asarray(Image.open(f).convert("RGB"), np.float32)
            s = max(W * 1.22 / im.shape[1], H * 1.22 / im.shape[0])
            im = cv2.resize(im, (round(im.shape[1] * s), round(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
            fx, fy = FOCUS[i % len(FOCUS)]
            ox = float(np.clip(fx * im.shape[1] - W / 2, 0, im.shape[1] - W))
            oy = float(np.clip(fy * im.shape[0] - self.cy, 0, im.shape[0] - H))
            im = np.clip((im - 128) * 1.08 + 128, 0, 255).astype(np.float32)
            self.stills.append((im, ox, oy))
        self.n = len(self.stills)
        self.build_map(src)
        self._cache = {}

    def build_map(self, src):
        """a dot-matrix world map (Natural Earth land, public domain), dark red, like the IMF's screens"""
        import json
        geo = json.load(open(os.path.join(src, "land.geojson")))
        MW, MH = W + 120, H + 60                                          # a little wider: it drifts
        self.mw, self.mh = MW, MH
        land = np.zeros((MH, MW), np.uint8)
        def xy(lon, lat):
            return (lon - LON0) / DEG + 60, (LAT0 - lat) / DEG + 30
        for f in geo["features"]:
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for ring in poly[:1]:
                    pts = np.array([xy(lo, la) for lo, la in ring], np.float32)
                    cv2.fillPoly(land, [np.round(pts * 4).astype(np.int32)], 1, cv2.LINE_AA, 2)
        dots = np.zeros((MH, MW), np.float32)
        sp = 8
        for y in range(sp // 2, MH, sp):
            for x in range(sp // 2, MW, sp):
                if land[y, x]:
                    cv2.circle(dots, (x * 4, y * 4), 6, 1.0, -1, cv2.LINE_AA, 2)
        self.dots = dots
        self.xy = xy
        f = ImageFont.truetype(os.path.join(src, "BarlowCondensed-Medium.ttf"), 34)
        self.labels = {}
        for _, _, name in PLACES:
            if name not in self.labels:
                m = Image.new("L", (int(sum(f.getlength(c) for c in name) + 8 * len(name)) + 20, 50), 0)
                d = ImageDraw.Draw(m); x = 10
                for c in name:
                    d.text((x, 38), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + 8
                m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
                self.labels[name] = np.asarray(m, np.float32) / 255

    def world(self, k):
        """the map layer at frame k: drifting dots, the trail of places so far, the newest one pinging"""
        ox = 60 + 40 * math.sin(2 * math.pi * k / N); oy = 30 + 12 * math.sin(2 * math.pi * k / N + 1.3)
        M = np.float32([[1, 0, -ox + 60], [0, 1, -oy + 30]])
        base = cv2.warpAffine(self.dots, np.float32([[1, 0, -ox], [0, 1, -oy]]), (W, H), flags=cv2.INTER_LINEAR)
        lay = np.zeros((H, W, 3), np.float32)
        lay += base[..., None] * np.array([62, 12, 9], np.float32)
        live = 1.0
        if k < CUT0:
            return lay, 0.0
        if k >= T_OUT[0]:
            live = 1 - float(smooth((k - T_OUT[0]) / 26.0))
        i_now = min(self.n - 1, (k - CUT0) // CUTLEN)
        line = np.zeros((H, W), np.float32); pts = np.zeros((H, W), np.float32)
        hot = np.zeros((H, W), np.float32); text = np.zeros((H, W), np.float32)
        def P(i):
            x, y = self.xy(PLACES[i][0], PLACES[i][1]); return x - ox, y - oy
        for i in range(i_now + 1):
            t = (k - CUT0 - i * CUTLEN)
            x, y = P(i)
            cv2.circle(pts, (int(x * 4), int(y * 4)), 10, 1.0, -1, cv2.LINE_AA, 2)
            if i > 0 and P(i) != P(i - 1):                                # the route, drawn as the cut lands
                (x0, y0) = P(i - 1)
                u = min(1.0, t / 8.0)
                mx, my = (x0 + x) / 2, (y0 + y) / 2 - 0.18 * math.hypot(x - x0, y - y0)
                ts = np.linspace(0, u, 40)
                cx = (1 - ts) ** 2 * x0 + 2 * (1 - ts) * ts * mx + ts ** 2 * x
                cy = (1 - ts) ** 2 * y0 + 2 * (1 - ts) * ts * my + ts ** 2 * y
                cv2.polylines(line, [np.round(np.stack([cx, cy], 1) * 4).astype(np.int32)], False, 1.0, 1, cv2.LINE_AA, 2)
            if i == i_now:
                r = 6 + 34 * min(1.0, t / 12.0)
                cv2.circle(hot, (int(x * 4), int(y * 4)), int(r * 4), float(max(0.0, 1 - t / 14.0)), 2, cv2.LINE_AA, 2)
                cv2.circle(hot, (int(x * 4), int(y * 4)), 14, 1.0, -1, cv2.LINE_AA, 2)
                lb = self.labels[PLACES[i][2]]
                lx, ly = int(x + 12), int(y - lb.shape[0] - 6)
                if 0 <= lx < W - lb.shape[1] and 0 <= ly < H - lb.shape[0]:
                    text[ly:ly + lb.shape[0], lx:lx + lb.shape[1]] = lb * min(1.0, t / 4.0)
        red = np.array([235, 52, 30], np.float32)
        lay += (pts * 0.55 + line * 0.5)[..., None] * red * live
        lay += (hot + blur(hot, 4) * 1.5)[..., None] * red * live
        lay += text[..., None] * np.array([200, 196, 192], np.float32) * 0.8 * live
        return lay, live

    def still(self, k):
        if k in self._cache:
            return self._cache[k]
        i = min(self.n - 1, max(0, (k - CUT0) // CUTLEN))
        t = max(0.0, ((k - CUT0) - i * CUTLEN) / CUTLEN)
        im, ox, oy = self.stills[i]
        z = 1.0 + 0.06 * min(1.8, t)                                        # slow push in
        cx, cy = W / 2, self.cy
        M = np.float32([[z, 0, -ox * z + cx * (1 - z)], [0, z, -oy * z + cy * (1 - z)]])
        out = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        self._cache = {k: out}
        return out

    def fuse(self, k):
        for (a, b), rev in ((T_IN, False), (T_OUT, True)):
            if a <= k <= b:
                v = (k - a) / (b - a)
                u = 0.85 * v + 0.15 * float(smooth(v))
                x = self.x0 - 40 + u * (self.lw + 80)
                return (self.x0 + self.lw + self.x0 - x) if rev else x
        return None

    def frame(self, k):
        hx = self.fuse(k)
        if hx is not None:
            openm = smooth((hx - self.xx) / 18)
        elif T_IN[1] < k < T_OUT[0]:
            openm = np.ones((H, W), np.float32)
        else:
            openm = np.zeros((H, W), np.float32)
        img = np.zeros((H, W, 3), np.float32) + np.array([5, 4, 4], np.float32)
        wl, _ = self.world(k)
        img += wl * (1 - bigblur(self.la, 14)[..., None] * 0.9)                # the map stays clear of the title
        img += (bigblur(self.la, 40) * 0.5)[..., None] * np.array([90, 8, 4], np.float32) * (1 - openm[..., None])
        st = self.still(k) if openm.max() > 0 else None
        if st is not None:
            if T_IN[0] <= k <= T_IN[1]:
                g = float(smooth((k - T_IN[0]) / (T_IN[1] - T_IN[0])))
            elif T_OUT[0] <= k <= T_OUT[1]:
                g = 1 - float(smooth((k - T_OUT[0]) / (T_OUT[1] - T_OUT[0])))
            else:
                g = 1.0
            img += bigblur(st * (self.la * openm)[..., None], 26) * 0.12                   # a faint glow off the letters
        a = self.la[..., None]
        letters = self.red * (1 - openm[..., None])
        if st is not None:
            fill = 255 * (st / 255) ** 1.12 * 0.95                           # a touch deeper inside the letters
            letters = letters + fill * openm[..., None] + (self.rim * openm * 0.8)[..., None] * np.array([230, 30, 20], np.float32)
        img = img * (1 - a) + letters * a
        if hx is not None:                                                  # the fuse's head
            fl = 0.9 + 0.1 * math.sin(k * 2.3)
            d2 = (self.xx - hx) ** 2 + (self.yy - self.fy) ** 2
            core = np.exp(-d2 / (2 * 2.2 ** 2)); halo = np.exp(-d2 / (2 * 18.0 ** 2)); wide = np.exp(-d2 / (2 * 120.0 ** 2))
            streak = np.exp(-((self.yy - self.fy) / 1.6) ** 2) * np.exp(-np.abs(self.xx - hx) / 380)
            img += ((core * 3.0 + halo * 0.9) * fl)[..., None] * np.array([255, 236, 210], np.float32)
            img += ((wide * 0.35 + streak * 0.9) * fl)[..., None] * np.array([255, 120, 50], np.float32)
            under = np.exp(-((self.xx - hx) / 90) ** 2) * self.la * smooth((self.yy - self.top - self.lh * 0.4) / (self.lh * 0.6))
            img += (under * 0.8 * fl)[..., None] * np.array([255, 170, 110], np.float32)
        img = img * (1 - self.sub[..., None]) + self.sub[..., None] * np.array([238, 236, 232], np.float32)
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        img *= (1 - 0.45 * np.clip(rr - 0.4, 0, 1))[..., None]
        img += np.random.default_rng(900 + k).normal(size=(H, W)).astype(np.float32)[..., None] * 1.5
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
