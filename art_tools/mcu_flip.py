"""MCU card: big red MARVEL letters, CINEMATIC UNIVERSE and THE COLLECTION on black. Hover in the spirit of the studio
intro: the red gives way to film frames flipping inside the letters, the camera dives into a letter until the frames
fill the screen and the films flip by in release order, then it pulls back out, the frames settle into red letters
again with a sheen, and the subtitle returns. Seamless loop (first frame = cover).
Letters are vector outlines (Anton / Oswald, SIL OFL), filled with OpenCV so they stay sharp at any zoom.
usage: python3 art_tools/mcu_flip.py SRC_DIR OUT_DIR [--frames a,b,c]
  SRC_DIR: Anton-Regular.ttf, Oswald-VF.ttf, stills/NN_*.jpg (one official backdrop per film, release order)
"""
import glob, math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 260
SS = 2
RED = np.array([226, 35, 40], np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return smooth((k - a) / max(1, b - a))


class Word:
    """outline polygons of a word, laid out in screen pixels (y down), centred at (cx, cy) with cap height ch"""

    def __init__(self, text, font, ch, cx, cy, track=0.0):
        fp = FontProperties(fname=font)
        polys, x = [], 0.0
        for c in text:
            tp = TextPath((x, 0), c, size=100, prop=fp)
            polys += [p for p in tp.to_polygons() if len(p) > 2]
            x += TextPath((0, 0), c, size=100, prop=fp).get_extents().x1 + track * 100 + 3
        allp = np.concatenate(polys)
        x0, x1, y0, y1 = allp[:, 0].min(), allp[:, 0].max(), allp[:, 1].min(), allp[:, 1].max()
        k = ch / (y1 - y0)
        self.polys = [np.stack([(p[:, 0] - (x0 + x1) / 2) * k + cx, -(p[:, 1] - (y0 + y1) / 2) * k + cy], -1) for p in polys]
        self.box = ((x0 - (x0 + x1) / 2) * k + cx, cy - ch / 2, (x1 - (x0 + x1) / 2) * k + cx, cy + ch / 2)

    def mask(self, a=(0, 0), s=1.0, c=None):
        """coverage 0..1 at W x H; scaled by s about anchor a, the anchor placed at c"""
        c = a if c is None else c
        m = np.zeros((H * SS, W * SS), np.uint8)
        pts = []
        for p in self.polys:
            q = (np.asarray(c) + (p - np.asarray(a)) * s) * SS
            q = np.clip(q, -1e6, 1e6)
            pts.append(np.round(q * 16).astype(np.int32))
        cv2.fillPoly(m, pts, 255, lineType=cv2.LINE_AA, shift=4)
        return cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


class Scene:
    def __init__(self, src):
        anton = os.path.join(src, "Anton-Regular.ttf")
        self.marvel = Word("MARVEL", anton, 210, W / 2, 300, track=0.04)
        self.stills = []
        for f in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            im = Image.open(f).convert("RGB")
            k = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            self.stills.append(np.asarray(im.crop((x0, y0, x0 + W, y0 + H)), np.float32))
        self.sub1 = self.text_line("CINEMATIC UNIVERSE", os.path.join(src, "Oswald-VF.ttf"), 500, 46, 14, (242, 242, 242))
        self.sub2 = self.text_line("THE COLLECTION", os.path.join(src, "Oswald-VF.ttf"), 300, 21, 12, (200, 200, 204))
        # the anchor of the dive: middle of the L's stem
        Lp = self.marvel.polys[-1] if False else None
        bx = self.marvel.box
        self.anchor = self.find_stem()
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / W * 1.5) ** 2 + ((y - 320) / H * 1.9) ** 2)
        self.bg = 6 + np.exp(-(d / 0.42) ** 2)[..., None] * np.array([30, 6, 7], np.float32)
        self.sheen_x = None

    def find_stem(self):
        m = self.marvel.mask()
        bx = self.marvel.box
        # last letter (L): scan from the right edge for the widest vertical run of ink in the letter's left part
        x1 = int(bx[2]); cols = range(int(x1 - 0.19 * (bx[2] - bx[0])), x1)
        best = None
        for x in cols:
            col = m[int(bx[1]) + 5:int(bx[3]) - 5, x]
            if col.mean() > 0.97:
                best = x if best is None else best
                last = x
        cx = (best + last) / 2 if best is not None else (bx[2] - 40)
        return (cx, (bx[1] + bx[3]) / 2 - 20)

    def text_line(self, text, font, wght, size, track, color):
        f = ImageFont.truetype(font, size * 2); f.set_variation_by_axes([wght])
        ws = [f.getlength(c) for c in text]
        im = Image.new("RGBA", (round(sum(ws) + track * 2 * len(text)) + 20, size * 3), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); x = 10
        for c, w in zip(text, ws):
            d.text((x, size * 2.4), c, font=f, fill=color + (255,), anchor="ls"); x += w + track * 2
        im = im.crop(im.getbbox())
        return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)

    def red_fill(self, k, mask):
        """the red of the letters: lit from above, darker at the foot, and a sheen that runs across when they settle"""
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        bx = self.marvel.box
        v = 1.08 - 0.28 * np.clip((y - bx[1]) / (bx[3] - bx[1]), 0, 1)
        col = RED * v[..., None]
        sh = seg(k, 222, 244)
        if 0 < sh < 1:
            sx = bx[0] - 200 + (bx[2] - bx[0] + 400) * sh
            band = np.exp(-(((x - sx) + (y - 300) * 0.35) / 34) ** 2)
            col = col + band[..., None] * np.array([255, 190, 180]) * 0.55
        return col

    def frame(self, k):
        n = len(self.stills)
        # ---- timeline
        to_frames = seg(k, 12, 30) * (1 - seg(k, 218, 238))            # red -> film frames inside the letters
        dive = seg(k, 32, 76) * (1 - seg(k, 176, 220))                  # 0 letters, 1 inside the L
        subs = (1 - seg(k, 14, 34)) + seg(k, 228, 252)
        subs = min(1.0, subs)
        s = math.exp(math.log(46) * dive ** 1.7)
        a = self.anchor
        c = (a[0] + (W / 2 - a[0]) * dive, a[1] + (H / 2 - a[1]) * dive)
        # which film: fast flipping, in release order through the dive, a quicker pass before and after
        if 72 <= k < 180:
            idx = min(n - 1, int((k - 72) / (180 - 72) * n))
        else:
            idx = (k // 2) % n
        still = self.stills[idx]
        # ---- compose
        m = self.marvel.mask(a, s, c)
        img = self.bg.copy()
        inside = still * (0.82 + 0.18 * dive)                           # frames a touch darker inside small letters
        red = self.red_fill(k, m)
        letter = red * (1 - to_frames) + inside * to_frames
        # thin dark rim so the letters read on bright frames
        img = img * (1 - m[..., None]) + letter * m[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        if subs > 0.001:
            bx = self.marvel.box
            for im, y in ((self.sub1, bx[3] + 30), (self.sub2, bx[3] + 30 + self.sub1.height + 22)):
                t = im.copy(); t.putalpha(t.getchannel("A").point(lambda v: round(v * subs)))
                out.alpha_composite(t, (round(W / 2 - im.width / 2), round(y)))
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
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for m, i in enumerate(range(0, N, N // 16)):
        if m < 16:
            sheet.paste(frames[i].resize((320, 180)), ((m % 4) * 320, (m // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", N, "seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    only = [int(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")] if "--frames" in sys.argv else None
    render(sys.argv[1], sys.argv[2], only)
