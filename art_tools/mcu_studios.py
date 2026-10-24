"""MCU card on the Marvel Studios logo (official SVG from TMDB): the logo on black with THE COLLECTION under it.
Hover in the spirit of the studio intro: film frames start flipping inside the MARVEL letters, the camera dives into
the L until the frames fill the screen and the films flip by in release order, then pulls back out, the letters turn
white again with a light sweep over the red, and the subtitle returns. Seamless loop (first frame = cover).
The SVG is re-rendered for every frame through a moving viewBox, so the letters stay sharp at any zoom.
usage: python3 art_tools/mcu_studios.py SRC_DIR OUT_DIR [--frames a,b,c]
  SRC_DIR: marvel-studios.svg, Oswald-VF.ttf, stills/NN_*.jpg (one official backdrop per film, release order)
"""
import glob, io, math, os, re, sys
import numpy as np
import cairosvg
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 260
SS = 2
RED = np.array([229, 11, 20], np.float32)          # the logo's own red


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return smooth((k - a) / max(1, b - a))


class Logo:
    """the SVG split into three masks (red box, MARVEL letters, STUDIOS + rules), rendered through any window"""

    def __init__(self, path):
        svg = open(path).read()
        self.vb = [float(v) for v in re.search(r'viewBox="([^"]*)"', svg).group(1).split()]
        svg = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r"\1", svg, count=1)
        svg = svg.replace("<svg ", '<svg preserveAspectRatio="none" ', 1)

        def variant(keep):
            m = {"#e50b14": "none", "#ffffff": "none", "#000000": "none"}; m.update(keep)
            return re.sub(r"fill:(#[0-9a-fA-F]{6})", lambda g: "fill:" + m.get(g.group(1).lower(), "none"), svg)
        self.v = {"letters": variant({"#ffffff": "#ffffff", "#e50b14": "#000000"}),
                  "box": variant({"#e50b14": "#ffffff", "#ffffff": "#000000"}),
                  "studios": variant({"#000000": "#ffffff"})}

    def masks(self, window, w, h):
        out = {}
        for k, s in self.v.items():
            s = re.sub(r'viewBox="[^"]*"', 'viewBox="%.6f %.6f %.6f %.6f"' % window, s, count=1)
            png = cairosvg.svg2png(bytestring=s.encode(), output_width=w, output_height=h, background_color="black")
            a = np.asarray(Image.open(io.BytesIO(png)).convert("L"), np.float32) / 255
            out[k] = a.reshape(h // SS, SS, w // SS, SS).mean((1, 3))
        return out


class Scene:
    def __init__(self, src):
        self.logo = Logo(os.path.join(src, "marvel-studios.svg"))
        vx, vy, vw, vh = self.logo.vb
        self.k = 960 / vw                                   # logo 960 px wide on the cover
        self.o = (W / 2 - vw * self.k / 2 - vx * self.k, 325 - vh * self.k / 2 - vy * self.k)
        self.stills = []
        for f in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            im = Image.open(f).convert("RGB")
            k = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            self.stills.append(np.asarray(im.crop((x0, y0, x0 + W, y0 + H)), np.float32))
        self.sub = self.text_line("THE COLLECTION", os.path.join(src, "Oswald-VF.ttf"), 400, 26, 16, (232, 232, 235))
        self.sub_y = 325 + vh * self.k / 2 + 46
        self.anchor = self.find_stem()
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / W * 1.5) ** 2 + ((y - 310) / H * 1.9) ** 2)
        self.bg = 7 + np.exp(-(d / 0.42) ** 2)[..., None] * np.array([26, 5, 6], np.float32)
        self.cover_masks = self.logo.masks(self.window(1.0, self.anchor), W * SS, H * SS)

    def window(self, s, c):
        """viewBox for zoom s about the anchor, with the anchor shown at screen point c"""
        A = self.anchor
        x0 = ((0 - c[0]) / s + A[0] - self.o[0]) / self.k
        y0 = ((0 - c[1]) / s + A[1] - self.o[1]) / self.k
        return (x0, y0, W / (s * self.k), H / (s * self.k))

    def find_stem(self):
        """the middle of the L's stem, in cover screen pixels"""
        self.anchor = (W / 2, H / 2)
        m = self.logo.masks(self.window(1.0, self.anchor), W * SS, H * SS)["letters"]
        cols = np.nonzero(m.max(0) > 0.5)[0]
        rows = np.nonzero(m.max(1) > 0.5)[0]
        y0, y1 = rows.min(), rows.max()
        # walk the columns from the right: the L's stem is the last run of columns full of ink top to bottom
        full = [x for x in range(cols.min(), cols.max() + 1) if m[y0 + 3:y1 - 3, x].mean() > 0.97]
        runs, cur = [], [full[0]]
        for x in full[1:]:
            if x == cur[-1] + 1: cur.append(x)
            else: runs.append(cur); cur = [x]
        runs.append(cur)
        stem = runs[-1]
        return ((stem[0] + stem[-1]) / 2, (y0 + y1) / 2)

    def text_line(self, text, font, wght, size, track, color):
        f = ImageFont.truetype(font, size * 2); f.set_variation_by_axes([wght])
        ws = [f.getlength(c) for c in text]
        im = Image.new("RGBA", (round(sum(ws) + track * 2 * len(text)) + 20, size * 3), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); x = 10
        for c, w in zip(text, ws):
            d.text((x, size * 2.4), c, font=f, fill=color + (255,), anchor="ls"); x += w + track * 2
        im = im.crop(im.getbbox())
        return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)

    def frame(self, k):
        n = len(self.stills)
        to_frames = seg(k, 12, 30) * (1 - seg(k, 218, 238))
        dive = seg(k, 32, 76) * (1 - seg(k, 176, 220))
        sub_a = min(1.0, (1 - seg(k, 14, 34)) + seg(k, 228, 252))
        s = math.exp(math.log(60) * dive ** 1.7)
        A = self.anchor
        c = (A[0] + (W / 2 - A[0]) * dive, A[1] + (H / 2 - A[1]) * dive)
        m = self.cover_masks if s == 1.0 and c == A else self.logo.masks(self.window(s, c), W * SS, H * SS)
        idx = min(n - 1, int((k - 72) / (180 - 72) * n)) if 72 <= k < 180 else (k // 2) % n
        still = self.stills[idx]
        img = self.bg.copy()
        # red box, with a light sweep when the letters settle
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        red = RED * (1.06 - 0.12 * np.clip((y - 200) / 220, 0, 1))[..., None]
        sh = seg(k, 222, 246)
        if 0 < sh < 1:
            sx = -300 + (W + 600) * sh
            band = np.exp(-(((x - sx) + (y - 300) * 0.4) / 40) ** 2)
            red = red + band[..., None] * np.array([255, 170, 160], np.float32) * 0.5
        img = img * (1 - m["box"][..., None]) + red * m["box"][..., None]
        white = np.full((H, W, 3), 246, np.float32)
        if 0 < sh < 1:
            white = white + band[..., None] * 9
        let = white * (1 - to_frames) + still * to_frames
        img = img * (1 - m["letters"][..., None]) + let * m["letters"][..., None]
        img = img * (1 - m["studios"][..., None]) + white * m["studios"][..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        if sub_a > 0.001:
            t = self.sub.copy(); t.putalpha(t.getchannel("A").point(lambda v: round(v * sub_a)))
            out.alpha_composite(t, (round(W / 2 - t.width / 2), round(self.sub_y)))
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
