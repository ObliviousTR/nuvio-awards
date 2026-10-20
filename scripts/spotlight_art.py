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


def cover(out_path, *, card, tag, title, subtitle, accent, backdrop=None, portrait=None, logo=None, poster=None):
    """card: small card name top-left ('THE HEADLINER'); tag: label above the title ('ACTOR SPOTLIGHT')."""
    acc = hex_rgb(accent)
    bg = fetch(backdrop, "w1280")
    if bg:
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
    spaced(d, (left, 58), card.upper(), font("SemiBold", 20), (235, 235, 235), 4)
    d.rectangle((left, 92, left + 46, 96), fill=acc)

    title_font = font("ExtraBold", 64)
    lines = wrap(d, title.upper(), title_font, maxw)
    if len(lines) > 3:
        title_font = font("ExtraBold", 48)
        lines = wrap(d, title.upper(), title_font, maxw)[:4]
    lh = title_font.size + 6
    sub_font = font("Medium", 20)
    tag_font = font("SemiBold", 16)
    block = 28 + len(lines) * lh + 14 + 26
    y = H - 72 - block
    # tag with accent dot
    d.ellipse((left, y + 5, left + 9, y + 14), fill=acc)
    spaced(d, (left + 18, y), tag.upper(), tag_font, (230, 230, 230), 3)
    y += 28
    d.rectangle((left - 14, y + 6, left - 9, y + len(lines) * lh - 4), fill=acc)
    for ln in lines:
        d.text((left, y), ln, font=title_font, fill=(255, 255, 255))
        y += lh
    y += 14
    spaced(d, (left, y), subtitle.upper(), sub_font, (190, 190, 196), 2)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    base.save(out_path, "JPEG", quality=86, optimize=True, progressive=True)


def backdrop(out_path, path):
    im = fetch(path, "original")
    if not im:
        return False
    im = cover_fit(im.convert("RGB"), 1920, 1080)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path, "JPEG", quality=82, optimize=True, progressive=True)
    return True
