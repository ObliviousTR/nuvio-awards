"""Our own horizontal logos for the Favourites row (transparent PNG, white on transparent, made with Pillow)."""
import io, os, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "spotlight", "logos")
RED = (229, 9, 20)


def skew(im, k=0.21):
    """Italic slant (shear to the right)."""
    w, h = im.size
    return im.transform((w + int(h * k), h), Image.AFFINE, (1, k, -h * k, 0, 1, 0), Image.BICUBIC)


def trim(im, pad=8):
    box = im.getchannel("A").getbbox()
    im = im.crop(box)
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    out.paste(im, (pad, pad))
    return out


def live_sport_a(scale=2):
    """Broadcast style: red slanted LIVE plate with a pulse dot, then SPORT, both italic."""
    s = scale
    f = art.font("ExtraBold", 120 * s)
    im = Image.new("RGBA", (1500 * s, 220 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    live_w = d.textlength("LIVE", font=f)
    x0, y0 = 20 * s, 30 * s
    plate = (x0, y0, x0 + live_w + 120 * s, y0 + 150 * s)
    d.rounded_rectangle(plate, radius=14 * s, fill=RED + (255,))
    cx, cy = x0 + 46 * s, y0 + 75 * s
    d.ellipse((cx - 30 * s, cy - 30 * s, cx + 30 * s, cy + 30 * s), outline=(255, 255, 255, 110), width=6 * s)
    d.ellipse((cx - 16 * s, cy - 16 * s, cx + 16 * s, cy + 16 * s), fill=(255, 255, 255, 255))
    d.text((x0 + 92 * s, y0 + 2 * s), "LIVE", font=f, fill=(255, 255, 255, 255))
    d.text((plate[2] + 26 * s, y0 + 2 * s), "SPORT", font=f, fill=(255, 255, 255, 255))
    return trim(skew(im))


def live_sport_b(scale=2):
    """Signal icon (dot + two arcs) and LIVE SPORT with LIVE in red."""
    s = scale
    f = art.font("ExtraBold", 120 * s)
    im = Image.new("RGBA", (1500 * s, 220 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = 100 * s, 110 * s
    d.ellipse((cx - 22 * s, cy - 22 * s, cx + 22 * s, cy + 22 * s), fill=RED + (255,))
    for r, a in ((50, 255), (78, 170)):
        d.arc((cx - r * s, cy - r * s, cx + r * s, cy + r * s), -50, 50, fill=(255, 255, 255, a), width=11 * s)
        d.arc((cx - r * s, cy - r * s, cx + r * s, cy + r * s), 130, 230, fill=(255, 255, 255, a), width=11 * s)
    x = cx + 110 * s
    d.text((x, 30 * s), "LIVE", font=f, fill=RED + (255,))
    x += d.textlength("LIVE ", font=f)
    d.text((x, 30 * s), "SPORT", font=f, fill=(255, 255, 255, 255))
    return trim(im)


def simkl_glyph(size):
    import cairosvg
    svg = open(os.path.join(OUT, "simkl-glyph.svg")).read().replace("<path ", '<path fill="#ffffff" ')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)))


def my_simkl_a(scale=2):
    """Simkl glyph + MY SIMKL."""
    s = scale
    f = art.font("ExtraBold", 120 * s)
    g = simkl_glyph(150 * s)
    im = Image.new("RGBA", (1400 * s, 220 * s), (0, 0, 0, 0))
    im.alpha_composite(g, (10 * s, 35 * s))
    d = ImageDraw.Draw(im)
    d.text((200 * s, 30 * s), "MY SIMKL", font=f, fill=(255, 255, 255, 255))
    return trim(im)


def my_simkl_b(scale=2):
    """Lower-case 'my' in a lighter weight next to the Simkl glyph and SIMKL."""
    s = scale
    fl = art.font("Medium", 120 * s)
    fb = art.font("ExtraBold", 120 * s)
    g = simkl_glyph(150 * s)
    im = Image.new("RGBA", (1500 * s, 220 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((10 * s, 22 * s), "my", font=fl, fill=(255, 255, 255, 220))
    x = 10 * s + d.textlength("my", font=fl) + 24 * s
    im.alpha_composite(g, (int(x), 35 * s))
    x += 150 * s + 26 * s
    d.text((x, 30 * s), "SIMKL", font=fb, fill=(255, 255, 255, 255))
    return trim(im)


def my_simkl_c(scale=2):
    """Pure wordmark: light 'my' + heavy SIMKL, no icon."""
    s = scale
    fl, fb = art.font("Medium", 120 * s), art.font("ExtraBold", 120 * s)
    im = Image.new("RGBA", (1300 * s, 220 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((10 * s, 22 * s), "my", font=fl, fill=(255, 255, 255, 215))
    d.text((10 * s + d.textlength("my", font=fl) + 18 * s, 30 * s), "SIMKL", font=fb, fill=(255, 255, 255, 255))
    return trim(im)


def my_simkl_d(scale=2):
    """Small icon, thin divider, then 'my simkl' in one weight."""
    s = scale
    f = art.font("SemiBold", 110 * s)
    g = simkl_glyph(104 * s)
    im = Image.new("RGBA", (1300 * s, 220 * s), (0, 0, 0, 0))
    im.alpha_composite(g, (10 * s, 58 * s))
    d = ImageDraw.Draw(im)
    d.rectangle((150 * s, 50 * s, 155 * s, 170 * s), fill=(255, 255, 255, 140))
    d.text((190 * s, 32 * s), "my simkl", font=f, fill=(255, 255, 255, 255))
    return trim(im)


def my_simkl_e(scale=2):
    """Outlined MY tag + SIMKL."""
    s = scale
    ft, fb = art.font("ExtraBold", 64 * s), art.font("ExtraBold", 120 * s)
    im = Image.new("RGBA", (1300 * s, 220 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tw = d.textlength("MY", font=ft)
    d.rounded_rectangle((10 * s, 62 * s, 10 * s + tw + 44 * s, 158 * s), radius=16 * s, outline=(255, 255, 255, 255), width=7 * s)
    d.text((32 * s, 66 * s), "MY", font=ft, fill=(255, 255, 255, 255))
    d.text((10 * s + tw + 72 * s, 30 * s), "SIMKL", font=fb, fill=(255, 255, 255, 255))
    return trim(im)


def my_simkl_f(scale=2):
    """SIMKL with a small 'my' tucked above its first letter."""
    s = scale
    fs, fb = art.font("SemiBold", 56 * s), art.font("ExtraBold", 130 * s)
    im = Image.new("RGBA", (1100 * s, 260 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((14 * s, 6 * s), "my", font=fs, fill=(255, 255, 255, 230))
    d.text((10 * s, 58 * s), "SIMKL", font=fb, fill=(255, 255, 255, 255))
    return trim(im)


if __name__ == "__main__":
    for name, fn in (("livesport-a", live_sport_a), ("livesport-b", live_sport_b),
                     ("mysimkl-a", my_simkl_a), ("mysimkl-b", my_simkl_b), ("mysimkl-c", my_simkl_c),
                     ("mysimkl-d", my_simkl_d), ("mysimkl-e", my_simkl_e), ("mysimkl-f", my_simkl_f)):
        fn().save(os.path.join(OUT, f"{name}.png"))
    print("logos ok")
