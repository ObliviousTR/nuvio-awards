"""Spider-Verse card from a reference image Ozzy picked (a fan-made logo, found on Pinterest): the Disney+ promo line and
the small studio mark are taken out, the picture is set on a 16:9 cover, and the hover animates the picture itself:
the logo is lifted off its webs (inpainted behind), then a slow parallax breath, two short multiverse glitches
(red/cyan split, sliced bands) and a light sweep over the letters. Every motion is periodic: seamless loop.
usage: python3 art_tools/spiderverse_ref.py REF.png OUT_DIR [--keep-marvel]
"""
import math, os, sys
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH = 1280, 720, 512, 288
N, MS = 170, 40          # 6.8 s


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
    return Image.fromarray(bg), logo, (x0, y0, x1, y1)


def zoom(im, s, cx, cy):
    if abs(s - 1) < 1e-4:
        return im.copy()
    w, h = round(im.width * s), round(im.height * s)
    big = im.resize((w, h), Image.BICUBIC)
    x0, y0 = round(cx * s - cx), round(cy * s - cy)
    return big.crop((x0, y0, x0 + im.width, y0 + im.height))


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
    lg = zoom(logo, 1 + 0.075 * breath, cx, cy)
    g = 0.0 if cover else max(burst(k, 52, 66), burst(k, 118, 128) * 0.8)
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
    if not cover and 84 <= k < 108:                                 # light over the letters
        p = (k - 84) / 24
        band = Image.new("L", (W, H), 0)
        x = -200 + p * (W + 400)
        ImageDraw.Draw(band).polygon([(x - 60, 0), (x + 10, 0), (x - 140, H), (x - 210, H)], fill=150)
        letters = lg.convert("L").point(lambda v: 255 if v > 110 else 0).filter(ImageFilter.GaussianBlur(1))
        band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(18)), ImageChops.multiply(letters, lg.getchannel("A")))
        lay = Image.new("RGBA", (W, H), (255, 255, 255, 0)); lay.putalpha(band)
        out.alpha_composite(lay)
    return out.convert("RGB")


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


def main(ref, out, keep_marvel=False):
    cv, s, oy = load(ref, keep_marvel)
    bg, logo, box = split_logo(cv, s, oy)
    os.makedirs(out, exist_ok=True)
    cover = frame(0, bg, logo, box, cover=True)
    frames = [frame(k, bg, logo, box) for k in range(N)]
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=80)
    cover.save(os.path.join(out, "cover.jpg"), quality=92)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(cover, float)).mean())
    sheet = Image.new("RGB", (4 * 320, 3 * 180))
    for n, i in enumerate(range(0, N, N // 12)):
        if n < 12:
            sheet.paste(frames[i].resize((320, 180)), ((n % 4) * 320, (n // 4) * 180))
    sheet.save(os.path.join(out, "sheet.jpg"), quality=85)
    print("frames", N, "seam", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--keep-marvel" in sys.argv)
