"""Characterful TV title logos for the Based On, Reality TV and Documentaries rows (Ozzy, 31 Oct 2026: "dümdüz metin
güzel gözükmüyor, biraz hareket katalım"). Every logo sits on the same 2.2:1 transparent canvas, left aligned and
vertically centred, so Nuvio's 220x100 dp slot draws all of them at one size."""
import os, sys, re
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import universe_motion as um
import folder_art as fa

um.FONTS.update({
    "bangers": "ofl/bangers/Bangers-Regular.ttf",
    "pressstart": "ofl/pressstart2p/PressStart2P-Regular.ttf",
    "specialelite": "apache/specialelite/SpecialElite-Regular.ttf",
    "cinzeldeco": "ofl/cinzeldecorative/CinzelDecorative-Bold.ttf",
    "cinzel": "ofl/cinzel/Cinzel%5Bwght%5D.ttf",
    "playfairit": "ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
    "montit": "ofl/montserrat/Montserrat-Italic%5Bwght%5D.ttf",
    "bebas": "ofl/bebasneue/BebasNeue-Regular.ttf",
    "oswald": "ofl/oswald/Oswald%5Bwght%5D.ttf",
})
CW, CH = 1100, 500


def T(text, face, size, col=(255, 255, 255), tr=0, weight=None):
    return um.trim(um.text_layer(text, um.font(face, size, weight=weight), col, tr))


def stack(layers, gap, align="left"):
    w = max(l.width for l in layers)
    h = sum(l.height for l in layers) + gap * (len(layers) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for l in layers:
        out.alpha_composite(l, ((w - l.width) // 2 if align == "center" else 0, y))
        y += l.height + gap
    return out


def lines_of(title, limit=12):
    words = title.upper().split()
    if len(title) <= limit or len(words) < 2:
        return [title.upper()]
    cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:cut]), " ".join(words[cut:])]


def solid(layer, col):
    out = Image.new("RGBA", layer.size, tuple(col) + (0,))
    out.putalpha(layer.getchannel("A"))
    return out


def outline(layer, w, col=(10, 10, 14)):
    p = um.padded(layer, w + 2)
    e = solid(p, col)
    e.putalpha(p.getchannel("A").filter(ImageFilter.MaxFilter(2 * w + 1)))
    e.alpha_composite(p)
    return e


def on_canvas(logo, shadow=0.55, align="left"):
    """fit to the shared 2.2:1 canvas with a soft shadow so it reads over the bright parts of a hero"""
    pad = 24
    sh = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    sh.putalpha(logo.getchannel("A").point(lambda v: v * shadow).filter(ImageFilter.GaussianBlur(10)))
    lg = Image.new("RGBA", (logo.width + 40, logo.height + 44), (0, 0, 0, 0))
    lg.alpha_composite(sh, (20, 26)); lg.alpha_composite(logo, (20, 20))
    r = min((CW - pad) / lg.width, (CH - pad) / lg.height)
    lg = lg.resize((round(lg.width * r), round(lg.height * r)), Image.LANCZOS)
    out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    x = (CW - lg.width) // 2 if align == "center" else 0
    out.alpha_composite(lg, (x, (CH - lg.height) // 2))
    return out


# ---------------------------------------------------------------- Based On: each source in its own lettering
def _kicker(text, face, size, col, tr):
    return T(text, face, size, col, tr)


def _comics(word):
    W = um.trim(um.comic_word(word, 330, (255, 214, 40), ow=9))
    W = um.trim(W.rotate(4, Image.BICUBIC, expand=True))
    pop = solid(W, (230, 40, 50))                 # a red print offset behind the yellow, like a misregistered cover
    L = Image.new("RGBA", (W.width + 22, W.height + 22), (0, 0, 0, 0))
    L.alpha_composite(pop, (22, 22)); L.alpha_composite(W, (0, 0))
    # the kicker in a white caption box with a black frame, tilted the other way
    k = T("BASED ON", "bangers", 92, (14, 14, 18), 6)
    box = Image.new("RGBA", (k.width + 56, k.height + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rectangle((0, 0, box.width - 1, box.height - 1), fill=(14, 14, 18))
    d.rectangle((6, 6, box.width - 7, box.height - 7), fill=(255, 250, 235))
    box.alpha_composite(k, (28, 20))
    box = um.trim(box.rotate(-3, Image.BICUBIC, expand=True))
    out = Image.new("RGBA", (max(L.width, box.width + 30), L.height + box.height - 30), (0, 0, 0, 0))
    out.alpha_composite(L, (0, box.height - 30))
    out.alpha_composite(box, (30, 0))
    return out


def _games(word):
    a, b = word.split() if " " in word else (word, "")
    s = 150
    rows = [T(t, "pressstart", s, (255, 255, 255)) for t in (a, b) if t]
    M = stack(rows, round(s * 0.35))
    body = um.gradient_fill(M, (80, 240, 255), (255, 70, 220))
    step = round(s / 8)                            # one font pixel: the shadow steps by whole pixels
    shadow = Image.new("RGBA", (M.width + step * 3, M.height + step * 3), (0, 0, 0, 0))
    for i in range(1, 4):
        shadow.alpha_composite(solid(M, (40, 10, 90)), (step * i, step * i))
    L = Image.new("RGBA", shadow.size, (0, 0, 0, 0))
    L.alpha_composite(shadow); L.alpha_composite(body)
    # scanlines through the lettering
    sc = Image.new("L", L.size, 255)
    dd = ImageDraw.Draw(sc)
    for y in range(0, L.height, step):
        dd.rectangle((0, y + step - max(2, step // 4), L.width, y + step - 1), fill=150)
    L.putalpha(ImageChops.multiply(L.getchannel("A"), sc))
    G = um.padded(L, 40)
    glow = um.glow(G, 22, (255, 80, 230), 0.8)
    glow.alpha_composite(G)
    k = T("BASED ON", "pressstart", 46, (255, 225, 70), 8)
    hearts = _hearts(round(46 / 7))
    kr = Image.new("RGBA", (k.width + 40 + hearts.width, max(k.height, hearts.height)), (0, 0, 0, 0))
    kr.alpha_composite(k, (0, (kr.height - k.height) // 2))
    kr.alpha_composite(hearts, (k.width + 40, (kr.height - hearts.height) // 2))
    out = Image.new("RGBA", (max(glow.width, kr.width + 40), glow.height + kr.height - 10), (0, 0, 0, 0))
    out.alpha_composite(kr, (40, 0))
    out.alpha_composite(glow, (0, kr.height - 10))
    return out


def _hearts(px, n=3):
    H = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
    one = Image.new("RGBA", (7 * px, 6 * px), (0, 0, 0, 0))
    d = ImageDraw.Draw(one)
    for y, r in enumerate(H):
        for x, c in enumerate(r):
            if c == "1":
                d.rectangle((x * px, y * px, x * px + px - 1, y * px + px - 1), fill=(255, 60, 90))
    out = Image.new("RGBA", (one.width * n + px * 2 * (n - 1), one.height), (0, 0, 0, 0))
    for i in range(n):
        out.alpha_composite(one, (i * (one.width + px * 2), 0))
    return out


def _books(word):
    W = T(word.capitalize(), "playfairit", 340, (255, 255, 255), 2, weight=700)
    W = um.gradient_fill(W, (255, 236, 190), (214, 160, 80))
    k = T("BASED ON THE", "cinzel", 64, (236, 214, 170), 16, weight=600)
    # a flourish under the word: a hairline that thickens to a diamond in the middle
    fl = Image.new("RGBA", (W.width, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(fl); c = fl.width // 2
    col = (226, 186, 110, 255)
    d.polygon([(30, 20), (c - 30, 17), (c - 30, 23)], fill=col)
    d.polygon([(fl.width - 30, 20), (c + 30, 17), (c + 30, 23)], fill=col)
    d.polygon([(c, 4), (c + 16, 20), (c, 36), (c - 16, 20)], fill=col)
    return stack([k, W, fl], 26, "center")


def _true(word):
    rows = [outline(T(t, "specialelite", 230, (240, 234, 220), 6), 2, (240, 234, 220)) for t in word.split()]
    M = stack(rows, 20)
    # inked typewriter: a faint grain knocked out of the letters
    import random
    rnd = random.Random(7)
    g = Image.new("L", M.size, 255)
    dd = ImageDraw.Draw(g)
    for _ in range(M.width * M.height // 260):
        x, y = rnd.randrange(M.width), rnd.randrange(M.height)
        dd.point((x, y), fill=rnd.choice((60, 120, 180)))
    M.putalpha(ImageChops.multiply(M.getchannel("A"), g))
    # a red rubber stamp, slightly turned, overlapping the top-right of the text
    k = outline(T("BASED ON", "specialelite", 120, (226, 50, 50), 10), 2, (226, 50, 50))
    st = Image.new("RGBA", (k.width + 60, k.height + 46), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    d.rectangle((0, 0, st.width - 1, st.height - 1), outline=(226, 50, 50, 255), width=8)
    st.alpha_composite(k, (30, 23))
    sg = Image.new("L", st.size, 255)
    dd = ImageDraw.Draw(sg)
    for _ in range(st.width * st.height // 50):
        dd.point((rnd.randrange(st.width), rnd.randrange(st.height)), fill=0)
    st.putalpha(ImageChops.multiply(st.getchannel("A"), sg.filter(ImageFilter.MinFilter(3))))
    st = um.trim(st.rotate(-5, Image.BICUBIC, expand=True))
    out = Image.new("RGBA", (max(M.width, st.width), M.height + st.height - 10), (0, 0, 0, 0))
    out.alpha_composite(st, (0, 0))
    out.alpha_composite(M, (0, st.height - 10))
    return out


def _myth(word):
    W = T(word, "cinzeldeco", 210, (255, 255, 255), 10)
    W = um.gradient_fill(W, (255, 240, 196), (196, 140, 54))
    G = um.padded(W, 40)
    g = um.glow(G, 26, (255, 190, 90), 0.55)
    g.alpha_composite(G)
    k = T("BASED ON", "cinzel", 66, (240, 214, 160), 22, weight=700)
    rule = 150
    kr = Image.new("RGBA", (k.width + 2 * (rule + 40), k.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(kr); y = k.height // 2
    col = (226, 186, 110, 255)
    for x0, x1 in ((0, rule), (kr.width - rule, kr.width)):
        d.line((x0, y, x1, y), fill=col, width=4)
    for cx in (rule + 12, kr.width - rule - 12):
        d.polygon([(cx, y - 10), (cx + 10, y), (cx, y + 10), (cx - 10, y)], fill=col)
    kr.alpha_composite(k, (rule + 40, 0))
    f = T("& FOLKLORE", "cinzeldeco", 120, (255, 255, 255), 16)
    f = um.gradient_fill(f, (250, 228, 180), (200, 150, 70))
    return stack([kr, g, f], -10, "center")


def basedon_logo(word, look):
    """word: the emblem word (COMICS, VIDEO GAMES, BOOKS, TRUE STORIES, MYTHOLOGY); look: comic|game|book|true|myth"""
    f = {"comic": _comics, "game": _games, "book": _books, "true": _true, "myth": _myth}[look]
    return on_canvas(f(word))


# ---------------------------------------------------------------- Reality TV: a game-show lower third
def reality_logo(title, accent):
    accent = tuple(accent)
    ls = lines_of(title, 10)
    s = 200
    rows = []
    for i, t in enumerate(ls):
        col = accent if i == len(ls) - 1 else (255, 255, 255)
        L = T(t, "montit", s, col, 2, weight=900)
        rows.append(outline(L, 5, (12, 10, 18)))
    M = stack(rows, -6)
    # a slanted accent bar under the title, a thinner white one after it
    sk = 0.22
    bar_h = 26
    bar = Image.new("RGBA", (M.width, bar_h * 2 + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(bar)
    bw = round(M.width * 0.62)
    d.polygon([(bar_h * sk * 2, 0), (bw, 0), (bw - bar_h * sk * 2, bar_h), (0, bar_h)], fill=accent + (255,))
    d.polygon([(bw + 18, 0), (bw + 18 + round(M.width * 0.12), 0),
               (bw + 18 + round(M.width * 0.12) - bar_h * sk * 2, bar_h), (bw + 18 - bar_h * sk * 2, bar_h)],
              fill=(255, 255, 255, 255))
    # the REALITY TV tag: a slanted accent plate with a white play mark
    k = T("REALITY TV", "montit", 70, (14, 12, 20), 8, weight=900)
    pw, ph = k.width + 140, k.height + 40
    tag = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    off = round(ph * sk)
    d.polygon([(off, 0), (pw, 0), (pw - off, ph), (0, ph)], fill=(255, 255, 255, 255))
    d.polygon([(off, 0), (off + 70, 0), (70, ph), (0, ph)], fill=accent + (255,))
    tri = [(36, ph // 2 - 16), (36, ph // 2 + 16), (62, ph // 2)]
    d.polygon([(x + 4, y) for x, y in tri], fill=(255, 255, 255, 255))
    tag.alpha_composite(k, (100, 20))
    out = stack([tag, M, bar], 18)
    return on_canvas(out)


# ---------------------------------------------------------------- Documentaries: a camera viewfinder
def docs_logo(title, accent):
    accent = tuple(accent)
    ls = lines_of(title, 10)
    s = 250
    rows = [T(t, "bebas", s, (255, 255, 255), 14) for t in ls]
    M = stack(rows, 18)
    # REC dot + DOCUMENTARY label
    k = T("DOCUMENTARY", "oswald", 74, (230, 230, 230), 14, weight=600)
    r = k.height // 2 + 4
    kr = Image.new("RGBA", (k.width + 2 * r + 26, max(k.height, 2 * r)), (0, 0, 0, 0))
    d = ImageDraw.Draw(kr)
    cy = kr.height // 2
    d.ellipse((0, cy - r, 2 * r, cy + r), fill=(235, 40, 40, 255))
    kr.alpha_composite(k, (2 * r + 26, (kr.height - k.height) // 2))
    inner = stack([kr, M], 34)
    # viewfinder corners around everything
    px, py = 60, 46
    W, H = inner.width + 2 * px, inner.height + 2 * py
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    L, t = 100, 16
    col = accent + (255,)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (W - 1, 0, -1, 1), (0, H - 1, 1, -1), (W - 1, H - 1, -1, -1)):
        d.rectangle(sorted((x, x + sx * L)) and (min(x, x + sx * L), min(y, y + sy * t), max(x, x + sx * L), max(y, y + sy * t)), fill=col)
        d.rectangle((min(x, x + sx * t), min(y, y + sy * L), max(x, x + sx * t), max(y, y + sy * L)), fill=col)
    out.alpha_composite(inner, (px, py))
    return on_canvas(out)
