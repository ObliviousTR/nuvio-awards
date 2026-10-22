"""Re-letter Kaptain's director / actor cards whose name text is wrong (truncated, wrong subtitle, different style):
the old lettering is covered with the card's own bottom fade and the name is set again in the row's style
(Montserrat ExtraBold, tracked caps, small tracked subtitle). Works on both the cover and the focus (selected)
image; the focus image keeps its coloured frame and gets the accent bar.
usage: python3 art_tools/reletter.py OUT_DIR   (reads the delivered build + the local nuvio-art mirror)
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "spotlight", "fonts")
ART = "/home/claude/nuvio-art/"
RAW = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/"
JOBS = {  # folder title -> (name lines, subtitle)
    "Billy Wilder": (["BILLY", "WILDER"], "DIRECTOR"),
    "George Miller": (["GEORGE", "MILLER"], "DIRECTOR"),
    "Alejandro González Iñárritu": (["ALEJANDRO", "GONZÁLEZ IÑÁRRITU"], "DIRECTOR"),
    "Joel & Ethan Coen": (["JOEL & ETHAN", "COEN"], "DIRECTORS"),
    "Clint Eastwood": (["CLINT", "EASTWOOD"], "DIRECTOR"),
}


def f(w, s):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat-{w}.ttf"), s)


def tracked(d, xy, text, fnt, fill, sp):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + sp
    return x


def width(text, fnt, sp):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(c, font=fnt) + sp for c in text) - sp


def letter(im, lines, sub, focus=False, tint=None, fade=None):
    im = im.convert("RGB")
    W, H = im.size
    k = W / 1000
    inset = round(30 * k) if focus else 0
    # tint for the fade: the card's own colour just above the text block
    tint = tint or tuple(int(v * 0.55) for v in ImageStat.Stat(im.crop((inset + 20, int(H * 0.64), W - inset - 20, int(H * 0.66)))).mean)
    fade = Image.new("L", (W, H), 0)
    fd = ImageDraw.Draw(fade)
    if fade:  # soft: (start, max opacity) eased over the whole bottom, no solid block
        y0 = int(H * fade[0])
        for y in range(y0, H - inset):
            t = (y - y0) / (H - y0)
            fd.line((inset, y, W - inset, y), fill=int(255 * fade[1] * t * t * (3 - 2 * t)))
    else:
        y0 = int(H * 0.66)
        for y in range(y0, H - inset):
            fd.line((inset, y, W - inset, y), fill=min(255, int(255 * ((y - y0) / (H * 0.13)) ** 1.2)))
    im = Image.composite(Image.new("RGB", (W, H), tint), im, fade)
    d = ImageDraw.Draw(im)
    size = round(72 * k)
    sp = round(6 * k)
    x0 = round(100 * k)
    maxw = W - x0 - round(60 * k) - inset
    while max(width(l, f("ExtraBold", size), sp) for l in lines) > maxw:
        size -= 2
    fn = f("ExtraBold", size)
    lh = round(size * 1.12)
    base = round(H * 0.943) - round(30 * k)  # top of the subtitle line
    top = base - lh * len(lines) - round(10 * k)
    for i, l in enumerate(lines):
        tracked(d, (x0, top + i * lh), l, fn, (255, 255, 255), sp)
    tracked(d, (x0 + 2, base), sub, f("SemiBold", round(26 * k)), (175, 175, 175), round(9 * k))
    if focus:  # accent bar in the frame's colour
        edge = ImageStat.Stat(im.crop((round(6 * k), H // 2 - 50, round(12 * k), H // 2 + 50))).mean
        d.rectangle((x0 - round(26 * k), top + round(8 * k), x0 - round(22 * k), base + round(30 * k)), fill=tuple(int(v) for v in edge))
    return im


def slug(s):
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main(out):
    d = json.load(open(os.path.join(ROOT, "builder", "out", "delivered", "baseline.json"), encoding="utf-8"))
    for row in d:
        for fo in row["folders"]:
            if fo["title"] not in JOBS:
                continue
            lines, sub = JOBS[fo["title"]]
            dd = os.path.join(out, slug(fo["title"]))
            os.makedirs(dd, exist_ok=True)
            for key, name, focus in (("coverImageUrl", "cover.jpg", False), ("focusGifUrl", "focus.jpg", True)):
                u = fo.get(key)
                if not u:
                    continue
                src = Image.open(ART + u.split("?")[0].replace(RAW, ""))
                src.seek(0)
                letter(src, lines, sub, focus).save(os.path.join(dd, name), quality=90)
            print("lettered", fo["title"], dd)


if __name__ == "__main__":
    main(sys.argv[1])
