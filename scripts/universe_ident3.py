"""Universes & Franchises, round 3: seamless loops. Frame 0 is the cover and the last frame leads straight back into
it - no cuts, no dips to black; everything moves continuously.
  wizarding  the light goes down and the camera drifts back into the dark while the wands fold away; then, from the
             dark, the camera comes in, the beam opens, the Wizarding World name catches the light and the wands rise
             and fan out (after the Fantastic Beasts opening)
  starwars   the logo recedes into the stars, a crawl rises from the bottom of the screen in perspective and drifts
             away into the distance (our own words about the saga, not a film's crawl), then the logo comes back out of
             the depth to its place
usage: python3 scripts/universe_ident3.py OUT_DIR [ids...]
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art_tools"))
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import universe_motion as U
import universe_ident2 as V
from keyframe_webp import encode

W, H, GW, GH = U.W, U.H, U.GW, U.GH
place, fit, trim = U.place, U.fit, U.trim
clamp, seg, smooth = V.clamp, V.seg, V.smooth


def inout(x):
    """ease in and out (cubic)"""
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def scaled_onto(base, layer, s, cx, cy):
    """paste layer (W x H, RGBA) scaled by s about (cx, cy) onto base"""
    if s <= 0.01:
        return base
    w, h = max(1, round(W * s)), max(1, round(H * s))
    lay = layer.resize((w, h), Image.BICUBIC)
    if s <= 1:
        base.alpha_composite(lay, (round(cx - cx * s), round(cy - cy * s)))
    else:
        x0, y0 = round(cx * s - cx), round(cy * s - cy)
        base.alpha_composite(lay.crop((x0, y0, x0 + W, y0 + H)))
    return base


# ---------------------------------------------------------------- Wizarding World
class Wizarding(V.Wizarding):
    n = 230          # 9.2 s
    OUT = 50         # cover -> dark, far away (2 s)
    IN0, IN1 = 50, 200

    def state(self, k):
        """(camera scale, light 0..1, wand rise 0..1, fan 0..1) at frame k"""
        if k <= self.OUT:
            p = inout(k / self.OUT)
            return 1.10 - 0.62 * p, 1 - p, 1 - smooth(p * 1.4), 1 - smooth(p * 1.6)
        p = seg(k, self.IN0, self.IN1)
        cam = 0.48 + 0.62 * (1 - (1 - p) ** 2.2)               # approach, slowing as it arrives
        light = smooth(seg(k, self.IN0 + 10, self.IN0 + 80))
        rise = smooth(seg(k, self.IN0 + 55, self.IN0 + 95))
        fan = smooth(seg(k, self.IN0 + 85, self.IN1 - 8))
        return cam, light, rise, fan

    def stage(self, rise, fan):
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        px, py = self.pivot
        for i in sorted(range(len(self.wands)), key=lambda i: -abs(i - 8)):
            wd = self.wands[i]
            a = self.angle(i, fan)
            L = wd.height
            canvas = Image.new("RGBA", (L * 2, L * 2), (0, 0, 0, 0))
            canvas.alpha_composite(wd, (L - wd.width // 2, L - wd.height + round(L * (1 - rise))))
            canvas = canvas.crop((0, 0, L * 2, L + 2))              # below the bar: hidden (they rise out of it)
            full = Image.new("RGBA", (L * 2, L * 2), (0, 0, 0, 0))
            full.alpha_composite(canvas)
            rot = full.rotate(-a, resample=Image.BICUBIC, center=(L, L))
            st.alpha_composite(rot, (round(px - L), round(py - L)))
        st.alpha_composite(self.bar, (round(px - self.bar.width / 2), round(py - 2)))
        place(st, self.text, self.tx, self.ty, 1)
        return st

    def scene(self, k, cover=False):
        cam, light, rise, fan = (1.10, 1.0, 1.0, 1.0) if cover else self.state(k)
        cv = self.bg.copy().convert("RGBA")
        cv.putalpha(255)
        dark = Image.new("RGBA", (W, H), (0, 0, 0, round(255 * (1 - light) * 0.85)))
        cv.alpha_composite(U.alpha(self.beam, 0.15 + 0.85 * light))
        st = self.stage(rise, fan)
        lit = 0.08 + 0.92 * light                                    # the gold is never fully gone, just in shadow
        st.putalpha(st.getchannel("A").point(lambda v: round(v * lit)))
        scaled_onto(cv, st, cam, W / 2, H / 2 + 20)
        cv.alpha_composite(dark)
        d = ImageDraw.Draw(cv)
        t = (0 if cover else k) / 25
        for (x, y, s, ph) in self.dust:
            yy = (y + 12 * s * t) % H
            xx = x + 14 * math.sin(t * 0.7 + ph)
            al = round(130 * s * (0.55 + 0.45 * math.sin(ph + t * 1.7)) * (0.3 + 0.7 * light))
            d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(200, 225, 235, al))
        if not cover and self.IN1 - 30 <= k < self.IN1 - 6:
            U.sweep(cv, seg(k, self.IN1 - 30, self.IN1 - 6), strength=80)
        tag = 1.0 if cover else (1 - smooth(seg(k, 0, 18)) if k < self.IN0 else smooth(seg(k, self.IN1 - 10, self.n - 6)))
        U.tagline(cv, self.tag, H - 70, tag, size=22, color=(214, 196, 150))
        return cv.convert("RGB")

    def frame(self, k):
        return self.scene(k)

    def cover(self):
        return self.scene(0, cover=True)


# ---------------------------------------------------------------- Star Wars
CRAWL_TITLE = ("THE SAGA", "A COLLECTION")
CRAWL = ("From the deserts of Tatooine to the forests of Endor, the story of the Skywalkers and of every hero "
         "who rose against the Empire has been gathered in one place. Here are the films, the series and the "
         "legends of the Republic, the Rebellion and the Resistance: Jedi and Sith, smugglers and bounty hunters, "
         "droids and Wookiees, and the Force that binds them all, from a galaxy far, far away....")


def find_coeffs(dst, src):
    """PIL perspective coefficients mapping output points dst to input points src"""
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(m, float); b = np.array(src, float).reshape(8)
    return np.linalg.solve(A, b).tolist()


class StarWars:
    n = 274            # 11 s: recede + crawl, the cover rises from below, a short hold
    RISE0, RISE1 = 222, 262
    YELLOW = (229, 177, 58)

    def __init__(self):
        self.logo = trim(U.key_black(U.commons("File:Star Wars Logo.svg")))
        fp = os.path.join(U.CACHE, "LibreFranklin.ttf")
        if not os.path.exists(fp):
            open(fp, "wb").write(U.get("https://raw.githubusercontent.com/google/fonts/main/ofl/librefranklin/LibreFranklin%5Bwght%5D.ttf"))
        self.tex = self.crawl_texture(fp)
        r = random.Random(3)
        self.stars = [(r.uniform(0, W), r.uniform(0, H), r.uniform(0.3, 1.0)) for _ in range(340)]
        self.field = self.starfield()

    def crawl_texture(self, fp):
        TW = 1000
        f = ImageFont.truetype(fp, 54); f.set_variation_by_axes([700])
        ft = ImageFont.truetype(fp, 64); ft.set_variation_by_axes([800])
        lines, words, cur = [], CRAWL.split(), []
        for w in words:
            if f.getlength(" ".join(cur + [w])) > TW - 40 and cur:
                lines.append(cur); cur = [w]
            else:
                cur.append(w)
        lines.append(cur)
        lh = 70
        Ht = 220 + len(lines) * lh + 40
        im = Image.new("L", (TW, Ht), 0)
        d = ImageDraw.Draw(im)
        for i, t in enumerate(CRAWL_TITLE):
            d.text(((TW - ft.getlength(t)) / 2, 10 + i * 84), t, font=ft, fill=255)
        y = 220
        for j, ln in enumerate(lines):          # justified, last line left aligned
            if j < len(lines) - 1 and len(ln) > 1:
                gap = (TW - 40 - sum(f.getlength(w) for w in ln)) / (len(ln) - 1)
                x = 20
                for w in ln:
                    d.text((x, y), w, font=f, fill=255); x += f.getlength(w) + gap
            else:
                d.text((20, y), " ".join(ln), font=f, fill=255)
            y += lh
        return im

    def starfield(self):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        d = ImageDraw.Draw(im)
        for x, y, s in self.stars:
            r = 0.6 + 0.9 * s
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, round(255 * s)))
        return im

    def crawl(self, cv, scroll):
        """the text plane: bottom edge of the screen to a horizon near the top; scroll = texture rows passed"""
        TW, TH = self.tex.size
        horizon, bw, tw = H * 0.06, W * 0.98, W * 0.20
        win = 1250                                  # texture rows visible from bottom to horizon
        top = scroll - win                           # texture row at the horizon
        dst = [(W / 2 - tw / 2, horizon), (W / 2 + tw / 2, horizon), (W / 2 + bw / 2, H), (W / 2 - bw / 2, H)]
        src = [(0, top), (TW, top), (TW, scroll), (0, scroll)]
        pad = Image.new("L", (TW, TH + 2 * win), 0)
        pad.paste(self.tex, (0, win))
        src = [(x, y + win) for x, y in src]
        plane = pad.transform((W, H), Image.PERSPECTIVE, find_coeffs(dst, src), Image.BICUBIC)
        fade = Image.linear_gradient("L").resize((W, H)).point(lambda v: round(255 * clamp((v / 255 - 0.12) / 0.45) ** 1.3))
        plane = ImageChops.multiply(plane, fade)
        lay = Image.new("RGBA", (W, H), self.YELLOW + (0,))
        lay.putalpha(plane)
        cv.alpha_composite(lay)

    def logo_at(self, cv, s, a=1.0, dy=0.0):
        if s < 0.004 or a <= 0:
            return
        lg = fit(self.logo, max(2, 620 * s), max(2, 330 * s))
        place(cv, lg, W / 2, H / 2 - 20 + dy, a)

    def scene(self, k):
        cv = self.field.copy()
        n = self.n
        # the logo: recedes (classic), later returns from the same point
        if k < 95:
            p = seg(k, 0, 95)
            s = 0.965 ** k * (1 - smooth(seg(k, 70, 95)))
            self.logo_at(cv, s, 1.0)
        dy = None
        if k >= self.RISE0:                          # the cover comes up from below the screen and settles
            p = seg(k, self.RISE0, self.RISE1)
            dy = (H * 0.95) * (1 - p) ** 3
            self.logo_at(cv, 1.0, 1.0, dy)
        # the crawl: rises from below and drifts into the distance
        TH = self.tex.size[1]
        if 30 <= k < 250 and not (dy is not None and dy < 1):
            q = seg(k, 30, 250)
            self.crawl(cv, -60 + q * (TH + 1310))
        if dy is None:
            U.tagline(cv, "A GALAXY FAR, FAR AWAY", H / 2 - 20 + 330 / 2 + 40, 1 - smooth(seg(k, 0, 14)), color=(255, 232, 31))
        elif H / 2 - 20 + 330 / 2 + 40 + dy < H + 20:
            U.tagline(cv, "A GALAXY FAR, FAR AWAY", H / 2 - 20 + 330 / 2 + 40 + dy, 1, color=(255, 232, 31))
        return cv.convert("RGB")

    def frame(self, k):
        return self.scene(k)

    def cover(self):
        cv = self.field.copy()
        self.logo_at(cv, 1.0)
        U.tagline(cv, "A GALAXY FAR, FAR AWAY", H / 2 - 20 + 330 / 2 + 40, 1, color=(255, 232, 31))
        return cv.convert("RGB")


IDENTS = {"wizarding": Wizarding, "starwars": StarWars}
REST, MS = 10, 40


def render(uid, out_dir):
    ident = IDENTS[uid]()
    cover = ident.cover()
    body = [ident.frame(k) for k in range(ident.n)]
    seq = [cover] * REST + body
    d = os.path.join(out_dir, uid)
    os.makedirs(d, exist_ok=True)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in seq], [MS] * len(seq), os.path.join(d, "hover.webp"), quality=76)
    cover.save(os.path.join(d, "cover.jpg"), quality=92)
    # seam check: how far the first and the last frames are from the cover
    a0 = np.asarray(body[0], float); a1 = np.asarray(body[-1], float); c = np.asarray(cover, float)
    seam = (round(float(np.abs(a0 - c).mean()), 2), round(float(np.abs(a1 - c).mean()), 2))
    picks = [seq[i] for i in range(0, len(seq), max(1, len(seq) // 16))][:16]
    sheet = Image.new("RGB", (4 * 320, 4 * 180))
    for n, f in enumerate(picks):
        sheet.paste(f.resize((320, 180)), ((n % 4) * 320, (n // 4) * 180))
    sheet.save(os.path.join(d, "sheet.jpg"), quality=85)
    return len(seq), os.path.getsize(os.path.join(d, "hover.webp")) // 1024, "seam", seam



# ---------------------------------------------------------------- Wizarding World, v3 (no reverse opening)
class Wizarding3(V.Wizarding):
    """Cover: the name and its line, centred, under the beam. Hover: they glide down, the bar appears, the wands rise
    and fan out, a moment's hold with a glint, the fan closes, the wands sink, the name glides back to the centre."""
    n = 220
    TY0, TY1 = H / 2 - 4, H / 2 + 95

    def timeline(self, k):
        down = inout(seg(k, 0, 32)) * (1 - inout(seg(k, 186, 216)))
        bar = smooth(seg(k, 18, 36)) * (1 - smooth(seg(k, 180, 198)))
        rise = smooth(seg(k, 30, 62)) * (1 - smooth(seg(k, 168, 192)))
        fan = smooth(seg(k, 52, 118)) * (1 - smooth(seg(k, 146, 178)))
        cam = 1 + 0.05 * math.sin(math.pi * seg(k, 0, self.n))
        self.tag_a = smooth(seg(k, 110, 128))                       # the line writes in once the fan is open...
        self.tag_f = 1 - smooth(seg(k, 148, 162))                   # ...and fades before the fan closes
        return down, bar, rise, fan, cam

    def scene(self, k, cover=False):
        down, bar, rise, fan, cam = (0, 0, 0, 0, 1) if cover else self.timeline(k)
        if cover:
            self.tag_a, self.tag_f = 0, 0
        ty = self.TY0 + (self.TY1 - self.TY0) * down
        self.ty = ty
        self.pivot = (W / 2, ty - self.text.height / 2 - 18)
        cv = self.bg.copy().convert("RGBA")
        cv.alpha_composite(self.beam)
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        px, py = self.pivot
        if rise > 0.001:
            for i in sorted(range(len(self.wands)), key=lambda i: -abs(i - 8)):
                wd = self.wands[i]
                a = self.angle(i, fan)
                L = wd.height
                canvas = Image.new("RGBA", (L * 2, L * 2), (0, 0, 0, 0))
                canvas.alpha_composite(wd, (L - wd.width // 2, L - wd.height + round(L * (1 - rise))))
                full = Image.new("RGBA", (L * 2, L * 2), (0, 0, 0, 0))
                full.alpha_composite(canvas.crop((0, 0, L * 2, L + 2)))
                st.alpha_composite(full.rotate(-a, resample=Image.BICUBIC, center=(L, L)), (round(px - L), round(py - L)))
        if bar > 0:
            b = self.bar.resize((max(1, round(self.bar.width * (0.2 + 0.8 * bar))), self.bar.height))
            st.alpha_composite(U.alpha(b, bar), (round(px - b.width / 2), round(py - 2)))
        place(st, self.text, W / 2, ty, 1)
        if self.tag_a > 0 and self.tag_f > 0:
            tg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            U.tagline(tg, self.tag, ty + self.text.height / 2 + 42, 1, size=22, color=(214, 196, 150))
            st.alpha_composite(U.alpha(U.wipe(tg, self.tag_a, soft=120), self.tag_f))
        scaled_onto(cv, st, cam, W / 2, H / 2 + 20)
        d = ImageDraw.Draw(cv)
        u = 2 * math.pi * ((0 if cover else k) / self.n)     # periodic over the loop: dust is where it began
        for (x, y, s, ph) in self.dust:
            yy = y + 22 * s * math.sin(u + ph * 1.3)
            xx = x + 16 * math.sin(u + ph)
            al = round(130 * s * (0.55 + 0.45 * math.sin(ph + 2 * u)))
            d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(200, 225, 235, al))
        if not cover and 122 <= k < 146:
            U.sweep(cv, seg(k, 122, 146), strength=80)
        return cv.convert("RGB")

    def frame(self, k):
        return self.scene(k)

    def cover(self):
        return self.scene(0, cover=True)


IDENTS["wizarding"] = Wizarding3


if __name__ == "__main__":
    out = sys.argv[1]
    for uid in sys.argv[2:] or IDENTS:
        try:
            print(uid, render(uid, out), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(uid, "FAILED", e, flush=True)

