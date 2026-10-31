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
    if "\n" in title:
        return title.upper().split("\n")
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
    # one-line titles would be a thin strip on the TV: give them a second line from the folder's name
    title = {"INVESTIGATIVE": "INVESTIGATIVE\n& SCANDALS", "TRUE CRIME": "TRUE\nCRIME"}.get(title.upper(), title)
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


um.FONTS.update({
    "fredoka": "ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf",
    "pacifico": "ofl/pacifico/Pacifico-Regular.ttf",
    "creepster": "ofl/creepster/Creepster-Regular.ttf",
    "luckiest": "apache/luckiestguy/LuckiestGuy-Regular.ttf",
    "delagothic": "ofl/delagothicone/DelaGothicOne-Regular.ttf",
    "cormit": "ofl/cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf",
    "yellowtail": "apache/yellowtail/Yellowtail-Regular.ttf",
    "jp": "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf",
})


def extrude(layer, col, steps, dx=1, dy=1):
    out = Image.new("RGBA", (layer.width + steps * abs(dx), layer.height + steps * abs(dy)), (0, 0, 0, 0))
    s = solid(layer, col)
    for i in range(steps, 0, -1):
        out.alpha_composite(s, (i * dx, i * dy))
    out.alpha_composite(layer, (0, 0))
    return out


def mood_kicker(accent, size=58):
    return T("MOOD", "montit", size, tuple(accent), 18, weight=800)


# ---------------------------------------------------------------- Anime: a title card with a hanko-style plate
ANIME = {
    "Seasonal & Currently Airing": ("NOW AIRING", "放送中"),
    "Shonen & High-Octane Action": ("SHONEN", "少年"),
    "Seinen, Dark & Psychological": ("SEINEN", "青年"),
    "Isekai, Magic & Fantasy Worlds": ("ISEKAI", "異世界"),
    "Romance, Comedy & Slice of Life": ("SLICE OF LIFE", "日常"),
    "All-Time Top Rated Anime": ("TOP RATED", "名作"),
    "Anime Movies & Feature Films": ("MOVIES", "映画"),
    "Anime Film Collections": ("FILM SAGAS", "劇場版"),
    "Studio Spotlight": ("STUDIOS", "スタジオ"),
}


def anime_logo(main, jp, accent):
    accent = tuple(accent)
    dark = tuple(round(c * 0.45) for c in accent)
    rows = []
    for t in lines_of(main, 10):
        L = T(t, "delagothic", 190, (255, 255, 255), 4)
        L = um.trim(L.transform(L.size, Image.AFFINE, (1, 0.18, -L.height * 0.18, 0, 1, 0), Image.BICUBIC))  # italic lean
        L = Image.new("RGBA", (L.width + 40, L.height), (0, 0, 0, 0)) if False else L
        rows.append(L)
    M = stack(rows, 14)
    M = outline(M, 6, (12, 10, 16))
    M = extrude(M, dark, 10, 1, 1)
    # the Japanese word on an accent plate (a hanko-like seal) beside the ANIME kicker
    jpL = T(jp, "jp", 92, (255, 255, 255), 6, weight=900)
    plate = Image.new("RGBA", (jpL.width + 56, jpL.height + 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    d.rounded_rectangle((0, 0, plate.width - 1, plate.height - 1), radius=12, fill=accent + (255,))
    d.rounded_rectangle((7, 7, plate.width - 8, plate.height - 8), radius=8, outline=(255, 255, 255, 190), width=3)
    plate.alpha_composite(outline(jpL, 2, dark), (28 - 4, 18 - 4))
    k = T("ANIME", "montit", 70, accent, 24, weight=900)
    top = Image.new("RGBA", (plate.width + 30 + k.width, plate.height), (0, 0, 0, 0))
    top.alpha_composite(plate, (0, 0))
    top.alpha_composite(k, (plate.width + 30, (plate.height - k.height) // 2))
    out = stack([top, M], 22)
    return on_canvas(out)


# ---------------------------------------------------------------- Moods: each feeling in its own lettering
def _feelgood(a):
    W = T("FEEL-GOOD", "fredoka", 230, (255, 255, 255), 2, weight=700)
    W = um.gradient_fill(W, (255, 236, 90), (255, 150, 40))
    W = outline(W, 7, (255, 255, 255))
    W = extrude(W, (230, 90, 40), 8)
    # sun rays fanning out behind the top-left of the word
    rays = Image.new("RGBA", (W.width, W.height + 60), (0, 0, 0, 0))
    out = Image.new("RGBA", (W.width, W.height), (0, 0, 0, 0))
    out.alpha_composite(W)
    return stack([mood_kicker(a), out], 16)


def _cozy(a):
    W1 = T("Cozy &", "pacifico", 170, (255, 255, 255))
    W2 = T("Comforting", "pacifico", 170, (255, 255, 255))
    M = stack([W1, W2], -30)
    M.alpha_composite(Image.new("RGBA", M.size, (0, 0, 0, 0)))
    body = um.gradient_fill(M, (255, 232, 196), (240, 150, 80))
    g = um.padded(body, 40)
    gl = um.glow(g, 24, (255, 160, 70), 0.6)
    gl.alpha_composite(g)
    return stack([mood_kicker(a), gl], -10)


def _adrenaline(a):
    rows = [T(t, "montit", 200, (255, 255, 255), 0, weight=900) for t in ("ADRENALINE", "RUSH")]
    M = stack(rows, 16)
    M = um.trim(M.transform((M.width + 80, M.height), Image.AFFINE, (1, 0.22, -M.height * 0.22 + 0, 0, 1, 0),
                            Image.BICUBIC))
    body = um.gradient_fill(M, (255, 220, 60), (255, 60, 30))
    body = outline(body, 5, (20, 8, 4))
    # speed lines streaking off to the left
    out = Image.new("RGBA", (body.width + 260, body.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    import random
    rnd = random.Random(3)
    for i in range(9):
        y = round((i + 0.5) * body.height / 9 + rnd.uniform(-8, 8))
        ln = rnd.randint(140, 250)
        d.polygon([(260 - ln, y), (270, y - 5), (270, y + 5)], fill=(255, 120 + rnd.randint(0, 100), 40, 230))
    out.alpha_composite(body, (240, 0))
    return stack([Image.new("RGBA", (240, 1)), ], 0) if False else stack([_indent(mood_kicker(a), 240), out], 14)


def _indent(l, x):
    o = Image.new("RGBA", (l.width + x, l.height), (0, 0, 0, 0))
    o.alpha_composite(l, (x, 0))
    return o


def _epic(a):
    W1 = T("EPIC", "cinzel", 230, (255, 255, 255), 30, weight=900)
    W2 = T("& SWEEPING", "cinzel", 110, (255, 255, 255), 26, weight=700)
    W1 = um.gradient_fill(W1, (255, 242, 200), (200, 150, 70))
    W2 = um.gradient_fill(W2, (250, 230, 180), (210, 160, 80))
    w = max(W1.width, W2.width)
    # a sweeping arc between the two words
    arc = Image.new("RGBA", (w, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(arc)
    for i in range(6):
        d.arc((-w * 0.1, 10 + i * 0.6, w * 1.1, 260), 200, 340, fill=(226, 186, 110, 255 - i * 30), width=3)
    M = stack([W1, arc, W2], 0, "center")
    g = um.padded(M, 30)
    gl = um.glow(g, 22, (255, 200, 110), 0.4)
    gl.alpha_composite(g)
    return stack([_indent(mood_kicker(a), 30), gl], 0)


def _mind(a):
    W = stack([T(t, "montit", 210, (255, 255, 255), 0, weight=900) for t in ("MIND-", "BENDING")], -4)
    W = um.padded(W, 30)
    out = Image.new("RGBA", W.size, (0, 0, 0, 0))
    out.alpha_composite(solid(W, (0, 230, 255)), (0, 0))
    out = ImageChops.add(out, Image.new("RGBA", W.size, (0, 0, 0, 0)))
    m = Image.new("RGBA", W.size, (0, 0, 0, 0))
    m.alpha_composite(solid(W, (0, 230, 255)), (-14, 0))
    m2 = Image.new("RGBA", W.size, (0, 0, 0, 0))
    m2.alpha_composite(solid(W, (255, 40, 200)), (14, 0))
    m.alpha_composite(m2)
    m.alpha_composite(W)
    # glitch: shift a few horizontal slices
    import random
    rnd = random.Random(5)
    res = m.copy()
    for _ in range(5):
        y = rnd.randrange(30, m.height - 40); h = rnd.randint(8, 22); dx = rnd.choice((-1, 1)) * rnd.randint(14, 34)
        sl = m.crop((0, y, m.width, y + h))
        res.paste((0, 0, 0, 0), (0, y, m.width, y + h))
        res.alpha_composite(sl, (dx if dx > 0 else 0, y), (0 if dx > 0 else -dx, 0))
    return stack([_indent(mood_kicker(a), 30), res], 4)


def _slowburn(a):
    W = T("Slow Burn", "cormit", 300, (255, 255, 255), 0, weight=600)
    body = um.gradient_fill(W, (255, 236, 200), (255, 110, 30))
    g = um.padded(body, 50)
    ember = um.glow(g, 30, (255, 90, 20), 0.85)
    ember2 = um.glow(g, 8, (255, 160, 60), 0.6)
    ember.alpha_composite(ember2); ember.alpha_composite(g)
    return stack([_indent(mood_kicker(a), 50), ember], -20)


def _gritty(a):
    import random
    rnd = random.Random(11)
    rows = [T("DARK &", "bebas", 260, (236, 230, 222), 10), T("GRITTY", "bebas", 260, (196, 34, 38), 10)]
    M = stack(rows, 8)
    g = Image.new("L", M.size, 255)
    d = ImageDraw.Draw(g)
    for _ in range(M.width * M.height // 400):
        x, y = rnd.randrange(M.width), rnd.randrange(M.height); r = rnd.choice((1, 1, 2, 2, 3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice((0, 60, 120)))
    for _ in range(8):           # scratches
        x = rnd.randrange(M.width); y = rnd.randrange(M.height)
        d.line((x, y, x + rnd.randint(-50, 50), y + rnd.randint(40, 120)), fill=40, width=2)
    M.putalpha(ImageChops.multiply(M.getchannel("A"), g.filter(ImageFilter.GaussianBlur(0.6))))
    return stack([mood_kicker(a), M], 14)


def _spooky(a):
    rows = [T(t, "creepster", 220, (255, 255, 255), 6) for t in ("SPOOKY &", "CREEPY")]
    M = stack(rows, 4)
    body = um.gradient_fill(M, (210, 255, 170), (70, 200, 90))
    g = um.padded(body, 40)
    gl = um.glow(g, 26, (90, 255, 110), 0.75)
    gl.alpha_composite(outline(g, 3, (10, 30, 10)), (-5, -5))
    return stack([_indent(mood_kicker(a), 40), gl], -10)


def _tears(a):
    W = T("Tearjerkers", "playfairit", 230, (255, 255, 255), 0, weight=700)
    body = um.gradient_fill(W, (235, 245, 255), (130, 175, 230))
    # a single tear falling from the dot of the j
    drop = Image.new("RGBA", (70, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(drop)
    d.ellipse((8, 40, 62, 94), fill=(150, 200, 255, 255))
    d.polygon([(35, 0), (10, 62), (60, 62)], fill=(150, 200, 255, 255))
    d.ellipse((20, 56, 34, 70), fill=(235, 248, 255, 255))
    out = Image.new("RGBA", (body.width + 90, body.height + 40), (0, 0, 0, 0))
    out.alpha_composite(body, (0, 0))
    out.alpha_composite(drop, (body.width + 14, body.height - 90))
    return stack([mood_kicker(a), out], 6)


def _retro(a):
    N = T("80s & 90s", "montit", 210, (255, 255, 255), 0, weight=900)
    N = um.trim(N.transform((N.width + 60, N.height), Image.AFFINE, (1, 0.2, -N.height * 0.2, 0, 1, 0), Image.BICUBIC))
    # chrome: sky blue to white above a hard horizon, dark to pink below
    w, h = N.size
    g = Image.new("RGBA", (w, h))
    for y in range(h):
        f = y / h
        if f < 0.55:
            c = tuple(round(a0 + (b0 - a0) * f / 0.55) for a0, b0 in zip((60, 140, 255), (235, 250, 255)))
        else:
            c = tuple(round(a0 + (b0 - a0) * (f - 0.55) / 0.45) for a0, b0 in zip((60, 20, 90), (255, 120, 220)))
        g.paste(c + (255,), (0, y, w, y + 1))
    g.putalpha(N.getchannel("A"))
    g = outline(g, 4, (255, 255, 255))
    V = T("Vibes", "yellowtail", 230, (255, 70, 180))
    V = um.trim(V.rotate(6, Image.BICUBIC, expand=True))
    Vg = um.padded(V, 30)
    neon = um.glow(Vg, 18, (255, 60, 170), 0.9)
    neon.alpha_composite(Vg)
    out = Image.new("RGBA", (max(g.width, round(g.width * 0.42) + neon.width), g.height + neon.height - 120), (0, 0, 0, 0))
    out = Image.new("RGBA", (max(g.width, round(g.width * 0.5) + neon.width), g.height + neon.height - 70), (0, 0, 0, 0))
    out.alpha_composite(g, (0, 0))
    out.alpha_composite(neon, (round(g.width * 0.5), g.height - 70))
    return stack([mood_kicker(a), out], 10)


MOODS = {"Feel-Good": _feelgood, "Cozy & Comforting": _cozy, "Adrenaline Rush": _adrenaline,
         "Epic & Sweeping": _epic, "Mind-Bending": _mind, "Slow Burn": _slowburn, "Dark & Gritty": _gritty,
         "Spooky & Creepy": _spooky, "Tearjerkers": _tears, "80s & 90s Vibes": _retro}


def mood_logo(folder, accent):
    return on_canvas(MOODS[folder](tuple(accent)))


# ---------------------------------------------------------------- Kids & Family: bouncy, many-coloured letters
KIDS_COLS = [(255, 204, 40), (255, 92, 130), (70, 200, 255), (120, 222, 90), (176, 120, 255), (255, 146, 50)]


def kids_logo(title, accent, seed=0):
    f = um.font("luckiest", 190)
    rows = []
    ci = seed
    for li, t in enumerate(lines_of(title, 10)):
        glyphs = []
        for j, c in enumerate(t):
            if c == " ":
                glyphs.append(None)
                continue
            g = um.trim(um.text_layer(c, f, (255, 255, 255)))
            col = KIDS_COLS[ci % len(KIDS_COLS)]; ci += 1
            g = um.gradient_fill(g, tuple(min(255, v + 50) for v in col), col)
            g = outline(g, 9, (255, 255, 255))
            g = extrude(g, (30, 30, 70), 7)
            g = g.rotate((-5, 4, -2, 6, -4, 3)[j % 6], Image.BICUBIC, expand=True)
            glyphs.append(g)
        sp = round(190 * 0.3)
        w = sum(g.width - 14 if g else sp for g in glyphs)
        h = max(g.height for g in glyphs if g) + 24
        row = Image.new("RGBA", (w + 20, h), (0, 0, 0, 0))
        x = 0
        for j, g in enumerate(glyphs):
            if g is None:
                x += sp; continue
            row.alpha_composite(g, (x, 12 + (-10, 6, -4, 10, -8, 2)[j % 6] + (h - 24 - g.height) // 2))
            x += g.width - 14
        rows.append(um.trim(row))
    M = stack(rows, -10)
    return on_canvas(M)
