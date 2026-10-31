"""Title logos for Nuvio TV's hero (drawn at most 220x100 dp) where a folder has none or an unreadable one
(Ozzy, 31 Oct 2026). One family: a small kicker in the row's accent colour over the subject in heavy caps."""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import universe_motion as um
import folder_art as fa

um.FONTS.setdefault("jp", "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf")


def kicker_logo(main, kicker, accent, jp=None, maxw=1100):
    """main: the subject (caps, heavy); kicker: a small tracked label above it; jp: optional Japanese word set
    before the kicker in the accent colour"""
    size = 190
    import re
    lines = re.sub(r"(\d)S\b", r"\1s", main.upper()).split("\n")      # decades keep their small s: 80s

    def block(sz):
        ls = [um.trim(um.text_layer(t, fa.black(sz), (255, 255, 255), 4)) for t in lines]
        lh = max(l.height for l in ls) + round(sz * 0.12)
        b = Image.new("RGBA", (max(l.width for l in ls), lh * (len(ls) - 1) + ls[-1].height), (0, 0, 0, 0))
        for i, l in enumerate(ls):
            b.alpha_composite(l, (0, i * lh))
        return b
    M = block(size)
    while M.width > maxw and size > 60:
        size -= 8
        M = block(size)
    M.info["size"] = size
    ks = max(40, round(M.info["size"] * 0.26))      # the kicker follows the lettering's size, one line or two
    parts = []
    if jp:
        parts.append(um.trim(um.text_layer(jp, um.font("jp", round(ks * 1.08), weight=800), accent, 2)))
    parts.append(um.trim(um.text_layer(kicker.upper(), fa.black(ks), accent if not jp else (235, 235, 235),
                                       round(ks * 0.28))))
    gap = round(ks * 0.5)
    kw = sum(p.width for p in parts) + gap * (len(parts) - 1)
    kh = max(p.height for p in parts)
    vg = round(M.height * 0.22)
    W, H = max(M.width, kw) + 24, kh + vg + M.height + 24
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = 12
    for p in parts:
        out.alpha_composite(p, (x, 12 + (kh - p.height) // 2))
        x += p.width + gap
    out.alpha_composite(M, (12, 12 + kh + vg))
    # a soft shadow so the logo reads over the brighter parts of a hero
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.putalpha(out.getchannel("A").point(lambda v: v * 0.55).filter(ImageFilter.GaussianBlur(10)))
    final = Image.new("RGBA", out.size, (0, 0, 0, 0))
    final.alpha_composite(sh, (0, 4))
    final.alpha_composite(out)
    return um.trim(final)


def bar_logo(title, sub, accent, maxw=1150):
    """the cover's own type (Kids & Family, after Kaptain): an accent bar on the left, the title in heavy caps, the
    subtitle tracked small under it"""
    size = 150
    words = title.upper().split()
    if len(title) > 12 and len(words) > 1:          # long titles on two lines, so the TV draws them larger
        cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    else:
        lines = [title.upper()]

    def block(sz):
        ls = [um.trim(um.text_layer(t, fa.black(sz), (255, 255, 255), 2)) for t in lines]
        lh = max(l.height for l in ls) + round(sz * 0.12)
        b = Image.new("RGBA", (max(l.width for l in ls), lh * (len(ls) - 1) + ls[-1].height), (0, 0, 0, 0))
        for i, l in enumerate(ls):
            b.alpha_composite(l, (0, i * lh))
        return b
    T = block(size)
    while T.width > maxw and size > 60:
        size -= 6
        T = block(size)
    ss = max(30, round(size * 0.26))
    S = um.trim(um.text_layer(sub.upper(), fa.semi(ss), (235, 235, 235), round(ss * 0.22)))
    while S.width > T.width * 1.25 and ss > 24:
        ss -= 2
        S = um.trim(um.text_layer(sub.upper(), fa.semi(ss), (235, 235, 235), round(ss * 0.22)))
    gap = round(size * 0.16)
    bw = max(8, round(size * 0.075)); pad = round(size * 0.16)
    h = T.height + gap + S.height
    out = Image.new("RGBA", (bw + pad + max(T.width, S.width) + 24, h + 24), (0, 0, 0, 0))
    ImageDraw.Draw(out).rectangle((12, 12, 12 + bw, 12 + h), fill=tuple(accent) + (255,))
    out.alpha_composite(T, (12 + bw + pad, 12))
    out.alpha_composite(S, (12 + bw + pad, 12 + T.height + gap))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.putalpha(out.getchannel("A").point(lambda v: v * 0.55).filter(ImageFilter.GaussianBlur(10)))
    final = Image.new("RGBA", out.size, (0, 0, 0, 0))
    final.alpha_composite(sh, (0, 4)); final.alpha_composite(out)
    return um.trim(final)
