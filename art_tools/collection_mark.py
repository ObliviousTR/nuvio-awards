"""The COLLECTION mark under a universe's title logo on Nuvio TV (Ozzy, 31 Oct 2026), after Kaptain's collection
logo: the word, tracked wide, between two thin rules; the whole mark as wide as the title above it."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import universe_motion as um
import folder_art as fa


def mark(width, style="lines", color=(236, 236, 240), word="COLLECTION"):
    h = max(28, round(width * 0.052))
    T = um.trim(um.text_layer(word, fa.semi(h), color, round(h * 0.55)))
    gap = round(h * 0.9)
    rule = max(2, round(h * 0.07))
    side = max(0, (width - T.width) // 2 - gap)
    out = Image.new("RGBA", (max(width, T.width), T.height + 4), (0, 0, 0, 0))
    tx = (out.width - T.width) // 2
    out.alpha_composite(T, (tx, 2))
    if side > 8:
        y = 2 + T.height // 2 - rule // 2
        for x0, flip in ((0, False), (tx + T.width + gap, True)):
            seg = Image.new("RGBA", (side, rule), color + (255,))
            if style == "fade":                          # the rules fade out away from the word
                a = np.linspace(0, 255, side) if not flip else np.linspace(255, 0, side)
                seg.putalpha(Image.fromarray(np.tile(a, (rule, 1)).astype(np.uint8)))
            out.alpha_composite(seg, (x0, y))
            if style == "diamond":                       # a small diamond where the rule meets the word
                d = round(rule * 3.2)
                cx = x0 + side if not flip else x0
                ImageDraw.Draw(out).polygon([(cx - d, y + rule / 2), (cx, y + rule / 2 - d), (cx + d, y + rule / 2),
                                             (cx, y + rule / 2 + d)], fill=color + (255,))
    return out


def with_mark(logo, style="lines", color=(236, 236, 240)):
    logo = um.trim(logo.convert("RGBA"))
    m = mark(logo.width, style, color)
    gap = round(m.height * 0.9)
    out = Image.new("RGBA", (max(logo.width, m.width), logo.height + gap + m.height), (0, 0, 0, 0))
    out.alpha_composite(logo, ((out.width - logo.width) // 2, 0))
    out.alpha_composite(m, ((out.width - m.width) // 2, logo.height + gap))
    return out
