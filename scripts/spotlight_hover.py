"""Spotlight hover animations: each card gets its own take on the "filmography" idea (Ozzy, 30 Oct 2026). The cover
is rebuilt in layers (spotlight_art.cover_layers), so every loop starts and ends exactly on the cover; the hero
(portrait, poster or logo) steps aside, the subject's own titles come in as textless stills (or posters) with
"TITLE · YEAR", and the hero comes back.

  headliner  strip      a filmstrip of stills slides in from the right, one card settling after another
  visionary  viewfinder a camera viewfinder (2.39:1, frame lines, scene count): the films cut in with a slow push
  powerhouse shelf      the logo lifts; the studio's posters rise onto a shelf, three at a time
  saga       timeline   release order: numbered chapters ride along a timeline, a dot for each one
  pulse      mosaic     a 2x2 mosaic that pops in on the beat; one tile at a time lights up, a pulse line below
  prestige   deck       a gold-edged deck of stills; the top card is dealt away to show the next
  legend     reel       a 35 mm film strip runs up through the frame, black-and-white, with grain and flicker
  retro      vhs        a VHS tape plays: PLAY, tracking glitches between the films, the tape counter, STOP
  yerli      wipe       the stills take the portrait's place behind red diagonal wipes

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
    if l >= im.width or t >= im.height or x >= W or y >= H:
        return
    im = faded(im, a)
    crop = im.crop((l, t, min(im.width, W - x), min(im.height, H - y)))
    b.paste(crop, (x + l, y + t), crop)


def zoomed(im, w, h, z):
    """im cover-fitted to w x h at zoom z (about the centre)"""
    if z == 1:
        return cover_fit(im, w, h)
    big = cover_fit(im, round(w * z), round(h * z))
    x, y = (big.width - w) // 2, (big.height - h) // 2
    return big.crop((x, y, x + w, y + h))


class Kit:
    """what every style works with: the cover layers, the films, the accent and the label typography"""

    def __init__(self, L, films, tr=False):
        self.L, self.acc, self.tr = L, L.acc, tr
        self.up = (lambda t: t.replace("i", "İ").upper()) if tr else str.upper
        self.films = films
        self.cover = L.compose()

    def label(self, d, x, y, f, size=19, fill=(240, 240, 240)):
        d.rectangle((x, y + 3, x + 4, y + size), fill=self.acc)
        x = spaced(d, (x + 14, y), self.up(f["title"]), font("SemiBold", size), fill, 3)
        if f.get("year"):
            spaced(d, (x + 6, y), "·  " + str(f["year"]), font("Medium", size), (170, 170, 176), 3)

    def label_img(self, f, size=19, w=900):
        im = Image.new("RGBA", (w, size + 12), (0, 0, 0, 0))
        self.label(ImageDraw.Draw(im), 0, 0, f, size)
        return im.crop(im.getbbox() or (0, 0, 1, 1))

    def hero(self, b, dx=0, dy=0, a=1.0):
        if self.L.hero is not None:
            put(b, self.L.hero, (dx, dy), a)

    def finish(self, b):
        b.paste(self.L.text, (0, 0), self.L.text)
        return b


def card_img(im, w, h, border=None, bw=0, shadow=150, blur=14):
    """a still as a card with a soft shadow (and a border), padded by 24 px for the shadow"""
    pad = 24
    c = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", c.size, 0)
    ImageDraw.Draw(sh).rectangle((pad, pad + 8, pad + w, pad + h + 8), fill=shadow)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    c.paste(Image.new("RGBA", c.size, (0, 0, 0, 255)), (0, 0), sh)
    c.paste(cover_fit(im, w, h), (pad, pad))
    if border:
        ImageDraw.Draw(c).rectangle((pad, pad, pad + w - 1, pad + h - 1), outline=border, width=bw)
    return c


# ---------------------------------------------------------------------------------------------- headliner: strip
def strip(K):
    CW, CH, GAP, CY, CX = 640, 360, 26, 112, 580
    films = K.films[:5]
    cards = []
    for f in films:
        c = card_img(f["img"], CW, CH)
        cards.append((c, K.label_img(f)))
    n, step = len(cards), CW + GAP
    HOLD0, IN, HOLD, MOVE, OUT, HOLD1 = 18, 30, 24, 15, 32, 16
    keys, f = [(HOLD0, W - CX)], HOLD0 + IN
    keys.append((f, 0))
    for k in range(1, n):
        f += HOLD; keys.append((f, -step * (k - 1)))
        f += MOVE; keys.append((f, -step * k))
    f += HOLD; keys.append((f, -step * (n - 1)))
    f += OUT; keys.append((f, -step * (n - 1) - (CX + CW)))
    total, back = f + HOLD1, f - OUT
    fade = gradient_mask(W, H, [(0, 0), (0.36, 0), (0.47, 255), (1, 255)])
    pw = W - (K.L.hero.getbbox() or (W, 0, W, 0))[0] if K.L.hero is not None else 0
    out = []
    for i in range(total):
        pk = ramp(i, HOLD0, IN) if i < back else 1 - ramp(i, back, OUT)
        bg = ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.18 * pk) if pk else K.L.bg
        b = K.L.base(bg)
        if pk < 1:
            K.hero(b, dx=pk * (pw + 40), a=1 - pk * 0.85)
        if HOLD0 < i < total - HOLD1:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            o = keyed(keys, i)
            for k, (c, lab) in enumerate(cards):
                x = CX + o + k * step
                put(layer, c, (x - 24, CY - 24))
                put(layer, lab, (x, CY + CH + 20))
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), fade))
            b.paste(layer, (0, 0), layer)
        out.append(K.finish(b))
    return out


# ------------------------------------------------------------------------------------------ visionary: viewfinder
def viewfinder(K):
    FX, FY, FW, FH = 560, 108, 660, 372
    IW, IH = FW, round(FW / 2.39)
    IY = FY + (FH - IH) // 2
    films = K.films[:6]
    n = len(films)
    HOLD0, IN, SHOT, DIS, OUT, HOLD1 = 14, 22, 36, 8, 24, 12
    start = HOLD0 + IN - 6
    end = start + n * SHOT
    total = end + OUT + HOLD1
    labs = [K.label_img(f) for f in films]
    frame = Image.new("RGBA", (FW + 40, FH + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    o, L_ = 20, 34
    for (x, y, sx, sy) in ((o, o, 1, 1), (o + FW, o, -1, 1), (o, o + FH, 1, -1), (o + FW, o + FH, -1, -1)):
        d.line((x, y, x + sx * L_, y), fill=K.acc, width=3)
        d.line((x, y, x, y + sy * L_), fill=K.acc, width=3)
    cx, cy = o + FW // 2, o + FH // 2
    d.line((cx - 12, cy, cx + 12, cy), fill=(255, 255, 255, 110), width=1)
    d.line((cx, cy - 12, cx, cy + 12), fill=(255, 255, 255, 110), width=1)
    spaced(d, (o + FW - 92, o + 14), "2.39 : 1", font("SemiBold", 14), (230, 230, 230, 200), 2)
    out = []
    for i in range(total):
        pk = ramp(i, HOLD0, IN) if i < end else 1 - ramp(i, end, OUT)
        b = K.L.base(ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.3 * pk) if pk else None)
        if pk < 1:
            K.hero(b, dx=pk * 160, a=1 - pk)
        if pk > 0:
            s = 0.9 + 0.1 * pk
            gate = Image.new("RGBA", (FW, FH), (0, 0, 0, 255))
            k = min(n - 1, max(0, (i - start) // SHOT))
            t = i - start - k * SHOT
            shots = [(k, t)]
            if k > 0 and t < DIS:
                shots = [(k - 1, t + SHOT), (k, t)]
            for j, (kk, tt) in enumerate(shots):
                z = 1.0 + 0.07 * min(1.0, max(0.0, tt / (SHOT + DIS)))
                im = zoomed(films[kk]["img"], IW, IH, z)
                a = 1.0 if j == 0 else ease(tt / DIS)
                if a < 1:
                    base = gate.crop((0, IY - FY, IW, IY - FY + IH)).convert("RGB")
                    im = Image.blend(base, im, a)
                gate.paste(im, (0, IY - FY))
            g = ImageDraw.Draw(gate)
            spaced(g, (20, 16), f"SC {k + 1:02d}", font("SemiBold", 14), (230, 230, 230), 2)
            if (i // 12) % 2 == 0:
                g.ellipse((20 + 74, 20, 20 + 82, 28), fill=K.acc)
            fr = frame.copy()
            fr.paste(gate, (20, 20))
            ImageDraw.Draw(fr)
            if s != 1:
                fr = fr.resize((round(fr.width * s), round(fr.height * s)), Image.BICUBIC)
            fx = FX + (FW - FW * s) / 2 - 20 * s
            fy = FY + (FH - FH * s) / 2 - 20 * s
            put(b, fr, (fx, fy), pk)
            # the label changes with the cut
            la = pk * (1 if t >= 4 or k == 0 else t / 4)
            put(b, labs[k], (FX, FY + FH + 18), la)
        out.append(K.finish(b))
    return out


# ----------------------------------------------------------------------------------------------- powerhouse: shelf
def shelf(K):
    PW, PH, GAP, X0, Y0 = 200, 300, 22, 590, 132
    films = K.films[:6]
    sets = [films[:3], films[3:6]] if len(films) >= 6 else [films[:3]]
    posters = []
    for f in films:
        im = f.get("pimg") or f["img"]
        posters.append(card_img(im, PW, PH, shadow=170))
    years = []
    for f in films:
        y = Image.new("RGBA", (PW, 30), (0, 0, 0, 0))
        d = ImageDraw.Draw(y)
        d.rectangle((0, 4, 4, 22), fill=K.acc)
        spaced(d, (14, 0), str(f.get("year") or ""), font("SemiBold", 20), (235, 235, 235), 3)
        years.append(y)
    HOLD0, LOGO, RISE, STAG, HOLD, FALL, HOLD1 = 14, 20, 16, 6, 56, 14, 14
    plan, f0 = [], HOLD0 + 8
    for s in range(len(sets)):
        rise = f0
        fall = rise + RISE + 2 * STAG + HOLD
        plan.append((rise, fall))
        f0 = fall + 10
    back = plan[-1][1] + 6
    total = back + LOGO + HOLD1
    out = []
    for i in range(total):
        lk = ramp(i, HOLD0, LOGO) if i < back else 1 - ramp(i, back, LOGO)
        b = K.L.base(ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.3 * lk) if lk else None)
        K.hero(b, dy=-50 * lk, a=1 - lk)
        # the shelf line
        sl = lk
        if sl > 0:
            line = Image.new("RGBA", (round(3 * PW + 2 * GAP), 2), K.acc + (int(200 * sl),))
            put(b, line, (X0, Y0 + PH + 14))
        for s, (rise, fall) in enumerate(plan):
            for j in range(3):
                k = s * 3 + j
                if k >= len(films):
                    continue
                up_ = ramp(i, rise + j * STAG, RISE)
                down = ramp(i, fall + j * STAG, FALL)
                a = up_ * (1 - down)
                if a <= 0:
                    continue
                x = X0 + j * (PW + GAP)
                y = Y0 + 60 * (1 - up_) + 40 * down
                put(b, posters[k], (x - 24, y - 24), a)
                put(b, years[k], (x, Y0 + PH + 26), a)
        out.append(K.finish(b))
    return out


# -------------------------------------------------------------------------------------------------- saga: timeline
def timeline(K):
    CW, CH, GAP, CY, CX, LY = 560, 315, 30, 124, 600, 86
    films = K.films[:7]
    n, step = len(films), CW + GAP
    cards = []
    for k, f in enumerate(films):
        c = card_img(f["img"], CW, CH)
        d = ImageDraw.Draw(c)
        num = f"{k + 1:02d}"
        nf = font("ExtraBold", 84)
        shade = Image.new("L", (CW, 120), 0)
        for y in range(120):
            ImageDraw.Draw(shade).line((0, y, CW, y), fill=int(170 * y / 119))
        c.paste(Image.new("RGBA", (CW, 120), (0, 0, 0, 255)), (24, 24 + CH - 120), shade)
        d.text((24 + 18, 24 + CH - 100), num, font=nf, fill=(255, 255, 255, 0), stroke_width=2, stroke_fill=K.acc)
        cards.append((c, K.label_img(f, 18)))
    HOLD0, IN, HOLD, MOVE, OUT, HOLD1 = 16, 30, 22, 14, 30, 14
    keys, f = [(HOLD0, W - CX)], HOLD0 + IN
    keys.append((f, 0))
    for k in range(1, n):
        f += HOLD; keys.append((f, -step * (k - 1)))
        f += MOVE; keys.append((f, -step * k))
    f += HOLD; keys.append((f, -step * (n - 1)))
    f += OUT; keys.append((f, -step * (n - 1) - (CX + CW)))
    total, back = f + HOLD1, f - OUT
    fade = gradient_mask(W, H, [(0, 0), (0.37, 0), (0.47, 255), (1, 255)])
    out = []
    for i in range(total):
        pk = ramp(i, HOLD0, IN) if i < back else 1 - ramp(i, back, OUT)
        b = K.L.base(ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.25 * pk) if pk else None)
        if pk < 1:
            K.hero(b, dx=pk * 520, a=1 - pk * 0.9)
        if HOLD0 < i < total - HOLD1:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            d.line((CX - 60, LY, W, LY), fill=K.acc + (150,), width=2)
            o = keyed(keys, i)
            for k, (c, lab) in enumerate(cards):
                x = CX + o + k * step
                put(layer, c, (x - 24, CY - 24))
                put(layer, lab, (x, CY + CH + 18))
                d.line((x + 2, LY, x + 2, CY - 2), fill=K.acc + (140,), width=1)
                d.ellipse((x - 5, LY - 7, x + 9, LY + 7), fill=K.acc)
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), fade))
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * min(1, pk * 1.6))))
            b.paste(layer, (0, 0), layer)
        out.append(K.finish(b))
    return out


# --------------------------------------------------------------------------------------------------- pulse: mosaic
def mosaic(K):
    TW, TH, G, X0, Y0 = 304, 171, 14, 600, 112
    films = K.films[:8]
    sets = [films[:4], films[4:8]] if len(films) >= 8 else [films[:4]]
    tiles = [cover_fit(f["img"], TW, TH) for f in films]
    labs = [K.label_img(f) for f in films]
    pos = [(X0 + (j % 2) * (TW + G), Y0 + (j // 2) * (TH + G)) for j in range(4)]
    HOLD0, IN, BEAT, LIT, SWAP, OUT, HOLD1 = 14, 18, 6, 15, 14, 18, 12
    plan, f = [], HOLD0 + 6
    for s in range(len(sets)):
        pop = f
        lit = pop + 4 * BEAT + 6
        drop = lit + 4 * LIT
        plan.append((pop, lit, drop))
        f = drop + SWAP
    back = plan[-1][2] + 4
    total = back + OUT + HOLD1
    LY = Y0 + 2 * TH + G + 70
    out = []
    for i in range(total):
        pk = ramp(i, HOLD0, IN) if i < back else 1 - ramp(i, back, OUT)
        b = K.L.base(ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.35 * pk) if pk else None)
        K.hero(b, a=1 - pk)
        beats = []
        for s, (pop, lit, drop) in enumerate(plan):
            for j in range(4):
                k = s * 4 + j
                if k >= len(films):
                    continue
                t0 = pop + j * BEAT
                beats.append(t0)
                sc = 0.86 + 0.14 * ramp(i, t0, 8)
                a = ramp(i, t0, 6) * (1 - ramp(i, drop + j * 3, 10))
                if a <= 0:
                    continue
                on = lit + j * LIT <= i < lit + (j + 1) * LIT
                any_on = lit <= i < drop
                im = tiles[k]
                if any_on and not on:
                    im = ImageEnhance.Brightness(im).enhance(0.55)
                if on:
                    beats.append(lit + j * LIT)
                t = Image.new("RGBA", (TW + 8, TH + 8), (0, 0, 0, 0))
                t.paste(im, (4, 4))
                flash = max(0.0, 1 - (i - t0) / 10) if i >= t0 else 0
                if on or flash > 0:
                    ImageDraw.Draw(t).rectangle((1, 1, TW + 6, TH + 6), outline=K.acc + (int(255 * max(flash, on)),),
                                                width=3)
                if sc != 1:
                    t = t.resize((round(t.width * sc), round(t.height * sc)), Image.BICUBIC)
                x, y = pos[j]
                put(b, t, (x - 4 + (TW + 8) * (1 - sc) / 2, y - 4 + (TH + 8) * (1 - sc) / 2), a)
                if on:
                    put(b, labs[k], (X0, Y0 + 2 * TH + G + 22), min(1, (i - lit - j * LIT) / 4 + 0.25))
        if pk > 0:
            # the pulse line: a heartbeat blip on every beat, running out to the right
            line = Image.new("RGBA", (2 * TW + G, 60), (0, 0, 0, 0))
            d = ImageDraw.Draw(line)
            pts = []
            last = max([t for t in beats if t <= i], default=-99)
            age = i - last
            for x in range(0, line.width, 4):
                c = (age * 26) % (line.width + 120) - 60
                yv = 30
                dxp = x - c
                if -24 < dxp < 24 and age < 30:
                    yv = 30 - 22 * math.sin(math.pi * (dxp + 24) / 24) * math.exp(-abs(dxp) / 14)
                pts.append((x, yv))
            d.line(pts, fill=K.acc + (int(220 * pk),), width=2)
            put(b, line, (X0, LY - 30))
        out.append(K.finish(b))
    return out


# -------------------------------------------------------------------------------------------------- prestige: deck
def deck(K):
    CW, CH = 600, 338
    CX, CY = 905, 290
    films = K.films[:5]
    n = len(films)
    gold = K.acc
    cards = [card_img(f["img"], CW, CH, border=gold, bw=3, shadow=190, blur=16) for f in films]
    labs = [K.label_img(f) for f in films]
    ANG = [0, -3.5, 3, -2, 2.5, -1.5]
    HOLD0, IN, HOLD, DEAL, OUT, HOLD1 = 14, 26, 30, 16, 26, 12
    deal_at = [HOLD0 + IN + HOLD + k * (HOLD + DEAL) for k in range(n)]
    back = deal_at[-1] - 4
    total = back + OUT + HOLD1
    out = []
    for i in range(total):
        pk = ramp(i, HOLD0, IN) if i < back else 1 - ramp(i, back, OUT)
        b = K.L.base(ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.3 * pk) if pk else None)
        if pk < 1:
            K.hero(b, dx=pk * 400, a=1 - pk)
        enter = 1 - ramp(i, HOLD0, IN)
        dealt = sum(ramp(i, t, DEAL) for t in deal_at)          # how far through the deck, as a float
        for k in range(n - 1, -1, -1):
            depth = k - dealt
            if depth < -1:
                continue
            if depth < 0:                                   # being dealt away: off to the left, under the shade
                t = depth + 1
                x, y, ang, a = CX - 640 * (1 - t), CY + 30 * (1 - t), -10 * (1 - t), t
                s = 1
            else:
                dd = min(depth, 4)
                lo, hi = int(dd), min(int(dd) + 1, 5)
                ang = ANG[lo] + (ANG[hi] - ANG[lo]) * (dd - lo)
                s = 1 - 0.035 * dd
                x, y, a = CX + 14 * dd, CY - 10 * dd, 1 if depth < 3 else max(0, 4 - depth)
            x += 700 * enter + (700 * (1 - pk) if i >= back else 0)
            if a <= 0:
                continue
            c = cards[k]
            if depth > 0:
                c = Image.merge("RGBA", (*ImageEnhance.Brightness(c.convert("RGB")).enhance(1 - 0.12 * min(depth, 3))
                                         .split(), c.getchannel("A")))
            if depth <= 0.02 and depth >= 0 and k > 0:                # a gold shimmer across the card that just settled
                pass
            if s != 1:
                c = c.resize((round(c.width * s), round(c.height * s)), Image.BICUBIC)
            if ang:
                c = c.rotate(ang, resample=Image.BICUBIC, expand=True)
            put(b, c, (x - c.width / 2, y - c.height / 2), a)
        # shimmer on the top card
        top = min(n - 1, int(dealt + 0.001))
        settled = deal_at[top - 1] + DEAL if top > 0 else HOLD0 + IN
        st = (i - settled) / 22
        if 0 <= st <= 1 and pk > 0.5 and i < back:
            sh = Image.new("L", (W, H), 0)
            xs = CX - CW / 2 - 120 + (CW + 240) * ease(st)
            ImageDraw.Draw(sh).polygon([(xs, CY - CH / 2), (xs + 60, CY - CH / 2), (xs - 20, CY + CH / 2),
                                        (xs - 80, CY + CH / 2)], fill=70)
            clip = Image.new("L", (W, H), 0)
            ImageDraw.Draw(clip).rectangle((CX - CW / 2, CY - CH / 2, CX + CW / 2, CY + CH / 2), fill=255)
            sh = ImageChops.multiply(sh.filter(ImageFilter.GaussianBlur(10)), clip)
            b = Image.composite(Image.new("RGB", (W, H), (255, 236, 190)), b, sh)
        if pk > 0 and i < back:
            la = min(1, max(0, (i - (deal_at[top - 1] + DEAL if top > 0 else HOLD0 + IN - 6)) / 5))
            put(b, labs[top], (CX - CW / 2, CY + CH / 2 + 34), la * pk)
        out.append(K.finish(b))
    return out


# ---------------------------------------------------------------------------------------------------- legend: reel
def reel(K, seed=7):
    FW_, FH_, SP, PITCH = 368, 207, 36, 235
    SX = 790                                            # strip left edge
    STW = FW_ + 2 * SP
    films = K.films[:6]
    n = len(films)
    rnd = random.Random(seed)
    tone = []
    for f in films:
        g = ImageOps.grayscale(cover_fit(f["img"], FW_, FH_))
        g = ImageOps.autocontrast(g, cutoff=1)
        tone.append(ImageOps.colorize(g, (18, 14, 10), (238, 226, 205)))
    # the strip itself, long enough for every frame
    sh = PITCH * (n + 4)
    strip_ = Image.new("RGBA", (STW, sh), (16, 14, 12, 255))
    d = ImageDraw.Draw(strip_)
    for y in range(0, sh, 26):
        for x in (9, STW - 9 - 16):
            d.rounded_rectangle((x, y + 6, x + 16, y + 18), radius=3, fill=(0, 0, 0, 0))
    ef = font("SemiBold", 11)
    for k in range(n + 4):
        y = (k + 2) * PITCH - FH_ // 2
        if 0 <= k < n:
            strip_.paste(tone[k], (SP, y))
            d.text((SP + 4, y - 18), f"{k + 1:02d}  ▸  {films[k].get('year') or ''}", font=ef, fill=K.acc + (220,))
        else:
            d.rectangle((SP, y, SP + FW_, y + FH_), fill=(28, 25, 22, 255))
    holes = strip_.getchannel("A")
    labs = []
    for f in films:
        im = Image.new("RGBA", (330, 200), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        yf = font("ExtraBold", 52)
        txt = str(f.get("year") or "")
        dd.text((330 - dd.textlength(txt, font=yf), 0), txt, font=yf, fill=K.acc)
        tf = font("SemiBold", 19)
        y = 66
        for ln in wrap(dd, K.up(f["title"]), tf, 300)[:3]:
            dd.text((330 - dd.textlength(ln, font=tf), y), ln, font=tf, fill=(235, 230, 222))
            y += 26
        labs.append(im)
    HOLD0, IN, HOLD, MOVE, OUT, HOLD1 = 14, 30, 26, 14, 30, 12
    # offset = y of the strip's top; frame k is centred when top = H/2 - (k + 2) * PITCH
    c = lambda k: H / 2 - (k + 2) * PITCH
    keys, f = [(HOLD0, H + 40)], HOLD0 + IN
    keys.append((f, c(0)))
    for k in range(1, n):
        f += HOLD; keys.append((f, c(k - 1)))
        f += MOVE; keys.append((f, c(k)))
    f += HOLD; keys.append((f, c(n - 1)))
    f += OUT; keys.append((f, -sh - 20))
    total, back = f + HOLD1, f - OUT
    grain = [Image.effect_noise((STW // 4, H // 4), 40).resize((STW, H), Image.BILINEAR) for _ in range(6)]
    out = []
    for i in range(total):
        pk = ramp(i, HOLD0, IN) if i < back else 1 - ramp(i, back, OUT)
        b = K.L.base(ImageEnhance.Brightness(K.L.bg).enhance(1 - 0.3 * pk) if pk else None)
        if pk < 1:
            K.hero(b, dx=pk * 480, a=1 - pk * 0.9)
        if HOLD0 < i < total - HOLD1:
            top = keyed(keys, i)
            layer = Image.new("RGBA", (STW, H), (0, 0, 0, 0))
            t0 = int(max(0, -top))
            lo = min(sh, t0 + H - int(max(0, top)))
            if top < H and lo > t0:
                layer.paste(strip_.crop((0, t0, STW, lo)), (0, int(max(0, top))))
            rgb = layer.convert("RGB")
            fl = 1 + (rnd.random() - 0.5) * 0.08
            rgb = ImageEnhance.Brightness(rgb).enhance(fl)
            g = grain[i % len(grain)]
            rgb = ImageChops.overlay(rgb, Image.merge("RGB", (g, g, g)).point(lambda v: 128 + (v - 128) // 6))
            layer = Image.merge("RGBA", (*rgb.split(), layer.getchannel("A")))
            if rnd.random() < 0.08:                     # a scratch now and then
                x = rnd.randint(SP, SP + FW_)
                ImageDraw.Draw(layer).line((x, 0, x + rnd.randint(-6, 6), H), fill=(230, 222, 205, 70), width=1)
            put(b, layer, (SX, 0))
            # the label beside the frame in the gate
            k = int(round(min(n - 1, max(0, (H / 2 - top) / PITCH - 2))))
            near = abs((H / 2 - top) / PITCH - 2 - k)
            put(b, labs[k], (SX - 30 - 330, H / 2 - 70), max(0, 1 - near * 3) * pk)
        out.append(K.finish(b))
    return out


def osd_text(d, word, sym, fnt):
    """a VCR's on-screen word with its symbol drawn (VT323 has no ▶ or ■), top right, with a drop shadow"""
    x = W - 60 - 30 - 14 - d.textlength(word, font=fnt)
    for off, col in ((2, (0, 0, 0)), (0, (245, 245, 245))):
        d.text((x + off, 44 + off), word, font=fnt, fill=col)
        sx, sy = W - 60 - 30 + off, 58 + off
        if sym == "play":
            d.polygon([(sx, sy), (sx + 26, sy + 13), (sx, sy + 26)], fill=col)
        else:
            d.rectangle((sx + 2, sy + 2, sx + 24, sy + 24), fill=col)


# ------------------------------------------------------------------------------------------------------ retro: vhs
def vhs(K, seed=3):
    films = K.films[:5]
    n = len(films)
    rnd = random.Random(seed)
    RX = 400
    RW = W - RX
    mask = gradient_mask(RW, H, [(0, 0), (0.32, 255), (1, 255)])

    def tape(im):
        im = cover_fit(im, RW, H)
        r, g, b_ = im.split()
        r = ImageChops.offset(r, 4, 0)
        b_ = ImageChops.offset(b_, -3, 0)
        im = Image.merge("RGB", (r, g, b_)).filter(ImageFilter.GaussianBlur(1.8))   # tape softness
        im = ImageEnhance.Color(im).enhance(1.25)
        im = ImageEnhance.Contrast(im).enhance(1.08)
        return im

    stills = [tape(f["img"]) for f in films]
    lines = Image.new("L", (RW, H), 255)
    dl = ImageDraw.Draw(lines)
    for y in range(0, H, 5):                       # coarse enough to survive the 512 px hover
        dl.line((0, y, RW, y), fill=215)
        dl.line((0, y + 1, RW, y + 1), fill=215)
    osd = mono(46)
    small = mono(36)
    HOLD0, GL, PLAY, OUT, HOLD1 = 12, 8, 40, 10, 12
    t_in = HOLD0
    seg = [t_in + GL + k * (PLAY + GL) for k in range(n)]          # each film starts here
    stop = seg[-1] + PLAY
    total = stop + 12 + GL + HOLD1
    out = []

    def screen(k):
        bg = K.L.bg.copy()
        im = stills[k]
        bg.paste(im, (RX, 0), mask)
        return bg

    def glitch(img, amt):
        a = np.asarray(img).copy()
        h = a.shape[0]
        band = rnd.randint(0, h - 120)
        for y in range(band, band + rnd.randint(60, 140)):
            if y < h:
                a[y] = np.roll(a[y], int(rnd.gauss(0, 30 * amt)), axis=0)
        for _ in range(int(14 * amt)):
            y = rnd.randint(0, h - 3)
            a[y:y + rnd.randint(1, 3), RX:] = np.clip(a[y:y + 1, RX:].astype(int) + rnd.randint(60, 160), 0, 255)
        return Image.fromarray(a)

    noise = [Image.effect_noise((RW // 6, H // 6), 50).resize((RW, H), Image.BILINEAR).convert("RGB") for _ in range(4)]
    for i in range(total):
        if i < t_in:
            out.append(K.cover.copy())
            continue
        if i >= stop + 12 + GL:
            out.append(K.cover.copy())
            continue
        # which screen, and how hard the tape glitches
        if i < seg[0]:
            amt = 1 - abs((i - t_in) - GL / 2) / (GL / 2)
            scr = K.L.bg if i - t_in < GL / 2 else screen(0)
        elif i >= stop + 12:
            amt = 1 - abs((i - stop - 12) - GL / 2) / (GL / 2)
            scr = screen(n - 1) if i - stop - 12 < GL / 2 else K.L.bg
        else:
            k = min(n - 1, (i - seg[0]) // (PLAY + GL))
            t = i - seg[k]
            if t >= PLAY and k < n - 1:
                tt = t - PLAY
                amt = 1 - abs(tt - GL / 2) / (GL / 2)
                scr = screen(k if tt < GL / 2 else k + 1)
            else:
                amt, scr = 0.0, screen(k)
        scr = scr.copy()
        reg = scr.crop((RX, 0, W, H))
        reg = Image.composite(reg, Image.new("RGB", reg.size, (0, 0, 0)), lines)
        nz = noise[i % 4]
        reg = Image.blend(reg, ImageChops.add(reg, nz, scale=2.2), 0.12 + 0.7 * amt)
        scr.paste(reg, (RX, 0), mask)
        if amt > 0:
            scr = glitch(scr, amt)
        b = K.L.base(scr)
        if i < seg[0] and i - t_in < GL / 2 or i >= stop + 12 + GL / 2:
            K.hero(b)
        d = ImageDraw.Draw(b)
        # on-screen display, VCR style
        if i < stop:
            if (i - t_in) < 40 or (i // 14) % 2 == 0:
                osd_text(d, "PLAY", "play", osd)
        elif i < stop + 12 + GL:
            osd_text(d, "STOP", "stop", osd)
        if seg[0] <= i < stop:
            k = min(n - 1, (i - seg[0]) // (PLAY + GL))
            sec = (i - seg[0]) * MS // 1000
            cnt = f"SP  0:{sec // 60:02d}:{sec % 60:02d}"
            d.text((W - 60 - d.textlength(cnt, font=small), H - 92), cnt, font=small, fill=(235, 235, 235))
            f = films[k]
            name, yr = f["title"].upper(), str(f.get("year") or "")
            lab = f"{name}  {yr}"
            while d.textlength(lab, font=small) > 560 and len(name) > 4:
                name = name[:-2].rstrip()
                lab = f"{name}…  {yr}"
            x = W - 60 - d.textlength(lab, font=small)
            d.rectangle((x - 18, H - 132, x - 12, H - 104), fill=K.acc)
            d.text((x + 2, H - 136 + 2), lab, font=small, fill=(0, 0, 0))
            d.text((x, H - 136), lab, font=small, fill=(250, 250, 250))
        out.append(K.finish(b))
    return out


# ------------------------------------------------------------------------------------------------------ yerli: wipe
def wipe(K):
    films = K.films[:5]
    n = len(films)
    RX = 440
    RW = W - RX
    mask = gradient_mask(RW, H, [(0, 0), (0.33, 255), (1, 255)])
    red = K.acc
    labs = []
    for f in films:
        im = Image.new("RGBA", (760, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        tf = font("ExtraBold", 30)
        lines = wrap(d, K.up(f["title"]), tf, 520)[:2]
        y = 0
        for ln in lines:
            d.text((760 - d.textlength(ln, font=tf), y), ln, font=tf, fill=(255, 255, 255))
            y += 36
        yr = str(f.get("year") or "")
        yf = font("SemiBold", 18)
        x = 760 - d.textlength(yr, font=yf) - 3 * len(yr)
        d.rectangle((x - 16, y + 8, x - 10, y + 24), fill=red)
        spaced(d, (x, y + 6), yr, yf, (215, 215, 220), 3)
        labs.append(im.crop(im.getbbox() or (0, 0, 1, 1)))
    HOLD0, WIPE, HOLD, HOLD1 = 14, 16, 34, 14
    starts = [HOLD0 + k * (WIPE + HOLD) for k in range(n + 1)]     # the last wipe brings the portrait back
    total = starts[-1] + WIPE + HOLD1

    def scene(k, t):
        """k = -1: the cover's own right side (backdrop + portrait); else a still, slowly pushing in"""
        if k < 0 or k >= n:
            b = K.L.base()
            K.hero(b)
            return b
        bg = ImageEnhance.Brightness(K.L.bg).enhance(0.7)
        im = zoomed(films[k]["img"], RW, H, 1 + 0.06 * min(1, t / (WIPE + HOLD + WIPE)))
        bg.paste(im, (RX, 0), mask)
        return K.L.base(bg)

    out = []
    for i in range(total):
        k = max(-1, min(n, sum(1 for s in starts if i >= s) - 1))   # the wipe running (or last run)
        t = i - starts[k] if k >= 0 else 0
        prev = k - 1 if k < n else n - 1
        cur = k if k < n else n
        if k < 0:
            out.append(K.cover.copy())
            continue
        if t >= WIPE:
            b = scene(cur, t + WIPE)
        else:
            a = scene(prev, t + WIPE + HOLD + WIPE)
            c = scene(cur, t)
            p = ease(t / WIPE)
            lead = RX - 200 + (RW + 520) * p                 # the leading edge of the red band, slanted
            trail = lead - 170
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).polygon([(0, 0), (trail + 120, 0), (trail - 120, H), (0, H)], fill=255)
            band = Image.new("L", (W, H), 0)
            ImageDraw.Draw(band).polygon([(trail + 120, 0), (lead + 120, 0), (lead - 120, H), (trail - 120, H)],
                                         fill=255)
            reg = Image.new("L", (W, H), 0)
            ImageDraw.Draw(reg).rectangle((RX - 40, 0, W, H), fill=255)
            reg = reg.filter(ImageFilter.GaussianBlur(30))
            b = Image.composite(c, a, ImageChops.multiply(m, reg))
            b = Image.composite(Image.new("RGB", (W, H), red), b,
                                ImageChops.multiply(band, reg).point(lambda v: int(v * 0.92)))
        if 0 <= k < n:
            la = min(1.0, max(0.0, (t - WIPE + 4) / 6))
            if k + 1 <= n and i >= starts[k + 1] - 4:
                la = max(0.0, (starts[k + 1] - i) / 4)
            put(b, labs[k], (W - 60 - labs[k].width, 56), la)
        out.append(K.finish(b))
    return out


STYLES = {"headliner": strip, "visionary": viewfinder, "powerhouse": shelf, "saga": timeline, "pulse": mosaic,
          "prestige": deck, "legend": reel, "retro": vhs, "yerli": wipe}
QUALITY = {"retro": 60, "legend": 62, "yerli": 66, "prestige": 66}   # noisy or detailed frames: kept near 2 MB
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
    K = Kit(L, films, tr=tr)
    return STYLES[slot](K)


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
