"""Studios row: each card opens with a short ident inspired by the studio's own logo animation, then the logo settles
small in the corner while three of the studio's iconic films play behind it (textless key art), a light runs round
the card, and the logo comes back to the middle (seamless loop, 8 s). Cover = the settled ident.
Logos are the studios' own (TMDB company logos, kept in nuvio-art art/logos/studios); the motion is ours.
The film trio moves on every month through each studio's pool (.github/workflows/studio-art.yml -> studio-art).
usage: python3 art_tools/studio_art.py OUT_DIR [titles...]
"""
import io, math, os, random, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import genre_art as g
import kids_art as K
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

W, H = 1280, 720
OW, OH = 512, 288
N = 160
LOGOS = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/art/logos/studios/"


def get_logo(name):
    for _ in range(3):
        try:
            b = urllib.request.urlopen(urllib.request.Request(LOGOS + name, headers={"User-Agent": "nuvio-awards"}), timeout=60).read()
            return Image.open(io.BytesIO(b)).convert("RGBA")
        except Exception:
            continue
    raise RuntimeError("logo " + name)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def out3(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def gradient(top, bottom, w=W, h=H, glow=None):
    col = Image.new("RGB", (1, h))
    for y in range(h):
        f = y / (h - 1)
        col.putpixel((0, y), tuple(round(top[i] + (bottom[i] - top[i]) * f) for i in range(3)))
    im = col.resize((w, h))
    if glow:  # (x, y, radius, colour, strength)
        x, y, r, c, s = glow
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).ellipse((x - r, y - r, x + r, y + r), fill=round(255 * s))
        im = Image.composite(Image.new("RGB", (w, h), c), im, m.filter(ImageFilter.GaussianBlur(r * 0.6)))
    return im


def starfield(im, n=140, seed=3, top=0.8):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(n):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H * top), rnd.uniform(0.6, 1.8)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(60, 190)))
    return im


def tinted(alpha, top=(255, 255, 255), bottom=(205, 222, 245)):
    """A white-to-ice gradient fill in the shape of `alpha`."""
    w, h = alpha.size
    fill = gradient(top, bottom, w, h).convert("RGBA")
    fill.putalpha(alpha)
    return fill


def glow_of(layer, r, col, k):
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, round(v * k)))
    g_ = Image.new("RGBA", layer.size, col + (0,))
    g_.putalpha(a)
    return g_


def alpha_mul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def sweep(layer, p, width=0.18, strength=0.85):
    """A diagonal gleam across the shape of `layer` (p 0..1)."""
    w, h = layer.size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    x = -w * 0.3 + p * w * 1.6
    d.polygon([(x, 0), (x + w * width, 0), (x + w * width - h * 0.5, h), (x - h * 0.5, h)], fill=round(255 * strength))
    m = ImageChops.multiply(m.filter(ImageFilter.GaussianBlur(w * 0.03)), layer.getchannel("A"))
    s = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    s.putalpha(m)
    return s


# ---------------------------------------------------------------- Paramount: stars swoop round the mountain
class Paramount:
    title, accent = "Paramount Pictures", (90, 160, 255)
    pool = [("movie", "The Godfather", 1972), ("movie", "The Truman Show", 1998), ("movie", "Saving Private Ryan", 1998),
            ("movie", "A Quiet Place", 2018), ("movie", "Breakfast at Tiffany's", 1961), ("movie", "Sonic the Hedgehog", 2020),
            ("movie", "Chinatown", 1974), ("movie", "Gladiator II", 2024)]

    def __init__(self):
        from scipy import ndimage as ndi
        src = get_logo("paramount.png")
        a = np.asarray(src)[..., 3] > 40
        lab, n = ndi.label(a)
        sizes = ndi.sum(a, lab, range(1, n + 1))
        k = (H * 0.64) / src.height
        self.k = k
        stars, body = [], np.zeros_like(a)
        objs = ndi.find_objects(lab)
        for i, s in enumerate(sizes, 1):
            if s < 50:
                continue
            sl = objs[i - 1]
            cy, cx = ndi.center_of_mass(lab == i)
            if 1700 < s < 2200:                                 # the stars are the 22 equal small shapes
                stars.append((cx, cy, sl))
            elif cy > src.height * 0.94:
                continue                                        # the TM mark
            else:
                body |= lab == i
        al = Image.fromarray((np.asarray(src)[..., 3] * body).astype(np.uint8))
        bw, bh = round(src.width * k), round(src.height * k)
        self.ox, self.oy = (W - bw) / 2, (H - bh) / 2 + 6
        self.body = tinted(al.resize((bw, bh), Image.LANCZOS))
        star = None
        self.stars = []
        cx0, cy0 = src.width / 2, src.height * 0.56
        for cx, cy, sl in stars:
            crop = src.crop((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)).getchannel("A")
            crop = crop.resize((max(1, round(crop.width * k)), max(1, round(crop.height * k))), Image.LANCZOS)
            ang = math.atan2(cy - cy0, cx - cx0)
            self.stars.append((self.ox + cx * k, self.oy + cy * k, ang, tinted(crop)))
        self.stars.sort(key=lambda s: -s[2])                    # land from the lower left, clockwise over the top
        self.c0 = (self.ox + cx0 * k, self.oy + cy0 * k)
        self.R = np.median([math.hypot(s[0] - self.c0[0], s[1] - self.c0[1]) for s in self.stars])
        self.stage = starfield(gradient((6, 16, 52), (34, 92, 178), glow=(W / 2, H * 1.05, W * 0.45, (90, 150, 230), 0.55)), 160, top=0.95)

    @staticmethod
    def unwrap(a):
        """Ring angle measured the way the stream travels: from the lower right (+) over the top (-pi/2) to the lower
        left (below -pi)."""
        return a if a < 1.2 else a - 2 * math.pi

    def logo(self, t, final=False):
        """The ident at progress t (0..1) as an RGBA layer over the stage."""
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tb = 1.0 if final else out3(t / 0.4)
        if tb > 0:
            b = alpha_mul(self.body, tb)
            off = round((1 - tb) * 50)
            lay.alpha_composite(glow_of(b, 18, (150, 200, 255), 0.6 * tb), (round(self.ox), round(self.oy) + off))
            lay.alpha_composite(b, (round(self.ox), round(self.oy) + off))
            if not final and 0.55 < t < 0.9:
                lay.alpha_composite(sweep(b, (t - 0.55) / 0.35), (round(self.ox), round(self.oy) + off))
        # one stream of stars: every star enters low on the right, sweeps up and over the mountain in a wide curve and
        # tightens into its slot on the ring; the far (left) slots are served first, so the ring closes towards the
        # right while the stream keeps flowing over the stars already parked
        phi0 = 0.95                                     # entry angle (lower right), image coordinates
        order = sorted(range(len(self.stars)), key=lambda j: self.unwrap(self.stars[j][2]))
        far = phi0 - self.unwrap(self.stars[order[0]][2])
        for rank, j in enumerate(order):
            fx, fy, ang, im = self.stars[j]
            phf = self.unwrap(ang)
            dist = phi0 - phf
            start, dur = 0.10 + rank * 0.019, 0.20 + 0.24 * dist / far
            p = 1.0 if final else (t - start) / dur
            if p <= 0:
                continue
            p = min(1.0, p)
            trail = ((0.0, 1.0),) if final or p >= 1 else ((0.0, 1.0), (0.035, 0.55), (0.07, 0.32), (0.11, 0.18), (0.16, 0.08))
            for lag, alpha in trail:
                q = max(0.0, p - lag)
                e = 1 - (1 - q) ** 2.2                    # fast across the sky, easing into the slot
                ph = phi0 - dist * e
                r = self.R * (1 + 1.5 * (1 - e) ** 1.4)
                x, y = self.c0[0] + r * math.cos(ph), self.c0[1] + r * math.sin(ph)
                sc = (0.7 + 0.3 * e) * (1 - 0.35 * lag / 0.16)
                st = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
                st = alpha_mul(st, alpha * min(1.0, q * 6))
                if lag == 0 and p < 1:
                    lay.alpha_composite(glow_of(st, 9, (200, 225, 255), 1.6), (round(x - st.width / 2), round(y - st.height / 2)))
                lay.alpha_composite(st, (round(x - st.width / 2), round(y - st.height / 2)))
        return lay


# ---------------------------------------------------------------- Disney & Pixar: a spark writes the Disney name, PIXAR bounces in
class DisneyPixar:
    title, accent = "Disney & Pixar Animation", (255, 205, 110)
    pool = [("movie", "Encanto", 2021), ("movie", "Tangled", 2010), ("movie", "Soul", 2020), ("movie", "Big Hero 6", 2014),
            ("movie", "Incredibles 2", 2018), ("movie", "Luca", 2021), ("movie", "Wreck-It Ralph", 2012),
            ("movie", "Elemental", 2023)]

    def __init__(self):
        d = get_logo("walt-disney-animation.png")
        d = d.crop(d.getchannel("A").getbbox())
        dw = round(W * 0.62)
        d = d.resize((dw, round(d.height * dw / d.width)), Image.LANCZOS)
        self.disney = tinted(d.getchannel("A"), (255, 255, 255), (232, 238, 255))
        self.dx, self.dy = (W - dw) / 2, H * 0.38 - d.height / 2 - 10
        p = get_logo("pixar.png")
        p = p.crop(p.getchannel("A").getbbox())
        pw = round(W * 0.36)
        k = pw / p.width
        p = p.resize((pw, round(p.height * k)), Image.LANCZOS)
        a = np.asarray(p)[..., 3] > 30
        cols = a.any(0)
        runs, s0 = [], None
        for x, c in enumerate(cols):
            if c and s0 is None:
                s0 = x
            if not c and s0 is not None:
                runs.append((s0, x)); s0 = None
        if s0 is not None:
            runs.append((s0, len(cols)))
        self.px, self.py = (W - pw) / 2, H * 0.71 - p.height / 2
        self.letters = [(x0, tinted(p.crop((x0, 0, x1, p.height)).getchannel("A"), (255, 255, 255), (225, 232, 248)))
                        for x0, x1 in runs]
        self.ph = p.height
        rnd = random.Random(9)
        self.dust = [(rnd.uniform(0, 1), rnd.uniform(-18, 18), rnd.uniform(10, 70), rnd.uniform(1.2, 3.2)) for _ in range(90)]
        self.stage = starfield(gradient((4, 10, 42), (26, 64, 150), glow=(W / 2, H * 1.2, W * 0.42, (240, 170, 110), 0.28)), 130, seed=5)

    def spark(self, u):
        """Position on the spark's arc (u 0..1): up from the lower left, over the Disney name, down to the right."""
        x0, x1 = W * 0.12, W * 0.88
        x = x0 + (x1 - x0) * u
        y = H * 0.58 - math.sin(math.pi * u) * H * 0.40
        return x, y

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        u = 1.0 if final else ease(t / 0.5)
        # the Disney name, revealed behind the spark
        sx, sy = self.spark(u)
        m = Image.new("L", self.disney.size, 0)
        reveal = sx - self.dx
        if final or u >= 1:
            m = Image.new("L", self.disney.size, 255)
        elif reveal > 0:
            ImageDraw.Draw(m).rectangle((0, 0, reveal, self.disney.height), fill=255)
            m = m.filter(ImageFilter.GaussianBlur(12))
        dl = self.disney.copy()
        dl.putalpha(ImageChops.multiply(dl.getchannel("A"), m))
        lay.alpha_composite(glow_of(dl, 14, (255, 220, 150), 0.5), (round(self.dx), round(self.dy)))
        lay.alpha_composite(dl, (round(self.dx), round(self.dy)))
        if not final and t < 0.62:
            dr = ImageDraw.Draw(lay)
            for (pu, dx, fall, r) in self.dust:           # fairy-dust trail that drifts down and fades
                if pu > u:
                    continue
                age = (u - pu) * 2.2
                if age > 1:
                    continue
                x, y = self.spark(pu)
                y += fall * age
                a_ = round(230 * (1 - age))
                dr.ellipse((x + dx - r, y - r, x + dx + r, y + r), fill=(255, 235, 180, a_))
            if u < 1:
                hd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(hd).ellipse((sx - 14, sy - 14, sx + 14, sy + 14), fill=(255, 245, 210, 255))
                lay.alpha_composite(glow_of(hd, 22, (255, 210, 130), 2.2))
                lay.alpha_composite(hd)
        # PIXAR letters drop in and bounce
        for j, (x0, im) in enumerate(self.letters):
            s = 1.0 if final else (t - 0.46 - j * 0.06) / 0.22
            if s <= 0:
                continue
            s = min(1.0, s)
            if s < 0.55:                                  # fall
                f = s / 0.55
                dy, sxk, syk = -(1 - f * f) * H * 0.09, 0.94, 1.08
            elif s < 0.7:                                 # squash
                f = (s - 0.55) / 0.15
                dy, sxk, syk = 0, 1 + 0.16 * math.sin(math.pi * f), 1 - 0.22 * math.sin(math.pi * f)
            elif s < 0.9:                                 # little hop
                f = (s - 0.7) / 0.2
                dy, sxk, syk = -math.sin(math.pi * f) * self.ph * 0.25, 1.0, 1.0
            else:
                dy, sxk, syk = 0, 1.0, 1.0
            w_, h_ = max(1, round(im.width * sxk)), max(1, round(im.height * syk))
            li = im.resize((w_, h_), Image.LANCZOS)
            x = self.px + x0 + im.width / 2 - w_ / 2
            y = self.py + self.ph - h_ + dy
            lay.alpha_composite(alpha_mul(li, min(1.0, s / 0.25)), (round(x), round(y)))
        lt = 1.0 if final else ease((t - 0.82) / 0.14)
        if lt > 0:
            ln = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            half = W * 0.13 * lt
            yy = (self.dy + self.disney.height + self.py) / 2 + 4
            ImageDraw.Draw(ln).line((W / 2 - half, yy, W / 2 + half, yy), fill=(255, 210, 130, 230), width=3)
            lay.alpha_composite(glow_of(ln, 6, (255, 200, 120), 1.2))
            lay.alpha_composite(ln)
        return lay


# ---------------------------------------------------------------- helpers for the rest of the row
def fit_logo(name, w=None, h=None):
    im = get_logo(name)
    im = im.crop(im.getchannel("A").getbbox())
    k = min((w or 1e9) / im.width, (h or 1e9) / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def place(lay, im, cx, cy, a=1.0):
    lay.alpha_composite(alpha_mul(im, a), (round(cx - im.width / 2), round(cy - im.height / 2)))


def scaled(im, k):
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def beam(lay, x0, y0, ang, length, width, col, a):
    """A searchlight beam from (x0, y0) at angle ang (radians, 0 = up), soft edged."""
    if a <= 0:
        return
    b = Image.new("L", (W, H), 0)
    dx, dy = math.sin(ang), -math.cos(ang)
    px, py = -dy, dx
    x1, y1 = x0 + dx * length, y0 + dy * length
    ImageDraw.Draw(b).polygon([(x0 - px * 6, y0 - py * 6), (x0 + px * 6, y0 + py * 6),
                               (x1 + px * width, y1 + py * width), (x1 - px * width, y1 - py * width)], fill=255)
    fade = Image.new("L", (W, H), 0)
    ImageDraw.Draw(fade).ellipse((x0 - length, y0 - length, x0 + length, y0 + length), fill=255)
    fade = fade.filter(ImageFilter.GaussianBlur(length * 0.35))
    b = ImageChops.multiply(b.filter(ImageFilter.GaussianBlur(18)), fade)
    l_ = Image.new("RGBA", (W, H), col + (0,))
    l_.putalpha(b.point(lambda v: round(v * a)))
    lay.alpha_composite(l_)


def clouds(seed, n=26, col=(255, 255, 255)):
    rnd = random.Random(seed)
    m = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(m)
    for _ in range(n):
        x, y = rnd.uniform(0, W * 2), rnd.uniform(H * 0.2, H * 1.9)
        for _k in range(6):
            r = rnd.uniform(60, 170)
            ox, oy = rnd.uniform(-160, 160), rnd.uniform(-40, 40)
            d.ellipse((x + ox - r, y + oy - r * 0.6, x + ox + r, y + oy + r * 0.6), fill=rnd.randint(70, 160))
    m = m.filter(ImageFilter.GaussianBlur(38))
    c = Image.new("RGBA", m.size, col + (0,))
    c.putalpha(m)
    return c


def split_columns(im):
    """Split a logo into its letters (column gaps)."""
    a = np.asarray(im)[..., 3] > 30
    cols = a.any(0)
    runs, s0 = [], None
    for x, c in enumerate(cols):
        if c and s0 is None:
            s0 = x
        if not c and s0 is not None:
            runs.append((s0, x)); s0 = None
    if s0 is not None:
        runs.append((s0, len(cols)))
    return [(x0, im.crop((x0, 0, x1, im.height))) for x0, x1 in runs]


# ---------------------------------------------------------------- A24: a white line opens into the logo
class A24:
    title, accent = "A24", (235, 235, 235)
    pool = [("movie", "Midsommar", 2019), ("movie", "Uncut Gems", 2019), ("movie", "Ex Machina", 2015),
            ("movie", "Lady Bird", 2017), ("movie", "The Green Knight", 2021), ("movie", "Past Lives", 2023),
            ("movie", "The Zone of Interest", 2023), ("movie", "Talk to Me", 2023)]

    def __init__(self):
        self.l = tinted(fit_logo("a24.png", w=W * 0.40).getchannel("A"), (255, 255, 255), (238, 238, 238))
        self.stage = gradient((6, 6, 7), (14, 14, 16))
        rnd = random.Random(2)
        self.grain = [Image.effect_noise((W // 2, H // 2), 40).resize((W, H)) for _ in range(4)]

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cx, cy = W / 2, H / 2
        if final:
            place(lay, self.l, cx, cy)
            return lay
        lw = ease(t / 0.3) * self.l.width * 1.1
        la = 1 - ease((t - 0.45) / 0.15)
        if lw > 2 and la > 0:
            ln = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ln).line((cx - lw / 2, cy, cx + lw / 2, cy), fill=(255, 255, 255, 255), width=3)
            lay.alpha_composite(alpha_mul(glow_of(ln, 6, (255, 255, 255), 1.4), la))
            lay.alpha_composite(alpha_mul(ln, la))
        o = ease((t - 0.28) / 0.32)
        if o > 0:
            m = Image.new("L", self.l.size, 0)
            hh = self.l.height / 2 * o
            ImageDraw.Draw(m).rectangle((0, self.l.height / 2 - hh, self.l.width, self.l.height / 2 + hh), fill=255)
            li = self.l.copy()
            li.putalpha(ImageChops.multiply(li.getchannel("A"), m))
            fr = round(10 * (1 - ease((t - 0.45) / 0.4)))                 # colour fringe settles
            if fr > 0:
                for col, dx in (((255, 40, 60), -fr), ((40, 220, 255), fr)):
                    c_ = Image.new("RGBA", li.size, col + (0,))
                    c_.putalpha(li.getchannel("A").point(lambda v: v * 120 // 255))
                    place(lay, c_, cx + dx, cy)
            place(lay, li, cx, cy)
        gr = (1 - ease((t - 0.7) / 0.3)) * 0.5
        if gr > 0:
            gm = self.grain[int(t * 40) % 4].point(lambda v: round(max(0, v - 150) * gr))
            g_ = Image.new("RGBA", (W, H), (255, 255, 255, 0))
            g_.putalpha(gm)
            lay.alpha_composite(g_)
        return lay


# ---------------------------------------------------------------- Blumhouse: a bare bulb flickers on in a dark room
class Blumhouse:
    title, accent = "Blumhouse Productions", (255, 180, 100)
    pool = [("movie", "The Invisible Man", 2020), ("movie", "M3GAN", 2022), ("movie", "Split", 2016),
            ("movie", "The Black Phone", 2021), ("movie", "Five Nights at Freddy's", 2023), ("movie", "Sinister", 2012),
            ("movie", "The Purge", 2013), ("movie", "Happy Death Day", 2017)]
    FLICK = [(0.10, 0.0), (0.14, 0.7), (0.16, 0.05), (0.22, 0.0), (0.26, 0.9), (0.28, 0.2), (0.31, 1.0), (0.36, 0.35),
             (0.38, 1.0), (0.55, 1.0), (0.57, 0.6), (0.59, 1.0)]

    def __init__(self):
        self.l = tinted(fit_logo("blumhouse.png", w=W * 0.56).getchannel("A"), (246, 240, 228), (210, 200, 185))
        self.stage = gradient((3, 3, 4), (10, 9, 9))

    def light(self, t):
        L = 0.0
        for (t0, v0), (t1, v1) in zip(self.FLICK, self.FLICK[1:]):
            if t0 <= t < t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0) if t1 - t0 > 0.05 else v0
        return 1.0 if t >= self.FLICK[-1][0] else 0.0

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        L = 1.0 if final else self.light(t)
        bx, by = W / 2, H * 0.17
        room = Image.new("L", (W, H), 0)
        ImageDraw.Draw(room).ellipse((bx - W * 0.42, by - H * 0.5, bx + W * 0.42, by + H * 0.95), fill=255)
        rl = Image.new("RGBA", (W, H), (110, 80, 50, 0))
        rl.putalpha(room.filter(ImageFilter.GaussianBlur(160)).point(lambda v: round(v * 0.55 * L)))
        lay.alpha_composite(rl)
        d = ImageDraw.Draw(lay)
        d.line((bx, 0, bx, by - 14), fill=(40, 34, 28, 255), width=3)
        bulb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bulb).ellipse((bx - 11, by - 14, bx + 11, by + 12), fill=(255, 220, 160, round(60 + 195 * L)))
        lay.alpha_composite(alpha_mul(glow_of(bulb, 30, (255, 190, 110), 2.4), L))
        lay.alpha_composite(bulb)
        place(lay, self.l, W / 2, H * 0.58, 0.08 + 0.92 * L)
        return lay


# ---------------------------------------------------------------- NEON: the tubes buzz on letter by letter
class Neon:
    title, accent = "NEON", (255, 70, 200)
    pool = [("movie", "Parasite", 2019), ("movie", "Anora", 2024), ("movie", "Longlegs", 2024),
            ("movie", "Portrait of a Lady on Fire", 2019), ("movie", "I, Tonya", 2017), ("movie", "Triangle of Sadness", 2022),
            ("movie", "Monkey Man", 2024), ("movie", "Spencer", 2021)]

    def __init__(self):
        lg = fit_logo("neon.png", w=W * 0.62)
        self.lg = lg
        self.letters = split_columns(lg)
        self.x0, self.y0 = (W - lg.width) / 2, (H - lg.height) / 2
        rnd = random.Random(7)
        self.on_at = [0.12 + k * 0.13 + rnd.uniform(0, 0.04) for k in range(len(self.letters))]
        self.rnd = rnd
        st = gradient((14, 6, 20), (24, 10, 30))
        d = ImageDraw.Draw(st)
        for y in range(0, H, 46):                                            # a dark brick wall behind the sign
            d.line((0, y, W, y), fill=(10, 4, 14))
            off = 0 if (y // 46) % 2 else 60
            for x in range(off, W, 120):
                d.line((x, y, x, y + 46), fill=(10, 4, 14))
        self.stage = st

    def level(self, k, t):
        t0 = self.on_at[k]
        if t < t0:
            return 0.0
        dt = t - t0
        if dt < 0.12:
            return 1.0 if random.Random(int(t * 400) + k * 31).random() < 0.45 + dt * 4 else 0.12
        return 1.0

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for k, (x0, im) in enumerate(self.letters):
            L = 1.0 if final else self.level(k, t)
            a = im.getchannel("A")
            off = Image.new("RGBA", im.size, (70, 50, 70, 0))
            off.putalpha(a.point(lambda v: v * 150 // 255))                # the unlit glass
            lay.alpha_composite(off, (round(self.x0 + x0), round(self.y0)))
            if L > 0:
                core = tinted(a, (255, 225, 245), (255, 190, 235))
                lay.alpha_composite(alpha_mul(glow_of(core, 28, self.accent, 1.6), L), (round(self.x0 + x0), round(self.y0)))
                lay.alpha_composite(alpha_mul(glow_of(core, 8, self.accent, 1.8), L), (round(self.x0 + x0), round(self.y0)))
                lay.alpha_composite(alpha_mul(core, L), (round(self.x0 + x0), round(self.y0)))
        return lay


# ---------------------------------------------------------------- Studio Ghibli: the line drawing draws itself
class Ghibli:
    title, accent = "Studio Ghibli", (150, 215, 255)
    pool = [("movie", "Howl's Moving Castle", 2004), ("movie", "Kiki's Delivery Service", 1989),
            ("movie", "The Boy and the Heron", 2023), ("movie", "Castle in the Sky", 1986), ("movie", "Ponyo", 2008),
            ("movie", "Nausicaä of the Valley of the Wind", 1984), ("movie", "Porco Rosso", 1992), ("movie", "The Wind Rises", 2013)]

    def __init__(self):
        from scipy import ndimage as ndi
        lg = fit_logo("studio-ghibli.png", w=W * 0.72)
        a = np.asarray(lg)[..., 3]
        self.lg = tinted(Image.fromarray(a), (255, 255, 255), (255, 255, 255))
        self.x0, self.y0 = (W - lg.width) / 2, (H - lg.height) / 2
        # drawing order: geodesic distance along the strokes from the top of each stroke (Totoro: the left part)
        m = a > 20
        split = int(lg.width * 0.33)                                          # left: the drawing, right: the type
        draw = m.copy(); draw[:, split:] = False
        lab, n = ndi.label(ndi.binary_dilation(draw, iterations=2))
        order = np.full(a.shape, np.inf)
        objs = ndi.find_objects(lab)
        comps = sorted(range(1, n + 1), key=lambda i: (objs[i - 1][1].start, objs[i - 1][0].start))
        base = 0
        for i in comps:
            sl = objs[i - 1]
            comp = (lab[sl] == i)
            if comp.sum() < 15:
                continue
            ys, xs = np.nonzero(comp)
            k = np.argmin(ys)
            sub = np.full(comp.shape, np.inf)
            front = np.zeros_like(comp); front[ys[k], xs[k]] = True
            step = 0
            while front.any() and step < 6000:
                sub[front] = base + step
                front = ndi.binary_dilation(front) & comp & np.isinf(sub)
                step += 1
            o = order[sl]
            o[comp] = np.minimum(o[comp], sub[comp])
            base += step
        order[draw & ~np.isfinite(order)] = base
        self.order = np.where(np.isfinite(order), order / max(1, base), 1.0)
        self.type_mask = Image.fromarray(((m & ~draw) * 255).astype(np.uint8))
        self.draw_alpha = a * draw
        self.stage = gradient((40, 150, 225), (110, 195, 245))

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if final:
            place(lay, self.lg, W / 2, H / 2)
            return lay
        p = ease(t / 0.62)
        vis = (self.order <= p) * self.draw_alpha
        d = Image.new("RGBA", self.lg.size, (255, 255, 255, 0))
        d.putalpha(Image.fromarray(vis.astype(np.uint8)))
        lay.alpha_composite(d, (round(self.x0), round(self.y0)))
        ta = ease((t - 0.55) / 0.25)
        if ta > 0:
            ty = Image.new("RGBA", self.lg.size, (255, 255, 255, 0))
            ty.putalpha(ImageChops.multiply(self.type_mask, self.lg.getchannel("A")).point(lambda v: round(v * ta)))
            lay.alpha_composite(ty, (round(self.x0), round(self.y0 + (1 - ta) * 12)))
        return lay


# ---------------------------------------------------------------- monuments under searchlights (20th Century, Searchlight)
class Monument:
    logo_file, beams_n, sky = "", 5, ((10, 18, 48), (60, 70, 110))

    def __init__(self):
        lg = fit_logo(self.logo_file, w=W * self.width, h=H * 0.62)
        self.l = tinted(lg.getchannel("A"), (255, 226, 140), (176, 120, 40))
        self.l_shade = glow_of(self.l, 22, (255, 200, 110), 0.5)
        self.stage = starfield(gradient(self.sky[0], self.sky[1], glow=(W / 2, H * 1.1, W * 0.5, (255, 170, 90), 0.35)), 80, seed=11, top=0.6)

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p = 1.0 if final else out3(t / 0.7)
        k = 1 + 0.22 * (1 - p)
        cy = H * 0.54 + (1 - p) * H * 0.22
        bl = 1.0 if final else ease(t / 0.25)
        for j in range(self.beams_n):
            ph = (j - (self.beams_n - 1) / 2) / max(1, self.beams_n - 1)
            sw = 0.0 if final else math.sin(t * 6.0 + j * 1.3) * 0.18
            x0 = W / 2 + ph * W * 0.48
            beam(lay, x0, H + 10, ph * 0.7 + sw, H * 1.4, 70, (255, 248, 225), 0.42 * bl)
        L = scaled(self.l, k)
        place(lay, scaled(self.l_shade, k), W / 2, cy)
        place(lay, L, W / 2, cy, min(1.0, 0.2 + p))
        if not final and 0.65 < t < 0.95:
            place(lay, sweep(L, (t - 0.65) / 0.3, strength=0.6), W / 2, cy)
        return lay


class TwentiethCentury(Monument):
    title, accent = "20th Century Studios", (255, 200, 100)
    logo_file, width, beams_n = "20th-century.png", 0.46, 5
    pool = [("movie", "The Sound of Music", 1965), ("movie", "Bohemian Rhapsody", 2018), ("movie", "The Martian", 2015),
            ("movie", "Life of Pi", 2012), ("movie", "Free Guy", 2021), ("movie", "The Devil Wears Prada", 2006),
            ("movie", "Cast Away", 2000), ("movie", "Edward Scissorhands", 1990)]


class Searchlight(Monument):
    title, accent = "Searchlight Pictures", (255, 215, 140)
    logo_file, width, beams_n, sky = "searchlight.png", 0.62, 2, ((8, 10, 26), (40, 44, 70))
    pool = [("movie", "Poor Things", 2023), ("movie", "The Grand Budapest Hotel", 2014), ("movie", "Birdman", 2014),
            ("movie", "The Shape of Water", 2017), ("movie", "Jojo Rabbit", 2019), ("movie", "Nomadland", 2020),
            ("movie", "12 Years a Slave", 2013), ("movie", "Slumdog Millionaire", 2008)]

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cy = H * 0.52
        if final:
            for side in (-1, 1):
                beam(lay, W / 2 + side * W * 0.3, H + 10, side * 0.35, H * 1.5, 80, (255, 250, 230), 0.4)
            place(lay, self.l_shade, W / 2, cy)
            place(lay, self.l, W / 2, cy)
            return lay
        # one great beam scans the sky from the left and lights the name on its way; a second joins it
        a1 = -1.0 + 2.0 * ease(t / 0.6)
        beam(lay, W * 0.5, H + 10, a1 * 0.9, H * 1.6, 95, (255, 250, 230), 0.55)
        if t > 0.55:
            k = ease((t - 0.55) / 0.3)
            for side in (-1, 1):
                beam(lay, W / 2 + side * W * 0.3, H + 10, side * 0.35, H * 1.5, 80, (255, 250, 230), 0.4 * k)
        bx = W * 0.5 + math.tan(a1 * 0.9) * (H + 10 - cy)
        m = Image.new("L", self.l.size, 0)
        lx = bx - (W - self.l.width) / 2
        if lx > 0:
            ImageDraw.Draw(m).rectangle((0, 0, lx, self.l.height), fill=255)
        reveal = m.filter(ImageFilter.GaussianBlur(40))
        lit = 1.0 if t > 0.62 else None
        li = self.l.copy()
        if lit is None:
            li.putalpha(ImageChops.multiply(li.getchannel("A"), reveal))
        place(lay, alpha_mul(self.l_shade, ease(t / 0.6)), W / 2, cy)
        place(lay, li, W / 2, cy)
        return lay


# ---------------------------------------------------------------- Warner Bros.: the shield flies in through the clouds
class WarnerBros:
    title, accent = "Warner Bros. Pictures", (255, 205, 60)
    pool = [("movie", "Sinners", 2025), ("movie", "Gravity", 2013), ("movie", "Inception", 2010), ("movie", "Wonka", 2023),
            ("movie", "Gran Torino", 2008), ("movie", "Beetlejuice", 1988), ("movie", "Argo", 2012), ("movie", "Weapons", 2025)]

    def __init__(self):
        self.l = fit_logo("warner-bros.png", h=H * 0.62)
        self.stage = gradient((70, 130, 210), (190, 220, 245))
        self.c1, self.c2 = clouds(4), clouds(8, 18)
        st = self.stage.convert("RGBA")
        st.alpha_composite(self.c2.resize((W, H)).crop((0, 0, W, H)) if False else self.c2.crop((W // 2, H // 2, W * 3 // 2, H * 3 // 2)))
        self.stage = st.convert("RGB")

    def cloud_layer(self, c, z, a):
        k = 1 + z
        w_, h_ = round(W * 2 / k), round(H * 2 / k)
        x0, y0 = (W * 2 - w_) / 2, (H * 2 - h_) / 2
        return alpha_mul(c.crop((round(x0), round(y0), round(x0) + w_, round(y0) + h_)).resize((W, H)), a)

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if final:
            place(lay, glow_of(self.l, 22, (255, 230, 150), 0.45), W / 2, H / 2)
            place(lay, self.l, W / 2, H / 2)
            return lay
        p = out3(t / 0.7)
        k = 0.12 + 0.88 * p
        L = scaled(self.l, k)
        place(lay, L, W / 2, H / 2 + (1 - p) * 40, min(1.0, 0.15 + p * 1.5))
        # the camera flies through the near clouds, which part and rush past
        lay.alpha_composite(self.cloud_layer(self.c1, 1.0 + 3.5 * ease(t / 0.75), 1 - ease((t - 0.25) / 0.45)))
        if 0.68 < t < 0.98:
            place(lay, sweep(self.l, (t - 0.68) / 0.3, strength=0.7), W / 2, H / 2)
        return lay


# ---------------------------------------------------------------- Universal: the name swings round the globe
class Universal:
    title, accent = "Universal Pictures", (120, 190, 255)
    pool = [("movie", "Jaws", 1975), ("movie", "Wicked", 2024), ("movie", "Nope", 2022), ("movie", "Twisters", 2024),
            ("movie", "The Bourne Ultimatum", 2007), ("movie", "Love Actually", 2003), ("movie", "Les Misérables", 2012),
            ("movie", "Hot Fuzz", 2007)]

    def __init__(self):
        from scipy import ndimage as ndi
        lg = fit_logo("universal.png", w=W * 0.74)
        a = np.asarray(lg)[..., 3]
        m = a > 30
        lab, n = ndi.label(m)
        objs = ndi.find_objects(lab)
        h = lg.height
        letters, globe = [], np.zeros_like(m)
        for i, sl in enumerate(objs, 1):
            cy = (sl[0].start + sl[0].stop) / 2
            if 0.36 * h < cy < 0.62 * h and (sl[0].stop - sl[0].start) > 0.12 * h:
                letters.append((sl[1].start, sl[0].start, tinted(Image.fromarray((a * (lab == i))[sl].astype(np.uint8)),
                                                                  (255, 255, 255), (215, 225, 240))))
            else:
                globe |= lab == i
        self.globe = tinted(Image.fromarray((a * globe).astype(np.uint8)), (120, 175, 245), (40, 90, 180))
        self.letters = sorted(letters, key=lambda x: x[0])
        self.x0, self.y0 = (W - lg.width) / 2, (H - lg.height) / 2
        self.lw = lg.width
        self.stage = starfield(gradient((2, 4, 14), (8, 16, 40), glow=(W / 2, H / 2, W * 0.32, (30, 70, 150), 0.5)), 220, seed=13, top=1.0)

    def logo(self, t, final=False):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ga = 1.0 if final else ease(t / 0.35)
        gk = 1.0 if final else 1.12 - 0.12 * out3(t / 0.8)
        G = scaled(self.globe, gk)
        place(lay, alpha_mul(glow_of(G, 30, (90, 160, 255), 0.9), ga), W / 2, H / 2)
        place(lay, G, W / 2, H / 2, ga)
        n = len(self.letters)
        for j, (lx, ly, im) in enumerate(self.letters):
            fx, fy = self.x0 + lx + im.width / 2, self.y0 + ly + im.height / 2
            p = 1.0 if final else out3((t - 0.18 - j * 0.045) / 0.42)
            if p <= 0:
                continue
            # round the far side of the globe from the right, then forward into place
            ang = (1 - p) * math.pi * 0.9
            x = W / 2 + (fx - W / 2) * math.cos(ang) + self.lw * 0.55 * math.sin(ang)
            depth = math.cos(ang)
            sc = 0.6 + 0.4 * max(0.0, depth) if p < 1 else 1.0
            y = fy - (1 - depth) * 12
            L = scaled(im, sc)
            place(lay, L, x, y, min(1.0, p * 3) * (0.35 + 0.65 * max(0.0, depth)))
        if not final and 0.72 < t < 0.98:
            full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for lx, ly, im in self.letters:
                full.alpha_composite(im, (round(self.x0 + lx), round(self.y0 + ly)))
            lay.alpha_composite(sweep(full, (t - 0.72) / 0.26, strength=0.6))
        return lay


STUDIOS = {c.title: c for c in (A24, Blumhouse, Neon, Ghibli, DisneyPixar, Searchlight, WarnerBros, Universal, Paramount,
                                TwentiethCentury)}


# ---------------------------------------------------------------- the loop
def film_scene(img):
    im = g.art.graded(img, 0.95, 1.05, (W, H))
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((-W * 0.25, -H * 0.55, W * 0.55, H * 0.55), fill=215)       # a dark pool behind the corner logo
    m = m.filter(ImageFilter.GaussianBlur(W * 0.08))
    return Image.composite(Image.new("RGB", (W, H), (4, 5, 10)), im, m)


def build(title, out):
    st = STUDIOS[title]()
    films = K.trio(st.pool, 3)
    scenes = [film_scene(K.g.load_img(p)) for _, _, p in films]
    final = st.logo(1.0, final=True)
    bb = final.getchannel("A").getbbox()
    lg = final.crop(bb)
    cover = st.stage.convert("RGBA")
    cover.alpha_composite(final)
    cover = cover.convert("RGB")
    S = len(scenes)
    T_OUT, T_IN0, T_IN1, T_MOVE, T_F1, T_BACK = 3, 7, 49, 59, 145, 160   # films ~1.6 s each
    frames = []
    for i in range(N):
        if i < T_OUT:
            cv = cover.copy()
        elif i < T_IN0:
            cv = st.stage.convert("RGBA")
            cv.alpha_composite(alpha_mul(final, 1 - ease((i - T_OUT) / (T_IN0 - T_OUT))))
            cv = cv.convert("RGB")
        elif i < T_IN1:
            cv = st.stage.convert("RGBA")
            cv.alpha_composite(st.logo((i - T_IN0) / (T_IN1 - T_IN0)))
            cv = cv.convert("RGB")
        else:
            # logo travels to the corner while the films play, and back at the end
            if i < T_MOVE:
                m = ease((i - T_IN1) / (T_MOVE - T_IN1))
            elif i < T_F1:
                m = 1.0
            else:
                m = 1 - ease((i - T_F1) / (T_BACK - 1 - T_F1))
            q = min(1.0, max(0.0, (i - T_IN1) / (T_F1 - T_IN1)))
            seg = min(S - 1, int(q * S))
            loc = q * S - seg
            bg = g.art.zoomed(scenes[seg], 0.02 + 0.05 * loc)
            if loc > 0.82 and seg < S - 1:
                bg = Image.blend(bg, g.art.zoomed(scenes[seg + 1], 0.02), (loc - 0.82) / 0.18)
            cv = Image.blend(st.stage, bg, m).convert("RGBA")
            sc = 1 - 0.66 * m
            L = lg.resize((max(1, round(lg.width * sc)), max(1, round(lg.height * sc))), Image.LANCZOS)
            cx0, cy0 = bb[0] + lg.width / 2, bb[1] + lg.height / 2
            tx, ty = 40 + L.width / 2, 34 + L.height / 2
            x, y = cx0 + (tx - cx0) * m, cy0 + (ty - cy0) * m
            cv.alpha_composite(L, (round(x - L.width / 2), round(y - L.height / 2)))
            if m > 0.02:                                   # the card's light runs round once while the films play
                fr = Image.new("L", (W, H), 0)
                pts = g.frame_path(q)
                if len(pts) > 1 and q > 0:
                    ImageDraw.Draw(fr).line(pts, fill=255, width=4, joint="curve")
                gl = Image.new("RGBA", (W, H), st.accent + (0,))
                gl.putalpha(fr.filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, round(v * 1.6 * m))))
                cv.alpha_composite(gl)
                ln = Image.new("RGBA", (W, H), st.accent + (0,))
                ln.putalpha(fr.point(lambda v: round(v * m)))
                cv.alpha_composite(ln)
            cv = cv.convert("RGB")
        frames.append(cv.resize((OW, OH), Image.LANCZOS))
    dd = os.path.join(out, g.slug_of(title))
    os.makedirs(dd, exist_ok=True)
    frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * N, loop=0,
                   quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(dd, "cover.jpg"), quality=90)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 16, 24, 32, 44, 70, 100, 130]):
        strip.paste(frames[idx], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(dd, "frames.jpg"), quality=80)
    return [f[1] for f in films]


if __name__ == "__main__":
    out = sys.argv[1]
    bad = False
    for t in sys.argv[2:] or STUDIOS:
        try:
            print("built", t, "·", ", ".join(map(str, build(t, out))))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", t, e)
            bad = True
    sys.exit(1 if bad else 0)
