"""Spotlight card art: a 1280x720 cover (text on the image, since the Nuvio folder hides its title) and a
1920x1080 hero backdrop. Pillow only; images come from the TMDB image CDN."""
import io, os, urllib.request
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "spotlight", "fonts")
IMG = "https://image.tmdb.org/t/p/"
W, H = 1280, 720


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat-{weight}.ttf"), size)


def fetch(path, size="original"):
    if not path:
        return None
    req = urllib.request.Request(IMG + size + path, headers={"User-Agent": "nuvio-spotlight"})
    for _ in range(3):
        try:
            return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
        except Exception:
            continue
    return None


def cover_fit(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 4  # keep faces (upper part) in frame
    return im.crop((x, y, x + w, y + h))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient_mask(w, h, stops):
    """Horizontal alpha mask; stops = [(x_fraction, alpha 0-255), ...]."""
    m = Image.new("L", (w, 1))
    px = m.load()
    for x in range(w):
        f = x / max(1, w - 1)
        for (f0, a0), (f1, a1) in zip(stops, stops[1:]):
            if f0 <= f <= f1:
                px[x, 0] = round(a0 + (a1 - a0) * (f - f0) / max(1e-6, f1 - f0))
                break
    return m.resize((w, h))


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if draw.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def spaced(draw, xy, text, fnt, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + spacing
    return x


def cover(out_path, *, card, tag, title, subtitle, accent, backdrop=None, portrait=None, logo=None, poster=None,
          base=None, tr=False):
    """card: small card name top-left ('THE HEADLINER'); tag: label above the title ('ACTOR SPOTLIGHT').
    base: a ready background image (skips the backdrop)."""
    acc = hex_rgb(accent)
    up = (lambda t: t.replace("i", "İ").upper()) if tr else str.upper  # Turkish capitals: i → İ
    bg = None if base else fetch(backdrop, "w1280")
    if base:
        pass
    elif bg:
        base = cover_fit(bg.convert("RGB"), W, H)
        base = ImageEnhance.Brightness(base).enhance(0.55)
        base = ImageEnhance.Color(base).enhance(0.8)
    else:
        base = Image.new("RGB", (W, H), (18, 18, 22))
        glow = Image.new("RGB", (W, H), acc)
        base = Image.composite(glow, base, gradient_mask(W, H, [(0, 0), (0.6, 30), (1, 90)]))
    # left shade for the text
    black = Image.new("RGB", (W, H), (8, 8, 10))
    base = Image.composite(black, base, gradient_mask(W, H, [(0, 235), (0.45, 170), (0.75, 40), (1, 0)]))

    if portrait:
        p = fetch(portrait, "h632")
        if p:
            p = p.convert("RGB")
            ph = H
            pw = round(p.width * ph / p.height)
            p = p.resize((pw, ph), Image.LANCZOS)
            x = W - pw
            mask = gradient_mask(pw, ph, [(0, 0), (0.28, 255), (1, 255)])
            base.paste(p, (x, 0), mask)
    elif poster:
        p = fetch(poster, "w500")
        if p:
            p = p.convert("RGB")
            ph = H - 120
            pw = round(p.width * ph / p.height)
            p = p.resize((pw, ph), Image.LANCZOS)
            shadow = Image.new("L", (pw + 60, ph + 60), 0)
            ImageDraw.Draw(shadow).rectangle((30, 30, pw + 30, ph + 30), fill=170)
            shadow = shadow.filter(ImageFilter.GaussianBlur(18))
            x, y = W - pw - 80, 60
            base.paste(Image.new("RGB", shadow.size, (0, 0, 0)), (x - 30, y - 20), shadow)
            base.paste(p, (x, y))
    elif logo:
        lg = fetch(logo, "w500")
        if lg:
            lg = lg.convert("RGBA")
            # company logos are often dark on transparent: render them white
            alpha = lg.getchannel("A")
            white = Image.new("RGBA", lg.size, (255, 255, 255, 255))
            white.putalpha(alpha)
            r = min(420 / lg.width, 220 / lg.height)
            white = white.resize((round(lg.width * r), round(lg.height * r)), Image.LANCZOS)
            x = W - white.width - 110
            y = (H - white.height) // 2 - 40
            base.paste(white, (x, y), white)

    d = ImageDraw.Draw(base)
    left, maxw = 72, 600
    # card name, top-left
    spaced(d, (left, 58), up(card), font("SemiBold", 20), (235, 235, 235), 4)
    d.rectangle((left, 92, left + 46, 96), fill=acc)

    title_font = font("ExtraBold", 64)
    lines = wrap(d, up(title), title_font, maxw)
    if len(lines) > 3:
        title_font = font("ExtraBold", 48)
        lines = wrap(d, up(title), title_font, maxw)[:4]
    lh = title_font.size + 6
    sub_font = font("Medium", 20)
    tag_font = font("SemiBold", 16)
    block = 28 + len(lines) * lh + 14 + 26
    y = H - 72 - block
    # tag with accent dot
    d.ellipse((left, y + 5, left + 9, y + 14), fill=acc)
    spaced(d, (left + 18, y), up(tag), tag_font, (230, 230, 230), 3)
    y += 28
    d.rectangle((left - 14, y + 6, left - 9, y + len(lines) * lh - 4), fill=acc)
    for ln in lines:
        d.text((left, y), ln, font=title_font, fill=(255, 255, 255))
        y += lh
    y += 14
    sub = up(subtitle)
    while sub_font.size > 13 and sum(d.textlength(ch, font=sub_font) + 2 for ch in sub) > W - left - 60:
        sub_font = font("Medium", sub_font.size - 1)
    spaced(d, (left, y), sub, sub_font, (190, 190, 196), 2)
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        base.save(out_path, "JPEG", quality=86, optimize=True, progressive=True)
    return base


def backdrop(out_path, path):
    im = fetch(path, "original")
    if not im:
        return False
    im = cover_fit(im.convert("RGB"), 1920, 1080)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path, "JPEG", quality=82, optimize=True, progressive=True)
    return True


def poster_wall(out_path, posters, *, card, tag, title, subtitle, accent, angle=-12):
    """A tilted wall of posters in the accent colour, used for cards whose content is personal (My Simkl)."""
    acc = hex_rgb(accent)
    pw, ph, gap = 170, 255, 16
    cols, rows = 11, 5
    wall = Image.new("RGB", (cols * (pw + gap), rows * (ph + gap)), (10, 12, 18))
    imgs = [im for im in (fetch(p, "w342") for p in posters) if im]
    for i in range(cols * (rows + 1)):
        if not imgs:
            break
        im = imgs[i % len(imgs)].convert("RGB").resize((pw, ph), Image.LANCZOS)
        c, r = i % cols, i // cols
        wall.paste(im, (c * (pw + gap), r * (ph + gap) - (ph // 2 if c % 2 else 0)))
    wall = wall.rotate(angle, resample=Image.BICUBIC, fillcolor=(10, 12, 18))
    x, y = (wall.width - W) // 2, (wall.height - H) // 2
    base = wall.crop((x, y, x + W, y + H))
    # duotone toward the accent colour, darker toward the text side
    grey = ImageEnhance.Color(base).enhance(0.15)
    base = Image.blend(grey, Image.new("RGB", (W, H), acc), 0.3)
    base = ImageEnhance.Brightness(base).enhance(0.75)
    glow = Image.new("RGB", (W, H), tuple(min(255, c + 60) for c in acc))
    base = Image.composite(glow, base, gradient_mask(W, H, [(0, 0), (0.65, 0), (1, 60)]))
    cover(out_path, card=card, tag=tag, title=title, subtitle=subtitle, accent=accent, base=base)


def live_pill(im, glow=1.0):
    """A red LIVE badge, top-right; glow 0..1 animates the dot."""
    d = ImageDraw.Draw(im, "RGBA")
    f = font("ExtraBold", 22)
    w = 40 + d.textlength("LIVE", font=f) + 26
    x1, y0 = W - 72, 50
    x0, y1 = x1 - w, y0 + 44
    d.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(229, 9, 20, 235))
    cx, cy = x0 + 24, (y0 + y1) // 2
    r = 6 + 5 * glow
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, round(70 * glow)))
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 255, 255, 255))
    d.text((cx + 16, y0 + 9), "LIVE", font=f, fill=(255, 255, 255))
    return im


def ken_burns_gif(out_path, render, frames=24, size=(480, 270), ms=100):
    """render(t) -> 1280x720 RGB frame for t in 0..1. Saves a looping GIF (forward and back)."""
    import math
    imgs = []
    for i in range(frames):
        t = i / (frames - 1)
        imgs.append(render(t).resize(size, Image.LANCZOS))
    imgs += imgs[-2:0:-1]
    pal = imgs[len(imgs) // 2].convert("P", palette=Image.ADAPTIVE, colors=160)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    q[0].save(out_path, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True, disposal=1)


def zoomed(im, z):
    """Crop toward the centre by factor z (0 = none) and scale back to the frame size."""
    w, h = im.size
    cw, ch = round(w / (1 + z)), round(h / (1 + z))
    x, y = (w - cw) // 2, (h - ch) // 2
    return im.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS)


def soft_fade(base, start=0.5, top=170):
    """Light bottom gradient only (the Favourites style: no vignette, art stays bright)."""
    shade = Image.new("RGB", (W, H), (0, 0, 0))
    m = Image.new("L", (1, H))
    for y in range(H):
        f = (y / H - start) / (1 - start)
        m.putpixel((0, y), 0 if f <= 0 else round(top * f ** 1.4))
    return Image.composite(shade, base, m.resize((W, H)))


def put_logo(base, lg, maxw=560, maxh=190, bottom=58):
    """Logo centred near the bottom, with a soft shadow."""
    lg = lg.convert("RGBA")
    w0, h0 = base.size
    k = w0 / W
    r = min(maxw * k / lg.width, maxh * k / lg.height)
    lg = lg.resize((round(lg.width * r), round(lg.height * r)), Image.LANCZOS)
    x, y = (w0 - lg.width) // 2, round(h0 - bottom * k - lg.height)
    pad = round(40 * k)
    sh = Image.new("RGBA", (lg.width + 2 * pad, lg.height + 2 * pad), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", lg.size, (0, 0, 0, 255)), (pad, pad), lg.getchannel("A").point(lambda v: v * 0.75))
    sh = sh.filter(ImageFilter.GaussianBlur(16 * k))
    out = base.convert("RGBA")
    out.alpha_composite(sh, (x - pad, y - round(34 * k)))
    out.alpha_composite(lg, (x, y))
    return out.convert("RGB")


def graded(im, b=0.92, c=1.05, size=(W, H)):
    im = cover_fit(im.convert("RGB"), *size)
    return ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(b)).enhance(c)
