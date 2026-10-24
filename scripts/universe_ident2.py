"""Universes & Franchises, cover-first trial (round 2): a designed static cover; the hover starts on it, plays the
franchise's kind of opening and lands back on it.
  wizarding  after the Fantastic Beasts opening: a dark teal stage under a top light, dust in the beam, the
             Wizarding World name in bevelled gold and a fan of wands rising behind it, slow push in
  starwars   after the saga's opening: the blue "A long time ago..." line, then the logo comes from huge to its
             place among the stars
usage: python3 scripts/universe_ident2.py OUT_DIR [ids...]
"""
import io, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art_tools"))
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import universe_motion as U
from keyframe_webp import encode

W, H, GW, GH = U.W, U.H, U.GW, U.GH
ease, place, fit, trim = U.ease, U.place, U.fit, U.trim


def clamp(x):
    return max(0.0, min(1.0, x))


def seg(k, a, b):
    return clamp((k - a) / max(1, b - a))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def radial(c0, c1, cx=0.5, cy=0.5, rx=0.75, ry=None, size=(W, H)):
    w, h = size
    ry = ry or rx
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x / w - cx) / rx * w / h) ** 2 + ((y / h - cy) / ry) ** 2)
    d = np.clip(d, 0, 1)[..., None] ** 1.2
    a = np.array(c1, float) * (1 - d) + np.array(c0, float) * d
    return Image.fromarray(a.astype("uint8"), "RGB")


def bevel(mask, depth=5, dark=(52, 33, 8), mid=(170, 122, 46), light=(255, 234, 176), spec=1.1, lx=-0.45, ly=-0.85):
    """Gold (or any metal) bevel from a mask: height = blurred mask, shaded by a light from the top left."""
    a = np.asarray(mask, float) / 255
    hgt = np.asarray(mask.filter(ImageFilter.GaussianBlur(depth)), float) / 255
    gy, gx = np.gradient(hgt)
    k = depth * 2.2
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(hgt)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    L = np.array([lx, ly, 0.75]); L = L / np.linalg.norm(L)
    d = np.clip((nx * L[0] + ny * L[1] + nz * L[2]) / n, 0, 1)
    flat = (np.abs(gx) + np.abs(gy)) < 1e-3
    d = np.where(flat, 0.62, d)
    c = np.array(dark) + (np.array(mid) - np.array(dark)) * np.clip(d / 0.6, 0, 1)[..., None]
    c = c + (np.array(light) - np.array(mid)) * np.clip((d - 0.6) / 0.4, 0, 1)[..., None]
    c = c + 255 * spec * (d ** 40)[..., None]
    out = np.dstack([np.clip(c, 0, 255), a * 255]).astype("uint8")
    return Image.fromarray(out, "RGBA")


def scale_frame(im, s, cx=W / 2, cy=H / 2):
    """camera push: scale the whole picture by s about (cx, cy)"""
    if abs(s - 1) < 1e-4:
        return im
    w, h = round(W * s), round(H * s)
    big = im.resize((w, h), Image.BICUBIC)
    x0, y0 = round(cx * s - cx), round(cy * s - cy)
    return big.crop((x0, y0, x0 + W, y0 + H))


# ---------------------------------------------------------------- Wizarding World (Fantastic Beasts opening)
def wand(seed, length=None):
    """one wand, pointing up, pivot at the bottom centre of the returned image: a carved handle and a tapering shaft"""
    r = random.Random(seed)
    length = length or round(r.uniform(225, 275))
    w = 48
    im = Image.new("L", (w, length), 0)
    d = ImageDraw.Draw(im)
    hl = r.uniform(0.22, 0.32) * length          # handle length
    base_w, tip_w = r.uniform(11, 14), r.uniform(3, 4)
    cx = w / 2
    pts_l, pts_r = [], []
    for i in range(41):
        f = i / 40
        y = length - f * length
        width = base_w + (tip_w - base_w) * f
        if f * length < hl:                         # handle: knobs and rings
            width = base_w * (1.0 + 0.45 * math.sin(f * length / hl * math.pi * r.choice([2, 3, 4])) ** 4)
        wob = 1.2 * math.sin(f * 7 + seed)
        pts_l.append((cx - width / 2 + wob, y)); pts_r.append((cx + width / 2 + wob, y))
    d.polygon(pts_l + pts_r[::-1], fill=255)
    d.ellipse((cx - base_w * 0.7, length - base_w * 1.2, cx + base_w * 0.7, length), fill=255)
    return bevel(im.filter(ImageFilter.GaussianBlur(0.6)), depth=2, spec=1.0)


class Wizarding:
    n = 170
    tag = "HARRY POTTER  ·  FANTASTIC BEASTS"

    def __init__(self):
        logo = trim(U.whiten_dark(U.commons("File:Wizarding World logo.svg")))
        logo = fit(logo, 620, 230)
        m = logo.getchannel("A")
        self.text = bevel(m, depth=4)
        self.tx, self.ty = W / 2, H / 2 + 95
        self.pivot = (W / 2, self.ty - self.text.height / 2 - 18)
        self.wands = [wand(i) for i in range(17)]
        self.bar = bevel(Image.new("L", (440, 7), 255), depth=2)
        self.bg = radial((4, 10, 14), (26, 52, 66), cy=0.42, rx=0.9, ry=0.8)
        self.beam = self.make_beam()
        r = random.Random(4)
        self.dust = [(r.uniform(0.25, 0.75) * W, r.uniform(0, H), r.uniform(0.3, 1), r.uniform(0, 6.28)) for _ in range(90)]

    def make_beam(self):
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(W * 0.43, -20), (W * 0.57, -20), (W * 0.80, H), (W * 0.20, H)], fill=150)
        m = m.filter(ImageFilter.GaussianBlur(70))
        fade = Image.linear_gradient("L").resize((W, H)).point(lambda v: 255 - v)
        m = ImageChops.multiply(m, fade)
        lay = Image.new("RGBA", (W, H), (150, 200, 220, 0))
        lay.putalpha(m)
        return lay

    def angle(self, i, p):
        """wand i: all upright in a bundle, then fanned out from -84 to +84 degrees"""
        final = -84 + 168 * i / (len(self.wands) - 1)
        q = smooth((p - abs(i - 8) * 0.03) / 0.7)
        return final * q

    def scene(self, k, cover=False):
        lit = 1.0 if cover else smooth(seg(k, 4, 46))
        fan = 1.0 if cover else seg(k, 40, 120)
        rise = 1.0 if cover else ease(seg(k, 26, 60))
        cv = self.bg.copy().convert("RGBA")
        cv.alpha_composite(U.alpha(self.beam, 0.55 + 0.45 * lit))
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        px, py = self.pivot
        for i in sorted(range(len(self.wands)), key=lambda i: -abs(i - 8)):
            wd = self.wands[i]
            a = self.angle(i, fan)
            L = wd.height
            canvas = Image.new("RGBA", (L * 2, L * 2), (0, 0, 0, 0))
            canvas.alpha_composite(wd, (L - wd.width // 2, L - wd.height + round(L * (1 - rise) * 0.6)))
            rot = canvas.rotate(-a, resample=Image.BICUBIC, center=(L, L))
            st.alpha_composite(rot, (round(px - L), round(py - L)))
        st.alpha_composite(self.bar, (round(px - self.bar.width / 2), round(py - 2)))
        place(st, self.text, self.tx, self.ty, 1)
        # light: everything comes out of the dark as the beam opens
        if lit < 1:
            st.putalpha(st.getchannel("A").point(lambda v: round(v * lit)))
        cv.alpha_composite(st)
        d = ImageDraw.Draw(cv)
        t = (k if not cover else self.n) / 25
        for (x, y, s, ph) in self.dust:
            yy = (y + 12 * s * t) % H
            xx = x + 14 * math.sin(t * 0.7 + ph)
            al = round(130 * s * (0.5 + 0.5 * math.sin(ph + t * 1.7)) * (0.4 + 0.6 * lit))
            d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(200, 225, 235, al))
        if not cover and 128 <= k < 150:
            U.sweep(cv, seg(k, 128, 150), strength=90)
        s = 1.0 + 0.10 * smooth(seg(k, 0, 160)) if not cover else 1.10
        img = scale_frame(cv.convert("RGB"), s, W / 2, H / 2 + 20)
        out = img.convert("RGBA")
        U.tagline(out, self.tag, H - 70, 1 if cover else seg(k, 140, 158), size=22, color=(214, 196, 150))
        return out.convert("RGB")

    def frame(self, k):
        return self.scene(k)

    def cover(self):
        return self.scene(self.n, cover=True)


# ---------------------------------------------------------------- Star Wars
class StarWars:
    n = 175
    LINE = ("A long time ago in a galaxy far,", "far away....")

    def __init__(self):
        self.logo = trim(U.key_black(U.commons("File:Star Wars Logo.svg")))
        fp = os.path.join(U.CACHE, "LibreFranklin.ttf")
        if not os.path.exists(fp):
            open(fp, "wb").write(U.get("https://raw.githubusercontent.com/google/fonts/main/ofl/librefranklin/LibreFranklin%5Bwght%5D.ttf"))
        self.font = ImageFont.truetype(fp, 46)
        try:
            self.font.set_variation_by_axes([400])
        except Exception:
            pass
        r = random.Random(3)
        self.stars = [(r.uniform(0, W), r.uniform(0, H), r.uniform(0.3, 1.0)) for _ in range(320)]

    def starfield(self, a):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        d = ImageDraw.Draw(im)
        for x, y, s in self.stars:
            r = 0.6 + 0.9 * s
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, round(255 * s * a)))
        return im

    def line(self, a):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        if a > 0:
            d = ImageDraw.Draw(im)
            x0 = W * 0.2
            for i, t in enumerate(self.LINE):
                d.text((x0, H / 2 - 60 + i * 64), t, font=self.font, fill=(75, 213, 238, round(255 * a)))
        return im

    def logo_at(self, cv, s, a=1.0):
        lg = fit(self.logo, 620 * s, 330 * s)
        place(cv, lg, W / 2, H / 2 - 20, a)

    def frame(self, k):
        if k < 70:                                   # the blue line
            a = smooth(seg(k, 4, 18)) * (1 - smooth(seg(k, 56, 68)))
            return self.line(a).convert("RGB")
        if k < 76:
            return Image.new("RGB", (W, H), (0, 0, 0))
        p = seg(k, 76, 150)
        cv = self.starfield(min(1, seg(k, 76, 84) + 0.0))
        s = 4.2 - 3.2 * (1 - (1 - p) ** 2.6)        # huge, then easing down to its place
        self.logo_at(cv, s)
        U.tagline(cv, "A GALAXY FAR, FAR AWAY", H / 2 - 20 + 330 / 2 + 40, seg(k, 150, 166), color=(255, 232, 31))
        return cv.convert("RGB")

    def cover(self):
        cv = self.starfield(1)
        self.logo_at(cv, 1.0)
        U.tagline(cv, "A GALAXY FAR, FAR AWAY", H / 2 - 20 + 330 / 2 + 40, 1, color=(255, 232, 31))
        return cv.convert("RGB")


IDENTS = {"wizarding": Wizarding, "starwars": StarWars}
PRE, DIP, REST, MS = 3, 6, 14, 40


def render(uid, out_dir):
    ident = IDENTS[uid]()
    cover = ident.cover()
    black = Image.new("RGB", (W, H), (0, 0, 0))
    seq = [cover] * PRE + [Image.blend(cover, black, ease((i + 1) / DIP)) for i in range(DIP)]
    body = [ident.frame(k) for k in range(ident.n)]
    for j in range(8):
        i = len(body) - 8 + j
        body[i] = Image.blend(body[i], cover, (j + 1) / 8)
    seq += body + [cover] * REST
    d = os.path.join(out_dir, uid)
    os.makedirs(d, exist_ok=True)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in seq], [MS] * len(seq), os.path.join(d, "hover.webp"), quality=76)
    cover.save(os.path.join(d, "cover.jpg"), quality=92)
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
