"""Star Trek card: deep space, the STAR TREK wordmark and THE COLLECTION under it (Antonio, the LCARS-style face).
Hover (10 s): the title fades, the stars start to stream past and the ship jumps to warp with a flash. Through the warp
the eras come at us one after another, each a face growing out of the vanishing point, filling the frame and passing:
Spock, Khan, Picard, Sisko, Janeway, Kirk, Burnham, Picard, Pike. No holds, no cuts. The ship drops out of warp with
a second flash, the stars settle where they started and the title returns. First frame = last frame = cover.
Stars and flashes are drawn analytically; the stars travel a whole number of depth periods over the loop, so they end
exactly where they began.
usage: python3 art_tools/startrek_warp.py SRC_DIR OUT_DIR [--frames a,b]
  SRC_DIR: logo.png (STAR TREK wordmark), Antonio.ttf, stills/NN_*.jpg (+ NN_*.json: {"fx", "fy", "fh"} = centre
           and height of the face as shares of the still)
"""
import glob, json, math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 250                                         # 10.0 s
F = 640.0                                       # focal length (px) of the star camera
NSTAR, ZD = 2200, 1.0                           # stars and the depth they wrap over

T_TITLE_OUT = (6, 20)
T_TITLE_IN = (220, 238)
FLASH_IN, FLASH_OUT = 36, 214                   # the jump to warp and the drop out of it
# speed (depth units per frame) keyframes: rest, impulse, warp, rest; scaled so the loop's travel is whole periods
SPEED = [(0, 0.0), (8, 0.0), (30, 0.012), (40, 0.11), (204, 0.11), (220, 0.0), (N, 0.0)]

# the stills: each grows from the vanishing point at a steady zoom rate and passes the camera
PW0, PW1, LIFE = 40.0, 1900.0, 80               # panel width at birth / at the end of its life (px), frames
STEP, FIRST = 17, -2                            # frames between births, first birth
FADE_IN, SOLO, FADE_OUT = (60, 300), 1150, 1900  # widths: fade in, start fading out, gone
FACE_SHARE, FACE_V = 0.42, 0.45                 # face height as share of the panel, its centre this far down


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    return smooth((k - ab[0]) / max(1, ab[1] - ab[0]))


def speed_raw(k):
    for (a, va), (b, vb) in zip(SPEED, SPEED[1:]):
        if a <= k < b:
            return va + (vb - va) * smooth((k - a) / (b - a))
    return 0.0


class Scene:
    def __init__(self, src):
        rng = np.random.default_rng(7)
        # stars in camera space: x, y spread wide enough to fill the frame at every depth
        self.sx = rng.uniform(-1.6, 1.6, NSTAR); self.sy = rng.uniform(-1.0, 1.0, NSTAR)
        self.sz0 = rng.uniform(0.02, ZD, NSTAR)
        self.mag = rng.random(NSTAR) ** 2.2
        self.tint = rng.random(NSTAR)
        raw = np.array([speed_raw(k) for k in range(N)])
        total = raw.sum(); periods = max(1, round(total / ZD))
        self.v = raw * periods * ZD / total
        self.travel = np.concatenate([[0], np.cumsum(self.v)])          # travel before frame k
        # a still, faint nebula behind everything
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        neb = np.zeros((H, W, 3), np.float32) + np.array([3, 4, 10], np.float32)
        for (cx, cy, rx, ry, col) in ((420, 260, 520, 300, (20, 26, 58)), (930, 470, 460, 260, (34, 18, 50)),
                                      (640, 360, 760, 420, (8, 12, 26))):
            g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
            neb += g[..., None] * np.array(col, np.float32)
        self.neb = neb
        self.xx, self.yy = xx, yy
        # title
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA"); lg = lg.crop(lg.getbbox())
        lw = 700; self.logo = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
        f = ImageFont.truetype(os.path.join(src, "Antonio.ttf"), 64)
        try:
            f.set_variation_by_axes([400])
        except Exception:
            pass
        txt, tr = "THE COLLECTION", 26
        m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 20, 130), 0)
        d = ImageDraw.Draw(m); x = 10
        for c in txt:
            d.text((x, 100), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        self.sub = Image.merge("RGBA", (Image.new("L", m.size, 200), Image.new("L", m.size, 214),
                                        Image.new("L", m.size, 234), m))
        self.ty = 302
        # stills, cropped to 16:9 panels framed on the face, at the largest size they are drawn
        self.panels = []
        pw, ph = int(PW1), int(round(PW1 * 9 / 16))
        for fp in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            fr = {"fx": 0.5, "fy": 0.4, "fh": 0.4}
            jp = os.path.splitext(fp)[0] + ".json"
            if os.path.exists(jp):
                fr.update(json.load(open(jp)))
            im = Image.open(fp).convert("RGB")
            hs = min(1.0, fr["fh"] / FACE_SHARE)                          # share of the still's height shown
            ch = hs * im.height; cw = ch * 16 / 9
            if cw > im.width:
                cw = im.width; ch = cw * 9 / 16
            cx = min(max(fr["fx"] * im.width, cw / 2), im.width - cw / 2)
            cy = min(max(fr["fy"] * im.height + (0.5 - FACE_V) * ch, ch / 2), im.height - ch / 2)
            box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
            p = im.resize((pw, ph), Image.LANCZOS, box=box)
            a = np.asarray(p, np.float32)
            lum = (a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
            a = a * 0.86 + lum * 0.14                                   # a touch less saturation, one family
            a = a * np.array([0.96, 0.98, 1.04], np.float32)               # and a cool cast to sit in space
            self.panels.append(np.clip(a, 0, 255))
        # panel alpha: a clean, slightly rounded frame (a viewscreen), with a thin rim of light on its edge
        rr = int(pw * 0.012)
        m = Image.new("L", (pw * 2, ph * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw * 2 - 1, ph * 2 - 1), radius=rr * 2, fill=255)
        self.pmask = np.asarray(m.resize((pw, ph), Image.LANCZOS), np.float32) / 255
        inner = cv2.erode(self.pmask, np.ones((7, 7), np.uint8))
        self.prim = np.clip(self.pmask - inner, 0, 1)
        self.n = len(self.panels)

    def stars(self, k, img, streak_gain=1.0):
        z = (self.sz0 - self.travel[k]) % ZD + 0.02
        v = self.v[k] if k < N else 0.0
        L = np.clip(v * 2.6, 0, 0.5)                                   # streak length in depth
        x0 = W / 2 + F * self.sx / z; y0 = H / 2 + F * self.sy / z
        z1 = z + L
        x1 = W / 2 + F * self.sx / z1; y1 = H / 2 + F * self.sy / z1
        b = np.clip(self.mag * 1.3 + 0.12, 0, 1) * np.clip(1.25 - z / ZD, 0.35, 1.0)
        lay = np.zeros((H, W, 3), np.float32)
        on = (x0 > -400) & (x0 < W + 400) & (y0 > -400) & (y0 < H + 400)
        warp = min(1.0, v / 0.06)
        for i in np.nonzero(on)[0]:
            col = np.array([255, 245, 235]) * (1 - self.tint[i] * 0.3) + np.array([170, 200, 255]) * self.tint[i] * 0.3
            col = col * (0.55 + 0.45 * warp * (self.tint[i] > 0.5))
            if L > 0.003:
                th = 1 if b[i] < 0.6 else 2
                cv2.line(lay, (int(x0[i] * 16), int(y0[i] * 16)), (int(x1[i] * 16), int(y1[i] * 16)),
                         tuple(float(c * b[i]) for c in col), th, cv2.LINE_AA, 4)
            else:
                r = 0.6 + 1.4 * b[i]
                cv2.circle(lay, (int(x0[i] * 16), int(y0[i] * 16)), int(r * 16), tuple(float(c * b[i]) for c in col),
                           -1, cv2.LINE_AA, 4)
        if warp > 0.01:
            lay = lay + cv2.GaussianBlur(lay, (0, 0), 2.2) * (0.9 * warp) * np.array([0.7, 0.85, 1.25], np.float32)
        return img + lay * streak_gain

    def flash(self, k):
        out = np.zeros((H, W, 3), np.float32)
        for c in (FLASH_IN, FLASH_OUT):
            a = math.exp(-((k - c) / 3.2) ** 2)
            if a < 0.003:
                continue
            r2 = ((self.xx - W / 2) / 210) ** 2 + ((self.yy - H / 2) / 150) ** 2
            bloom = np.exp(-r2)
            line = np.exp(-((self.yy - H / 2) / 5.5) ** 2) * np.exp(-((self.xx - W / 2) / 760) ** 2)
            out += (bloom[..., None] * np.array([190, 220, 255], np.float32) * 1.1 +
                    line[..., None] * np.array([210, 230, 255], np.float32) * 1.3) * a
        return out

    def width(self, i, k):
        t = (k - (FIRST + i * STEP)) / LIFE
        if t < 0 or t > 1:
            return None
        return PW0 * (PW1 / PW0) ** t

    def frame(self, k):
        img = self.neb.copy()
        img = self.stars(k, img)
        # the eras, smallest (farthest) first
        live = [(self.width(i, k), i) for i in range(self.n)]
        live = sorted([(w, i) for w, i in live if w is not None])
        gate = seg(k, (24, 38))
        for w, i in live:
            a = smooth((w - FADE_IN[0]) / (FADE_IN[1] - FADE_IN[0])) * (1 - smooth((w - SOLO) / (FADE_OUT - SOLO))) * gate
            if a < 0.003:
                continue
            ang = i * 2.39996 + 0.6
            off = max(0.0, w - 800) * 0.12
            cx = W / 2 + math.cos(ang) * off; cy = H / 2 + math.sin(ang) * off * 0.6
            s = w / PW1
            M = np.float32([[s, 0, cx - w / 2], [0, s, cy - w * 9 / 32]])
            interp = cv2.INTER_AREA if s < 0.7 else cv2.INTER_LINEAR
            lay = cv2.warpAffine(self.panels[i], M, (W, H), flags=interp)
            msk = cv2.warpAffine(self.pmask, M, (W, H), flags=cv2.INTER_LINEAR) * a
            rim = cv2.warpAffine(self.prim, M, (W, H), flags=cv2.INTER_LINEAR) * a
            lay = lay + rim[..., None] * np.array([150, 190, 255], np.float32) * 0.5
            img = img * (1 - msk[..., None]) + lay * msk[..., None]
        # streaks pass over the panels too, faintly, so the panels sit inside the warp
        if self.v[min(k, N - 1)] > 0.02:
            img = self.stars(k, img, streak_gain=0.22)
        img = img + self.flash(k)
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        ta = min(1.0, (1 - seg(k, T_TITLE_OUT)) + seg(k, T_TITLE_IN))
        if ta > 0.001:
            for im, y in ((self.logo, self.ty), (self.sub, self.ty + self.logo.height + 30)):
                t2 = im.copy(); t2.putalpha(t2.getchannel("A").point(lambda v: round(v * ta)))
                out.alpha_composite(t2, (round(W / 2 - t2.width / 2), y))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
    print("stills", sc.n, "frames", N, "seconds", N * MS / 1000, "star periods", round(sc.travel[-1] / ZD, 3))
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            sc.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [sc.frame(k) for k in range(N)]
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")] if "--frames" in sys.argv else None
    render(sys.argv[1], sys.argv[2], only)
