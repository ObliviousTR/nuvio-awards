"""Star Trek card: deep space, the STAR TREK wordmark and THE COLLECTION under it (Antonio, the LCARS-style face).
Hover (10 s): the title fades, the stars start to stream past and the ship jumps to warp with a flash. At warp we fly
past the eras: their people and their ships stand in space beside our path, left and right, come up out of the
distance and slide past us and out of frame - Spock and the first Enterprise, Khan, Picard and the Enterprise-D,
Deep Space Nine and Sisko, Voyager and Seven of Nine, the Kelvin Enterprise, Burnham, Picard, Pike. Nothing is
framed, nothing cuts; we move, they stay. The ship drops out of warp with a second flash, the stars settle where they
started and the title returns. First frame = last frame = cover.
One look for everything: navy space, cool light, the cut-outs graded down to a shared palette and rim-lit by the warp.
usage: python3 art_tools/startrek_warp.py SRC_DIR OUT_DIR [--frames a,b]
  SRC_DIR: logo.png (STAR TREK wordmark), Antonio.ttf, elements/NN_name.png (cut-outs, transparent background)
"""
import glob, math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 250                                         # 10.0 s
F = 640.0                                       # focal length (px)
NSTAR, ZD = 2200, 1.0                           # stars and the depth they wrap over

T_TITLE_OUT = (6, 20)
T_TITLE_IN = (220, 238)
FLASH_IN, FLASH_OUT = 36, 214                   # the jump to warp and the drop out of it
# star speed (depth units per frame): rest, impulse, warp, rest; scaled so the loop's travel is whole periods
SPEED = [(0, 0.0), (8, 0.0), (30, 0.012), (40, 0.11), (204, 0.11), (220, 0.0), (N, 0.0)]

# the elements, in the order we pass them: file stem, side (-1 left, +1 right), height above the path (world units,
# negative = up), size (world units: height for people, width for ships)
ELEMENTS = [
    ("spock", -1, 0.10, 0.78), ("enterprise", 1, -0.52, 0.85),
    ("khan", 1, 0.10, 0.80), ("enterprise_d", -1, -0.54, 1.0),
    ("picard_tng", -1, 0.12, 0.80), ("ds9", 1, -0.54, 0.95),
    ("sisko", 1, 0.10, 0.74), ("voyager", -1, -0.52, 0.85),
    ("seven", -1, 0.12, 0.78), ("enterprise_kelvin", 1, -0.52, 0.95),
    ("burnham", 1, 0.04, 0.95), ("picard", -1, 0.10, 0.80),
    ("pike", 1, 0.10, 0.80),
]
SHIPS = {"enterprise", "enterprise_d", "ds9", "voyager", "enterprise_kelvin"}
X_PEOPLE, X_SHIPS = 0.56, 0.22                   # people stand beside the path, ships pass over it
V = 0.062                                        # how fast we pass them (depth units per frame)
PASS0, PASS_STEP = 60, 11.4                     # frame we are level with the first (depth 1), frames between
Z_FAR, Z_SHOW = 3.1, 2.4                         # born invisible in the distance, fully there from Z_SHOW
NAVY = np.array([8, 12, 26], np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    return smooth((k - ab[0]) / max(1, ab[1] - ab[0]))


def speed_raw(k):
    for (a, va), (b, vb) in zip(SPEED, SPEED[1:]):
        if a <= k < b:
            return va + (vb - va) * smooth((k - a) / (b - a))
    return 0.0


def grade(rgb, people):
    """The shared palette: most of the colour taken out, shadows pulled to navy, highlights to a cool white. A little
    of each era's own colour stays (Spock's blue, Pike's gold) so they still read."""
    lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None] / 255
    lo, hi = NAVY * 1.2, np.array([228, 236, 255], np.float32)
    duo = lo + (hi - lo) * np.clip(lum, 0, 1) ** 0.95
    keep = 0.42 if people else 0.3
    return duo * (1 - keep) + rgb * keep


def soft_cut_edges(a):
    """Where a cut-out was cut by the edge of its photo (the bottom of a bust, a shoulder), fade that side out instead
    of leaving a straight line."""
    h, w = a.shape
    out = a.copy()
    for side in ("top", "bottom", "left", "right"):
        line = {"top": a[:3], "bottom": a[-3:], "left": a[:, :3], "right": a[:, -3:]}[side]
        if (line > 0.5).mean() < 0.06:
            continue
        if side in ("top", "bottom"):
            n = int(h * 0.28); g = np.clip(np.arange(h) / n, 0, 1) if side == "top" else np.clip((h - 1 - np.arange(h)) / n, 0, 1)
            out *= (g * g * (3 - 2 * g))[:, None]
        else:
            n = int(w * 0.22); g = np.clip(np.arange(w) / n, 0, 1) if side == "left" else np.clip((w - 1 - np.arange(w)) / n, 0, 1)
            out *= (g * g * (3 - 2 * g))[None, :]
    return out


class Scene:
    def __init__(self, src):
        rng = np.random.default_rng(7)
        self.sx = rng.uniform(-1.6, 1.6, NSTAR); self.sy = rng.uniform(-1.0, 1.0, NSTAR)
        self.sz0 = rng.uniform(0.02, ZD, NSTAR)
        self.mag = rng.random(NSTAR) ** 2.2
        raw = np.array([speed_raw(k) for k in range(N)])
        periods = max(1, round(raw.sum() / ZD))
        self.v = raw * periods * ZD / raw.sum()
        self.travel = np.concatenate([[0], np.cumsum(self.v)])
        # one-hue space: a deep navy with a soft blue glow round the vanishing point
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        neb = np.zeros((H, W, 3), np.float32) + NAVY * 0.55
        for (cx, cy, rx, ry, col) in ((640, 360, 700, 380, (12, 22, 52)), (430, 250, 420, 230, (8, 16, 40)),
                                      (900, 470, 380, 220, (6, 14, 36))):
            g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
            neb += g[..., None] * np.array(col, np.float32)
        self.neb = neb
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.66)) ** 2)
        self.vig = (1 - 0.38 * np.clip(r - 0.35, 0, 1) ** 1.4).astype(np.float32)
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
        # the elements: graded, soft where they were cut, rim-lit on the side that faces the path
        self.els = []
        for j, (name, side, yw, size) in enumerate(ELEMENTS):
            im = Image.open(os.path.join(src, "elements", f"{name}.png")).convert("RGBA")
            ship = name in SHIPS
            a = np.asarray(im, np.float32)
            rgb, al = a[..., :3], a[..., 3] / 255
            al = soft_cut_edges(al)
            if not ship:                                              # people fade out at the chest, all alike
                hh0 = al.shape[0]; n0 = int(hh0 * 0.34)
                g = np.clip((hh0 - 1 - np.arange(hh0)) / n0, 0, 1); al = al * (g * g * (3 - 2 * g))[:, None]
            rgb = grade(rgb, not ship)
            sh = max(4, int(min(al.shape) * 0.012))
            moved = np.roll(al, sh * side, axis=1)                    # light comes from the path, so from -side
            rim = np.clip(al - moved, 0, 1)
            rim = cv2.GaussianBlur(rim, (0, 0), sh * 0.6) * al
            rgb = rgb + rim[..., None] * np.array([150, 190, 255], np.float32) * 0.9
            hh, ww = al.shape
            world_h = size if not ship else size * hh / ww
            pass_k = PASS0 + j * PASS_STEP
            self.els.append(dict(rgb=np.clip(rgb, 0, 255).astype(np.float32), al=al.astype(np.float32), side=side,
                                 y=yw, h=world_h, x=X_SHIPS if ship else X_PEOPLE, pass_k=pass_k))

    def stars(self, k, img, gain=1.0):
        z = (self.sz0 - self.travel[k]) % ZD + 0.02
        v = self.v[k] if k < N else 0.0
        L = float(np.clip(v * 2.6, 0, 0.5))
        x0 = W / 2 + F * self.sx / z; y0 = H / 2 + F * self.sy / z
        x1 = W / 2 + F * self.sx / (z + L); y1 = H / 2 + F * self.sy / (z + L)
        b = np.clip(self.mag * 1.3 + 0.12, 0, 1) * np.clip(1.25 - z / ZD, 0.35, 1.0)
        lay = np.zeros((H, W, 3), np.float32)
        on = (x0 > -400) & (x0 < W + 400) & (y0 > -400) & (y0 < H + 400)
        warp = min(1.0, v / 0.06)
        for i in np.nonzero(on)[0]:
            c = (225 * b[i], 235 * b[i], 255 * b[i])
            if L > 0.003:
                cv2.line(lay, (int(x0[i] * 16), int(y0[i] * 16)), (int(x1[i] * 16), int(y1[i] * 16)),
                         tuple(ch * (1 - 0.35 * warp) for ch in c), 1, cv2.LINE_AA, 4)
            else:
                cv2.circle(lay, (int(x0[i] * 16), int(y0[i] * 16)), int((0.6 + 1.4 * b[i]) * 16), c, -1, cv2.LINE_AA, 4)
        if warp > 0.01:
            lay = lay + cv2.GaussianBlur(lay, (0, 0), 2.2) * (0.5 * warp) * np.array([0.65, 0.8, 1.2], np.float32)
        return img + lay * gain

    def flash(self, k):
        out = np.zeros((H, W, 3), np.float32)
        for c in (FLASH_IN, FLASH_OUT):
            a = math.exp(-((k - c) / 3.2) ** 2)
            if a < 0.003:
                continue
            bloom = np.exp(-(((self.xx - W / 2) / 210) ** 2 + ((self.yy - H / 2) / 150) ** 2))
            line = np.exp(-((self.yy - H / 2) / 5.5) ** 2) * np.exp(-((self.xx - W / 2) / 760) ** 2)
            out += (bloom[..., None] * np.array([190, 220, 255], np.float32) * 1.1 +
                    line[..., None] * np.array([210, 230, 255], np.float32) * 1.3) * a
        return out

    def frame(self, k):
        img = self.neb.copy()
        img = self.stars(k, img)
        live = []
        for e in self.els:
            z = 1.0 - (k - e["pass_k"]) * V
            if 0.3 < z < Z_FAR:
                live.append((z, e))
        for z, e in sorted(live, key=lambda t: -t[0]):               # far ones first
            hp = F * e["h"] / z
            s = hp / e["al"].shape[0]
            wp = e["al"].shape[1] * s
            cx = W / 2 + e["side"] * F * e["x"] / z
            cy = H / 2 + F * e["y"] / z
            if cx - wp / 2 > W + 10 or cx + wp / 2 < -10:
                continue
            M = np.float32([[s, 0, cx - wp / 2], [0, s, cy - hp / 2]])
            interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
            rgb = cv2.warpAffine(e["rgb"], M, (W, H), flags=interp)
            al = cv2.warpAffine(e["al"], M, (W, H), flags=interp)
            vis = smooth((Z_FAR - z) / (Z_FAR - Z_SHOW))                 # out of the distance
            haze = smooth((z - 1.0) / (Z_FAR - 1.0))                      # far = sunk in the navy
            rgb = rgb * (1 - 0.7 * haze) + NAVY * 1.6 * 0.7 * haze
            img = img * (1 - al[..., None] * vis) + rgb * al[..., None] * vis
        if self.v[min(k, N - 1)] > 0.02:
            img = self.stars(k, img, gain=0.18)                          # the warp streaks over everything, faintly
        img = img + self.flash(k)
        img = img * self.vig[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        ta = min(1.0, (1 - seg(k, T_TITLE_OUT)) + seg(k, T_TITLE_IN))
        if ta > 0.001:
            for im, y in ((self.logo, self.ty), (self.sub, self.ty + self.logo.height + 30)):
                t2 = im.copy(); t2.putalpha(t2.getchannel("A").point(lambda v: round(v * ta)))
                out.alpha_composite(t2, (round(W / 2 - t2.width / 2), y))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
    print("elements", len(sc.els), "frames", N, "star periods", round(sc.travel[-1] / ZD, 3))
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
