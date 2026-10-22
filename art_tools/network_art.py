"""Networks row: an animated focus image for every channel, in the look of Kaptain's static ones (black poster, the
channel's flagship show faint behind its logo, a frame and glow in the channel colour), now moving: the channel's
best-known shows cross-fade behind the logo with a slow push-in, the frame traces itself around the card, the logo
glows up and a light passes over it. Shows: TMDB, the channel's most-voted series with a textless backdrop.
Fuji TV / MBS (no Kaptain art) also gets a cover in the same look and a hero.
usage: python3 art_tools/network_art.py BASELINE_JSON OUT_DIR [titles...]
"""
import io, json, math, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

PW, PH = 600, 900           # render size (Kaptain's posters are 1000x1500; the focus WebP goes out at 400x600)
OW, OH = 400, 600
NETS = {"HBO": [49], "FX": [88], "AMC": [174], "Showtime": [67], "BBC": [4, 332, 3, 100], "ITV": [9],
        "Channel 4": [26], "U&Dave": [388], "Sky Atlantic": [1063], "TV Tokyo": [98], "Fuji TV / MBS": [1, 94],
        "Adult Swim": [80], "Comedy Central": [47], "Syfy": [77], "Cartoon Network": [56], "Discovery Channel": [64],
        "National Geographic": [43], "History Channel": [65], "Food Network": [143], "USA Network": [30], "NBC": [6],
        "FOX": [19], "ABC": [2], "CBS": [16]}
ACCENT = {"Fuji TV / MBS": (235, 40, 60)}
RAW = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/"


def load(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def accent_of(focus):
    im = focus.convert("RGBA")
    px = [im.getpixel((x, im.height // 2)) for x in range(12)]
    return max(px, key=lambda p: p[3] * (max(p[:3]) - min(p[:3]) + 1))[:3]


def shows(nets, n=4):
    r = (tmdb("/discover/tv", with_networks="|".join(map(str, nets)), sort_by="vote_count.desc",
              without_genres="10763|10767|10766") or {}).get("results", [])
    out = []
    for s in r:
        im = tmdb(f"/tv/{s['id']}/images", include_image_language="null") or {}
        bd = sorted([b for b in im.get("backdrops", []) if not b.get("iso_639_1")], key=lambda b: -b["vote_count"])
        if bd:
            out.append(art.fetch(bd[0]["file_path"], "w1280").convert("RGB"))
        if len(out) == n:
            break
    return out


def portrait(img, accent, b):
    im = art.cover_fit(img, PW, PH)
    im = ImageEnhance.Brightness(ImageEnhance.Color(im).enhance(0.8)).enhance(b)
    return Image.blend(im, Image.new("RGB", (PW, PH), accent), 0.12)


def zoomed(im, z):
    w, h = im.size
    cw, ch = round(w / (1 + z)), round(h / (1 + z))
    x, y = (w - cw) // 2, (h - ch) // 3
    return im.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS)


def vign(im):
    v = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(v).ellipse((-PW * 0.35, -PH * 0.2, PW * 1.35, PH * 1.2), fill=255)
    return Image.composite(im, Image.new("RGB", (PW, PH)), v.filter(ImageFilter.GaussianBlur(110)))


def frame_path(p):
    """Points of the rounded card outline, traced from the top centre clockwise, up to fraction p."""
    m, r = 6, 26
    x0, y0, x1, y1 = m, m, PW - m, PH - m
    pts = []
    seg = [((PW / 2, y0), (x1 - r, y0)), None, ((x1, y0 + r), (x1, y1 - r)), None, ((x1 - r, y1), (x0 + r, y1)), None,
           ((x0, y1 - r), (x0, y0 + r)), None, ((x0 + r, y0), (PW / 2, y0))]
    corners = [(x1 - r, y0 + r, -90, 0), (x1 - r, y1 - r, 0, 90), (x0 + r, y1 - r, 90, 180), (x0 + r, y0 + r, 180, 270)]
    ci = 0
    for s in seg:
        if s is None:
            cx, cy, a0, a1 = corners[ci]
            ci += 1
            for k in range(9):
                a = math.radians(a0 + (a1 - a0) * k / 8)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        else:
            (ax, ay), (bx, by) = s
            for k in range(12):
                pts.append((ax + (bx - ax) * k / 11, ay + (by - ay) * k / 11))
    n = max(2, round(len(pts) * p))
    return pts[:n]


def make(logo, stills, accent):
    lg = logo.convert("RGBA")
    k = min(PW * 0.66 / lg.width, PH * 0.2 / lg.height)
    lg = lg.resize((round(lg.width * k), round(lg.height * k)), Image.LANCZOS)
    bgs = [portrait(s, accent, 0.36) for s in stills] or [Image.new("RGB", (PW, PH), (10, 10, 12))]

    def glow(layer, r, a):
        g = Image.new("RGBA", (layer.width + 6 * r, layer.height + 6 * r), accent + (0,))
        m = Image.new("L", g.size, 0)
        m.paste(layer.getchannel("A"), (3 * r, 3 * r))
        g.putalpha(m.filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, round(v * a))))
        return g

    def frame(i, n):
        t = i / n
        seg = t * len(bgs)
        j = min(len(bgs) - 1, int(seg))
        loc = seg - j
        bg = zoomed(bgs[j], 0.03 + 0.07 * loc)
        if loc > 0.8:
            bg = Image.blend(bg, zoomed(bgs[(j + 1) % len(bgs)], 0.03), (loc - 0.8) / 0.2)
        cv = vign(bg).convert("RGBA")
        # accent bloom behind the logo
        bloom = Image.new("L", (PW, PH), 0)
        ImageDraw.Draw(bloom).ellipse((PW * 0.1, PH * 0.3, PW * 0.9, PH * 0.7), fill=round(70 * (0.75 + 0.25 * math.sin(t * math.pi * 4))))
        bl = Image.new("RGBA", (PW, PH), accent + (0,))
        bl.putalpha(bloom.filter(ImageFilter.GaussianBlur(90)))
        cv.alpha_composite(bl)
        a = ease(t / 0.2)
        s = 0.92 + 0.08 * ease(t / 0.3)
        L = lg.resize((round(lg.width * s), round(lg.height * s)), Image.LANCZOS)
        g = glow(L, 14, 0.9 * a)
        cv.alpha_composite(g, (round(PW / 2 - g.width / 2), round(PH / 2 - g.height / 2)))
        L2 = L.copy()
        L2.putalpha(L.getchannel("A").point(lambda v: round(v * a)))
        cv.alpha_composite(L2, (round(PW / 2 - L.width / 2), round(PH / 2 - L.height / 2)))
        if 0.45 < t < 0.7:  # light over the logo
            sp = (t - 0.45) / 0.25
            band = Image.new("L", L.size, 0)
            bx = -80 + sp * (L.width + 160)
            ImageDraw.Draw(band).polygon([(bx, 0), (bx + 40, 0), (bx - 30, L.height), (bx - 70, L.height)], fill=170)
            band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(8)), L.getchannel("A"))
            wl = Image.new("RGBA", L.size, (255, 255, 255, 0))
            wl.putalpha(band)
            cv.alpha_composite(wl, (round(PW / 2 - L.width / 2), round(PH / 2 - L.height / 2)))
        # the frame traces itself round the card, then stays
        pts = frame_path(ease(t / 0.35))
        fr = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        ImageDraw.Draw(fr).line(pts, fill=accent + (255,), width=4, joint="curve")
        gl = Image.new("RGBA", (PW, PH), accent + (0,))
        gl.putalpha(fr.getchannel("A").filter(ImageFilter.GaussianBlur(8)))
        cv.alpha_composite(gl)
        cv.alpha_composite(fr)
        return cv.convert("RGB")
    return frame


def main():
    base, out = sys.argv[1], sys.argv[2]
    only = set(sys.argv[3:])
    d = json.load(open(base, encoding="utf-8"))
    row = [c for c in d if c["title"] == "Networks"][0]
    for f in row["folders"]:
        t = f["title"]
        if only and t not in only:
            continue
        try:
            logo = load(f["titleLogoUrl"].split("?")[0])
            if t == "Fuji TV / MBS":
                fuji = load("https://image.tmdb.org/t/p/original/4x4GsmRmSLLL0RVNKsoqAVH43tz.png").convert("RGBA")
                mbs = [x for x in (tmdb("/network/94/images") or {}).get("logos", []) if x["file_path"].endswith(".png")]
                mbs = load("https://image.tmdb.org/t/p/original" + mbs[0]["file_path"]).convert("RGBA")
                logo = stack(white(fuji, keep=True), white(mbs))
            accent = ACCENT.get(t) or accent_of(load(f["focusGifUrl"].split("?")[0]))
            stills = shows(NETS[t])
            frame = make(logo, stills, accent)
            slug = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
            while "--" in slug:
                slug = slug.replace("--", "-")
            dd = os.path.join(out, slug)
            os.makedirs(dd, exist_ok=True)
            n = 96
            frames = [frame(i, n).resize((OW, OH), Image.LANCZOS) for i in range(n)]
            frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * n,
                           loop=0, quality=80, method=5, minimize_size=True, allow_mixed=True)
            if t == "Fuji TV / MBS":  # cover + hero in Kaptain's look
                cov = make(logo, [ImageEnhance.Brightness(s).enhance(0.45) for s in stills[:1]], accent)
                c = cov(n - 1, n)
                # Kaptain's covers have no frame: crop the frame off by repainting the edge black
                c = ImageOps.expand(c.crop((10, 10, PW - 10, PH - 10)), 10, (0, 0, 0)).resize((1000, 1500), Image.LANCZOS)
                c.save(os.path.join(dd, "cover.jpg"), quality=90)
                art.graded(stills[0], 0.95, 1.03, (1920, 1080)).save(os.path.join(dd, "backdrop.jpg"), quality=86)
                logo.save(os.path.join(dd, "logo.png"))
            strip = Image.new("RGB", (OW * 6, OH))
            for j, idx in enumerate([0, 12, 25, 45, 70, 95]):
                strip.paste(frames[idx], (j * OW, 0))
            strip.resize((OW * 3, OH // 2)).save(os.path.join(dd, "frames.jpg"), quality=80)
            print("built", t, dd)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", t, e)


def white(im, keep=False):
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and (not keep or max(r, g, b) - min(r, g, b) < 60):
                px[x, y] = (255, 255, 255, a)
    bb = im.getchannel("A").getbbox()
    return im.crop(bb)


def stack(a, b, gap=60):
    b = b.resize((round(b.width * a.width * 0.7 / b.width), round(b.height * a.width * 0.7 / b.width)), Image.LANCZOS)
    out = Image.new("RGBA", (max(a.width, b.width), a.height + gap + b.height), (0, 0, 0, 0))
    out.alpha_composite(a, ((out.width - a.width) // 2, 0))
    out.alpha_composite(b, ((out.width - b.width) // 2, a.height + gap))
    return out


if __name__ == "__main__":
    main()
