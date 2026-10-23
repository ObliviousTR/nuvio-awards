"""Reality TV row, "on air": every card plays three shows of its kind under a reality-TV graphics package - a lower
third with the show and its channel - and its own game element that carries one show to the next:
  Cooking      a kitchen countdown; at 0:00 TIME'S UP and the next kitchen
  Makeover     a before / after slider sweeping one show away for the next
  (Trending: ranking bars, Strategy: countdown + ELIMINATED, Panel & Quiz: a scoreboard, Dating: a heart meter)
The card's name sits like Kaptain's (big, lower left) on the cover and tucks into a tag top left on hover.
The trio moves on every month through each card's pool; pictures are fanart.tv / TMDB show art.
usage: python3 art_tools/reality_art.py OUT_DIR [folder titles...]     (REALITY_TEST=1: local stills)
"""
import datetime as dt, math, os, random, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from reletter import f as font, tracked, width

W, H = 1280, 720
OW, OH = 512, 288
TEST = bool(os.environ.get("REALITY_TEST"))

# folder -> (title, subtitle, accent, game, pool of (show, first-air year))
CARDS = {
    "Culinary & Cooking Battles": ("COOKING BATTLES", "CHEFS, BAKERS & KITCHEN HEAT", (235, 70, 50), "timer", [
        ("Hell's Kitchen", 2005), ("The Great British Bake Off", 2010), ("MasterChef", 2010), ("Nailed It!", 2018),
        ("Top Chef", 2006), ("Kitchen Nightmares", 2007), ("Culinary Class Wars", 2024), ("Chopped", 2009),
        ("MasterChef Australia", 2009)]),
    "Makeover, Motors & Craft Battles": ("MAKEOVER & MOTORS", "HOMES, CARS, CRAFTS & FRESH STARTS", (160, 110, 255), "slider", [
        ("Queer Eye", 2018), ("Top Gear", 2002), ("The Repair Shop", 2017), ("Fixer Upper", 2013), ("Blown Away", 2019),
        ("Pimp My Ride", 2004), ("Making It", 2018), ("Wheeler Dealers", 2003), ("Selling Sunset", 2019)]),
}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def amul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def cover_fit(im, w=W, h=H):
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 3
    return im.crop((x, y, x + w, y + h))


def zoomed(im, z):
    w, h = im.size
    cw, ch = w / (1 + z), h / (1 + z)
    x, y = (w - cw) / 2, (h - ch) / 2
    return im.resize((w, h), Image.BILINEAR, box=(x, y, x + cw, y + ch))


# ---------------------------------------------------------------- shows
def shows_of(folder, n=3):
    pool = CARDS[folder][4]
    if TEST:
        import glob
        fs = [f for f in sorted(glob.glob("/home/claude/nuvio-art/mirror/files/*/*.jpg")) if os.path.getsize(f) > 150000]
        rnd = random.Random(folder)
        out = []
        while len(out) < n:
            p = rnd.choice(fs)
            im = Image.open(p)
            if im.width >= 1200 and 1.6 < im.width / im.height < 1.9:
                out.append((pool[len(out)][0], "NETWORK", p))
        return out
    import kids_art as K
    m = dt.date.today().year * 12 + dt.date.today().month
    start = (m * n) % len(pool)
    out = []
    for t, y in pool[start:] + pool[:start]:
        a = K.art_of(("tv", t, y))
        if not a:
            continue
        det = K.tmdb(f"/tv/{a[0]}") or {}
        nets = [x["name"] for x in det.get("networks", [])]
        out.append((det.get("name") or t, (nets[0] if nets else "").upper(), a[2]))
        if len(out) == n:
            break
    return out


def load(p):
    if TEST:
        return Image.open(p).convert("RGB")
    import kids_art as K
    return K.g.load_img(p)


# ---------------------------------------------------------------- the package
def fall(top=0.5, a=0.85):
    f = np.clip((np.linspace(0, 1, H, dtype=np.float32) - top) / (1 - top), 0, 1) ** 1.3 * a
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.putalpha(Image.fromarray((np.repeat(f[:, None], W, 1) * 255).astype(np.uint8)))
    return lay


def title_block(title, sub, accent):
    """Kaptain's card lettering: accent bar, big title, tracked subtitle (lower left)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    fn = font("ExtraBold", 74)
    while width(title, fn, 3) > W * 0.86 and fn.size > 40:
        fn = font("ExtraBold", fn.size - 2)
    y = H - 168
    d.rectangle((46, y + 8, 52, y + fn.size + 46), fill=accent + (255,))
    tracked(d, (68 + 3, y + 3), title, fn, (0, 0, 0, 150), 3)
    tracked(d, (68, y), title, fn, (255, 255, 255, 255), 3)
    tracked(d, (70, y + fn.size + 14), sub, font("SemiBold", 22), (230, 230, 235, 255), 6)
    return lay


def tag(title, accent):
    """The card's name tucked into a tag, top left."""
    fn = font("ExtraBold", 24)
    tw = width(title, fn, 4)
    lay = Image.new("RGBA", (round(tw) + 70, 52), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, lay.width - 1, 51), radius=10, fill=(12, 12, 14, 215))
    d.ellipse((18, 19, 32, 33), fill=accent + (255,))
    tracked(d, (44, 13), title, fn, (255, 255, 255, 255), 4)
    return lay


def lower_third(show, net, accent, p):
    """Reality-TV lower third: an accent block and a white bar slide in from the left (p 0..1), the show's name on it."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if p <= 0:
        return lay
    d = ImageDraw.Draw(lay)
    fn = font("ExtraBold", 40)
    t = show.upper()
    while width(t, fn, 2) > W * 0.62 and fn.size > 24:
        fn = font("ExtraBold", fn.size - 2)
    tw = width(t, fn, 2)
    x0, y0 = 48, H - 150
    e1, e2 = ease(p / 0.6), ease((p - 0.25) / 0.75)
    bar_w = (tw + 64) * e2
    d.rectangle((x0, y0, x0 + 16 * e1, y0 + 66), fill=accent + (255,))
    if bar_w > 2:
        d.rectangle((x0 + 16, y0, x0 + 16 + bar_w, y0 + 66), fill=(250, 250, 250, 245))
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(txt), (x0 + 40, y0 + 10), t, fn, (18, 18, 20, 255), 2)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle((x0 + 16, y0, x0 + 16 + bar_w, y0 + 66), fill=255)
        txt.putalpha(Image.composite(txt.getchannel("A"), Image.new("L", (W, H), 0), m))
        lay.alpha_composite(txt)
    if net and e2 > 0.5:
        sf = font("SemiBold", 20)
        nw = width(net, sf, 6)
        d.rectangle((x0 + 16, y0 + 66, x0 + 16 + nw + 48, y0 + 100), fill=accent + (round(255 * ease((e2 - 0.5) * 2)),))
        tracked(d, (x0 + 40, y0 + 72), net, sf, (255, 255, 255, round(255 * ease((e2 - 0.5) * 2))), 6)
    return lay


# ---------------------------------------------------------------- game elements
def timer(sec, accent, flash=0.0):
    """A kitchen countdown, top right; red in the last seconds; TIME'S UP at zero."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x1, y0 = W - 48, 44
    box = (x1 - 250, y0, x1, y0 + 96)
    d.rounded_rectangle(box, radius=18, fill=(12, 12, 14, 225), outline=accent + (255,), width=4)
    # a little stopwatch crown
    d.rounded_rectangle((box[0] + 30, y0 - 14, box[0] + 54, y0 + 2), radius=4, fill=accent + (255,))
    if sec > 0:
        s = f"0:{int(math.ceil(sec)):02d}"
        col = (255, 70, 60) if sec <= 5 else (255, 255, 255)
        fn = font("ExtraBold", 62)
        tw = width(s, fn, 2)
        tracked(d, ((box[0] + box[2]) / 2 - tw / 2, y0 + 10), s, fn, col + (255,), 2)
    else:
        fn = font("ExtraBold", 34)
        s = "TIME'S UP!"
        tw = width(s, fn, 2)
        tracked(d, ((box[0] + box[2]) / 2 - tw / 2, y0 + 28), s, fn, (255, 70, 60, 255), 2)
    if flash > 0:
        g = Image.new("RGBA", (W, H), (255, 255, 255, round(110 * flash)))
        lay.alpha_composite(g)
    return lay


def whip(a, b, u):
    """A whip pan: a slides out left, b comes in from the right, both smeared."""
    e = ease(u)
    off = round(W * e)
    out = Image.new("RGB", (W, H))
    out.paste(a, (-off, 0))
    out.paste(b, (W - off, 0))
    blur = math.sin(math.pi * u)
    if blur > 0.05:
        smear = out.resize((W // 10, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        out = Image.blend(out, smear, 0.85 * blur)
    return out


def slider(a, b, u, accent):
    """Before / after: the handle sweeps right to left; to its left the old show (BEFORE), to its right the new one."""
    x = round(W * (1 - ease(u)))
    out = a.copy()
    out.paste(b.crop((x, 0, W, H)), (x, 0))
    cv = out.convert("RGBA")
    d = ImageDraw.Draw(cv)
    if 0 < x < W:
        d.rectangle((x - 3, 0, x + 3, H), fill=(255, 255, 255, 255))
        cy = H * 0.45
        d.ellipse((x - 34, cy - 34, x + 34, cy + 34), fill=(255, 255, 255, 255))
        d.polygon([(x - 8, cy - 12), (x - 22, cy), (x - 8, cy + 12)], fill=accent + (255,))
        d.polygon([(x + 8, cy - 12), (x + 22, cy), (x + 8, cy + 12)], fill=accent + (255,))
        fn = font("ExtraBold", 22)
        if x > 200:
            tw = width("BEFORE", fn, 5)
            d.rounded_rectangle((x - tw - 70, 120, x - 24, 162), radius=8, fill=(12, 12, 14, 210))
            tracked(d, (x - tw - 48, 129), "BEFORE", fn, (255, 255, 255, 255), 5)
        if x < W - 200:
            d.rounded_rectangle((x + 24, 120, x + 24 + width("AFTER", fn, 5) + 46, 162), radius=8, fill=accent + (235,))
            tracked(d, (x + 46, 129), "AFTER", fn, (255, 255, 255, 255), 5)
    return cv.convert("RGB")


# ---------------------------------------------------------------- the card
def slug_of(t):
    s = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


def build(folder, out):
    title, sub, accent, game, _ = CARDS[folder]
    shows = shows_of(folder)
    pics = [cover_fit(load(p)) for _, _, p in shows]
    fl = fall()
    tb = title_block(title, sub, accent)
    tg = tag(title, accent)
    cv = pics[0].convert("RGBA")
    cv.alpha_composite(fl)
    cv.alpha_composite(tb)
    cover = cv.convert("RGB")
    HOLD, DOCK, SEG, BACK = 6, 12, 46, 14
    S = len(shows)
    T1 = HOLD + DOCK
    T2 = T1 + SEG * S
    N_ = T2 + BACK
    TR = 8                                   # the hand-over between shows (last frames of a segment)
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < T1:      # the big title gives way to the tag and the lower third
            u = (i - HOLD) / DOCK
            c = zoomed(pics[0], 0.01 * u).convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(amul(tb, 1 - ease(u * 1.6)))
            c.alpha_composite(amul(tg, ease((u - 0.3) / 0.7)), (40, 34))
            c.alpha_composite(lower_third(shows[0][0], shows[0][1], accent, (u - 0.4) / 0.6))
            if game == "timer":
                c.alpha_composite(amul(timer(30, accent), ease((u - 0.3) / 0.7)))
        elif i < T2:
            k, t = divmod(i - T1, SEG)
            z = 0.01 + 0.04 * t / SEG
            pic = zoomed(pics[k], z)
            last = k == S - 1
            lt = 1.0
            game_lay = None
            if game == "timer":
                sec = 30 * (1 - t / (SEG - TR))
                flash = 0.0
                if t >= SEG - TR:
                    sec = 0
                    flash = max(0.0, 1 - (t - (SEG - TR)) / 3)
                    if not last:   # time's up: whip to the next kitchen
                        pic = whip(pic, zoomed(pics[k + 1], 0.01), (t - (SEG - TR) - 2) / (TR - 2)) if t - (SEG - TR) >= 2 else pic
                game_lay = timer(sec, accent, flash)
                lt = 1 - ease((t - (SEG - TR)) / 3) if t >= SEG - TR else ease(t / 6) if k > 0 else 1.0
            elif game == "slider":
                if t >= SEG - 14 and not last:
                    u = (t - (SEG - 14)) / 14
                    pic = slider(pic, zoomed(pics[k + 1], 0.01), u, accent)
                    lt = 1 - ease(u * 2)
                elif k > 0:
                    lt = ease(t / 8)
            c = pic.convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(tg, (40, 34))
            c.alpha_composite(lower_third(shows[k][0], shows[k][1], accent, lt))
            if game_lay is not None:
                c.alpha_composite(game_lay)
        else:           # back to the card
            u = ease((i - T2) / BACK)
            c = Image.blend(zoomed(pics[-1], 0.05), pics[0], u).convert("RGBA")
            c.alpha_composite(fl)
            c.alpha_composite(amul(tg, 1 - u), (40, 34))
            c.alpha_composite(lower_third(shows[-1][0], shows[-1][1], accent, 1 - u * 1.4))
            if game == "timer":
                c.alpha_composite(amul(timer(0, accent), 1 - u))
            c.alpha_composite(amul(tb, ease((u - 0.3) / 0.7)))
        frames.append(c.convert("RGB").resize((OW, OH), Image.LANCZOS))
    d = os.path.join(out, slug_of(folder))
    os.makedirs(d, exist_ok=True)
    frames[0].save(os.path.join(d, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * len(frames),
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    cover.save(os.path.join(d, "cover.jpg"), quality=90)
    n = len(frames)
    strip = Image.new("RGB", (OW * 4, OH * 2))
    for j, idx in enumerate([0, 14, 40, 58, 62, 90, 108, n - 6]):
        strip.paste(frames[min(idx, n - 1)], ((j % 4) * OW, (j // 4) * OH))
    strip.save(os.path.join(d, "frames.jpg"), quality=80)
    return [f"{s} ({nw})" for s, nw, _ in shows]


if __name__ == "__main__":
    out = sys.argv[1]
    bad = False
    for fo in sys.argv[2:] or CARDS:
        try:
            print("built", fo, "·", ", ".join(build(fo, out)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", fo, e)
            bad = True
    sys.exit(1 if bad else 0)
