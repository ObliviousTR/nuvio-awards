"""Covers (+ hover WebP + hero backdrop) for the folders that still had an emoji, a placeholder or a duplicate cover.
Each template copies the look of the row it sits in, so the new tile sits with Kaptain's neighbours:
  bottom_title  Kids & Family / Documentaries   photo, accent bar, bold title + tracked subtitle (docs: duotone)
  discover      Discover                        huge word, part filled with the picture, rest outlined
  decade        By Decade                       the number filled with a film still, white keyline
  world_map     International Cinema            neon country outlines on black, grey tracked caption
  anime_sheet   Anime                           layout sheet: peg holes, vertical kanji, outlined word, cut note
  logo_tile     Streaming / Studios / Awards    brand logo on its own colour field (or over a still)
  network       Networks (poster)               dark blurred show collage, white logos
  portrait      Iconic Actors / Directors       cut-out portrait on a dark studio backdrop, name block
usage: python3 art_tools/folder_art.py OUT_DIR [job ids...]
"""
import io, json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import universe_motion as um
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

CW, CH = 1920, 1080
PW, PH = 1000, 1500
um.FONTS["montserrat"] = "ofl/montserrat/Montserrat%5Bwght%5D.ttf"
um.FONTS["jp"] = "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"


def black(size):
    return um.font("montserrat", size, weight=900)


def xbold(size):
    return art.font("ExtraBold", size)


def semi(size):
    return art.font("SemiBold", size)


def tl(text, fnt, col=(255, 255, 255), tr=0):
    return um.text_layer(text, fnt, col, tr)


# ---------------------------------------------------------------- sources
def images(kind, tid):
    return tmdb(f"/{kind}/{tid}/images", include_image_language="null,en") or {}


def still(kind, tid, idx=0):
    """A textless backdrop (no language tag), best voted first."""
    bd = [b for b in images(kind, tid).get("backdrops", []) if not b.get("iso_639_1")]
    bd.sort(key=lambda b: (-b["vote_count"], -b["width"]))
    return art.fetch(bd[min(idx, len(bd) - 1)]["file_path"]).convert("RGB")


def find(kind, query, year=None):
    p = {"query": query}
    if year:
        p["year" if kind == "movie" else "first_air_date_year"] = year
    r = (tmdb(f"/search/{kind}", **p) or {}).get("results", [])
    return r[0]["id"]


def logo_png(path):
    return um.trim(Image.open(io.BytesIO(um.get("https://image.tmdb.org/t/p/original" + path))).convert("RGBA"))


def whiten(im, keep_colour=True):
    """Dark ink -> white; saturated colours (a red dot, an orange line) stay."""
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and (not keep_colour or max(r, g, b) - min(r, g, b) < 60):
                px[x, y] = (255, 255, 255, a)
    return im


def ink_from_white(im):
    """A logo on a white plate (jpg): ink becomes alpha; dark ink -> white, coloured ink keeps its colour."""
    im = im.convert("RGB")
    out = Image.new("RGBA", im.size)
    src, dst = im.load(), out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = src[x, y]
            a = 255 - min(r, g, b)
            if a < 30:
                continue
            sat = max(r, g, b) - min(r, g, b)
            dst[x, y] = (r, g, b, 255) if sat > 80 else (255, 255, 255, a)
    return um.trim(out)


def plate_to_alpha(im):
    """A logo on a black plate: brightness becomes alpha."""
    return um.trim(um.key_black(im.convert("RGBA"), 25, 90))


# ---------------------------------------------------------------- shared looks
def cover(img, w, h, z=0.0, b=0.92, c=1.05):
    return art.zoomed(art.graded(img, b, c, (w, h)), z)


def fade_bottom(im, start=0.45, top=235, col=(0, 0, 0)):
    w, h = im.size
    m = Image.new("L", (1, h))
    for y in range(h):
        f = (y / h - start) / (1 - start)
        m.putpixel((0, y), 0 if f <= 0 else round(top * min(1, f) ** 1.3))
    return Image.composite(Image.new("RGB", (w, h), col), im, m.resize((w, h)))


def vignette(im, strength=0.8):
    w, h = im.size
    v = Image.new("L", (w, h), 0)
    ImageDraw.Draw(v).ellipse((-w * 0.25, -h * 0.35, w * 1.25, h * 1.35), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(w // 10)).point(lambda x: round(255 - (255 - x) * strength))
    return Image.composite(im, Image.new("RGB", (w, h), (0, 0, 0)), v)


def duotone(im, dark, light, k=0.85):
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    d = ImageOps.colorize(g, dark, light)
    return Image.blend(im, d, k)


def outline_text(layer, w=4, col=(255, 255, 255), a=230):
    m = layer.getchannel("A")
    ring = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(w * 2 + 1)), m.filter(ImageFilter.MinFilter(3)))
    out = Image.new("RGBA", layer.size, col + (0,))
    out.putalpha(ring.point(lambda v: v * a // 255))
    return out


def textured(layer, tex):
    """Fill a text layer with a picture (tex is scaled to cover the layer)."""
    t = art.cover_fit(tex, *layer.size).convert("RGBA")
    t.putalpha(layer.getchannel("A"))
    return t


# ---------------------------------------------------------------- templates: frame(p, z) -> RGB, p = reveal 0..1, z = drift 0..1
def bottom_title(img, title, sub, accent, duo=None, w=CW, h=CH):
    tf, sf = xbold(round(118 * w / CW)), semi(round(38 * w / CW))
    T = tl(title, tf, tr=3)
    S = tl(sub, sf, (225, 225, 225), tr=4)
    x0 = round(112 * w / CW)

    def frame(p, z):
        im = cover(img, w, h, 0.02 + 0.05 * z, 0.95, 1.06)
        if duo:
            im = duotone(im, *duo)
        im = fade_bottom(im, 0.42, 225).convert("RGBA")
        ty = round(h * 0.835) - T.height
        sy = ty + T.height + round(22 * h / CH)
        a1, a2, a3 = um.ease(p / 0.35), um.ease((p - 0.15) / 0.4), um.ease((p - 0.45) / 0.35)
        bar_h = round((sy + S.height - ty + 16) * a1)
        ImageDraw.Draw(im).rectangle((x0 - 24, ty - 8, x0 - 18, ty - 8 + bar_h), fill=accent + (255,))
        um.comp(im, um.alpha(T, a2), x0 - round(40 * (1 - a2)), ty)
        um.comp(im, um.alpha(S, a3), x0, sy)
        return im.convert("RGB")
    return frame


def discover(img, word, sub, subcol, split, w=CW, h=CH):
    size = 230
    while um.text_layer(word, black(size), (255, 255, 255), 6).width > w * 0.64:
        size -= 6
    W_ = black(size)
    full = tl(word, W_, tr=6)
    ss = 46
    while tl(sub, semi(ss), subcol, tr=8).width > full.width * 0.98:
        ss -= 2
    S = tl(sub, semi(ss), subcol, tr=8)

    def frame(p, z):
        bg = vignette(cover(img, w, h, 0.03 + 0.05 * z, 0.5, 1.1), 0.9).convert("RGBA")
        tex = ImageEnhance.Color(ImageEnhance.Brightness(art.zoomed(art.graded(img, 1.0, 1.1, (w, h)), 0.1 + 0.05 * z)).enhance(1.35)).enhance(1.25)
        cut = split * um.ease(p / 0.7)
        # build the word letter by letter: filled with the picture up to `cut`, outlined after
        lay = Image.new("RGBA", full.size, (0, 0, 0, 0))
        mfill = Image.new("L", full.size, 0)
        n = len(word)
        x = 0
        d = ImageDraw.Draw(Image.new("L", (1, 1)))
        for i, ch in enumerate(word):
            adv = d.textlength(ch, font=W_) + 6
            if ch != " " and i < cut:
                ImageDraw.Draw(mfill).rectangle((x, 0, x + adv, full.height), fill=round(255 * min(1, cut - i)))
            x += adv
        fill = textured(full, tex)
        fill.putalpha(ImageChops.multiply(full.getchannel("A"), mfill))
        lay.alpha_composite(outline_text(full, 3, (255, 255, 255), round(235 * min(1, p / 0.25))))
        lay.alpha_composite(fill)
        um.place(bg, lay, w / 2, h * 0.43)
        um.place(bg, S, w / 2, h * 0.43 + full.height / 2 + 70, um.ease((p - 0.55) / 0.35))
        return bg.convert("RGB")
    return frame


def decade(img, text, w=CW, h=CH):
    L = tl(text, black(620), tr=-8)
    L = um.fit(L, w * 0.9, h * 0.66)

    def frame(p, z):
        bg = ImageEnhance.Brightness(cover(img, w, h, 0.02 + 0.04 * z).filter(ImageFilter.GaussianBlur(10))).enhance(0.32).convert("RGBA")
        s = 1.06 - 0.06 * um.ease(p)
        lw, lh = round(L.width * s), round(L.height * s)
        Ls = L.resize((lw, lh), Image.LANCZOS)
        fill = textured(Ls, ImageEnhance.Brightness(art.zoomed(art.graded(img, 1, 1.08, (w, h)), 0.04 * z)).enhance(1.12))
        ring = outline_text(Ls, 5, (255, 255, 255), 235)
        lay = um.padded(Ls, 40)
        lay = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        lay.alpha_composite(um.glow(um.padded(Ls, 40), 18, (0, 0, 0), 0.9))
        lay.alpha_composite(fill, (40, 40))
        lay.alpha_composite(ring, (40, 40))
        um.place(bg, lay, w / 2, h / 2, um.ease(p / 0.4))
        return bg.convert("RGB")
    return frame


GEO = None


def countries(isos):
    global GEO
    if GEO is None:
        GEO = json.loads(um.get("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"))
    out = []
    for f in GEO["features"]:
        pr = f["properties"]
        iso = pr.get("ISO_A2_EH") or pr.get("ISO_A2")
        if iso in isos:
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            out.append((iso, [ring for poly in polys for ring in poly]))
    return out


def world_map(isos, lines, box, w=CW, h=CH):
    shapes = countries(isos)
    lon0, lat0, lon1, lat1 = box
    k = math.cos(math.radians((lat0 + lat1) / 2))
    sx = (w * 0.9) / ((lon1 - lon0) * k)
    sy = (h * 0.62) / (lat1 - lat0)
    s = min(sx, sy)
    ox = w / 2 - (lon0 + lon1) / 2 * k * s
    oy = h * 0.35 + (lat0 + lat1) / 2 * s
    P = lambda lon, lat: (ox + lon * k * s, oy - lat * s)
    hues = [(255, 70, 70), (255, 150, 40), (255, 220, 60), (120, 230, 90), (60, 200, 255), (120, 120, 255), (220, 90, 255)]
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for j, (iso, rings) in enumerate(shapes):
        col = hues[j % len(hues)]
        for r in rings:
            if len(r) > 4:
                d.line([P(*pt[:2]) for pt in r] + [P(*r[0][:2])], fill=col + (235,), width=3, joint="curve")
    caption = [tl(t, xbold(92), (150, 150, 150), tr=5) for t in lines]

    def frame(p, z):
        bg = Image.new("RGB", (w, h), (9, 9, 12))
        g = Image.new("L", (w, h), 0)
        ImageDraw.Draw(g).ellipse((w * 0.1, h * 0.05, w * 0.9, h * 0.95), fill=40)
        bg = Image.composite(Image.new("RGB", (w, h), (30, 30, 36)), bg, g.filter(ImageFilter.GaussianBlur(180))).convert("RGBA")
        m = um.wipe(lay, um.ease(p / 0.7), soft=260)
        bg.alpha_composite(um.glow(m, 10, (255, 255, 255), 0.25))
        bg.alpha_composite(m)
        y = h * 0.75
        for c in caption:
            um.place(bg, um.glow(um.padded(c, 20), 12, (0, 0, 0), 0.8), w / 2, y)
            um.place(bg, c, w / 2, y, um.ease((p - 0.35) / 0.45))
            y += c.height + 34
        return bg.convert("RGB")
    return frame


def anime_sheet(img, word, kanji, note, show, w=CW, h=CH):
    W_ = tl(word, black(150), tr=6)
    fillw = Image.new("RGBA", W_.size, (255, 255, 255, 0))
    fillw.putalpha(W_.getchannel("A").point(lambda v: v * 70 // 255))
    ring = outline_text(W_, 3, (255, 255, 255), 230)
    jp = um.font("jp", 46, weight=700)
    kan = [tl(c, jp) for c in kanji]
    n1, n2 = tl(note, semi(18), tr=3), tl(show.upper(), semi(18), tr=2)
    x0, y0, x1, y1 = round(w * 0.035), round(h * 0.065), round(w * 0.80), round(h * 0.915)

    def frame(p, z):
        bg = ImageEnhance.Brightness(cover(img, w, h, 0.08).filter(ImageFilter.GaussianBlur(14))).enhance(0.38).convert("RGBA")
        inner = art.zoomed(art.graded(img, 0.98, 1.06, (x1 - x0, y1 - y0)), 0.02 + 0.06 * z)
        bg.paste(inner, (x0, y0))
        d = ImageDraw.Draw(bg)
        d.rectangle((x0, y0, x1, y1), outline=(235, 235, 235, 255), width=3)
        for fx in (0.08, 0.5, 0.92):  # peg holes
            cx = x0 + (x1 - x0) * fx
            d.ellipse((cx - 9, y0 - 9, cx + 9, y0 + 9), fill=(250, 250, 250, 255))
        red = (230, 40, 50, 255)
        for (cx, cy, sx, sy) in ((x0 - 12, y0 - 12, 1, 1), (x0 - 12, y1 + 12, 1, -1)):
            d.line((cx, cy, cx + 46 * sx, cy), fill=red, width=4)
            d.line((cx, cy, cx, cy + 46 * sy), fill=red, width=4)
        ky = y0 + 30
        for kc in kan:
            um.comp(bg, kc, x0 + 22, ky)
            ky += kc.height + 8
        a = um.ease((p - 0.2) / 0.5)
        wy = y1 - 120 - W_.height
        um.comp(bg, um.alpha(fillw, a), x0 + 26, wy)
        um.comp(bg, um.alpha(ring, a), x0 + 26, wy)
        um.comp(bg, um.alpha(n1, a), x0 + 30, y1 - 86)
        um.comp(bg, um.alpha(n2, a), x0 + 30, y1 - 56)
        return bg.convert("RGB")
    return frame


def logo_tile(logo, top, bottom, maxw=0.52, maxh=0.42, glow_col=None, img=None, img_b=0.35, neon=False, stars=False,
              w=CW, h=CH):
    lg = um.fit(logo, w * maxw, h * maxh)
    rnd = random.Random(5)
    sts = [(rnd.uniform(0, w), rnd.uniform(0, h * 0.7), rnd.uniform(0.6, 2.2)) for _ in range(160)] if stars else []

    def frame(p, z):
        if img is not None:
            bg = vignette(ImageEnhance.Brightness(cover(img, w, h, 0.02 + 0.05 * z)).enhance(img_b), 0.9)
        else:
            bg = Image.new("RGB", (w, h))
            gd = ImageDraw.Draw(bg)
            for y in range(h):
                f = y / h
                gd.line((0, y, w, y), fill=tuple(round(top[i] + (bottom[i] - top[i]) * f) for i in range(3)))
            bg = vignette(bg, 0.5)
        bg = bg.convert("RGBA")
        d = ImageDraw.Draw(bg)
        for (x, y, r) in sts:
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, round(140 + 100 * math.sin(z * 6 + x))))
        a = um.ease(p / 0.6)
        s = 0.94 + 0.06 * a
        L = lg.resize((round(lg.width * s), round(lg.height * s)), Image.LANCZOS)
        on = a
        if neon and p < 0.8:
            on = a * (1 if random.Random(int(p * 1000)).random() < p / 0.8 else 0.15)
        if glow_col:
            um.place(bg, um.glow(um.padded(L, 60), 28 if neon else 40, glow_col, (1.6 if neon else 0.7) * on), w / 2, h / 2)
            if neon:
                um.place(bg, um.glow(um.padded(L, 60), 8, glow_col, 1.8 * on), w / 2, h / 2)
        um.place(bg, L, w / 2, h / 2, on if neon else a)
        if p >= 1 and not neon:
            pass
        return bg.convert("RGB")
    return frame


def network(logos, stills, w=PW, h=PH):
    def frame(p, z):
        bg = Image.new("RGB", (w, h), (8, 8, 10))
        tile_h = h // len(stills)
        for i, s in enumerate(stills):
            t = ImageEnhance.Brightness(art.cover_fit(s, w, tile_h)).enhance(0.28).filter(ImageFilter.GaussianBlur(6))
            bg.paste(t, (0, i * tile_h))
        bg = vignette(bg, 0.9).convert("RGBA")
        y = h / 2 - sum(l.height for l in logos) / 2 - 40 * (len(logos) - 1) / 2
        for l in logos:
            um.place(bg, l, w / 2, y + l.height / 2, um.ease(p / 0.6))
            y += l.height + 80
        return bg.convert("RGB")
    return frame


def portrait(person_img, lines, sub, w=PW, h=PH):
    """TMDB profile photo cut out (rembg) onto a dark studio backdrop, graded like Kaptain's actor cards."""
    from rembg import remove
    cut = remove(person_img.convert("RGB"))
    cut = um.trim(cut)
    r = max(w * 0.98 / cut.width, h * 0.86 / cut.height)
    cut = cut.resize((round(cut.width * r), round(cut.height * r)), Image.LANCZOS)
    rgb = ImageEnhance.Contrast(ImageEnhance.Color(cut.convert("RGB")).enhance(0.8)).enhance(1.08)
    cut = Image.merge("RGBA", (*rgb.split(), cut.getchannel("A")))
    bg = Image.new("RGB", (w, h), (8, 8, 9))
    g = Image.new("L", (w, h), 0)
    ImageDraw.Draw(g).ellipse((-w * 0.1, h * 0.02, w * 1.1, h * 0.75), fill=255)
    bg = Image.composite(Image.new("RGB", (w, h), (64, 64, 68)), bg, g.filter(ImageFilter.GaussianBlur(220))).convert("RGBA")
    rim = um.glow(cut, 12, (255, 255, 255), 0.18)
    um.comp(bg, rim, (w - cut.width) / 2, h - cut.height)
    um.comp(bg, cut, (w - cut.width) / 2, h - cut.height)
    out = vignette(bg.convert("RGB"), 0.55)
    sys.path.insert(0, HERE)
    from reletter import letter
    return letter(out, lines, sub)


# ---------------------------------------------------------------- jobs
def J(row, title, make):
    return {"row": row, "title": title, "make": make}


def jobs():
    m, tv = "movie", "tv"
    return [
        # Discover
        J("Discover", "Trending Series", lambda: discover(still(tv, 94997), "TRENDING", "THE MOST-WATCHED SERIES RIGHT NOW", (255, 170, 60), 5)),
        J("Discover", "New Series", lambda: discover(still(tv, 126308), "NEW SERIES", "FRESH SEASONS & BRAND-NEW SHOWS", (255, 70, 140), 3)),
        J("Discover", "Hidden Gems", lambda: discover(still(m, 14784), "HIDDEN GEMS", "UNDERRATED FILMS WORTH DISCOVERING", (90, 230, 200), 6)),
        J("Discover", "Awards & Prestige", lambda: discover(still(m, 496243), "PRESTIGE", "AWARD WINNERS & CRITICS' FAVOURITES", (240, 200, 90), 4)),
        # Kids & Family
        J("Kids & Family", "Disney & Pixar Magic", lambda: bottom_title(still(m, 354912), "DISNEY & PIXAR", "BELOVED CLASSICS & MODERN FAVOURITES", (90, 160, 255))),
        J("Kids & Family", "DreamWorks & Illumination", lambda: bottom_title(still(m, 809), "DREAMWORKS & MINIONS", "SHREK, KUNG FU PANDA, DESPICABLE ME & MORE", (120, 220, 80))),
        # Documentaries
        J("Documentaries", "Trending & Award-Winning Docs", lambda: bottom_title(still(m, find(m, "Searching for Sugar Man", 2012)), "TRENDING DOCS", "AWARD WINNERS & MOST-WATCHED STORIES", (240, 170, 60), duo=((25, 20, 15), (250, 205, 140)))),
        # By Decade
        J("By Decade", "🏆 Best of 2026", lambda: decade(still(m, 687163), "2026")),
        J("By Decade", "1980s", lambda: decade(still(m, 78), "80S")),
        # International
        J("International Cinema", "Central & Eastern Europe", lambda: world_map(
            {"PL", "CZ", "SK", "HU", "RO", "BG", "GR", "RS", "HR", "BA", "SI", "ME", "MK", "AL", "XK", "UA", "MD", "BY", "LT", "LV", "EE"},
            ["CENTRAL & EASTERN", "EUROPEAN CINEMA"], (12, 35, 41, 59))),
        # Anime
        J("Anime", "Seinen, Dark & Psychological", lambda: anime_sheet(still(tv, 88803), "SEINEN", "青年", "LAYOUT  ·  CUT 07", "Vinland Saga")),
        J("Anime", "All-Time Top Rated Anime", lambda: anime_sheet(still(tv, 31911), "LEGENDS", "名作", "KEY FRAME  ·  CUT 01", "Fullmetal Alchemist: Brotherhood")),
        J("Anime", "Anime Movies & Feature Films", lambda: anime_sheet(still(m, 372058), "FILMS", "映画", "CLEAN-UP  ·  CUT 22", "Your Name.")),
        J("Anime", "Anime Film Collections", lambda: anime_sheet(still(m, 283566), "SAGAS", "劇場版", "TIMING  ·  CUT 31", "Evangelion: 3.0+1.0")),
        # Streaming (Turkey)
        J("Streaming Services", "Exxen", lambda: logo_tile(plate_to_alpha(um.commons("File:Exxen.png", 1600)), (12, 12, 12), (0, 0, 0), glow_col=(255, 200, 0))),
        J("Streaming Services", "GAİN", lambda: logo_tile(ink_from_white(um.commons("File:GAİN LOGO.jpg", 1600)), (20, 20, 22), (0, 0, 0), maxw=0.4, glow_col=(230, 30, 40))),
        J("Streaming Services", "tabii", lambda: logo_tile(um.trim(um.commons("File:Trt-tabii-logo.png", 1600)), (8, 22, 24), (2, 6, 8), glow_col=(40, 240, 160))),
        # Studios
        J("Studios", "NEON", lambda: logo_tile(logo_png("/mQH8iJrHa3cS2Nd1pTVKh4e6W7t.png"), (14, 10, 18), (0, 0, 0), maxw=0.5, glow_col=(255, 120, 220), neon=True)),
        J("Studios", "Paramount Pictures", lambda: logo_tile(whiten(logo_png("/quak7YuVuz67E1KZzNN0d6WDtMY.png"), False), (6, 22, 70), (24, 84, 190), maxw=0.36, maxh=0.6, glow_col=(150, 200, 255), stars=True)),
        J("Studios", "Disney & Pixar Animation", lambda: logo_tile(pair(logo_png("/7A3l4fLdI7WF8b4dtinLCWIsDaD.png"), logo_png("/1TjvGVDMYsj6JBxOAkUHpPEwLf7.png")), (205, 225, 240), (150, 180, 210), maxw=0.7, maxh=0.45)),
        # Awards
        J("Awards & Festivals", "Criterion Collection & Arthouse", lambda: logo_tile(whiten(um.trim(um.commons("File:The Criterion Collection logo and wordmark.svg", 2000)), False), None, None, maxw=0.55, img=still(m, 490), img_b=0.3)),
        J("Awards & Festivals", "The Emmy Awards", emmy),
        # Networks
        J("Networks", "Fuji TV / MBS", lambda: network([um.fit(whiten(logo_png("/4x4GsmRmSLLL0RVNKsoqAVH43tz.png")), 640, 260), um.fit(whiten(net_logo(94)), 520, 200)],
                                                       net_stills("1|94"))),
    ] + [J("Iconic Actors", n, (lambda n=n: ("portrait", n, "FEATURED FILMOGRAPHY"))) for n in (
        "Frances McDormand", "Edward Norton", "Philip Seymour Hoffman", "Bryan Cranston", "Tilda Swinton", "Toni Collette",
        "Ethan Hawke", "Sam Rockwell", "Simon Pegg", "Robert Pattinson")] + [J("Legendary Directors", "Sofia Coppola", lambda: ("portrait", "Sofia Coppola", "DIRECTOR"))]


def pair(a, b, gap=90):
    a, b = um.fit(a, 900, 420), um.fit(b, 900, 260)
    hh = max(a.height, b.height)
    out = Image.new("RGBA", (a.width + b.width + gap * 2, hh), (0, 0, 0, 0))
    out.alpha_composite(a, (0, (hh - a.height) // 2))
    ImageDraw.Draw(out).line((a.width + gap, hh * 0.15, a.width + gap, hh * 0.85), fill=(40, 40, 50, 200), width=4)
    out.alpha_composite(b, (a.width + gap * 2, (hh - b.height) // 2))
    return out


def net_stills(nets, n=3):
    r = (tmdb("/discover/tv", with_networks=nets, sort_by="vote_count.desc") or {}).get("results", [])
    return [art.fetch(x["backdrop_path"]).convert("RGB") for x in r if x.get("backdrop_path")][:n]


def net_logo(nid):
    lg = [x for x in (tmdb(f"/network/{nid}/images") or {}).get("logos", []) if x["file_path"].endswith(".png")]
    return logo_png(lg[0]["file_path"])


def emmy():
    """TMDB's The Emmy Awards stills (statuette); the name set in gold Cinzel like the Oscars tile's logotype."""
    img = still("tv", 28464)
    name = um.stops_fill(tl("EMMY AWARDS", um.font("cinzel", 150, weight=600), tr=16),
                         [(0, (255, 236, 180)), (0.5, (226, 180, 90)), (1, (160, 110, 40))])
    return logo_tile(name, None, None, maxw=0.6, img=img, img_b=0.55, glow_col=(255, 190, 80))


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-").replace("--", "-")


def person(name):
    pid = (tmdb("/search/person", query=name) or {})["results"][0]["id"]
    pr = sorted((tmdb(f"/person/{pid}/images") or {}).get("profiles", []), key=lambda x: (-x["vote_average"], -x["height"]))
    img = art.fetch(pr[0]["file_path"]).convert("RGB")
    cr = (tmdb(f"/person/{pid}/movie_credits") or {})
    films = sorted([c for c in cr.get("cast", []) + cr.get("crew", []) if c.get("backdrop_path")], key=lambda c: -c.get("vote_count", 0))
    hero = art.fetch(films[0]["backdrop_path"]).convert("RGB") if films else None
    return img, hero


def render(job, out):
    d = os.path.join(out, slug(job["row"]), slug(job["title"]))
    os.makedirs(d, exist_ok=True)
    made = job["make"]()
    if isinstance(made, tuple) and made[0] == "portrait":
        _, name, sub = made
        img, hero = person(name)
        parts = name.upper().split(" ")
        lines = [" ".join(parts[:-1]), parts[-1]] if len(parts) > 1 else parts
        portrait(img, lines, sub).save(os.path.join(d, "cover.jpg"), quality=90)
        if hero is not None:
            art.graded(hero, 0.95, 1.03, (1920, 1080)).save(os.path.join(d, "backdrop.jpg"), quality=86)
        return d
    frame = made
    full = frame(1.0, 0.5)
    full.save(os.path.join(d, "cover.jpg"), quality=90)
    n = 54
    small = []
    for i in range(n):
        p = min(1, i / (n * 0.55))
        small.append(frame(p, i / n).resize((512, 288) if full.width > full.height else (300, 450), Image.LANCZOS))
    small[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=small[1:], duration=[55] * n, loop=0,
                  quality=80, method=5, minimize_size=True, allow_mixed=True)
    return d


if __name__ == "__main__":
    out = sys.argv[1]
    want = set(sys.argv[2:])
    for jb in jobs():
        if want and jb["title"] not in want and slug(jb["title"]) not in want:
            continue
        try:
            print("built", render(jb, out))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", jb["title"], e)
