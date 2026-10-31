"""Title logos for Iconic Actors and Legendary Directors on Nuvio TV (Ozzy, 31 Oct 2026), after Kaptain's: the
person's name set large in an elegant face with a soft silver finish, a fading rule, and CINEMATIC COLLECTION spaced
wide under it. Every logo is drawn on the same canvas at the same type size, so all names show at one size on the TV
(it fits the logo into 220x100 dp); long names take two lines rather than a smaller size."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import universe_motion as um
import folder_art as fa
import collection_mark as cm

um.FONTS.setdefault("playfair", "ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf")
um.FONTS.setdefault("cormorant", "ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf")
CW, CH = 1320, 600              # the canvas: the TV's logo box (220 x 100 dp) at 6x
SIZE = 126                      # the name's type size, the same for everyone
MAXW = 1300


def silver(mask, top=(255, 255, 255), bottom=(186, 192, 202)):
    h = mask.height
    g = np.linspace(0, 1, h)[:, None, None]
    rgb = (np.array(top) * (1 - g) + np.array(bottom) * g).astype(np.uint8)
    rgb = np.repeat(rgb, mask.width, axis=1)
    im = Image.fromarray(rgb, "RGB").convert("RGBA")
    im.putalpha(mask)
    return im


def lines_of(name, fnt):
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    if probe.textlength(name, font=fnt) <= MAXW:
        return [name]
    w = name.split()
    cut = min(range(1, len(w)), key=lambda i: abs(len(" ".join(w[:i])) - len(" ".join(w[i:]))))
    return [" ".join(w[:cut]), " ".join(w[cut:])]


def people_logo(name, sub="CINEMATIC COLLECTION", face="playfair", weight=600):
    fnt = um.font(face, SIZE, weight=weight)
    ls = lines_of(name, fnt)
    asc, desc = fnt.getmetrics()
    lh = round(SIZE * 1.08)
    m = Image.new("L", (CW, lh * len(ls) + desc + 40), 0)
    d = ImageDraw.Draw(m)
    lw = max(d.textlength(t, font=fnt) for t in ls)
    for i, t in enumerate(ls):                      # two-line names are centred on each other
        d.text(((lw - d.textlength(t, font=fnt)) / 2, 20 + i * lh), t, font=fnt, fill=255)
    m = m.crop(m.getbbox())
    name_im = silver(m)
    # the mark: one type size for everyone; its rules reach out to the name's width (at least a fixed span)
    mark = cm.mark(min(CW, max(name_im.width, 940)), "fade", (228, 230, 236), sub, size=36)
    gap = round(SIZE * 0.24)
    out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    bw = max(name_im.width, mark.width)
    block_h = name_im.height + gap + mark.height
    y = (CH - block_h) // 2
    nx = (bw - name_im.width) // 2
    sh = Image.new("RGBA", name_im.size, (0, 0, 0, 0))
    sh.putalpha(name_im.getchannel("A").point(lambda v: v * 0.5).filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(sh, (nx, y + 4))
    out.alpha_composite(name_im, (nx, y))
    out.alpha_composite(mark, ((bw - mark.width) // 2, y + name_im.height + gap))
    return out
