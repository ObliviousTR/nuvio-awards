"""Universes & Franchises, ident version (trial): like the Streaming Services row, the hover is the franchise's own kind
of opening - not a slideshow - built from our material (film stills from TMDB, the marks the row already uses,
procedural light, clouds and embers). It is inspired by each franchise's opening, not a copy of it.
  mcu         pages of the saga flip by faster and faster, turning red; the stills keep flipping inside the letters of
              MARVEL STUDIOS, then the red block fills in and the logo settles
  dc          dark blue, an anamorphic light streak crosses, rays turn behind the DC mark as it spins in and catches
              the light
  wizarding   a flight through night clouds towards a warm light; the Wizarding World mark comes out of it in gold
  middleearth embers in the dark, the ring comes out of the fire, MIDDLE-EARTH burns in like heated metal
Each loop starts on the cover, dips to black, plays the opening and lands back on exactly the cover frame.
usage: python3 scripts/universe_ident.py OUT_DIR [ids...]
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art_tools"))
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter
import universe_motion as U
import spotlight_art as art
from keyframe_webp import encode

W, H, GW, GH = U.W, U.H, U.GW, U.GH
ease, place, glow, padded, fit, trim = U.ease, U.place, U.glow, U.padded, U.fit, U.trim


def clamp(x):
    return max(0.0, min(1.0, x))


def seg(k, a, b):
    """0..1 progress of frame k through [a, b)"""
    return clamp((k - a) / max(1, b - a))


def radial(c0, c1, cx=0.5, cy=0.5, r=0.75, size=(W, H)):
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x / w - cx) * w / h) ** 2 + (y / h - cy) ** 2) / r
    d = np.clip(d, 0, 1)[..., None]
    a = np.array(c1, float) * (1 - d) + np.array(c0, float) * d
    return Image.fromarray(a.astype("uint8"), "RGB")


def tagline(cv, text, y, a, color=(255, 255, 255), size=24):
    if a > 0:
        U.tagline(cv, text, y, clamp(a), size=size, color=color)


def particles(n, seed):
    r = random.Random(seed)
    return [(r.uniform(0, W), r.uniform(0, H), r.uniform(0.4, 1.0), r.uniform(-0.6, 0.6), r.uniform(0, 1)) for _ in range(n)]


# ---------------------------------------------------------------- MCU
class MCU:
    n = 140
    tag = "THE INFINITY SAGA  ·  THE MULTIVERSE SAGA"

    def __init__(self):
        self.logo = U.clip("dC3uDJazzlM4z3lZJ5", maxw=900, maxh=240)[-1]
        stills = U.cands("mcu")[:40]
        self.stills = []
        for p in stills:
            try:
                self.stills.append(art.graded(art.fetch(p), 0.95, 1.08, (W, H)).convert("RGB"))
            except Exception:
                pass
        a = np.asarray(self.logo).astype(int)
        white = ((a[..., 0] > 200) & (a[..., 1] > 200) & (a[..., 2] > 200) & (a[..., 3] > 128)).astype("uint8") * 255
        self.letters = Image.fromarray(white, "L").filter(ImageFilter.GaussianBlur(0.6))
        self.bg = radial((0, 0, 0), (40, 2, 6), r=0.9)

    def still(self, k, red):
        im = self.stills[(k // 2) % len(self.stills)]
        r = random.Random(k // 2)
        z = r.uniform(1.04, 1.25)
        cw, ch = W / z, H / z
        x0, y0 = r.uniform(0, W - cw), r.uniform(0, H - ch)
        shift = (k % 2) * r.uniform(-30, 30)        # the page is still moving on its first frame
        im = im.crop((round(x0), round(y0 + shift), round(x0 + cw), round(y0 + ch + shift))).resize((W, H))
        if k % 2 == 0:
            im = im.filter(ImageFilter.BoxBlur(2))
        return Image.blend(im, Image.new("RGB", (W, H), (190, 12, 24)), red)

    def logo_at(self, s):
        lg = self.logo.resize((round(self.logo.width * s), round(self.logo.height * s)), Image.LANCZOS)
        m = self.letters.resize(lg.size, Image.LANCZOS)
        return lg, m

    def frame(self, k):
        cv = self.bg.copy().convert("RGBA")
        if k < 58:
            cv = self.still(k, 0.12 + 0.45 * seg(k, 0, 58)).convert("RGBA")
            if k % 9 == 0:
                U.flash(cv, 0.25)
        elif k < 112:
            p = seg(k, 58, 112)
            s = 2.3 - 1.3 * ease(seg(k, 58, 100))
            lg, m = self.logo_at(s)
            st = self.still(k, 0.35 + 0.4 * p).resize(lg.size)
            inside = st.convert("RGBA")
            inside.putalpha(m)
            fill = ease(seg(k, 92, 112))
            x, y = round(W / 2 - lg.width / 2), round(H / 2 - 10 - lg.height / 2)
            cv.alpha_composite(glow(padded(lg, 60), 40, (220, 20, 40), 0.5 + 0.6 * p), (x - 60, y - 60))
            if fill > 0:
                cv.alpha_composite(U.alpha(lg, fill), (x, y))
            cv.alpha_composite(U.alpha(inside, 1 - fill), (x, y))
        else:
            self.settled(cv, k)
        return cv.convert("RGB")

    def settled(self, cv, k=None):
        lg = self.logo
        x, y = round(W / 2 - lg.width / 2), round(H / 2 - 10 - lg.height / 2)
        cv.alpha_composite(glow(padded(lg, 60), 40, (220, 20, 40), 1.1), (x - 60, y - 60))
        cv.alpha_composite(lg, (x, y))
        if k is not None and k < 128:
            U.sweep(cv, seg(k, 112, 128), strength=110)
        tagline(cv, self.tag, H / 2 + lg.height / 2 + 30, 1 if k is None else seg(k, 116, 130), (235, 225, 225))
        return cv

    def cover(self):
        return self.settled(self.bg.copy().convert("RGBA")).convert("RGB")


# ---------------------------------------------------------------- DC
class DC:
    n = 130
    tag = "SUPERMAN  ·  BATMAN  ·  WONDER WOMAN  ·  JUSTICE LEAGUE"

    def __init__(self):
        self.spin = U.clip("46zn5FmNndXaJVjgdG", maxw=380, maxh=380)
        self.shine = U.clip("ensd2k3UXTw2ErdEet", maxw=380, maxh=380)
        self.bg = radial((2, 6, 16), (16, 44, 98), cy=0.46, r=0.8)
        self.dust = particles(90, 3)
        self.rays = self.make_rays()

    def make_rays(self):
        s = 1800
        im = Image.new("L", (s, s), 0)
        d = ImageDraw.Draw(im)
        r = random.Random(5)
        for i in range(28):
            a = i / 28 * 2 * math.pi + r.uniform(-0.05, 0.05)
            w = r.uniform(0.02, 0.06)
            d.polygon([(s / 2, s / 2), (s / 2 + s * math.cos(a - w), s / 2 + s * math.sin(a - w)),
                       (s / 2 + s * math.cos(a + w), s / 2 + s * math.sin(a + w))], fill=r.randint(60, 140))
        im = im.filter(ImageFilter.GaussianBlur(14))
        fade = radial((0, 0, 0), (255, 255, 255), r=0.55, size=(s, s)).convert("L")
        im = ImageChops.multiply(im, fade)
        lay = Image.new("RGBA", (s, s), (110, 170, 255, 0))
        lay.putalpha(im)
        return lay

    def streak(self, cv, p, y):
        if 0 < p < 1:
            x = -400 + p * (W + 800)
            st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(st)
            for i, (wd, al) in enumerate(((900, 40), (500, 90), (220, 200))):
                d.ellipse((x - wd, y - 3 - i, x + wd, y + 3 + i), fill=(150, 200, 255, al))
            st = st.filter(ImageFilter.GaussianBlur(3))
            cv.alpha_composite(st)
            core = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(core).ellipse((50, 50, 110, 110), fill=(220, 240, 255, 255))
            cv.alpha_composite(core.filter(ImageFilter.GaussianBlur(14)), (round(x - 80), round(y - 80)))

    def base(self, k, settle):
        cv = self.bg.copy().convert("RGBA")
        ra = self.rays.rotate((k if k is not None else self.n) * 0.35, resample=Image.BICUBIC)
        a = 0.85 if settle else 0.85 * ease(seg(k, 20, 70))
        place(cv, U.alpha(ra, a), W / 2, H / 2 - 30, 1)
        d = ImageDraw.Draw(cv)
        for (x, y, s, dx, ph) in self.dust:
            t = (k or 0) / 25 if not settle else 0
            xx, yy = (x + dx * 20 * t) % W, (y - 12 * s * t) % H
            al = round(90 * s * (0.6 + 0.4 * math.sin(ph * 6 + t)))
            d.ellipse((xx - s * 1.6, yy - s * 1.6, xx + s * 1.6, yy + s * 1.6), fill=(170, 210, 255, al))
        return cv

    def frame(self, k):
        settle = k >= 120
        cv = self.base(k, settle)
        if k < 30:
            cv = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), cv, ease(seg(k, 0, 30) * 0.7))
        self.streak(cv, seg(k, 6, 40), H / 2 - 30)
        if k >= 28:
            n = len(self.spin)
            if k < 95:
                lg = self.spin[min(n - 1, int(ease(seg(k, 28, 95)) * (n - 1)))]
            else:
                lg = self.shine[min(len(self.shine) - 1, int(seg(k, 95, 118) * (len(self.shine) - 1)))]
            s = 0.45 + 0.55 * ease(seg(k, 28, 95))
            lg = lg.resize((round(lg.width * s), round(lg.height * s)), Image.LANCZOS)
            place(cv, glow(padded(lg, 60), 36, (40, 130, 255), 1.2), W / 2, H / 2 - 30, clamp(seg(k, 28, 40)))
            place(cv, lg, W / 2, H / 2 - 30, clamp(seg(k, 28, 36)))
        tagline(cv, self.tag, H / 2 - 30 + 210, seg(k, 104, 118), (215, 228, 255), size=22)
        if settle:
            cv = self.cover().convert("RGBA")
        return cv.convert("RGB")

    def cover(self):
        cv = self.base(None, True)
        lg = self.shine[-1]
        place(cv, glow(padded(lg, 60), 36, (40, 130, 255), 1.2), W / 2, H / 2 - 30, 1)
        place(cv, lg, W / 2, H / 2 - 30, 1)
        tagline(cv, self.tag, H / 2 - 30 + 210, 1, (215, 228, 255), size=22)
        return cv.convert("RGB")


# ---------------------------------------------------------------- Wizarding World
def cloud_layer(seed, size=(1920, 1080), cover=0.5):
    r = np.random.default_rng(seed)
    w, h = size
    acc = np.zeros((h, w))
    for octave, amp in ((8, 1.0), (16, 0.5), (32, 0.28), (64, 0.14)):
        g = r.random((octave * h // w + 2, octave + 2))
        im = Image.fromarray((g * 255).astype("uint8"), "L").resize((w, h), Image.BICUBIC)
        acc += np.asarray(im, float) / 255 * amp
    acc /= acc.max()
    a = np.clip((acc - (1 - cover)) / 0.25, 0, 1) ** 1.3
    return Image.fromarray((a * 255).astype("uint8"), "L").filter(ImageFilter.GaussianBlur(6))


class Wizarding:
    n = 150
    tag = "HARRY POTTER  ·  FANTASTIC BEASTS"

    def __init__(self):
        lg = trim(U.whiten_dark(U.commons("File:Wizarding World logo.svg")))
        lg = fit(lg, 700, 250)
        self.logo = U.gradient_fill(lg, (255, 240, 196), (196, 150, 70))
        self.sky = radial((4, 8, 20), (30, 46, 80), cy=0.55, r=0.9)
        self.layers = []
        for i, (seed, cov) in enumerate(((11, 0.55), (12, 0.5), (13, 0.45), (14, 0.5))):
            m = cloud_layer(seed, cover=cov)
            col = Image.new("RGBA", m.size, (150, 165, 200, 0))
            shade = radial((70, 82, 112), (215, 205, 190), r=0.7, size=m.size)
            col = shade.convert("RGBA")
            col.putalpha(m)
            self.layers.append(col)
        self.sparks = particles(60, 9)

    def camera(self, k):
        """distance flown: fast at first, easing to a stop by frame 128"""
        return 1.0 - (1 - seg(k, 0, 128)) ** 2.4

    def clouds(self, cv, k, light):
        z = self.camera(k)
        for i, lay in enumerate(self.layers):
            ph = (i / len(self.layers) + z * 1.35) % 1.0       # each layer comes towards us, then passes
            if k >= 128:
                ph = (i / len(self.layers) + 1.35) % 1.0
            s = 0.9 + ph ** 1.6 * 2.6
            a = clamp(ph / 0.25) * clamp((1 - ph) / 0.35) * (0.35 + 0.5 * (1 - light))
            im = lay.resize((round(W * s), round(H * s)), Image.BILINEAR)
            x, y = round(W / 2 - im.width / 2), round(H / 2 - im.height / 2)
            box = (max(0, -x), max(0, -y), max(0, -x) + W, max(0, -y) + H)
            crop = im.crop(box)
            cv.alpha_composite(U.alpha(crop, a), (max(0, x), max(0, y)))

    def light(self, cv, a):
        if a > 0:
            g = radial((0, 0, 0), (255, 214, 140), r=0.45).convert("L").point(lambda v: round(v * a * 0.75))
            lay = Image.new("RGBA", (W, H), (255, 214, 150, 0))
            lay.putalpha(g)
            cv.alpha_composite(lay)

    def frame(self, k, cover=False):
        cv = self.sky.copy().convert("RGBA")
        la = ease(seg(k, 30, 100))
        self.light(cv, la)
        self.clouds(cv, k, la * 0.5)
        p = ease(seg(k, 78, 118))
        if p > 0:
            place(cv, glow(padded(self.logo, 50), 26, (255, 210, 140), 1.0 * p), W / 2, H / 2 - 10, 1)
            place(cv, self.logo, W / 2, H / 2 - 10, p)
            d = ImageDraw.Draw(cv)
            if not cover and k < 132:
                q = seg(k, 78, 132)
                for (x, y, s, dx, ph) in self.sparks:
                    xx = W / 2 + (x - W / 2) * 0.5 + dx * 60 * q
                    yy = H / 2 + (y - H / 2) * 0.35 - 90 * s * q
                    al = round(230 * max(0, math.sin(math.pi * clamp(q * 1.2 - ph * 0.2))))
                    r = 1.5 + 2 * s
                    d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 238, 190, al))
            if not cover and 112 <= k < 130:
                U.sweep(cv, seg(k, 112, 130), strength=120)
        tagline(cv, self.tag, H / 2 - 10 + self.logo.height / 2 + 40, 1 if cover else seg(k, 118, 132), (245, 228, 190))
        if k < 14 and not cover:
            cv = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), cv, seg(k, 0, 14))
        return cv.convert("RGB")

    def cover(self):
        return self.frame(self.n + 20, cover=True)


# ---------------------------------------------------------------- Middle-earth
class MiddleEarth:
    n = 150
    tag = "THE LORD OF THE RINGS  ·  THE HOBBIT"

    def __init__(self):
        f = U.font("cinzel", 112, weight=800)
        base = U.text_layer("MIDDLE-EARTH", f, (255, 255, 255), 14)
        self.word = U.gradient_fill(base, (255, 226, 150), (176, 120, 40))
        self.hot = U.gradient_fill(base, (255, 250, 220), (255, 150, 40))
        rings = [trim(f) for f in U.sticker("jU8YU7i8WJFLMMDrEb") if f.getchannel("A").getbbox()]
        big = max(r.width * r.height for r in rings)
        self.rings = [fit(r, 250, 250) for r in rings if r.width * r.height > 0.25 * big]   # drop stray specks
        self.bg = radial((0, 0, 0), (34, 12, 2), cy=0.9, r=0.9)
        self.embers = particles(120, 21)

    def fire(self, cv, a):
        if a > 0:
            g = radial((0, 0, 0), (255, 255, 255), cy=1.05, r=0.7).convert("L").point(lambda v: round(v * a))
            lay = Image.new("RGBA", (W, H), (255, 96, 16, 0))
            lay.putalpha(g)
            cv.alpha_composite(lay)

    def ember_layer(self, cv, k, a):
        if a <= 0:
            return
        d = ImageDraw.Draw(cv)
        t = k / 25
        for (x, y, s, dx, ph) in self.embers:
            yy = (y - 70 * s * t) % (H + 40) - 20
            xx = x + dx * 40 * math.sin(t * 1.3 + ph * 6)
            al = round(255 * a * s * (0.5 + 0.5 * math.sin(ph * 9 + t * 3)))
            r = 1 + 2.2 * s
            d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 150 + round(80 * s), 60, max(0, al)))

    def frame(self, k, cover=False):
        cv = self.bg.copy().convert("RGBA")
        heat = 0.25 + 0.55 * math.sin(math.pi * seg(k, 10, 90)) if not cover else 0.22
        self.fire(cv, heat if k < 130 or cover else 0.22 + (heat - 0.22) * (1 - seg(k, 120, 130)))
        if not cover:
            self.ember_layer(cv, k, (1 - seg(k, 118, 138)) * ease(seg(k, 0, 20)))
        # the ring: far and small in the fire, comes up close, then rises above the title
        z = ease(seg(k, 8, 70)) if not cover else 1
        up = ease(seg(k, 70, 100)) if not cover else 1
        idx = (k if not cover else self.n) % len(self.rings)
        r0 = self.rings[idx if (cover or k < 128) else self.n % len(self.rings)]
        s = 0.35 + 0.95 * z - 0.45 * up
        rg = r0.resize((round(r0.width * s), round(r0.height * s)), Image.LANCZOS)
        rh = (1.6 * (1 - up) + 0.5) if not cover else 0.5
        y = H / 2 + 40 - 40 * z - 140 * up
        place(cv, glow(padded(rg, 50), 28, (255, 110, 20), rh), W / 2, y, 1)
        place(cv, rg, W / 2, y, clamp(seg(k, 8, 26)) if not cover else 1)
        if not cover and 66 <= k < 80:
            U.flash(cv, 0.18 * (1 - abs(k - 70) / 10), (255, 160, 60))
        p = seg(k, 84, 124) if not cover else 1
        if p > 0:
            hot = U.wipe(self.hot, p, soft=80)
            cool = U.wipe(self.word, clamp((p - 0.18) / 0.82), soft=120)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            hg = (1 - seg(k, 120, 136)) * 1.4 if not cover else 0
            if hg > 0:
                place(lay, glow(padded(hot, 40), 18, (255, 120, 20), hg), W / 2, H / 2 + 80)
                place(lay, hot, W / 2, H / 2 + 80, clamp(1 - seg(k, 124, 136)))
            place(lay, cool, W / 2, H / 2 + 80)
            cv.alpha_composite(lay)
        tagline(cv, self.tag, H / 2 + 80 + self.word.height / 2 + 40, 1 if cover else seg(k, 124, 138), (240, 220, 170))
        if k < 10 and not cover:
            cv = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), cv, seg(k, 0, 10))
        return cv.convert("RGB")

    def cover(self):
        return self.frame(self.n, cover=True)


IDENTS = {"mcu": MCU, "dc": DC, "wizarding": Wizarding, "middleearth": MiddleEarth}
PRE, DIP, REST, MS = 3, 6, 14, 40


def render(uid, out_dir):
    ident = IDENTS[uid]()
    cover = ident.cover()
    black = Image.new("RGB", (W, H), (0, 0, 0))
    seq = [cover] * PRE + [Image.blend(cover, black, ease((i + 1) / DIP)) for i in range(DIP)]
    body = [ident.frame(k) for k in range(ident.n)]
    # the last frames converge on the cover: blend the final 8 so the landing is exact
    for j in range(8):
        i = len(body) - 8 + j
        body[i] = Image.blend(body[i], cover, (j + 1) / 8)
    seq += body + [cover] * REST
    d = os.path.join(out_dir, uid)
    os.makedirs(d, exist_ok=True)
    small = [f.resize((GW, GH), Image.LANCZOS) for f in seq]
    encode(small, [MS] * len(small), os.path.join(d, "hover.webp"), quality=74)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    picks = [seq[i] for i in range(0, len(seq), max(1, len(seq) // 12))][:12]
    sheet = Image.new("RGB", (4 * 320, 3 * 180))
    for n, f in enumerate(picks):
        sheet.paste(f.resize((320, 180)), ((n % 4) * 320, (n // 4) * 180))
    sheet.save(os.path.join(d, "sheet.jpg"), quality=85)
    return len(seq), os.path.getsize(os.path.join(d, "hover.webp")) // 1024


if __name__ == "__main__":
    out = sys.argv[1]
    for uid in sys.argv[2:] or IDENTS:
        try:
            print(uid, render(uid, out), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(uid, "FAILED", e, flush=True)
