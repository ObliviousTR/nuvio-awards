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


STUDIOS = {c.title: c for c in (Paramount, DisneyPixar)}


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
