"""Kaptain-style "layout sheet" cover + hover pair for the Anime cards Kaptain didn't make (Seinen, Legends, Films,
Sagas), so anime_art.py can animate them exactly like his.

Layout (measured off Kaptain's 2560x1440 sheets, drawn here at 1920x1080): blurred dark copy of the art behind a
sheet frame with three peg tabs, category-colour corner brackets, a vertical kanji column, the outlined category word,
a black "KEY FRAME · CUT nn" tag and the show name; a cut-out character group stands on the right and breaks out of
the frame. Hover: card edge lit in the colour, kanji / word / show name filled with it, the group 5.7 % bigger
(about the same anchor Kaptain uses) with a colour glow.
Writes <out>/<slug>/<slug>-cover.png, -hover.png and -core.png (the group's silhouette in its hover pose) plus
-fit.json (scale, anchor), which anime_art.py reads instead of guessing.
usage: python3 art_tools/anime_sheet.py SRC_DIR OUT_DIR [slug ...]
"""
import io, json, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import universe_motion as um
um.FONTS["jp"] = "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"

W, H = 1920, 1080
FR = (68, 83, 1185, 980)             # sheet frame
SCALE, ANCHOR = 1.057, (816, 1104)   # Kaptain's hover pose for the group
FONTS = os.path.join(ROOT, "spotlight", "fonts")


def mont(w, s):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat-{w}.ttf"), s)


# slug: word, kanji, tag, show, accent, inner art, [(cutout, height, (x, y) of its bottom-centre or right edge), ...]
CARDS = {
    "seasonal-currently-airing": dict(word="DISCOVER", kanji="発見", tag="LAYOUT  ·  CUT 03", show="THE APOTHECARY DIARIES",
        accent=(145, 229, 239), inner="new/apothecary_bd.jpg",
        group=[("new/apothecary.png", 930, ("c", 1420, 1080))]),
    "shonen-high-octane-action": dict(word="SHONEN", kanji="少年", tag="KEY FRAME  ·  CUT 12", show="JUJUTSU KAISEN",
        accent=(236, 98, 125), inner="new/jjk_bd.jpg",
        group=[("new/jjk.png", 960, ("c", 1420, 1080))]),
    "seinen-dark-psychological": dict(word="SEINEN", kanji="青年", tag="LAYOUT  ·  CUT 09", show="VINLAND SAGA",
        accent=(240, 128, 58), inner="seinen/fa_showbackground02_.jpg",
        group=[("cut/seinen.png", 960, ("c", 1330, 1072))]),
    "isekai-magic-fantasy-worlds": dict(word="ISEKAI", kanji="異世界", tag="IN-BETWEENS  ·  CUT 18",
        show="FRIEREN: BEYOND JOURNEY'S END", accent=(118, 215, 240), inner="new/frieren_bd.jpg",
        group=[("new/frieren.png", 1010, ("c", 1430, 1076))]),
    "romance-comedy-slice-of-life": dict(word="ROMANCE", kanji="日常", tag="TIMING  ·  CUT 05",
        show="KAGUYA-SAMA: LOVE IS WAR", accent=(242, 153, 205), inner="new/kaguya_bd.jpg",
        group=[("new/kaguya.png", 1000, ("r", 1920, 1080))]),
    "all-time-top-rated-anime": dict(word="LEGENDS", kanji="名作", tag="KEY FRAME  ·  CUT 01", show="ATTACK ON TITAN",
        accent=(238, 196, 88), inner="new/aot_bd.jpg",
        group=[("new/aot.png", 1000, ("c", 1420, 1078))]),
    "anime-movies-feature-films": dict(word="FILMS", kanji="映画", tag="CLEAN UP  ·  CUT 22", show="YOUR NAME.",
        accent=(168, 150, 250), inner="films/backdrop00_None.jpg",
        group=[("cut/films.png", 1130, ("r", 1920, 1080))]),
    "anime-film-collections": dict(word="SAGAS", kanji="劇場版", tag="COMPOSITE  ·  CUT 31", show="EVANGELION",
        accent=(134, 214, 96), inner="new/eva_bd.jpg",
        group=[("new/eva01.png", 1010, ("c", 1390, 1076))]),
    "studio-spotlight": dict(word="STUDIO", kanji="スタジオ", tag="CLEAN UP  ·  CUT 07", show="STUDIO GHIBLI",
        accent=(146, 186, 238), inner="new/spirited_bd.jpg",
        group=[("new/totoro.png", 940, ("c", 1420, 1072))]),
}


def cover_fit(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def cutout(path):
    im = Image.open(path).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 0 if v < 40 else v)
    im.putalpha(a)
    return im.crop(a.getbbox())


def group_layer(src, spec):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for path, hgt, (mode, x, y) in spec:
        im = cutout(os.path.join(src, path))
        im = im.resize((round(im.width * hgt / im.height), hgt), Image.LANCZOS)
        px = x - im.width if mode == "r" else x - im.width // 2
        lay.alpha_composite(im, (px, y - im.height)) if px >= 0 and y - im.height >= 0 else lay.paste(im, (px, y - im.height), im)
    return lay


def scaled(lay, s, ax, ay):
    a = 1 / s
    return lay.transform((W, H), Image.AFFINE, (a, 0, ax - a * ax, 0, a, ay - a * ay), Image.BICUBIC)


def glow(alpha, col, r, k):
    g = alpha.filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, int(v * k)))
    out = Image.new("RGBA", alpha.size, col + (0,))
    out.putalpha(g)
    return out


def tracked(d, xy, text, f, fill, sp):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + sp


def render(src, slug, c, out):
    acc = tuple(c["accent"])
    inner = Image.open(os.path.join(src, c["inner"])).convert("RGB")
    base = ImageEnhance.Brightness(cover_fit(inner, W, H).filter(ImageFilter.GaussianBlur(18))).enhance(0.42).convert("RGBA")
    x0, y0, x1, y1 = FR
    fw, fh = x1 - x0, y1 - y0
    pane = ImageEnhance.Contrast(cover_fit(inner, fw, fh)).enhance(1.04)
    shade = Image.new("L", (1, fh))
    for yy in range(fh):
        shade.putpixel((0, yy), round(150 * max(0.0, (yy / fh - 0.62) / 0.38) ** 1.3))   # darker foot for the type
    pane = Image.composite(Image.new("RGB", (fw, fh), (6, 6, 10)), pane, shade.resize((fw, fh)))
    m = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, fw - 1, fh - 1), 6, fill=255)
    base.paste(pane, (x0, y0), m)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(FR, 6, outline=(222, 222, 226, 255), width=3)
    for cx in (x0 + 60, (x0 + x1) // 2, x1 - 60):             # peg tabs
        d.rounded_rectangle((cx - 17, y0 - 22, cx + 17, y0 + 4), 6, fill=(236, 236, 238, 255))
        d.ellipse((cx - 6, y0 - 15, cx + 6, y0 - 3), fill=(10, 10, 12, 255))

    def brackets(dr):
        for (bx, by, sx, sy) in ((x0 - 8, y0 - 8, 1, 1), (x0 - 8, y1 + 10, 1, -1), (x1 + 8, y0 - 8, -1, 1), (x1 + 8, y1 + 10, -1, -1)):
            dr.line((bx, by, bx + 43 * sx, by), fill=acc + (255,), width=4)
            dr.line((bx, by, bx, by + 41 * sy), fill=acc + (255,), width=4)
    brackets(d)

    lay = group_layer(src, c["group"])
    jp = um.font("jp", 44, weight=800)
    wf = mont("ExtraBold", 150)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    while probe.textlength(c["word"], font=wf) > fw * 0.62 and wf.size > 80:
        wf = mont("ExtraBold", wf.size - 4)

    def type_layer(filled):
        t = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(t)
        ky = 120
        for ch in c["kanji"]:
            td.text((44, ky), ch, font=jp, fill=(acc if filled else (246, 246, 248)) + (255,))
            ky += 56
        wy = 828 - wf.getbbox("H")[3]
        if filled:
            td.text((88, wy), c["word"], font=wf, fill=acc + (255,), stroke_width=4, stroke_fill=(250, 250, 252, 255))
        else:
            mm = Image.new("L", (W, H), 0)
            md = ImageDraw.Draw(mm)
            md.text((88, wy), c["word"], font=wf, fill=255, stroke_width=4, stroke_fill=255)
            inner_m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(inner_m).text((88, wy), c["word"], font=wf, fill=255)
            ring = ImageChops.subtract(mm, inner_m)
            wl = Image.new("RGBA", (W, H), (236, 236, 240, 0))
            wl.putalpha(ring)
            t.alpha_composite(wl)
        lf = mont("SemiBold", 18)
        tw = sum(td.textlength(ch, font=lf) + 1.2 for ch in c["tag"])
        td.rectangle((85, 910, 85 + tw + 22, 937), fill=(4, 4, 6, 255))
        tracked(td, (96, 913), c["tag"], lf, (250, 250, 252, 255), 1.2)
        sf = mont("SemiBold", 21)
        tracked(td, (86, 950), c["show"].upper(), sf, (acc if filled else (212, 212, 218)) + (255,), 0.6)
        return t

    # cover
    cov = base.copy()
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: v * 120 // 255))
    cov.alpha_composite(ImageChops.offset(sh, 6, 8))
    cov.alpha_composite(lay)
    cov.alpha_composite(type_layer(False))

    # hover
    hov = base.copy()
    hl = scaled(lay, SCALE, *ANCHOR)
    a = hl.getchannel("A")
    hov.alpha_composite(glow(a, acc, 26, 1.6))
    hov.alpha_composite(glow(a, acc, 8, 1.4))
    hov.alpha_composite(hl)
    hov.alpha_composite(type_layer(True))
    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    em = Image.new("L", (W, H), 0)
    ImageDraw.Draw(em).rounded_rectangle((2, 2, W - 3, H - 3), 26, outline=255, width=4)
    edge.alpha_composite(glow(em, acc, 12, 1.2))
    el = Image.new("RGBA", (W, H), acc + (0,))
    el.putalpha(em)
    edge.alpha_composite(el)
    hov.alpha_composite(edge)

    d2 = os.path.join(out, slug)
    os.makedirs(d2, exist_ok=True)
    cov.convert("RGB").save(os.path.join(d2, f"{slug}-cover.png"))
    hov.convert("RGB").save(os.path.join(d2, f"{slug}-hover.png"))
    a.point(lambda v: 255 if v > 110 else 0).save(os.path.join(d2, f"{slug}-core.png"))
    json.dump({"scale": SCALE, "anchor": ANCHOR, "size": [W, H]}, open(os.path.join(d2, f"{slug}-fit.json"), "w"))
    print("built", slug)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    for slug in sys.argv[3:] or CARDS:
        render(src, slug, CARDS[slug], out)
