"""International Cinema cards (static): the country - or each country of a region - filled with its own flag, the
cloth lit softly, a thin glowing border; the card's name in the country's own language and a typeface of its own,
the English name small under it. One layout for all: the map takes the right of the card, the name the left; very
wide countries (Türkiye, China) take the top with the name under them.
Flags: lipis/flag-icons (MIT), rasterised with cairosvg. Outlines: Natural Earth 1:50m (public domain).
usage: python3 art_tools/intl_cover.py OUT_DIR [folder titles...]
"""
import io, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import intl_art as I
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from reletter import f as font, tracked, width

W, H = I.W, I.H
FONTS = {"blackhan": "ofl/blackhansans/BlackHanSans-Regular.ttf", "bodoni": "ofl/bodonimoda/BodoniModa%5Bopsz,wght%5D.ttf",
         "shrikhand": "ofl/shrikhand/Shrikhand-Regular.ttf", "jost": "ofl/jost/Jost%5Bwght%5D.ttf",
         "yuji": "ofl/yujisyuku/YujiSyuku-Regular.ttf", "mashan": "ofl/mashanzheng/MaShanZheng-Regular.ttf",
         "yatra": "ofl/yatraone/YatraOne-Regular.ttf", "playfair": "ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
         "abril": "ofl/abrilfatface/AbrilFatface-Regular.ttf", "caslon": "ofl/librecaslondisplay/LibreCaslonDisplay-Regular.ttf",
         "montserrat": "ofl/montserrat/Montserrat%5Bwght%5D.ttf", "bungee": "ofl/bungee/Bungee-Regular.ttf",
         "cinzel": "ofl/cinzel/Cinzel%5Bwght%5D.ttf"}
# folder -> (native title lines, font, weight, English line)
TITLES = {
    "South Korea": (["한국 영화"], "blackhan", None, "KOREAN CINEMA"),
    "Italy": (["CINEMA", "ITALIANO"], "bodoni", 800, "ITALIAN CINEMA"),
    "Türkiye": (["TÜRK SİNEMASI"], "shrikhand", None, "TURKISH CINEMA"),
    "Nordic Noir": (["NORDEN"], "jost", 300, "NORDIC CINEMA"),
    "Japan": (["日本映画"], "yuji", None, "JAPANESE CINEMA"),
    "Greater China": (["华语电影"], "mashan", None, "CHINESE CINEMA"),
    "India": (["भारतीय सिनेमा"], "yatra", None, "INDIAN CINEMA"),
    "UK & Ireland": (["BRITISH", "CINEMA"], "caslon", None, "UK & IRELAND"),
    "France": (["CINÉMA", "FRANÇAIS"], "playfair", 800, "FRENCH CINEMA"),
    "Spain": (["CINE", "ESPAÑOL"], "abril", None, "SPANISH CINEMA"),
    "Germany": (["DEUTSCHES", "KINO"], "jost", 700, "GERMAN CINEMA"),
    "Central & Eastern Europe": (["CENTRAL &", "EASTERN", "EUROPE"], "jost", 600, "CINEMA"),
    "Latin America": (["CINE", "LATINO-", "AMERICANO"], "bungee", None, "LATIN AMERICAN CINEMA"),
    "World Cinema Gems": (["WORLD", "CINEMA GEMS"], "cinzel", 700, "RUSSIA · IRAN · ARAB WORLD · SOUTHEAST ASIA"),
}
GEMS = "World Cinema Gems"
MAXSIZE = {GEMS: 80}


def ufont(name, size, weight=None):
    import universe_motion as um
    for k, v in FONTS.items():
        um.FONTS.setdefault(k, v)
    return um.font(name, size, weight)


def flag_svg(iso, w=1600):
    import cairosvg
    svg = I.get(f"https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/{iso.lower()}.svg")
    png = cairosvg.svg2png(bytestring=svg, output_width=w)
    return Image.open(io.BytesIO(png)).convert("RGB")


ANCHOR = {"JP": (138.4, 36.3)}   # the flag's centre (lon, lat): Honshu, not Hokkaido

# far-off members brought closer, like a map inset (lon, lat shift) - and the card's box to go with it
INSETS = {"Nordic Noir": ({"IS": (14.0, -7.5)}, (-10.8, 54.5, 31.8, 71.3))}


def per_country(folder, isos, box):
    """{iso: [rings]} for the countries drawn on the card (insets applied); and the box to frame them."""
    shifts, newbox = INSETS.get(folder, ({}, box))
    out = {}
    for iso in isos:
        r = I.rings_of([iso], box)
        if r:
            dx, dy = shifts.get(iso, (0, 0))
            def area(ring):  # shoelace, square degrees
                return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2
            big = max(area(q) for q in r)
            r = [q for q in r if area(q) > max(0.06, big * 0.002)]   # specks of island off
            out[iso] = [[(x + dx, y + dy) for x, y in ring] for ring in r]
    return out, newbox


def layout(rings_all, box, force=None):
    """The map takes the right of the card (name on the left) or the top (name under it), whichever lets it be bigger.
    Returns (projector, map area box in px, 'side' | 'top')."""
    w, s, e, n = box
    k = math.cos(math.radians((s + n) / 2))
    mw, mh = (e - w) * k, (n - s)
    areas = {"side": (W * 0.45, H * 0.05, W * 0.97, H * 0.95), "top": (W * 0.06, H * 0.05, W * 0.94, H * 0.6)}
    sc = {m: min((a[2] - a[0]) / mw, (a[3] - a[1]) / mh) for m, a in areas.items()}
    mode = "side" if sc["side"] >= sc["top"] * 0.95 else "top"
    if force:
        mode = force
    ax0, ay0, ax1, ay1 = areas[mode]
    P = I.projector(box, (ax0 + ax1) / 2, (ay0 + ay1) / 2, ax1 - ax0, ay1 - ay0)
    return P, areas[mode], mode


def cloth(im, mask, seed=0):
    """Light and shade of a flag gently folded: a slow diagonal wave, darker towards the borders."""
    a = np.asarray(im, np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wave = np.sin(xx / 95.0 + yy / 160.0 + seed) * 0.5 + np.sin(xx / 41.0 - yy / 70.0 + 2 * seed) * 0.25
    light = 1 + 0.07 * wave
    m = np.asarray(mask, np.float32) / 255
    inner = np.asarray(mask.filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
    edge = np.clip(1 - (inner - 0.5) * 2, 0, 1) * m
    a = a * light[..., None] * (1 - 0.22 * edge[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def flag_map(per, P, seed=0):
    """Each country filled with its own flag (cover-fitted to the country's own box), lit like cloth."""
    fill = Image.new("RGB", (W, H), (0, 0, 0))
    allm = Image.new("L", (W, H), 0)
    tints = []
    for iso, rings in per.items():
        m, paths = I.shape(rings, P)
        bb = m.getbbox()
        if not bb:
            continue
        fl = flag_svg(iso)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        # the whole flag inside the country (nothing of it cropped away), its edges carried on to the borders:
        # stripes run on, a plain field (Korea's white, Türkiye's red) simply continues
        a_ = np.asarray(fl.resize((60, 45)), np.float32)
        stripes = a_.std(0).mean() < 6 or a_.std(1).mean() < 6   # plain bands (Italy, Germany, France...)
        if stripes:  # bands simply stretch across the whole country
            f = np.asarray(fl.resize((bw, bh), Image.LANCZOS))
            layer = Image.new("RGB", (W, H), (0, 0, 0))
            layer.paste(Image.fromarray(f), (bb[0], bb[1]))
            fill.paste(layer, (0, 0), m)
            allm = ImageChops.lighter(allm, m)
            tints.append(tuple(int(v) for v in np.asarray(fl.resize((8, 8))).reshape(-1, 3).mean(0)))
            continue
        # emblems and crosses: centred on the country's heartland (the point deepest inside it), sized to fit
        from scipy import ndimage as ndi
        dist = ndi.distance_transform_edt(np.asarray(m) > 128)
        cy, cx = np.unravel_index(np.argmax(dist), dist.shape)
        if iso in ANCHOR:
            ax_, ay_ = P(*ANCHOR[iso])
            cx, cy = int(ax_), int(ay_)
        r = float(dist[cy, cx])
        k = min(bw / fl.width, bh / fl.height, 2.6 * r / max(fl.width, fl.height) * 1.25) * 0.95
        f = np.asarray(fl.resize((max(1, round(fl.width * k)), max(1, round(fl.height * k))), Image.LANCZOS))
        x0, y0 = round(cx - f.shape[1] / 2), round(cy - f.shape[0] / 2)
        pad = ((max(0, y0), max(0, H - y0 - f.shape[0])), (max(0, x0), max(0, W - x0 - f.shape[1])), (0, 0))
        f = np.pad(f, pad, mode="edge")[max(0, -y0):max(0, -y0) + H, max(0, -x0):max(0, -x0) + W]
        layer = Image.fromarray(f)
        fill.paste(layer, (0, 0), m)
        allm = ImageChops.lighter(allm, m)
        tints.append(tuple(int(v) for v in np.asarray(fl.resize((8, 8))).reshape(-1, 3).mean(0)))
    fill = cloth(fill, allm, seed)
    return fill, allm, tints


def border(mask, col=(255, 255, 255)):
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), mask)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = Image.new("RGBA", (W, H), col + (0,))
    g.putalpha(edge.filter(ImageFilter.GaussianBlur(7)).point(lambda v: min(255, round(v * 1.2))))
    out.alpha_composite(g)
    ln = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    ln.putalpha(edge.point(lambda v: round(v * 0.75)))
    out.alpha_composite(ln)
    return out


# the TV title logo (220x100 dp at most) needs a block, not a strip: other lines / sizes there (Ozzy, 31 Oct 2026)
TV_LINES = {"Türkiye": ["TÜRK", "SİNEMASI"], GEMS: ["WORLD", "CINEMA", "GEMS"]}
TV_MAXSIZE = {GEMS: 150}


def title_layer(folder, mode, area, tv=False):
    lines, fname, wght, en = TITLES[folder]
    if tv:
        lines = TV_LINES.get(folder, lines)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if mode == "side":
        maxw = W * (0.8 if tv else 0.36)
        x0 = W * 0.06
    else:
        maxw = W * 0.8
        x0 = None
    size = (TV_MAXSIZE if tv else MAXSIZE).get(folder, 150)
    while size > 40:
        fn = ufont(fname, size, wght)
        if max(d.textlength(l, font=fn) for l in lines) <= maxw:
            break
        size -= 4
    fn = ufont(fname, size, wght)
    lh = []
    for l in lines:
        bb = d.textbbox((0, 0), l, font=fn)
        lh.append((bb[1], bb[3]))
    gap = size * 0.12
    en_f = font("SemiBold", 24)
    en_w = width(en, en_f, 8)
    block_h = sum(b - a for a, b in lh) + gap * (len(lines) - 1) + 26 + 30
    if tv:                                            # its own canvas: from the top, nothing falls off the bottom
        y = 40
    elif mode == "side":
        y = H / 2 - block_h / 2
    else:
        y = area[3] + (H - area[3]) / 2 - block_h / 2 + 6
    for l, (a, b) in zip(lines, lh):
        lw = d.textlength(l, font=fn)
        x = x0 if x0 is not None else (W - lw) / 2
        d.text((x + 3, y - a + 4), l, font=fn, fill=(0, 0, 0, 160))
        d.text((x, y - a), l, font=fn, fill=(246, 244, 240, 255))
        y += (b - a) + gap
    y += 26 - gap
    ex = x0 if x0 is not None else (W - en_w) / 2
    tracked(d, (ex, y), en, en_f, (190, 190, 196, 255), 8)
    return lay


def gold_map(per, P):
    """The gems card: its regions in gold leaf, lit like the flags."""
    allm = Image.new("L", (W, H), 0)
    for rings in per.values():
        m, _ = I.shape(rings, P)
        allm = ImageChops.lighter(allm, m)
    ramp = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top, bot = np.array([255, 226, 150], np.float32), np.array([176, 120, 44], np.float32)
    fill = Image.fromarray(np.repeat(top * (1 - ramp) + bot * ramp, W, 1).astype(np.uint8))
    return cloth(fill, allm, 1.3), allm, [(214, 168, 80)]


def world_under(P, box):
    """Every other country, faint, under the gems' regions."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    I.rings_of(["TR"], box)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for f in I.GEO["features"]:
        g = f["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            d.polygon([P(x, y) for x, y in poly[0]], fill=255)
    lay.paste((34, 36, 44, 255), (0, 0), m)
    return lay


def parts(folder):
    """The card's layers: background, flag fill + mask, border, shadow, title - for the cover and the hover."""
    name, isos, box, fiso, cols, _ = I.CARDS[folder]
    per, box = per_country(folder, isos, box)
    rings_all = [r for rs in per.values() for r in rs]
    P, area, mode = layout(rings_all, box, "top" if folder == GEMS else None)
    fill, mask, tints = (gold_map if folder == GEMS else flag_map)(per, P)
    tint = tuple(int(np.mean([t[c] for t in tints])) for c in range(3)) if tints else (120, 120, 140)
    # background: near black, a faint glow of the flag's colour behind the map
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = (area[0] + area[2]) / 2, (area[1] + area[3]) / 2
    g = np.clip(1 - np.sqrt(((xx - cx) / (W * 0.45)) ** 2 + ((yy - cy) / (H * 0.6)) ** 2), 0, 1) ** 2
    bg = Image.fromarray((np.array([8, 8, 10], np.float32) + g[..., None] * np.array(tint, np.float32) * 0.18).astype(np.uint8))
    if folder == GEMS:
        bg = bg.convert("RGBA")
        bg.alpha_composite(world_under(P, box))
        bg = bg.convert("RGB")
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(mask.filter(ImageFilter.GaussianBlur(18)).point(lambda v: round(v * 0.85)))
    return {"bg": bg, "fill": fill, "mask": mask, "shadow": sh, "border": border(mask, tint), "tint": tint,
            "title": title_layer(folder, mode, area), "mode": mode, "area": area}


def compose(p, content=None, mask=None, shadow_a=1.0, border_a=1.0, title_a=1.0):
    """The card from its parts; content (RGB, card-sized) shown through the (possibly scaled) mask instead of the flag."""
    cv = p["bg"].convert("RGBA")
    m = mask or p["mask"]
    if shadow_a > 0:
        cv.alpha_composite(I.amul(p["shadow"], shadow_a), (8, 14))
    c = (content or p["fill"]).convert("RGBA")
    c.putalpha(m)
    cv.alpha_composite(c)
    if border_a > 0:
        cv.alpha_composite(I.amul(p["border"], border_a))
    if title_a > 0:
        cv.alpha_composite(I.amul(p["title"], title_a))
    return cv


def build_cover(folder):
    return compose(parts(folder)).convert("RGB")


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for fo in sys.argv[2:] or TITLES:
        build_cover(fo).save(os.path.join(out, I.slug_of(fo) + ".jpg"), quality=90)
        print("cover", fo)
