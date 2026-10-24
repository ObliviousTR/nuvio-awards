"""DC card on the DC Studios logo (official SVG from TMDB): the bullet and STUDIOS on a dark night blue, THE COLLECTION
under it. Hover: film frames start flipping in the white of the bullet around the DC letters, the camera dives into
that white until the frames fill the screen and the films and series flip by in release order, then it pulls back out,
the white returns with a light sweep over the blue, and the subtitle comes back. Seamless loop (first frame = cover).
The SVG is re-rendered for every frame through a moving viewBox, so it stays sharp at any zoom.
usage: python3 art_tools/dc_studios.py SRC_DIR OUT_DIR [--frames a,b,c]
  SRC_DIR: dc-studios.svg, Oswald-VF.ttf, stills/NN_*.jpg (one official backdrop per title, release order)
"""
import glob, io, math, os, re, sys
import numpy as np
import cairosvg
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 260
SS = 2
BLUE = np.array([2, 127, 193], np.float32)
DISC_C, LETTER_R = (198.5, 198.5), 108.5            # bullet centre and the inner white circle, in SVG units


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return smooth((k - a) / max(1, b - a))


class Logo:
    def __init__(self, path):
        svg = open(path).read()
        self.vb = [float(v) for v in re.search(r'viewBox="([^"]*)"', svg).group(1).split()]
        svg = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r"\1", svg, count=1)
        svg = svg.replace("<svg ", '<svg preserveAspectRatio="none" ', 1)
        paths = list(re.finditer(r"<path\b[^>]*?/>", svg, re.S))

        def only(keep):
            s = svg
            for j in range(len(paths) - 1, -1, -1):
                p = paths[j]
                s = s[:p.start()] + (re.sub(r"fill:#[0-9a-fA-F]{6}", "fill:#ffffff", p.group(0)) if j in keep else "") + s[p.end():]
            return s
        self.v = {"disc": only({0}), "blue": only({1}), "studios": only(set(range(2, len(paths))))}

    def masks(self, window, w, h):
        out = {}
        for k, s in self.v.items():
            s = re.sub(r'viewBox="[^"]*"', 'viewBox="%.6f %.6f %.6f %.6f"' % window, s, count=1)
            png = cairosvg.svg2png(bytestring=s.encode(), output_width=w, output_height=h, background_color="black")
            a = np.asarray(Image.open(io.BytesIO(png)).convert("L"), np.float32) / 255
            out[k] = a.reshape(h // SS, SS, w // SS, SS).mean((1, 3))
        x0, y0, ww, hh = window
        y, x = np.mgrid[0:h // SS, 0:w // SS].astype(np.float32)
        ux = x0 + (x + 0.5) / (w // SS) * ww; uy = y0 + (y + 0.5) / (h // SS) * hh
        r = np.sqrt((ux - DISC_C[0]) ** 2 + (uy - DISC_C[1]) ** 2)
        inner = np.clip((LETTER_R - r) / (ww / (w // SS)) + 0.5, 0, 1)    # 1 inside the inner white circle
        out["letters"] = out["blue"] * inner
        out["ring"] = out["blue"] * (1 - inner)
        out["white"] = np.clip(out["disc"] - out["blue"], 0, 1)
        out["portal"] = out["white"] * inner                                # the white around the letters
        return out


class Scene:
    def __init__(self, src):
        self.logo = Logo(os.path.join(src, "dc-studios.svg"))
        vx, vy, vw, vh = self.logo.vb
        self.k = 900 / vw
        self.cy = 342
        self.o = (W / 2 - vw * self.k / 2 - vx * self.k, self.cy - vh * self.k / 2 - vy * self.k)
        self.stills = []
        for f in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            im = Image.open(f).convert("RGB")
            k = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            self.stills.append(np.asarray(im.crop((x0, y0, x0 + W, y0 + H)), np.float32))
        # THE COLLECTION under STUDIOS, spread across the width of its rules (SVG x 436..1288, lower rule ends at y 327)
        x0, x1 = self.o[0] + 436 * self.k, self.o[0] + 1288 * self.k
        self.sub = self.justified("THE COLLECTION", os.path.join(src, "Oswald-VF.ttf"), 500, 30, x1 - x0, (240, 244, 250))
        self.sub_x, self.sub_y = x0, self.o[1] + 327 * self.k + 16
        self.anchor, r_px = self.find_portal()
        self.s_max = max(30.0, 820 / r_px)
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / W * 1.5) ** 2 + ((y - self.cy) / H * 1.9) ** 2)
        self.bg = np.array([5, 7, 12], np.float32) + np.exp(-(d / 0.45) ** 2)[..., None] * np.array([4, 22, 44], np.float32)
        self.cover_masks = self.logo.masks(self.window(1.0, self.anchor), W * SS, H * SS)

    def window(self, s, c):
        A = self.anchor
        return (((0 - c[0]) / s + A[0] - self.o[0]) / self.k, ((0 - c[1]) / s + A[1] - self.o[1]) / self.k,
                W / (s * self.k), H / (s * self.k))

    def find_portal(self):
        """the roomiest spot of white around the letters (cover pixels) and how much room it has"""
        self.anchor = (W / 2, H / 2)
        m = self.logo.masks(self.window(1.0, self.anchor), W * 4, H * 4)["portal"]
        big = np.asarray(Image.fromarray((m * 255).astype("uint8")).resize((W * 2, H * 2), Image.BILINEAR)) > 200
        dt = ndimage.distance_transform_edt(big)
        y, x = np.unravel_index(np.argmax(dt), dt.shape)
        return (x / 2, y / 2), dt[y, x] / 2

    def justified(self, text, font, wght, size, width, color):
        """letters spread evenly so the line is exactly `width` px wide"""
        f = ImageFont.truetype(font, size * 4); f.set_variation_by_axes([wght])
        ws = [f.getlength(c) for c in text]
        boxes = [f.getbbox(c) for c in text]
        ink = sum(ws) - boxes[0][0] - (ws[-1] - boxes[-1][2])
        gap = (width * 4 - ink) / (len(text) - 1) - 0          # extra space between letter advances
        extra = (width * 4 - ink) / (len(text) - 1)
        im = Image.new("RGBA", (round(width * 4) + 8, size * 6), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); x = -boxes[0][0]
        for c, w in zip(text, ws):
            d.text((x, size * 4.6), c, font=f, fill=color + (255,), anchor="ls"); x += w + extra
        bb = im.getbbox(); im = im.crop((0, bb[1], im.width, bb[3]))
        return im.resize((round(im.width / 4), round(im.height / 4)), Image.LANCZOS)

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
        dive = seg(k, 32, 78) * (1 - seg(k, 174, 220))
        sub_a = min(1.0, (1 - seg(k, 14, 34)) + seg(k, 228, 252))
        s = math.exp(math.log(self.s_max) * dive ** 1.6)
        A = self.anchor
        c = (A[0] + (W / 2 - A[0]) * dive, A[1] + (H / 2 - A[1]) * dive)
        m = self.cover_masks if dive == 0 else self.logo.masks(self.window(s, c), W * SS, H * SS)
        idx = min(n - 1, int((k - 74) / (178 - 74) * n)) if 74 <= k < 178 else (k // 2) % n
        still = self.stills[idx]
        img = self.bg.copy()
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        sh = seg(k, 222, 246)
        band = np.exp(-(((x - (-300 + (W + 600) * sh)) + (y - self.cy) * 0.4) / 40) ** 2) if 0 < sh < 1 else 0
        blue = BLUE * (1.08 - 0.16 * np.clip((y - (self.cy - 140)) / 280, 0, 1))[..., None] + \
            (band[..., None] * np.array([150, 210, 255], np.float32) * 0.55 if 0 < sh < 1 else 0)
        white = np.full((H, W, 3), 247, np.float32)
        # outer white of the bullet (thin rim) stays white; the white around the letters becomes the window
        rim = np.clip(m["white"] - m["portal"], 0, 1)
        img = img * (1 - rim[..., None]) + white * rim[..., None]
        win = white * (1 - to_frames) + still * to_frames
        img = img * (1 - m["portal"][..., None]) + win * m["portal"][..., None]
        bl = np.clip(m["ring"] + m["letters"], 0, 1)
        img = img * (1 - bl[..., None]) + blue * bl[..., None]
        img = img * (1 - m["studios"][..., None]) + white * m["studios"][..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        if sub_a > 0.001:
            t = self.sub.copy(); t.putalpha(t.getchannel("A").point(lambda v: round(v * sub_a)))
            out.alpha_composite(t, (round(self.sub_x), round(self.sub_y)))
        return out.convert("RGB")


def render(src, out, only=None):
    sc = Scene(src)
    print("portal", [round(v) for v in sc.anchor], "zoom", round(sc.s_max, 1))
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
