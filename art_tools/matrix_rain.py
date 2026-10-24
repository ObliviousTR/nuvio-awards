"""Matrix card: the digital rain on black, THE MATRIX title in its green glow and THE COLLECTION under it.
Hover: the rain wakes up, the camera dives into the code, and inside it the films surface out of the falling glyphs -
the bullet-time lean, the trio, the stopped bullets, the Animatrix, the rain fight, Resurrections - then the code pulls
back out and settles into the title again. Seamless loop: every column falls a whole number of times per loop and the
glyph flicker repeats with the loop.
Glyphs: katakana and digits from M PLUS 1 Code (SIL OFL), mirrored like the film's; title: The Matrix title
logo on TMDB; stills: official backdrops on TMDB.
usage: python3 art_tools/matrix_rain.py SRC_DIR OUT_DIR [--frames a,b]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS = 1280, 720, 512, 288, 40
N = 250
CS0, CS1 = 18, 42                       # cell size on the cover, and deep in the code
STILLS = ["603_6.jpg", "603_3.jpg", "604_1.jpg", "55931_2.jpg", "605_6.jpg", "624860_3.jpg"]
GREEN = np.array([70, 255, 110], np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return smooth((k - a) / max(1, b - a))


class Rain:
    def __init__(self, font_path, cols=200, rows=120, seed=7):
        chars = [chr(c) for c in range(0x30A2, 0x30F3) if c not in (0x30EE, 0x30F0, 0x30F1)] + list("0123456789Z:.=*+-<>|")
        f = ImageFont.truetype(font_path, 88); f.set_variation_by_axes([500])
        self.atlas_hi = []
        for ch in chars:
            m = Image.new("L", (96, 96), 0)
            ImageDraw.Draw(m).text((48, 50), ch, font=f, fill=255, anchor="mm")
            self.atlas_hi.append(m.transpose(Image.FLIP_LEFT_RIGHT))
        self.ng = len(chars)
        self.cache = {}
        rng = np.random.default_rng(seed)
        self.cols, self.rows = cols, rows
        self.L = rng.integers(10, 34, cols)                       # trail length
        self.P = rows // 4 + self.L + rng.integers(0, 22, cols)  # one fall, in cells (columns repeat down the grid)
        self.m = rng.integers(1, 4, cols)                        # falls per loop
        self.ph = rng.uniform(0, 1, cols)
        self.gl = rng.integers(0, self.ng, (rows, cols, 50))     # glyph per cell for each flicker step
        self.fl = rng.integers(1, 6, (rows, cols))               # some cells flicker faster

    def atlas(self, cs):
        if cs not in self.cache:
            self.cache[cs] = np.stack([np.asarray(a.resize((cs, cs), Image.LANCZOS), np.float32) / 255 for a in self.atlas_hi])
        return self.cache[cs]

    def field(self, k, r0, r1, c0, c1):
        """brightness (0..1, head = 1) and glyph index for the cells rows r0..r1, cols c0..c1 at frame k"""
        rr = np.arange(r0, r1)[:, None] % self.rows
        cc = np.arange(c0, c1)[None, :] % self.cols
        P, L = self.P[cc], self.L[cc]
        head = (self.ph[cc] + k / N * self.m[cc]) * P
        d = (head - rr) % P
        b = np.where(d < L, np.clip(1 - d / L, 0, 1) ** 1.6, 0.0)
        step = ((k // 5) * self.fl[rr, cc]) % 50
        g = self.gl[rr, cc, step]
        return b, g, d < 1


class Scene:
    def __init__(self, src):
        self.rain = Rain(os.path.join(src, "MPLUS1Code.ttf"))
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA")
        lg = lg.crop(lg.getbbox())
        self.logo = lg
        self.stills = []
        for f in STILLS:
            im = Image.open(os.path.join(src, f)).convert("RGB")
            k = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            self.stills.append(np.asarray(im.crop((x0, y0, x0 + W, y0 + H)), np.float32))
        f = ImageFont.truetype(os.path.join(src, "MPLUS1Code.ttf"), 46); f.set_variation_by_axes([500])
        txt = "THE COLLECTION"; tr = 24
        m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 20, 70), 0)
        d = ImageDraw.Draw(m); x = 10
        for c in txt:
            d.text((x, 52), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox())
        self.sub = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)

    def rain_layer(self, k, cs, bright, still=None, mix=0.0):
        """the code at cell size cs, zoomed about the screen centre"""
        A = self.rain.atlas(cs)
        cx, cy = W / 2, H / 2
        # global grid: column j sits at cx + (j - J0) * cs, with J0 the column under the centre
        J0, I0 = self.rain.cols // 2, self.rain.rows // 2
        c0 = J0 - math.ceil(cx / cs) - 1; c1 = J0 + math.ceil(cx / cs) + 2
        r0 = I0 - math.ceil(cy / cs) - 1; r1 = I0 + math.ceil(cy / cs) + 2
        b, g, hd = self.rain.field(k - k % 2, r0, r1, c0, c1)   # the code moves on every other frame (lighter file)
        R, C = b.shape
        if still is not None and mix > 0:
            # sample the still at the cell centres: the picture shows through the glyphs
            ys = np.clip(((np.arange(r0, r1) - I0) * cs + cy + cs / 2).astype(int), 0, H - 1)
            xs = np.clip(((np.arange(c0, c1) - J0) * cs + cx + cs / 2).astype(int), 0, W - 1)
            lum = (still[ys][:, xs] @ np.array([0.3, 0.55, 0.15], np.float32)) / 255
            b = b * (1 - mix) + mix * np.clip(b * (0.35 + 0.65 * lum) + 0.5 * lum ** 1.8, 0, 1)
        tiles = A[g] * (b * bright)[..., None, None]                 # R, C, cs, cs
        img = tiles.transpose(0, 2, 1, 3).reshape(R * cs, C * cs)
        heads = (A[g] * hd[..., None, None]).transpose(0, 2, 1, 3).reshape(R * cs, C * cs) * bright
        ox = round(cx + (c0 - J0) * cs); oy = round(cy + (r0 - I0) * cs)
        crop = lambda a: a[-oy:-oy + H, -ox:-ox + W]
        return crop(img), crop(heads)

    def frame(self, k):
        wake = seg(k, 14, 40) * (1 - seg(k, 206, 236))
        dive = seg(k, 40, 82) * (1 - seg(k, 196, 232))
        cs = int(round(CS0 * (CS1 / CS0) ** dive))
        bright = 0.55 + 0.45 * wake
        # which film, and how strongly it shows
        n = len(self.stills); jt = np.clip((k - 76) / (204 - 76), 0, 0.9999) * n
        i = int(jt); f = jt - i
        mix = seg(k, 72, 92) * (1 - seg(k, 196, 214)) * (1 - 0.85 * (smooth((f - 0.82) / 0.18) if i < n - 1 else 0)) \
            * (1 - 0.85 * (1 - smooth(f / 0.18)) if i > 0 else 1)
        still = self.stills[i]
        lum, heads = self.rain_layer(k, cs, bright, still if mix > 0 else None, mix)
        img = np.zeros((H, W, 3), np.float32)
        img += lum[..., None] * GREEN + heads[..., None] * np.array([150, 120, 140], np.float32)
        # a dim green-tinted picture under the code while a film is showing
        if mix > 0:
            st = still @ np.array([0.3, 0.55, 0.15], np.float32)
            img += (st[..., None] / 255) ** 1.1 * np.array([40, 190, 80], np.float32) * mix * 1.1
        glow = ndimage.gaussian_filter(lum, 2.2)
        img += glow[..., None] * GREEN * 0.45
        # title: dark pocket in the rain behind it, then the logo, scaling with the dive
        ta = (1 - seg(k, 40, 62)) + seg(k, 208, 234)
        ta = min(1.0, ta)
        if ta > 0.001:
            z = (cs / CS0)
            lw = 560 * z
            lg = self.logo.resize((round(lw), round(self.logo.height * lw / self.logo.width)), Image.LANCZOS)
            cyl = H / 2 - 18 + (H / 2 - 18 - H / 2) * (z - 1)
            x0, y0 = round(W / 2 - lg.width / 2), round(cyl - lg.height / 2)
            pocket = Image.new("L", (W, H), 0)
            pa = lg.getchannel("A").filter(ImageFilter.MaxFilter(9))
            pocket.paste(pa, (x0, y0), pa)
            pocket = np.asarray(pocket.filter(ImageFilter.GaussianBlur(26)), np.float32) / 255
            img *= (1 - 0.85 * np.clip(pocket * 1.6, 0, 1) * ta)[..., None]
            out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").convert("RGBA")
            pulse = 0.5 + 0.5 * math.sin(math.pi * seg(k, 14, 40)) * (k < 60)
            gl = Image.new("RGBA", lg.size, (60, 255, 110, 0)); gl.putalpha(lg.getchannel("A").point(lambda v: round(v * 0.55 * ta * (0.7 + 0.6 * pulse))))
            pad = 40; glb = Image.new("RGBA", (lg.width + 2 * pad, lg.height + 2 * pad), (0, 0, 0, 0)); glb.alpha_composite(gl, (pad, pad))
            out.alpha_composite(glb.filter(ImageFilter.GaussianBlur(12)), (x0 - pad, y0 - pad))
            l2 = lg.copy(); l2.putalpha(lg.getchannel("A").point(lambda v: round(v * ta)))
            out.alpha_composite(l2, (x0, y0))
            sa = (1 - seg(k, 16, 36)) + seg(k, 226, 248); sa = min(1.0, sa)
            if sa > 0.001 and z < 1.01:
                s = Image.new("RGBA", self.sub.size, (120, 255, 150, 0)); s.putalpha(self.sub.point(lambda v: round(v * sa)))
                out.alpha_composite(s, (round(W / 2 - s.width / 2), round(y0 + lg.height + 22)))
            return out.convert("RGB")
        return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


def render(src, out, only=None):
    sc = Scene(src)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            sc.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [sc.frame(k) for k in range(N)]
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=66)
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
