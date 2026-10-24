"""Spider-Verse card from a reference image Ozzy picked (a fan-made logo, found on Pinterest): the Disney+ promo line and
the small studio mark are taken out, the picture is set on a 16:9 cover, and the hover animates the picture itself:
the logo is lifted off its webs (inpainted behind), then a slow parallax breath, two short multiverse glitches
(red/cyan split, sliced bands) and a light sweep over the letters. Every motion is periodic: seamless loop.
Spider-Men of the films and series flip by inside the letters between the two glitches (stills: TMDB backdrops).
usage: python3 art_tools/spiderverse_ref.py REF.png OUT_DIR [--keep-marvel] [--stills A.jpg,B.jpg,...]
"""
import math, os, sys
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH = 1280, 720, 512, 288
N, MS = 200, 40          # 8 s
FLIP0, HOLD = 50, 8      # stills start at frame 50, 8 frames (320 ms) each


def load(ref, keep_marvel):
    a = np.asarray(Image.open(ref).convert("RGB")).copy()
    if not keep_marvel:
        a[318:368, 430:660] = 0                       # the small studio mark above the logo (on plain black)
    a = a[205:805]                                    # drop the Disney+ line below; keep the webs
    im = Image.fromarray(a)
    s = W / im.width
    im = im.resize((W, round(im.height * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.6, 60, 2))
    cv = Image.new("RGB", (W, H), (0, 0, 0))
    cv.paste(im, (0, (H - im.height) // 2))
    return cv, s, (H - im.height) // 2


def split_logo(cv, s, oy):
    a = np.asarray(cv).astype(np.uint8)
    lum = a.max(axis=2)
    box = np.zeros(lum.shape, np.uint8)
    x0, x1 = round(150 * s), round(935 * s)
    y0, y1 = round((385 - 205) * s) + oy, round((665 - 205) * s) + oy
    box[y0:y1, x0:x1] = 1
    m = ((lum > 42) & (box > 0)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    bg = cv2.inpaint(a, cv2.dilate(m, np.ones((7, 7), np.uint8)), 9, cv2.INPAINT_TELEA)
    logo = Image.fromarray(a).convert("RGBA")
    logo.putalpha(Image.fromarray(m).filter(ImageFilter.GaussianBlur(1.0)))
    R, G, B = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    face = (((R > G + 60) | ((B > G + 45) & (G < 130) & (R > 40))) & (m > 0)).astype(np.uint8) * 255
    face = cv2.morphologyEx(face, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    face = cv2.morphologyEx(face, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    global FACE, SHADE
    FACE = Image.fromarray(face).filter(ImageFilter.GaussianBlur(0.8))
    lum = a.mean(axis=2)
    SHADE = np.clip(lum / max(1, np.percentile(lum[face > 0], 90)), 0, 1.2)   # the hex pattern and the letter shading
    return Image.fromarray(bg), logo, (x0, y0, x1, y1)


FACE, SHADE, STILLS = None, None, []
TITLES = []                 # one per still: the line under the logo shows it while that still is up
LINE = "THE COLLECTION"
MODE = ["letters"]          # "letters": the heroes flip by inside the letters; "behind": full frame behind the logo


def fill_letters(lg, k):
    """the still of the moment, seen through the letter faces, keeping the letters' own shading"""
    i = (k - FLIP0) // HOLD
    if not STILLS or i < 0 or i >= len(STILLS):
        return lg
    st, (fx, fy) = STILLS[i]
    bb = FACE.getbbox()
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    z = 1.0 + 0.06 * ((k - FLIP0) % HOLD) / HOLD
    sc = max(bw / st.width, bh * 1.45 / st.height) * z           # the hero about as tall as the letters
    im = st.resize((round(st.width * sc), round(st.height * sc)), Image.BICUBIC)
    x0 = min(max(0, round(fx * im.width - bw / 2)), im.width - bw)
    y0 = min(max(0, round(fy * im.height - bh / 2)), im.height - bh)
    im = im.crop((x0, y0, x0 + bw, y0 + bh))
    full = Image.new("RGB", (W, H)); full.paste(im, bb[:2])
    arr = np.asarray(full, float) * (0.55 + 0.55 * SHADE[..., None])
    arr = np.clip(arr * 1.08, 0, 255).astype(np.uint8)
    fill = Image.fromarray(arr).convert("RGBA")
    fill.putalpha(ImageChops.multiply(FACE, lg.getchannel("A")))
    out = lg.copy()
    out.alpha_composite(fill)
    return out


def zoom(im, s, cx, cy):
    if abs(s - 1) < 1e-4:
        return im.copy()
    w, h = round(im.width * s), round(im.height * s)
    big = im.resize((w, h), Image.BICUBIC)
    x0, y0 = round(cx * s - cx), round(cy * s - cy)
    return big.crop((x0, y0, x0 + im.width, y0 + im.height))


def U_alpha(im, a):
    if a >= 1:
        return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: round(v * max(0, a)))); return im


def burst(k, a, b):
    """0..1..0 envelope for a glitch between frames a and b"""
    if k < a or k >= b:
        return 0.0
    return math.sin(math.pi * (k - a) / (b - a))


def frame(k, bg, logo, box, cover=False):
    cx, cy = W / 2, (box[1] + box[3]) / 2
    u = 0 if cover else k / N
    breath = 0.5 - 0.5 * math.cos(2 * math.pi * u)               # 0 -> 1 -> 0 over the loop
    out = zoom(bg, 1 + 0.03 * breath, cx, cy).convert("RGBA")
    if not cover and MODE[0] == "letters":
        logo = fill_letters(logo, k)
    if not cover and MODE[0] == "behind":
        i = (k - FLIP0) // HOLD
        if STILLS and 0 <= i < len(STILLS):
            st, (fx, fy) = STILLS[i]
            z = 1.0 + 0.05 * ((k - FLIP0) % HOLD) / HOLD
            sc = max(W / st.width, H / st.height) * z
            im = st.resize((round(st.width * sc), round(st.height * sc)), Image.BICUBIC)
            x0 = min(max(0, round(fx * im.width - W / 2)), im.width - W); y0 = min(max(0, round(fy * im.height - H / 2)), im.height - H)
            im = im.crop((x0, y0, x0 + W, y0 + H))
            a = min(1.0, (k - FLIP0) / 4, (FLIP0 + HOLD * len(STILLS) - k) / 4)
            dark = Image.blend(im, Image.new("RGB", (W, H)), 0.35).convert("RGBA")
            out.alpha_composite(U_alpha(dark, a))
    over_still = (not cover and MODE[0] == "behind" and STILLS and FLIP0 <= k < FLIP0 + HOLD * len(STILLS))
    if over_still:                                   # over a picture: only the letters themselves, with a soft shadow
        tight = logo.convert("L").point(lambda v: 255 if v > 62 else 0).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
        t = logo.copy(); t.putalpha(ImageChops.multiply(logo.getchannel("A"), tight))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(tight.filter(ImageFilter.GaussianBlur(12)).point(lambda v: round(v * 0.7)))
        logo = Image.new("RGBA", (W, H), (0, 0, 0, 0)); logo.alpha_composite(sh, (0, 6)); logo.alpha_composite(t)
    lg = zoom(logo, 1 + 0.075 * breath, cx, cy)
    end = FLIP0 + HOLD * len(STILLS)
    g = 0.0 if cover else max(burst(k, FLIP0 - 8, FLIP0 + 4), burst(k, end - 4, end + 8) * 0.9)
    if g > 0:
        r = np.random.default_rng(k)
        sh = round(14 * g)
        la = np.asarray(lg).copy()
        red = np.roll(la, -sh, axis=1); cyan = np.roll(la, sh, axis=1)
        ghost = np.zeros_like(la)
        ghost[..., 0] = red[..., 0]; ghost[..., 1] = cyan[..., 1]; ghost[..., 2] = cyan[..., 2]
        ghost[..., 3] = (np.maximum(red[..., 3], cyan[..., 3]) * 0.55 * g).astype(np.uint8)
        out.alpha_composite(Image.fromarray(ghost, "RGBA"))
        la2 = la.copy()
        for _ in range(int(3 + 5 * g)):                            # sliced bands, pushed sideways
            y = int(r.integers(box[1], box[3] - 8)); h = int(r.integers(6, 26)); dx = int(r.integers(-30, 30) * g)
            la2[y:y + h] = np.roll(la[y:y + h], dx, axis=1)
        lg = Image.fromarray(la2, "RGBA")
    out.alpha_composite(lg)
    if not cover and 150 <= k < 174:                                # light over the letters
        p = (k - 150) / 24
        band = Image.new("L", (W, H), 0)
        x = -200 + p * (W + 400)
        ImageDraw.Draw(band).polygon([(x - 60, 0), (x + 10, 0), (x - 140, H), (x - 210, H)], fill=150)
        letters = lg.convert("L").point(lambda v: 255 if v > 110 else 0).filter(ImageFilter.GaussianBlur(1))
        band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(18)), ImageChops.multiply(letters, lg.getchannel("A")))
        lay = Image.new("RGBA", (W, H), (255, 255, 255, 0)); lay.putalpha(band)
        out.alpha_composite(lay)
    draw_line(out, k, box, cover, g)
    return out.convert("RGB")


def line_font(size=24):
    for p in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", ".cache"),):
        for f in sorted(os.listdir(p)):
            if "Montserrat" in f:
                ft = ImageFont.truetype(os.path.join(p, f), size); ft.set_variation_by_axes([700]); return ft
    return ImageFont.load_default()


def text_layer(text, size=24, track=6, color=(225, 238, 255)):
    ft = line_font(size)
    ws = [ft.getlength(c) for c in text]
    tw = round(sum(ws) + track * (len(text) - 1)) + 4
    im = Image.new("RGBA", (tw, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im); x = 2
    for c, w in zip(text, ws):
        d.text((x, size * 0.3), c, font=ft, fill=color + (255,)); x += w + track
    return im.crop(im.getbbox() or (0, 0, 1, 1))


def draw_line(out, k, box, cover=False, glitch=0.0):
    """THE COLLECTION under the logo; while the heroes flip by, the title of each film / series runs through it"""
    y = box[3] + 34
    i = (k - FLIP0) // HOLD
    flipping = not cover and TITLES and 0 <= i < len(TITLES)
    if flipping:
        j = (k - FLIP0) % HOLD
        lay = text_layer(TITLES[i], size=22, track=4, color=(255, 255, 255))
        a = min(1.0, (j + 1) / 2); dy = round(10 * (1 - a))
    else:
        lay = text_layer(LINE, size=24, track=9)
        a, dy = 1.0, 0
    x = round(W / 2 - lay.width / 2)
    if glitch > 0:
        sh = round(10 * glitch)
        r = lay.copy(); r.putalpha(r.getchannel("A").point(lambda v: round(v * 0.8)))
        red = Image.new("RGBA", lay.size, (255, 40, 60, 0)); red.putalpha(r.getchannel("A"))
        cyan = Image.new("RGBA", lay.size, (40, 230, 255, 0)); cyan.putalpha(r.getchannel("A"))
        out.alpha_composite(red, (x - sh, y + dy)); out.alpha_composite(cyan, (x + sh, y + dy))
    out.alpha_composite(lay if a >= 1 else U_alpha(lay, a), (x, y + dy))


def tagline(im, y, text="EVERY SPIDER  ·  EVERY UNIVERSE"):
    font = None
    for p in ("/home/claude/nuvio-awards/scripts/.cache", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", ".cache")):
        if os.path.isdir(p):
            for f in os.listdir(p):
                if "Montserrat" in f:
                    font = ImageFont.truetype(os.path.join(p, f), 22); font.set_variation_by_axes([600]); break
        if font:
            break
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=font)
    d.text(((W - tw) / 2, y), text, font=font, fill=(205, 220, 255))


def main(ref, out, keep_marvel=False, stills=()):
    STILLS[:] = []
    for p in stills:                                   # path or path@fx:fy (where the hero is, 0..1)
        path, _, f = p.partition("@")
        fx, fy = (float(v) for v in f.split(":")) if f else (0.5, 0.5)
        STILLS.append((Image.open(path).convert("RGB"), (fx, fy)))
    cv, s, oy = load(ref, keep_marvel)
    bg, logo, box = split_logo(cv, s, oy)
    os.makedirs(out, exist_ok=True)
    cover = frame(0, bg, logo, box, cover=True)
    frames = [frame(k, bg, logo, box) for k in range(N)]
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=74)
    cover.save(os.path.join(out, "cover.jpg"), quality=92)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(cover, float)).mean())
    sheet = Image.new("RGB", (4 * 320, 3 * 180))
    for n, i in enumerate(range(0, N, N // 12)):
        if n < 12:
            sheet.paste(frames[i].resize((320, 180)), ((n % 4) * 320, (n // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", N, "seam", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    st = sys.argv[sys.argv.index("--stills") + 1].split(",") if "--stills" in sys.argv else []
    if "--titles" in sys.argv:
        TITLES[:] = sys.argv[sys.argv.index("--titles") + 1].split(";")
    if "--behind" in sys.argv:
        MODE[0] = "behind"
    main(sys.argv[1], sys.argv[2], "--keep-marvel" in sys.argv, st)
