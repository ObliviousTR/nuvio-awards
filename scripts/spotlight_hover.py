"""Spotlight hover animations (Ozzy, 30 Oct 2026). The hero (portrait, poster or logo) stays where it is; the
subject's own titles turn over in the dark left side, between the card name and the title block, each card in a
style of its own. The cover is rebuilt in layers (spotlight_art.cover_layers), so every loop starts and ends exactly
on the cover.

  headliner  strip      a filmstrip of stills, one card settling after another
  visionary  viewfinder a camera viewfinder (2.39:1, frame lines, scene count): the films cut in with a slow push
  powerhouse shelf      the studio's posters rise onto a shelf, three at a time
  saga       timeline   release order: numbered chapters ride along a timeline, a dot for each one
  pulse      mosaic     a 2x2 mosaic that pops in on the beat; one tile at a time lights up over a pulse line
  prestige   deck       a gold-edged deck of stills; the top card is dealt away to show the next
  legend     reel       a 35 mm film strip runs through, sepia black-and-white, with grain and flicker
  retro      vhs        a small CRT plays a VHS tape: power on, PLAY, tracking glitches, the tape counter, STOP
  yerli      wipe       the stills follow one another behind red diagonal wipes (Turkish titles)

render(slot, layers, films, out) writes a 512x288 WebP (40 ms a frame, every frame a keyframe; see
art_tools/keyframe_webp.py). films: [{"title", "year", "still": TMDB path, "poster": TMDB path}].
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "art_tools"))
from keyframe_webp import encode
from spotlight_art import FONTS, W, H, cover_fit, fetch, font, gradient_mask, spaced, wrap

GW, GH, MS = 512, 288, 40
LAB = 34                                                     # room for the "TITLE · YEAR" line under the content


def ease(x):
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ramp(i, a, n):
    """0 before frame a, eased 0 -> 1 over n frames, 1 after"""
    return ease((i - a) / max(1, n))


def keyed(keys, i):
    """piecewise eased interpolation over [(frame, value), ...]"""
    if i <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= i <= f1:
            return v0 + (v1 - v0) * ease((i - f0) / max(1, f1 - f0))
    return keys[-1][1]


def mono(size):
    return ImageFont.truetype(os.path.join(FONTS, "VT323-Regular.ttf"), size)


def faded(im, a):
    """an RGBA image at a fraction of its alpha"""
    if a >= 1:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def put(b, im, xy, a=1.0):
    """paste an RGBA image at (x, y), clipped to the frame, at alpha a"""
    if a <= 0:
        return
    x, y = round(xy[0]), round(xy[1])
    l, t = max(0, -x), max(0, -y)
    if l >= im.width or t >= im.height or x >= b.width or y >= b.height:
        return
    im = faded(im, a)
    crop = im.crop((l, t, min(im.width, b.width - x), min(im.height, b.height - y)))
    b.paste(crop, (x + l, y + t), crop)


def zoomed(im, w, h, z):
    """im cover-fitted to w x h at zoom z (about the centre)"""
    if z == 1:
        return cover_fit(im, w, h)
    big = cover_fit(im, round(w * z), round(h * z))
    x, y = (big.width - w) // 2, (big.height - h) // 2
    return big.crop((x, y, x + w, y + h))


def slide_keys(n, step, HOLD0, IN, HOLD, MOVE, OUT, enter, leave):
    """offsets for a strip of n items that settle one after another: (keys, total frames, frame the exit starts)"""
    keys, f = [(HOLD0, enter)], HOLD0 + IN
    keys.append((f, 0))
    for k in range(1, n):
        f += HOLD; keys.append((f, -step * (k - 1)))
        f += MOVE; keys.append((f, -step * k))
    f += HOLD; keys.append((f, -step * (n - 1)))
    f += OUT; keys.append((f, -step * (n - 1) + leave))
    return keys, f, f - OUT


class Kit:
    """what every style works with: the cover layers, the films, the box on the left, the hero's slow push-in and
    the label typography"""

    def __init__(self, L, films, tr=False):
        self.L, self.acc, self.tr = L, L.acc, tr
        self.up = (lambda t: t.replace("i", "İ").upper()) if tr else str.upper
        self.films = films
        self.cover = L.compose()
        a = np.asarray(L.text.getchannel("A"))
        rows = np.where(a[150:, :700].max(axis=1) > 0)[0]
        top = 150 + int(rows[0]) if len(rows) else H - 220      # where the title block starts (its tag line)
        bb = L.hero.getbbox() if L.hero is not None else None
        right = min(600, (bb[0] + 60 if bb else 640) - 40)
        self.box = (72, 124, right - 72, top - 30 - 124)        # x, y, width, height (the label line included)

    def stage(self, i, total):
        """the cover without its text: the hero stays exactly where it is (still frames merge in the WebP, which keeps
        the file small; a push-in on the hero doubled it)"""
        if not hasattr(self, "_stage"):
            self._stage = self.L.base()
            self.hero(self._stage)
        return self._stage.copy()

    def hero(self, b):
        if self.L.hero is not None:
            b.paste(self.L.hero, (0, 0), self.L.hero)

    def label(self, d, x, y, f, size=17, fill=(240, 240, 240), maxw=None):
        tf, yf = font("SemiBold", size), font("Medium", size)
        title = self.up(f["title"])
        yr = f"·  {f['year']}" if f.get("year") else ""
        width = lambda t: sum(d.textlength(c, font=tf) + 3 for c in t)
        if maxw:
            room = maxw - 14 - sum(d.textlength(c, font=yf) + 3 for c in yr) - 8
            while width(title) > room and len(title) > 4:
                title = title[:-2].rstrip() + "…" if not title.endswith("…") else title[:-3].rstrip() + "…"
        d.rectangle((x, y + 3, x + 4, y + size), fill=self.acc)
        x = spaced(d, (x + 14, y), title, tf, fill, 3)
        if yr:
            spaced(d, (x + 6, y), yr, yf, (170, 170, 176), 3)

    def label_img(self, f, size=17, maxw=None):
        im = Image.new("RGBA", (1000, size + 12), (0, 0, 0, 0))
        self.label(ImageDraw.Draw(im), 0, 0, f, size, maxw=maxw or self.box[2] + 60)
        return im.crop(im.getbbox() or (0, 0, 1, 1))

    def clip(self, layer, pad_l=34, pad_r=60):
        """fade a layer out at the box's sides (things slide in and out of it)"""
        x, _, w, _ = self.box
        m = gradient_mask(W, H, [(0, 0), ((x - pad_l) / W, 0), (x / W, 255), ((x + w + 6) / W, 255),
                                 ((x + w + pad_r) / W, 0), (1, 0)])
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), m))
        return layer

    def finish(self, b):
        b.paste(self.L.text, (0, 0), self.L.text)
        return b


def card_img(im, w, h, border=None, bw=0, shadow=150, blur=12):
    """a still as a card with a soft shadow (and a border), padded by 24 px for the shadow"""
    pad = 24
    c = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", c.size, 0)
    ImageDraw.Draw(sh).rectangle((pad, pad + 6, pad + w, pad + h + 6), fill=shadow)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    c.paste(Image.new("RGBA", c.size, (0, 0, 0, 255)), (0, 0), sh)
    c.paste(cover_fit(im, w, h), (pad, pad))
    if border:
        ImageDraw.Draw(c).rectangle((pad, pad, pad + w - 1, pad + h - 1), outline=border, width=bw)
    return c


def fit169(K, extra=0):
    """the largest 16:9 frame that fits the box (with `extra` px kept free vertically)"""
    _, _, bw, bh = K.box
    h = min(round(bw * 9 / 16), bh - LAB - extra)
    return round(h * 16 / 9), h


# ---------------------------------------------------------------------------------------------- headliner: strip
def strip(K):
    X0, Y0, _, _ = K.box
    CW, CH = fit169(K)
    step = CW + 24
    cards = [(card_img(f["img"], CW, CH), K.label_img(f, maxw=CW)) for f in K.films[:5]]
    keys, end, back = slide_keys(len(cards), step, 12, 22, 30, 14, 22, -60, -60)
    total = end + 12
    out = []
    for i in range(total):
        b = K.stage(i, total)
        a = ramp(i, 12, 22) if i < back else 1 - ramp(i, back, 22)
        if a > 0:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            o = keyed(keys, i)
            for j, (c, lab) in enumerate(cards):
                x = X0 + o + j * step
                put(layer, c, (x - 24, Y0 - 24))
                put(layer, lab, (x, Y0 + CH + 14))
            K.clip(layer)
            b.paste(layer, (0, 0), faded(layer, a))
        out.append(K.finish(b))
    return out


# ------------------------------------------------------------------------------------------ visionary: viewfinder
def viewfinder(K):
    X0, Y0, BW, _ = K.box
    FW, FH = fit169(K)
    FW = BW if FW > BW else FW
    IW, IH = FW - 20, round((FW - 20) / 2.39)
    IY = (FH - IH) // 2
    films = K.films[:6]
    n = len(films)
    HOLD0, IN, SHOT, DIS, OUT, HOLD1 = 12, 18, 36, 8, 18, 12
    start = HOLD0 + IN - 4
    end = start + n * SHOT
    total = end + OUT + HOLD1
    labs = [K.label_img(f, maxw=FW) for f in films]
    frame = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    L_ = 26
    for (x, y, sx, sy) in ((0, 0, 1, 1), (FW - 1, 0, -1, 1), (0, FH - 1, 1, -1), (FW - 1, FH - 1, -1, -1)):
        d.line((x, y, x + sx * L_, y), fill=K.acc, width=3)
        d.line((x, y, x, y + sy * L_), fill=K.acc, width=3)
    tag = "2.39 : 1"
    spaced(d, (FW - 14 - sum(d.textlength(c, font=font("SemiBold", 12)) + 2 for c in tag), 10), tag,
           font("SemiBold", 12), (230, 230, 230, 210), 2)
    out = []
    for i in range(total):
        b = K.stage(i, total)
        a = ramp(i, HOLD0, IN) if i < end else 1 - ramp(i, end, OUT)
        if a > 0:
            gate = Image.new("RGBA", (FW, FH), (6, 6, 8, 235))
            k = min(n - 1, max(0, (i - start) // SHOT))
            t = i - start - k * SHOT
            shots = [(k, t)] if not (k > 0 and t < DIS) else [(k - 1, t + SHOT), (k, t)]
            pic = None
            for j, (kk, tt) in enumerate(shots):
                z = 1.0 + 0.08 * min(1.0, max(0.0, (tt // 2 * 2) / (SHOT + DIS)))   # steps of 2: pairs merge
                im = zoomed(films[kk]["img"], IW, IH, z)
                pic = im if pic is None else Image.blend(pic, im, ease(tt / DIS))
            gate.paste(pic, (10, IY))
            g = ImageDraw.Draw(gate)
            cx, cy = FW // 2, FH // 2
            g.line((cx - 10, cy, cx + 10, cy), fill=(255, 255, 255, 120), width=1)
            g.line((cx, cy - 10, cx, cy + 10), fill=(255, 255, 255, 120), width=1)
            spaced(g, (14, 10), f"SC {k + 1:02d}", font("SemiBold", 12), (230, 230, 230), 2)
            if (i // 12) % 2 == 0:
                g.ellipse((78, 13, 86, 21), fill=K.acc)
            gate.alpha_composite(frame)
            s = 0.94 + 0.06 * a
            if s != 1:
                gate = gate.resize((round(FW * s), round(FH * s)), Image.BICUBIC)
            put(b, gate, (X0 + (FW - gate.width) / 2, Y0 + (FH - gate.height) / 2), a)
            la = a * (1 if t >= 4 or k == 0 else t / 4)
            put(b, labs[k], (X0, Y0 + FH + 14), la)
        out.append(K.finish(b))
    return out


# ----------------------------------------------------------------------------------------------- powerhouse: shelf
def shelf(K):
    X0, Y0, BW, BH = K.box
    G = 18
    PW = (BW - 2 * G) // 3
    PH = round(PW * 1.5)
    if PH > BH - LAB - 8:
        PH = BH - LAB - 8
        PW = round(PH / 1.5)
    films = K.films[:6]
    sets = [films[:3], films[3:6]] if len(films) >= 6 else [films[:3]]
    posters = [card_img(f.get("pimg") or f["img"], PW, PH, shadow=170) for f in films]
    years = []
    for f in films:
        y = Image.new("RGBA", (PW, 26), (0, 0, 0, 0))
        d = ImageDraw.Draw(y)
        d.rectangle((0, 4, 4, 20), fill=K.acc)
        spaced(d, (12, 0), str(f.get("year") or ""), font("SemiBold", 18), (235, 235, 235), 3)
        years.append(y)
    HOLD0, RISE, STAG, HOLD, FALL, HOLD1 = 12, 16, 6, 60, 14, 12
    plan, f0 = [], HOLD0 + 6
    for _ in sets:
        fall = f0 + RISE + 2 * STAG + HOLD
        plan.append((f0, fall))
        f0 = fall + 10
    back = plan[-1][1] + 2 * STAG + FALL
    total = back + HOLD1
    LY = Y0 + PH + 10
    out = []
    for i in range(total):
        b = K.stage(i, total)
        sl = ramp(i, HOLD0, 16) * (1 - ramp(i, back - 14, 14))
        if sl > 0:
            put(b, Image.new("RGBA", (3 * PW + 2 * G, 2), K.acc + (210,)), (X0, LY), sl)
        for s, (rise, fall) in enumerate(plan):
            for j in range(3):
                k = s * 3 + j
                if k >= len(films):
                    continue
                up_, down = ramp(i, rise + j * STAG, RISE), ramp(i, fall + j * STAG, FALL)
                a = up_ * (1 - down)
                if a <= 0:
                    continue
                x = X0 + j * (PW + G)
                put(b, posters[k], (x - 24, Y0 + 50 * (1 - up_) + 30 * down - 24), a)
                put(b, years[k], (x, LY + 12), a)
        out.append(K.finish(b))
    return out


# -------------------------------------------------------------------------------------------------- saga: timeline
def timeline(K):
    X0, Y0, BW, BH = K.box
    LY = Y0
    CY = Y0 + 22
    CW, CH = fit169(K, extra=22)
    step = CW + 26
    films = K.films[:7]
    cards = []
    nf = font("ExtraBold", max(36, CH * 30 // 100))
    for k, f in enumerate(films):
        c = card_img(f["img"], CW, CH)
        d = ImageDraw.Draw(c)
        hh = CH // 3
        grad = Image.linear_gradient("L").resize((CW, hh)).point(lambda v: int(v * 0.7))
        c.paste(Image.new("RGBA", (CW, hh), (0, 0, 0, 255)), (24, 24 + CH - hh), grad)
        d.text((24 + 14, 24 + CH - nf.size - 8), f"{k + 1:02d}", font=nf, fill=(255, 255, 255, 0), stroke_width=2,
               stroke_fill=K.acc)
        cards.append((c, K.label_img(f, maxw=CW)))
    keys, end, back = slide_keys(len(cards), step, 12, 22, 24, 14, 22, -60, -60)
    total = end + 12
    out = []
    for i in range(total):
        b = K.stage(i, total)
        a = ramp(i, 12, 22) if i < back else 1 - ramp(i, back, 22)
        if a > 0:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            d.line((X0 - 40, LY, X0 + BW + 60, LY), fill=K.acc + (150,), width=2)
            o = keyed(keys, i)
            for j, (c, lab) in enumerate(cards):
                x = X0 + o + j * step
                put(layer, c, (x - 24, CY - 24))
                put(layer, lab, (x, CY + CH + 14))
                d.line((x + 2, LY, x + 2, CY - 1), fill=K.acc + (150,), width=1)
                d.ellipse((x - 5, LY - 7, x + 9, LY + 7), fill=K.acc)
            K.clip(layer)
            b.paste(layer, (0, 0), faded(layer, a))
        out.append(K.finish(b))
    return out


# --------------------------------------------------------------------------------------------------- pulse: mosaic
def mosaic(K):
    X0, Y0, BW, BH = K.box
    G, PL = 10, 22                                     # gap, pulse line band
    TH = (BH - LAB - PL - G) // 2
    TW = round(TH * 16 / 9)
    if 2 * TW + G > BW:
        TW = (BW - G) // 2
        TH = round(TW * 9 / 16)
    films = K.films[:8]
    sets = [films[:4], films[4:8]] if len(films) >= 8 else [films[:4]]
    tiles = [cover_fit(f["img"], TW, TH) for f in films]
    labs = [K.label_img(f, maxw=2 * TW + G) for f in films]
    pos = [(X0 + (j % 2) * (TW + G), Y0 + (j // 2) * (TH + G)) for j in range(4)]
    GB = Y0 + 2 * TH + G                               # grid bottom
    HOLD0, BEAT, LIT, SWAP, OUT, HOLD1 = 12, 6, 16, 12, 16, 12
    plan, f = [], HOLD0 + 4
    for _ in sets:
        lit = f + 4 * BEAT + 6
        drop = lit + 4 * LIT
        plan.append((f, lit, drop))
        f = drop + SWAP
    back = plan[-1][2] + 4
    total = back + OUT + HOLD1
    out = []
    for i in range(total):
        b = K.stage(i, total)
        env = ramp(i, HOLD0, 10) * (1 - ramp(i, back, OUT))
        beats = []
        for s, (pop, lit, drop) in enumerate(plan):
            for j in range(4):
                k = s * 4 + j
                if k >= len(films):
                    continue
                t0 = pop + j * BEAT
                beats.append(t0)
                on = lit + j * LIT <= i < lit + (j + 1) * LIT
                if on:
                    beats.append(lit + j * LIT)
                sc = 0.86 + 0.14 * ramp(i, t0, 8)
                a = ramp(i, t0, 6) * (1 - ramp(i, drop + j * 3, 10))
                if a <= 0:
                    continue
                im = tiles[k]
                if lit <= i < drop and not on:
                    im = ImageEnhance.Brightness(im).enhance(0.5)
                t = Image.new("RGBA", (TW + 6, TH + 6), (0, 0, 0, 0))
                t.paste(im, (3, 3))
                flash = max(0.0, 1 - (i - t0) / 10) if i >= t0 else 0
                if on or flash > 0:
                    ImageDraw.Draw(t).rectangle((0, 0, TW + 5, TH + 5), outline=K.acc + (int(255 * max(flash, on)),),
                                                width=3)
                if sc != 1:
                    t = t.resize((round(t.width * sc), round(t.height * sc)), Image.BICUBIC)
                x, y = pos[j]
                put(b, t, (x - 3 + (TW + 6 - t.width) / 2, y - 3 + (TH + 6 - t.height) / 2), a)
                if on:
                    put(b, labs[k], (X0, GB + PL + 8), min(1, (i - lit - j * LIT) / 4 + 0.25))
        if env > 0:                                    # the pulse line: a heartbeat blip on every beat
            lw = 2 * TW + G
            line = Image.new("RGBA", (lw, PL), (0, 0, 0, 0))
            last = max([t for t in beats if t <= i], default=-99)
            age, c = i - last, ((i - last) * 22) % (lw + 120) - 60
            pts = []
            for x in range(0, lw, 3):
                dx = x - c
                yv = PL / 2
                if -20 < dx < 20 and age < 30:
                    yv -= (PL / 2 - 2) * math.sin(math.pi * (dx + 20) / 20) * math.exp(-abs(dx) / 12)
                pts.append((x, yv))
            ImageDraw.Draw(line).line(pts, fill=K.acc + (220,), width=2)
            put(b, line, (X0, GB + 4), env)
        out.append(K.finish(b))
    return out


# -------------------------------------------------------------------------------------------------- prestige: deck
def deck(K):
    X0, Y0, BW, BH = K.box
    CW, CH = fit169(K, extra=14)
    CW = min(CW, BW - 40)
    CH = round(CW * 9 / 16)
    CX, CY = X0 + CW / 2 + 6, Y0 + CH / 2 + 8
    films = K.films[:5]
    n = len(films)
    cards = [card_img(f["img"], CW, CH, border=K.acc, bw=3, shadow=190, blur=14) for f in films]
    labs = [K.label_img(f, maxw=CW) for f in films]
    ANG = [0, -3.5, 3, -2, 2.5, -1.5]
    HOLD0, IN, HOLD, DEAL, OUT, HOLD1 = 12, 22, 30, 16, 22, 12
    deal_at = [HOLD0 + IN + HOLD + k * (HOLD + DEAL) for k in range(n)]
    back = deal_at[-1]
    total = back + DEAL + HOLD1
    out = []
    for i in range(total):
        b = K.stage(i, total)
        env = ramp(i, HOLD0, IN)
        dealt = sum(ramp(i, t, DEAL) for t in deal_at)
        for k in range(n - 1, -1, -1):
            depth = k - dealt
            if depth <= -1:
                continue
            if depth < 0:                              # dealt away to the left, off the screen
                t = depth + 1
                x, y, ang, a, s = CX - (CW + 160) * (1 - t), CY + 24 * (1 - t), -9 * (1 - t), t, 1
            else:
                dd = min(depth, 4)
                lo, hi = int(dd), min(int(dd) + 1, 5)
                ang = ANG[lo] + (ANG[hi] - ANG[lo]) * (dd - lo)
                s = 1 - 0.04 * dd
                x, y, a = CX + 10 * dd, CY - 6 * dd, 1 if depth < 3 else max(0, 4 - depth)
            y += 40 * (1 - env)
            a *= env
            if a <= 0:
                continue
            c = cards[k]
            if depth > 0:
                c = Image.merge("RGBA", (*ImageEnhance.Brightness(c.convert("RGB")).enhance(1 - 0.14 * min(depth, 3))
                                         .split(), c.getchannel("A")))
            if s != 1:
                c = c.resize((round(c.width * s), round(c.height * s)), Image.BICUBIC)
            if ang:
                c = c.rotate(ang, resample=Image.BICUBIC, expand=True)
            put(b, c, (x - c.width / 2, y - c.height / 2), a)
        top = min(n - 1, int(dealt + 0.001))
        settled = deal_at[top - 1] + DEAL if top > 0 else HOLD0 + IN
        st = ((i - settled) // 2 * 2) / 16                   # in steps of 2 frames, so pairs merge
        if 0 <= st <= 1 and dealt < n - 0.5:           # a gold shimmer over the card that just settled
            sh = Image.new("L", (W, H), 0)
            xs = CX - CW / 2 - 100 + (CW + 200) * ease(st)
            ImageDraw.Draw(sh).polygon([(xs, CY - CH / 2), (xs + 50, CY - CH / 2), (xs - 20, CY + CH / 2),
                                        (xs - 70, CY + CH / 2)], fill=70)
            clip = Image.new("L", (W, H), 0)
            ImageDraw.Draw(clip).rectangle((CX - CW / 2, CY - CH / 2, CX + CW / 2, CY + CH / 2), fill=255)
            sh = ImageChops.multiply(sh.filter(ImageFilter.GaussianBlur(8)), clip)
            b = Image.composite(Image.new("RGB", (W, H), (255, 236, 190)), b, sh)
        if dealt < n - 0.2:
            la = env * min(1, max(0, (i - settled + 3) / 5)) * (1 - ramp(i, deal_at[top] - 3, 4))
            put(b, labs[top], (CX - CW / 2, CY + CH / 2 + 16), la)
        out.append(K.finish(b))
    return out


# ---------------------------------------------------------------------------------------------------- legend: reel
def reel(K, seed=7):
    X0, Y0, BW, BH = K.box
    SP = 22                                            # sprocket band, above and below the frames
    FH_ = min(round((BW - 60) * 9 / 16), BH - LAB - 2 * SP)
    FW_ = round(FH_ * 16 / 9)
    PITCH = FW_ + 16
    films = K.films[:6]
    n = len(films)
    rnd = random.Random(seed)
    tone = []
    for f in films:
        g = ImageOps.autocontrast(ImageOps.grayscale(cover_fit(f["img"], FW_, FH_)), cutoff=1)
        tone.append(ImageOps.colorize(g, (18, 14, 10), (238, 226, 205)))
    SH = FH_ + 2 * SP
    SL = PITCH * (n + 4)
    strip_ = Image.new("RGBA", (SL, SH), (16, 14, 12, 255))
    d = ImageDraw.Draw(strip_)
    for x in range(0, SL, 22):
        for y in (6, SH - 6 - 11):
            d.rounded_rectangle((x + 5, y, x + 16, y + 11), radius=2, fill=(0, 0, 0, 0))
    ef = font("SemiBold", 10)
    for k in range(n):
        x = k * PITCH + 2 * PITCH
        strip_.paste(tone[k], (x, SP))
        d.text((x + 4, SH - SP + 5), f"{k + 1:02d} ▸ {films[k].get('year') or ''}", font=ef, fill=K.acc + (230,))
    for k in (0, 1, n + 2, n + 3):
        x = k * PITCH
        d.rectangle((x, SP, x + FW_, SP + FH_), fill=(28, 25, 22, 255))
    labs = [K.label_img(f, maxw=BW) for f in films]
    # the strip's left edge so that frame k sits at the box's left: X0 - (k + 2) * PITCH
    keys, end, back = slide_keys(n, PITCH, 12, 26, 28, 14, 26, BW + 80, -(BW + 80))
    total = end + 12
    grain = [Image.effect_noise((SL // 4, SH // 4), 40).resize((SL, SH), Image.BILINEAR) for _ in range(4)]
    out = []
    for i in range(total):
        b = K.stage(i, total)
        a = ramp(i, 12, 20) if i < back else 1 - ramp(i, back + 6, 20)
        if a > 0:
            o = keyed(keys, i)
            sx = X0 - 2 * PITCH + o
            rgb = strip_.convert("RGB")
            fr = random.Random(seed * 1000 + i // 2)              # grain and flicker change every 2nd frame
            rgb = ImageEnhance.Brightness(rgb).enhance(1 + (fr.random() - 0.5) * 0.08)
            g = grain[(i // 2) % 4]
            rgb = ImageChops.overlay(rgb, Image.merge("RGB", (g, g, g)).point(lambda v: 128 + (v - 128) // 5))
            st = Image.merge("RGBA", (*rgb.split(), strip_.getchannel("A")))
            if fr.random() < 0.08:
                xx = fr.randint(0, SL - 1)
                ImageDraw.Draw(st).line((xx, SP, xx + fr.randint(-4, 4), SP + FH_), fill=(230, 222, 205, 80))
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            put(layer, st, (sx, Y0))
            K.clip(layer, pad_l=40, pad_r=70)
            b.paste(layer, (0, 0), faded(layer, a))
            k = int(round(min(n - 1, max(0, -o / PITCH))))
            near = abs(-o / PITCH - k)
            put(b, labs[k], (X0, Y0 + SH + 12), max(0, 1 - near * 3) * a)
        out.append(K.finish(b))
    return out


# ------------------------------------------------------------------------------------------------------ retro: vhs
def osd(d, x, y, word, sym, fnt, size):
    """a VCR's on-screen word with its symbol drawn (VT323 has no ▶ or ■), with a drop shadow"""
    for off, col in ((2, (0, 0, 0)), (0, (245, 245, 245))):
        d.text((x + off, y + off), word, font=fnt, fill=col)
        sx, sy = x + d.textlength(word, font=fnt) + 10 + off, y + size * 0.28 + off
        s = size * 0.5
        if sym == "play":
            d.polygon([(sx, sy), (sx + s, sy + s / 2), (sx, sy + s)], fill=col)
        else:
            d.rectangle((sx, sy, sx + s * 0.9, sy + s * 0.9), fill=col)


def vhs(K, seed=3):
    X0, Y0, BW, BH = K.box
    SW, SH = fit169(K)
    films = K.films[:5]
    n = len(films)
    rnd = random.Random(seed)

    def tape(im):
        im = cover_fit(im, SW, SH)
        r, g, b_ = im.split()
        im = Image.merge("RGB", (ImageChops.offset(r, 3, 0), g, ImageChops.offset(b_, -2, 0)))
        im = ImageEnhance.Contrast(ImageEnhance.Color(im.filter(ImageFilter.GaussianBlur(1.2))).enhance(1.25)).enhance(1.08)
        return im

    stills = [tape(f["img"]) for f in films]
    lines = Image.new("L", (SW, SH), 255)
    dl = ImageDraw.Draw(lines)
    for y in range(0, SH, 4):
        dl.line((0, y, SW, y), fill=200)
    vig = Image.radial_gradient("L").resize((SW, SH)).point(lambda v: 255 - int(v * 0.55))
    noise = [Image.effect_noise((SW // 4, SH // 4), 50).resize((SW, SH), Image.BILINEAR).convert("RGB") for _ in range(4)]
    big, small = mono(max(24, SH // 7)), mono(max(18, SH // 10))
    corners = Image.new("L", (SW, SH), 0)
    ImageDraw.Draw(corners).rounded_rectangle((0, 0, SW - 1, SH - 1), radius=14, fill=255)
    HOLD0, ON, GL, PLAY, OFF, HOLD1 = 12, 10, 8, 40, 10, 12
    seg = [HOLD0 + ON + 4 + k * (PLAY + GL) for k in range(n)]
    stop = seg[-1] + PLAY
    total = stop + 14 + OFF + HOLD1

    def glitch(img, amt):
        a = np.asarray(img).copy()
        h = a.shape[0]
        band = rnd.randint(0, max(1, h - 40))
        for y in range(band, min(h, band + rnd.randint(20, 60))):
            a[y] = np.roll(a[y], int(rnd.gauss(0, 18 * amt)), axis=0)
        for _ in range(int(10 * amt)):
            y = rnd.randint(0, h - 2)
            a[y:y + 2] = np.clip(a[y:y + 1].astype(int) + rnd.randint(60, 160), 0, 255)
        return Image.fromarray(a)

    out = []
    for i in range(total):
        b = K.stage(i, total)
        if HOLD0 <= i < stop + 14 + OFF:
            # what the tube shows, and how hard the tape glitches
            if i < seg[0]:
                k, amt = 0, 1.0 if i >= HOLD0 + ON else 0.0
            elif i >= stop:
                k, amt = n - 1, 0.0
            else:
                k = min(n - 1, (i - seg[0]) // (PLAY + GL))
                t = i - seg[k]
                amt = 0.0
                if t >= PLAY and k < n - 1:
                    tt = t - PLAY
                    amt = 1 - abs(tt - GL / 2) / (GL / 2)
                    k = k if tt < GL / 2 else k + 1
            scr = stills[k].copy() if i >= HOLD0 + ON or i >= stop else Image.new("RGB", (SW, SH), (200, 205, 215))
            scr = Image.composite(scr, Image.new("RGB", (SW, SH), (0, 0, 0)), lines)
            scr = Image.blend(scr, ImageChops.add(scr, noise[i % 4], scale=2.2), 0.12 + 0.7 * amt)
            if amt > 0:
                scr = glitch(scr, amt)
            scr = Image.composite(scr, Image.new("RGB", (SW, SH), (0, 0, 0)), vig)
            d = ImageDraw.Draw(scr)
            if HOLD0 + ON <= i < stop and ((i - seg[0]) < 30 or (i // 14) % 2 == 0):
                osd(d, SW - 16 - d.textlength("PLAY", font=big) - big.size * 0.6, 8, "PLAY", "play", big, big.size)
            if stop <= i < stop + 14:
                osd(d, SW - 16 - d.textlength("STOP", font=big) - big.size * 0.6, 8, "STOP", "stop", big, big.size)
            if seg[0] <= i < stop:
                sec = (i - seg[0]) * MS // 1000
                cnt = f"SP 0:{sec // 60:02d}:{sec % 60:02d}"
                d.text((SW - 16 - d.textlength(cnt, font=small) + 2, SH - small.size - 8 + 2), cnt, font=small, fill=(0, 0, 0))
                d.text((SW - 16 - d.textlength(cnt, font=small), SH - small.size - 8), cnt, font=small, fill=(240, 240, 240))
            # the tube switching on and off: a bright line that opens up / closes down
            if i < HOLD0 + ON:
                p = ease((i - HOLD0) / ON)
            elif i >= stop + 14:
                p = 1 - ease((i - stop - 14) / OFF)
            else:
                p = 1
            sc = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
            sc.paste(scr, (0, 0), corners)
            if p < 1:
                h = max(2, round(SH * p ** 1.5))
                sq = sc.resize((SW, h), Image.BILINEAR)
                sc = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
                bright = ImageEnhance.Brightness(sq).enhance(1 + 2.5 * (1 - p))
                sc.paste(bright, (0, (SH - h) // 2))
            # the set's dark bezel
            tv = Image.new("RGBA", (SW + 16, SH + 16), (0, 0, 0, 0))
            ImageDraw.Draw(tv).rounded_rectangle((0, 0, SW + 15, SH + 15), radius=20, fill=(12, 12, 14, 235))
            tv.alpha_composite(sc, (8, 8))
            env = ramp(i, HOLD0 - 8, 8) * (1 - ramp(i, stop + 14 + OFF, 8))
            put(b, tv, (X0 - 8, Y0 - 8), env)
            if seg[0] <= i < stop:
                f = films[k]
                name, yr = f["title"].upper(), str(f.get("year") or "")
                lf = mono(26)
                dd = ImageDraw.Draw(b)
                lab = f"{name}  {yr}"
                while dd.textlength(lab, font=lf) > SW - 20 and len(name) > 4:
                    name = name[:-2].rstrip()
                    lab = f"{name}…  {yr}"
                y = Y0 + SH + 10
                dd.rectangle((X0, y + 7, X0 + 4, y + 25), fill=K.acc)
                dd.text((X0 + 14, y), lab, font=lf, fill=(245, 245, 245))
        out.append(K.finish(b))
    return out


# ------------------------------------------------------------------------------------------------------ yerli: wipe
def wipe(K):
    X0, Y0, BW, BH = K.box
    AW, AH = fit169(K)
    films = K.films[:5]
    n = len(films)
    red = K.acc
    labs = [K.label_img(f, maxw=AW) for f in films]
    HOLD0, WIPE, HOLD, HOLD1 = 12, 14, 34, 12
    starts = [HOLD0 + k * (WIPE + HOLD) for k in range(n + 1)]     # the last wipe clears the box again
    total = starts[-1] + WIPE + HOLD1
    frame_mask = Image.new("L", (AW, AH), 255)

    def scene(k, t):
        if k < 0 or k >= n:
            return None
        return zoomed(films[k]["img"], AW, AH, 1 + 0.06 * min(1, (t // 2 * 2) / (WIPE + HOLD + WIPE)))

    out = []
    for i in range(total):
        b = K.stage(i, total)
        k = sum(1 for s in starts if i >= s) - 1                   # the wipe running (or the last one run)
        if k >= 0:
            t = i - starts[k]
            cur = scene(k, t)
            if t >= WIPE:
                area = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
                if cur is not None:
                    area.paste(cur, (0, 0))
            else:
                prev = scene(k - 1, t + WIPE + HOLD)
                p = ease(t / WIPE)
                sl = AH * 0.35                                     # the slant
                lead = -sl - 40 + (AW + 2 * sl + 200) * p
                trail = lead - 110
                area = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
                if prev is not None:
                    area.paste(prev, (0, 0))
                m = Image.new("L", (AW, AH), 0)
                ImageDraw.Draw(m).polygon([(-10, 0), (trail + sl, 0), (trail - sl, AH), (-10, AH)], fill=255)
                if cur is not None:
                    area.paste(cur, (0, 0), m)
                else:
                    area.paste(Image.new("RGBA", (AW, AH), (0, 0, 0, 0)), (0, 0), m)
                band = Image.new("L", (AW, AH), 0)
                ImageDraw.Draw(band).polygon([(trail + sl, 0), (lead + sl, 0), (lead - sl, AH), (trail - sl, AH)],
                                             fill=245)
                area.paste(Image.new("RGBA", (AW, AH), red + (255,)), (0, 0), band)
            put(b, area, (X0, Y0))
            if k < n:
                la = min(1.0, max(0.0, (t - WIPE + 4) / 6)) * (1 - ramp(i, starts[k + 1] - 4, 4))
                put(b, labs[k], (X0, Y0 + AH + 14), la)
        out.append(K.finish(b))
    return out


STYLES = {"headliner": strip, "visionary": viewfinder, "powerhouse": shelf, "saga": timeline, "pulse": mosaic,
          "prestige": deck, "legend": reel, "retro": vhs, "yerli": wipe}
QUALITY = {"retro": 64, "legend": 60, "visionary": 62, "prestige": 62, "yerli": 62}   # busy frames: about 2 MB
NEED = {"headliner": 3, "visionary": 3, "powerhouse": 3, "saga": 2, "pulse": 4, "prestige": 3, "legend": 3,
        "retro": 3, "yerli": 3}


def load(films):
    out = []
    for f in films:
        im = fetch(f.get("still"), "w1280")
        if not im:
            continue
        g = dict(f, img=im.convert("RGB"))
        if f.get("poster"):
            p = fetch(f["poster"], "w342")
            if p:
                g["pimg"] = p.convert("RGB")
        out.append(g)
    return out


def frames_for(slot, L, films, tr=False):
    return STYLES[slot](Kit(L, films, tr=tr))


def render(slot, L, films, out_path, tr=False):
    """films: [{title, year, still, poster}] (TMDB paths). False when there are too few films with stills."""
    films = load(films)
    if slot not in STYLES or len(films) < NEED.get(slot, 3):
        return False
    frames = frames_for(slot, L, films, tr)
    small = [f.resize((GW, GH), Image.LANCZOS) for f in frames]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    encode(small, [MS] * len(small), out_path, quality=QUALITY.get(slot, 72))
    return frames
