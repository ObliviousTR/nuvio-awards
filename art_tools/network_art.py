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

PW, PH = 480, 720           # render size (Kaptain's posters are 1000x1500; the focus WebP goes out at 400x600)
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


def heavy_vignette():
    v = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(v).ellipse((-PW * 0.15, PH * 0.12, PW * 1.15, PH * 0.88), fill=255)
    return v.filter(ImageFilter.GaussianBlur(130))


def make(logo, stills, accent):
    """Kaptain's Cinematic Ghost look, animated. Frame 0 = the cover: the channel's most popular show as a ghost behind
    a heavy vignette, plain logo. Then, per show: the channel colour glows up under the logo and lights the show, a
    glowing frame runs once round the card; when it closes, a breath (the glow swells and eases) while the next show
    fades in, and the frame starts its next lap. The last show hands back to the cover, so the loop is seamless."""
    lg = logo.convert("RGBA")
    k = min(PW * 0.66 / lg.width, PH * 0.2 / lg.height)
    lg = lg.resize((round(lg.width * k), round(lg.height * k)), Image.LANCZOS)
    bgs = [ImageEnhance.Color(art.cover_fit(s, PW, PH)).enhance(0.85) for s in stills] or [Image.new("RGB", (PW, PH), (10, 10, 12))]
    vg = heavy_vignette()
    black = Image.new("RGB", (PW, PH))
    tint = Image.new("RGB", (PW, PH), accent)
    bloom = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(bloom).ellipse((PW * 0.08, PH * 0.36, PW * 0.92, PH * 0.82), fill=255)
    bloom = bloom.filter(ImageFilter.GaussianBlur(95))
    lg_glow = Image.new("RGBA", (lg.width + 120, lg.height + 120), accent + (0,))
    m = Image.new("L", lg_glow.size, 0)
    m.paste(lg.getchannel("A"), (60, 60))
    lg_glow_mask = m.filter(ImageFilter.GaussianBlur(20))
    S = len(bgs)

    def frame(i, n):
        t = i / n
        c = ease(t / 0.1) if t < 0.94 else 1 - ease((t - 0.94) / 0.06)  # colour on, and off again at the loop's end
        seg = t * S
        j = min(S - 1, int(seg))
        loc = seg - j
        breath = math.sin(math.pi * (loc - 0.82) / 0.18) if loc > 0.82 else 0.0
        bg = zoomed(bgs[j], 0.03 + 0.07 * loc)
        if loc > 0.82:
            bg = Image.blend(bg, zoomed(bgs[(j + 1) % S], 0.03), (loc - 0.82) / 0.18)
        bg = ImageEnhance.Brightness(bg).enhance(0.22 + 0.16 * c)
        bg = Image.blend(bg, tint, 0.08 * c)
        bg = Image.composite(bg, black, vg)
        cv = bg.convert("RGBA")
        if c > 0:
            wl = Image.new("RGBA", (PW, PH), accent + (0,))
            wl.putalpha(bloom.point(lambda v: round(v * (0.42 + 0.18 * breath) * c)))
            cv.alpha_composite(wl)
            g = Image.new("RGBA", lg_glow.size, accent + (0,))
            g.putalpha(lg_glow_mask.point(lambda v: min(255, round(v * (0.9 + 0.5 * breath) * c))))
            cv.alpha_composite(g, (round(PW / 2 - g.width / 2), round(PH / 2 - g.height / 2)))
            # the frame: one lap per show, closed before the breath, cleared as the next lap starts
            lap = min(1.0, loc / 0.8)  # constant speed round the card
            fa = c * (1.0 if loc < 0.97 else 1 - (loc - 0.97) / 0.03)
            fr = Image.new("L", (PW, PH), 0)
            pts = frame_path(lap)
            if len(pts) > 1:
                ImageDraw.Draw(fr).line(pts, fill=255, width=4, joint="curve")
            head = Image.new("L", (PW, PH), 0)
            if lap < 1 and len(pts) > 1:  # bright head of the running line
                hx, hy = pts[-1]
                ImageDraw.Draw(head).ellipse((hx - 9, hy - 9, hx + 9, hy + 9), fill=255)
            glowm = ImageChops.lighter(fr, head).filter(ImageFilter.GaussianBlur(9 + 6 * breath))
            gl = Image.new("RGBA", (PW, PH), accent + (0,))
            gl.putalpha(glowm.point(lambda v: min(255, round(v * (1.1 + 0.8 * breath) * fa))))
            cv.alpha_composite(gl)
            ln = Image.new("RGBA", (PW, PH), accent + (0,))
            ln.putalpha(fr.point(lambda v: round(v * fa)))
            cv.alpha_composite(ln)
        cv.alpha_composite(lg, (round(PW / 2 - lg.width / 2), round(PH / 2 - lg.height / 2)))
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
            stills = shows(NETS[t], 3)
            frame = make(logo, stills, accent)
            slug = "".join(ch if ch.isalnum() else "-" for ch in t.lower()).strip("-")
            while "--" in slug:
                slug = slug.replace("--", "-")
            dd = os.path.join(out, slug)
            os.makedirs(dd, exist_ok=True)
            n = 120  # 3 shows x 40 frames, 50 ms: 2 s per show, 6 s loop
            frames = [frame(i, n).resize((OW, OH), Image.LANCZOS) for i in range(n)]
            frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * n,
                           loop=0, quality=80, method=5, minimize_size=True, allow_mixed=True)
            frame(0, n).resize((1000, 1500), Image.LANCZOS).save(os.path.join(dd, "cover.jpg"), quality=90)
            if t == "Fuji TV / MBS":  # hero + logo
                art.graded(stills[0], 0.95, 1.03, (1920, 1080)).save(os.path.join(dd, "backdrop.jpg"), quality=86)
                logo.save(os.path.join(dd, "logo.png"))
            strip = Image.new("RGB", (OW * 6, OH))
            for j, idx in enumerate([0, 20, 33, 38, 60, 119]):
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
