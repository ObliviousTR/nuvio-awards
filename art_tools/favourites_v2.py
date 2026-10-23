"""Favourites row, two looks on trial.
  A "pinboard"  the card is a cork board with one polaroid pinned to it, the name handwritten under the photo and a
                heart sticker; on hover the polaroid lifts, two more fan out from behind it, every photo slowly comes
                alive, the heart pops; then they tuck back and the card lands on the cover.
  C "rhythm"    as the Studios / Universes rows: the card's own short opening, the mark small in the corner while
                three pictures play (each named lower left), back to the cover.
Both loop seamlessly from the cover. Pictures: TMDB (Doctor Who, One Piece, trending series), Wikimedia Commons (sport).
usage: python3 art_tools/favourites_v2.py PICS_DIR OUT_DIR A|C [cards...]
"""
import io, math, os, random, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance
from reletter import f as font, tracked, width

W, H, OW, OH = 1280, 720, 512, 288
LOGOS = os.path.join(ROOT, "spotlight", "logos")
CACHE = os.path.join(ROOT, "scripts", ".cache")
HAND = "ofl/caveat/Caveat%5Bwght%5D.ttf"

# card -> logo, pictures (file stems in PICS_DIR), polaroid captions, label names for C (name, sub)
CARDS = {
    "doctorwho": {"logo": "whoniverse-gold.png", "title": "Doctor Who", "pics": ["dw23_2", "dw_5", "dw23_5"],
                  "notes": ["Doctor Who", "all the Doctors", "allons-y!"],
                  "labels": [("The TARDIS", "Bigger on the inside"), ("The Doctors", "Since 1963"), ("The Tenth Doctor", "Allons-y!")],
                  "accent": (70, 140, 255)},
    "onepace": {"logo": "onepace.png", "title": "One Pace", "pics": ["op_3", "op_1", "op_7"],
                "notes": ["One Pace", "Egghead", "Luffy!"],
                "labels": [("The Straw Hats", "One Pace"), ("Egghead", "The latest arc"), ("Monkey D. Luffy", "Captain")],
                "accent": (235, 70, 60)},
    "livesport": {"logo": "livesport-a.png", "title": "Live Sport", "pics": ["sport_cover", "sport_fb_0", "sport_bb_0"],
                  "notes": ["Live Sport", "matchday", "tip-off!"],
                  "labels": [("Live Sport", "Matches and replays"), ("Football", "Leagues and cups"), ("Basketball", "NBA and EuroLeague")],
                  "accent": (230, 40, 50)},
    "mysimkl": {"logo": "mysimkl-a.png", "title": "My Simkl", "pics": ["simkl_2", "simkl_1", "simkl_3"],
                "notes": ["My Simkl", "up next", "plan to watch"],
                "labels": None, "accent": (60, 200, 140)},
}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def out3(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def amul(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return im


def hand(size):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "Caveat.ttf")
    if not os.path.exists(p):
        open(p, "wb").write(urllib.request.urlopen("https://raw.githubusercontent.com/google/fonts/main/" + HAND, timeout=60).read())
    f = ImageFont.truetype(p, size)
    try:
        f.set_variation_by_axes([600])
    except Exception:
        pass
    return f


def fit(im, w, h):
    return ImageOps.fit(im.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.4))


def zoomed(im, z):
    if z <= 0:
        return im
    w, h = im.size
    dx, dy = w * z / 2, h * z / 2
    return im.crop((dx, dy, w - dx, h - dy)).resize((w, h), Image.BILINEAR)


# ---------------------------------------------------------------- A: pinboard
def cork(seed=4):
    rnd = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), np.float32) + np.array([138, 98, 62], np.float32)
    n = rnd.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 30) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) - 128
    base += n[..., None] * np.array([0.55, 0.45, 0.35])
    im = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for _ in range(2600):   # cork granules
        x, y = rnd.integers(0, W), rnd.integers(0, H)
        r = rnd.integers(1, 4)
        c = rnd.integers(60, 110) if rnd.random() < 0.6 else rnd.integers(170, 210)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(int(c), int(c * 0.72), int(c * 0.48)))
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse((-W * 0.25, -H * 0.35, W * 1.25, H * 1.35), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(140))
    return Image.composite(im, ImageEnhance.Brightness(im).enhance(0.45), v)


def polaroid(photo, note, pw=400):
    """A polaroid: white frame, the photo, a handwritten note in the wide bottom margin."""
    ph = round(pw * 0.78)
    m, mb = 22, 96
    card = Image.new("RGBA", (pw + 2 * m, ph + m + mb), (246, 243, 236, 255))
    card.paste(photo.resize((pw, ph), Image.LANCZOS), (m, m))
    d = ImageDraw.Draw(card)
    f = hand(54)
    while d.textlength(note, font=f) > pw and f.size > 30:
        f = hand(f.size - 2)
    tw = d.textlength(note, font=f)
    d.text(((card.width - tw) / 2, ph + m + 14), note, font=f, fill=(40, 38, 46, 255))
    return card


def pin(col=(214, 40, 48)):
    p = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    d.ellipse((14, 10, 50, 46), fill=col + (255,))
    d.ellipse((22, 16, 34, 28), fill=(255, 255, 255, 140))
    return p


def heart(size=70, col=(236, 60, 90)):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = s * 0.26
    d.ellipse((s * 0.5 - 2 * r, s * 0.18, s * 0.5, s * 0.18 + 2 * r), fill=col + (255,))
    d.ellipse((s * 0.5, s * 0.18, s * 0.5 + 2 * r, s * 0.18 + 2 * r), fill=col + (255,))
    d.polygon([(s * 0.5 - 2 * r + 4, s * 0.18 + r * 1.25), (s * 0.5 + 2 * r - 4, s * 0.18 + r * 1.25), (s * 0.5, s * 0.9)], fill=col + (255,))
    im = im.resize((size, size), Image.LANCZOS)
    o = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))   # white sticker edge
    edge = im.getchannel("A").filter(ImageFilter.MaxFilter(7))
    w = Image.new("RGBA", edge.size, (255, 255, 255, 255))
    w.putalpha(edge)
    o.alpha_composite(w, (6, 6))
    o.alpha_composite(im, (6, 6))
    return o


def place(cv, card, cx, cy, ang, sc=1.0, lift=0.0):
    c = card if sc == 1 else card.resize((round(card.width * sc), round(card.height * sc)), Image.LANCZOS)
    r = c.rotate(ang, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", r.size, (0, 0, 0, 0))
    sh.putalpha(r.getchannel("A").point(lambda v: round(v * (0.45 + 0.2 * lift))))
    sh = Image.merge("RGBA", (*Image.new("RGB", r.size, (0, 0, 0)).split(), sh.getchannel("A")))
    sh = sh.filter(ImageFilter.GaussianBlur(8 + 14 * lift))
    off = 6 + 22 * lift
    cv.alpha_composite(sh, (round(cx - r.width / 2 + off * 0.6), round(cy - r.height / 2 + off)))
    cv.alpha_composite(r, (round(cx - r.width / 2), round(cy - r.height / 2)))


def build_a(card, pics, out):
    c = CARDS[card]
    board = cork(hash(card) % 97).convert("RGBA")
    photos = [fit(p, 800, 624) for p in pics]
    PIN, HEART = pin(), heart()
    CX, CY = W / 2, H / 2 + 14

    def frame(t_open, kb, hp):
        """t_open 0..1: the fan; kb: Ken Burns time 0..1; hp: heart pop 0..1."""
        cv = board.copy()
        e = ease(t_open)
        # the two behind, fanning out to the sides
        for k, (dx, ang) in enumerate(((-385, 9), (385, -7))):
            if e <= 0.01:
                break
            ph = zoomed(photos[k + 1], 0.02 + 0.08 * kb)
            pc = polaroid(ph, c["notes"][k + 1], 390)
            place(cv, pc, CX + dx * e, CY + 18 - 6 * e, ang * e - 4 * (1 - e), 0.9 + 0.1 * e, 0.2 * e)
            if e > 0.6:
                cv.alpha_composite(amul(PIN, ease((e - 0.6) / 0.4)), (round(CX + dx * e - 32), round(CY + 18 - 6 * e - pc.height / 2 - 18)))
        # the front one lifts a little
        ph = zoomed(photos[0], 0.02 + 0.08 * kb * e)
        front = polaroid(ph, c["notes"][0], 470)
        place(cv, front, CX, CY - 8 * e, -3 + 1.5 * e, 1 + 0.04 * e, e)
        cv.alpha_composite(PIN, (round(CX - 32), round(CY - 8 * e - front.height / 2 - 22)))
        # heart sticker on the front polaroid's corner
        s = 1 + 0.35 * math.sin(math.pi * hp) if 0 < hp < 1 else 1
        hh = HEART.resize((round(HEART.width * s), round(HEART.height * s)), Image.LANCZOS)
        cv.alpha_composite(hh, (round(CX + 225 - hh.width / 2), round(CY + 205 - 8 * e - hh.height / 2)))
        return cv.convert("RGB")

    cover = frame(0, 0, 0)
    seq = []
    seq += [cover] * 6
    OPEN, HOLD, CLOSE, REST = 16, 56, 16, 8
    for i in range(OPEN):
        seq.append(frame(out3(i / (OPEN - 1)), 0, (i - 6) / 10 if i >= 6 else 0))
    for i in range(HOLD):
        seq.append(frame(1, i / (HOLD - 1), 0))
    for i in range(CLOSE):
        x = i / (CLOSE - 1)
        seq.append(frame(1 - ease(x), 1 - x, 0))
    seq += [cover] * REST
    return save(seq, cover, card, out)


# ---------------------------------------------------------------- C: rhythm
def build_c(card, pics, labels, out):
    c = CARDS[card]
    logo = Image.open(os.path.join(LOGOS, c["logo"])).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    k = min(W * 0.56 / logo.width, H * 0.3 / logo.height)
    logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    scenes = []
    for p in pics:
        im = fit(p, W, H)
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        d.ellipse((-W * 0.25, -H * 0.55, W * 0.55, H * 0.55), fill=205)
        d.ellipse((-W * 0.3, H * 0.62, W * 0.62, H * 1.3), fill=175)
        m = m.filter(ImageFilter.GaussianBlur(W * 0.08))
        scenes.append(Image.composite(Image.new("RGB", (W, H), (4, 5, 10)), im, m))
    stage = ImageEnhance.Brightness(fit(pics[0], W, H).filter(ImageFilter.GaussianBlur(3))).enhance(0.35)
    cx0, cy0 = W / 2, H / 2
    k_end = min(0.26 * W / logo.width, 0.2 * H / logo.height)
    tx, ty = 40 + logo.width * k_end / 2, 34 + logo.height * k_end / 2

    def lab(name, sub):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        t = name.upper()
        fn = font("ExtraBold", 40)
        tracked(d, (54, H - 120), t, fn, (255, 255, 255, 255), 3)
        tracked(d, (56, H - 120 + fn.size + 12), sub.upper(), font("SemiBold", 20), (210, 210, 210, 255), 8)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda v: round(v * 0.85)))
        sh.alpha_composite(lay)
        return sh
    labs = [lab(*x) for x in labels]

    def place_logo(cv, m, a=1.0, glow=0.0):
        s = 1 - (1 - k_end) * m
        L = logo if s == 1 else logo.resize((max(1, round(logo.width * s)), max(1, round(logo.height * s))), Image.LANCZOS)
        x, y = cx0 + (tx - cx0) * m, cy0 + (ty - cy0) * m
        if glow > 0:
            g = Image.new("RGBA", L.size, c["accent"] + (0,))
            g.putalpha(L.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, round(v * 2 * glow))))
            cv.alpha_composite(g, (round(x - L.width / 2), round(y - L.height / 2)))
        cv.alpha_composite(amul(L, a), (round(x - L.width / 2), round(y - L.height / 2)))

    def opening(u):
        """The card's own short opening, u 0..1, ends on the cover state."""
        cv = stage.convert("RGBA")
        if card == "doctorwho":       # the time vortex swirls up and the mark materialises (the TARDIS's fade in and out)
            v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(v)
            for r in range(0, 900, 22):
                a0 = (r * 0.9 + u * 540) % 360
                d.arc((W / 2 - r, H / 2 - r * 0.62, W / 2 + r, H / 2 + r * 0.62), a0, a0 + 120,
                      fill=(80, 150, 255, round(160 * (1 - abs(u - 0.5) * 2) * (1 - r / 900))), width=6)
            cv.alpha_composite(v.filter(ImageFilter.GaussianBlur(3)))
            a = (0.5 + 0.5 * math.sin(u * math.pi * 3 - math.pi / 2)) * ease(u / 0.5) if u < 0.83 else 1.0
            place_logo(cv, 0, max(a, ease((u - 0.8) / 0.2)), glow=0.6 * (1 - ease((u - 0.8) / 0.2)))
        elif card == "onepace":       # the mark sails in on a wave and bobs
            y = (1 - out3(u / 0.7)) * 260
            bob = math.sin(u * math.pi * 4) * 10 * (1 - ease((u - 0.7) / 0.3))
            L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            place_logo(L, 0)
            cv.alpha_composite(L, (0, round(y + bob)))
        elif card == "livesport":     # floodlights snap on one bank after another, then the mark
            for j in range(4):
                on = 1.0 if u > 0.12 + j * 0.13 else 0.0
                if on:
                    g = Image.new("L", (W, H), 0)
                    x = 120 + j * 340
                    ImageDraw.Draw(g).ellipse((x - 110, -80, x + 110, 120), fill=255)
                    g = g.filter(ImageFilter.GaussianBlur(60))
                    cv.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (255, 250, 235)).split(), g.point(lambda v: round(v * 0.55)))))
            place_logo(cv, 0, ease((u - 0.65) / 0.3))
        else:                         # My Simkl: posters flick by under the mark
            place_logo(cv, 0, ease(u / 0.6), glow=0.4 * (1 - ease((u - 0.6) / 0.4)))
        return cv

    cover = opening(1.0).convert("RGB")
    seq = [cover] * 6
    # out of the cover into the opening's first frame, then the opening
    OP = 30
    first = opening(0).convert("RGB")
    seq += [Image.blend(cover, first, ease(k / 7)) for k in range(8)]
    seq += [opening(i / (OP - 1)).convert("RGB") for i in range(OP)]
    MOVE, FILM, XF, BACK, REST = 12, 30, 8, 22, 8
    S = len(scenes)
    total = MOVE + FILM * S
    for i in range(total):
        q = i / total
        seg = min(S - 1, int(q * S))
        loc = q * S - seg
        m = out3(i / MOVE) if i < MOVE else 1.0
        bg = zoomed(scenes[seg], 0.02 + 0.05 * loc)
        if loc > 1 - XF / FILM and seg < S - 1:
            bg = Image.blend(bg, zoomed(scenes[seg + 1], 0.02), ease((loc - (1 - XF / FILM)) / (XF / FILM)))
        cv = Image.blend(stage, bg, m).convert("RGBA")
        la = ease((loc - 0.1) / 0.1) * (1 - ease((loc - 0.82) / 0.12))
        if seg == 0:
            la = ease((i - MOVE * 0.6) / 8) * (1 - ease((loc - 0.82) / 0.12))
        if la > 0:
            cv.alpha_composite(amul(labs[seg], la * m))
        place_logo(cv, m)
        seq.append(cv.convert("RGB"))
    last = zoomed(scenes[-1], 0.07)
    for i in range(BACK):
        u = out3(i / (BACK - 1))
        cv = Image.blend(last, stage, u).convert("RGBA")
        place_logo(cv, 1 - u)
        seq.append(cv.convert("RGB") if u < 1 else cover)
    seq += [cover] * REST
    return save(seq, cover, card, out)


def save(seq, cover, card, out):
    d = os.path.join(out, card)
    os.makedirs(d, exist_ok=True)
    small = [f.resize((OW, OH), Image.LANCZOS) for f in seq]
    small[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=small[1:], duration=[50] * len(small), loop=0,
                  quality=78, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    return len(small), os.path.getsize(os.path.join(d, "hover.webp")) // 1024


if __name__ == "__main__":
    pics_dir, out, look = sys.argv[1], sys.argv[2], sys.argv[3]
    names = {}
    for line in open(os.path.join(pics_dir, "list.txt"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and p[0].startswith("simkl_"):
            names[p[0]] = (p[1], p[2])
    for card in sys.argv[4:] or CARDS:
        c = CARDS[card]
        pics = [Image.open(os.path.join(pics_dir, s + ".jpg")) for s in c["pics"]]
        if look == "A":
            if card == "mysimkl":
                c["notes"] = [c["notes"][0]] + [names.get(s, ("", ""))[0] for s in c["pics"][1:]]
            print(card, build_a(card, pics, out))
        else:
            labels = c["labels"] or [names.get(s, ("", "")) for s in c["pics"]]
            print(card, build_c(card, pics, labels, out))
