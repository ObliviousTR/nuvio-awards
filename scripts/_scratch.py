"""Prototype: an original SPIDER-VERSE wordmark + build animation over clean multiverse scenes."""
import io, json, math, os, random, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from spotlight import tmdb
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops
OUT = "refs/sv"; os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
fp = os.path.join(OUT, "Anton-Regular.ttf")
open(fp, "wb").write(urllib.request.urlopen(urllib.request.Request(
    "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf", headers=UA), timeout=60).read())
W, H = 1280, 720
RED, BLUE, WHITE = (230, 36, 41), (40, 120, 255), (255, 255, 255)

# ---- clean scenes: textless backdrops, one per corner of the multiverse
films = {"Raimi": 557, "Amazing": 1930, "MCU": 634649, "Spider-Verse": 324857, "Across": 569094}
cands = []
for k, mid in films.items():
    im = tmdb(f"/movie/{mid}/images", include_image_language="null") or {}
    b = sorted([x for x in im.get("backdrops", []) if not x.get("iso_639_1") and x["width"] >= 1920],
               key=lambda x: -x["vote_average"])[:4]
    cands += [(k, x["file_path"]) for x in b]
json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=0)
sheet = Image.new("RGB", (4 * 330, 190 * 5), (40, 40, 40)); d = ImageDraw.Draw(sheet)
for i, (k, p) in enumerate(cands[:20]):
    t = art.fetch(p, "w300").convert("RGB"); t.thumbnail((320, 180))
    sheet.paste(t, ((i % 4) * 330, (i // 4) * 190)); d.text(((i % 4) * 330 + 4, (i // 4) * 190 + 4), f"{i} {k}", fill=(255, 255, 0))
sheet.save(os.path.join(OUT, "cands.jpg"), quality=80)
pick = [cands[i] for i in (2, 6, 10, 12, 18) if i < len(cands)]

# ---- the wordmark (original design): condensed caps, white face, red / blue dimensional offsets
def word_layer(text, size, color):
    f = ImageFont.truetype(fp, size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    sp = round(size * 0.02)
    w = sum(probe.textlength(c, font=f) + sp for c in text) - sp
    im = Image.new("L", (round(w) + 40, round(size * 1.35)), 0)
    art.spaced(ImageDraw.Draw(im), (20, 0), text, f, 255, sp)
    m = im.crop(im.getbbox())
    lay = Image.new("RGBA", m.size, color + (0,)); lay.putalpha(m)
    return lay

def web(size, progress):
    """Radial web emblem drawn up to progress 0..1."""
    s = size; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2; n = 12
    rays = min(1, progress * 1.6)
    for i in range(n):
        a = i * 2 * math.pi / n - math.pi / 2
        r = c * rays
        d.line((c, c, c + r * math.cos(a), c + r * math.sin(a)), fill=(255, 255, 255, 70), width=2)
    rings = max(0, (progress - 0.25) / 0.75)
    for j in range(1, 6):
        if rings * 5 < j - 0.999: break
        rr = c * j / 5.4
        pts = [(c + rr * math.cos(i * 2 * math.pi / n - math.pi / 2), c + rr * math.sin(i * 2 * math.pi / n - math.pi / 2)) for i in range(n)]
        # slightly sagging threads between rays
        for i in range(n):
            p0, p1 = pts[i], pts[(i + 1) % n]
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            sag = 0.92
            mx, my = c + (mx - c) * sag, c + (my - c) * sag
            d.line((p0, (mx, my), p1), fill=(255, 255, 255, 55), width=2, joint="curve")
    return im

TEXT = "SPIDER-VERSE"
face = word_layer(TEXT, 170, WHITE); red = word_layer(TEXT, 170, RED); blue = word_layer(TEXT, 170, BLUE)
LW = face.width

def logo(t, shimmer=None):
    """t 0..1 build: web draws, colour copies glitch in and lock onto the white face."""
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wb = web(620, min(1, t / 0.55))
    if t >= 0.85:  # once the name locks, the web steps back
        wb.putalpha(wb.getchannel("A").point(lambda v: round(v * 0.55)))
    cv.alpha_composite(wb, ((W - 620) // 2, (H - 620) // 2 - 10))
    x0, y0 = (W - LW) // 2, (H - face.height) // 2
    k = max(0, min(1, (t - 0.25) / 0.6))           # 0 scattered -> 1 locked
    e = 1 - (1 - k) ** 3
    off = 7 + (1 - e) * 120
    rnd = random.Random(int(t * 1000))
    def put(layer, dx, dy, alpha):
        if alpha <= 0: return
        l = layer.copy(); l.putalpha(l.getchannel("A").point(lambda v: round(v * alpha)))
        if k < 1:   # horizontal glitch slices while it settles
            sl = Image.new("RGBA", l.size, (0, 0, 0, 0)); hh = l.height
            for y in range(0, hh, 14):
                sh = round(rnd.uniform(-1, 1) * 40 * (1 - e))
                sl.paste(l.crop((0, y, l.width, min(hh, y + 14))), (sh, y))
            l = sl
        cv.alpha_composite(l, (x0 + round(dx), y0 + round(dy)))
    a = min(1, t / 0.3)
    put(blue, off, -off * 0.15, a)
    put(red, -off, off * 0.15, a)
    put(face, 0, 0, max(0, (t - 0.45) / 0.3) if t < 0.75 else 1)
    if shimmer is not None:  # light sweep across the face
        band = Image.new("L", (W, H), 0); bd = ImageDraw.Draw(band)
        bx = -300 + shimmer * (W + 600)
        bd.polygon([(bx, 0), (bx + 90, 0), (bx - 110, H), (bx - 200, H)], fill=150)
        band = band.filter(ImageFilter.GaussianBlur(30))
        m = ImageChops.multiply(band, cv.getchannel("A"))
        glow = Image.new("RGBA", (W, H), (255, 255, 255, 0)); glow.putalpha(m)
        cv.alpha_composite(glow)
    # tagline
    if t > 0.8:
        f = art.font("SemiBold", 26); g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        tag = "EVERY SPIDER  ·  EVERY UNIVERSE"
        tw = sum(gd.textlength(c, font=f) + 8 for c in tag)
        art.spaced(gd, ((W - tw) / 2, y0 + face.height + 28), tag, f, (255, 255, 255, round(255 * min(1, (t - 0.8) / 0.2))), 8)
        cv.alpha_composite(g)
    return cv

scenes = [ImageEnhance.Brightness(art.graded(art.fetch(p), 0.9, 1.05)).enhance(0.62) for _, p in pick]
def vignette(im):
    v = Image.new("L", (W, H), 0); ImageDraw.Draw(v).ellipse((-W * 0.2, -H * 0.3, W * 1.2, H * 1.3), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(120))
    return Image.composite(im, Image.new("RGB", (W, H), (0, 0, 0)), v)
BUILD, HOLD = 26, 34
N = BUILD + HOLD
frames = []
for i in range(N):
    g = i / N; seg = min(len(scenes) - 1, int(g * len(scenes))); loc = g * len(scenes) - seg
    bg = art.zoomed(scenes[seg], 0.02 + 0.06 * loc)
    if loc > 0.78:
        bg = Image.blend(bg, art.zoomed(scenes[(seg + 1) % len(scenes)], 0.02), (loc - 0.78) / 0.22)
    bg = vignette(bg).convert("RGBA")
    t = min(1, i / BUILD)
    sh = ((i - BUILD) / HOLD) if i >= BUILD and (i - BUILD) < HOLD * 0.5 else None
    if sh is not None: sh = sh * 2
    bg.alpha_composite(logo(t, sh))
    frames.append(bg.convert("RGB"))
cover = frames[BUILD + HOLD // 2]
frames[-1].save(os.path.join(OUT, "cover-last.jpg"), quality=90)
# cover: first scene + locked logo, no shimmer
c = vignette(art.zoomed(scenes[0], 0.04)).convert("RGBA"); c.alpha_composite(logo(1.0)); c.convert("RGB").save(os.path.join(OUT, "cover.jpg"), quality=90)
logo(1.0).save(os.path.join(OUT, "logo.png"))
small = [f.resize((512, 288), Image.LANCZOS) for f in frames]
pal = Image.new("RGB", (512, 288 * 4))
for j, idx in enumerate((5, BUILD, BUILD + 20, N - 1)): pal.paste(small[idx], (0, 288 * j))
pal = pal.convert("P", palette=Image.ADAPTIVE, colors=128)
q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in small]
q[0].save(os.path.join(OUT, "hover.gif"), save_all=True, append_images=q[1:], duration=[60] * BUILD + [95] * HOLD, loop=0, optimize=True)
strip = Image.new("RGB", (512 * 4, 288 * 2))
for j, idx in enumerate([0, 6, 12, 18, 24, 34, 46, N - 1]): strip.paste(small[idx], ((j % 4) * 512, (j // 4) * 288))
strip.save(os.path.join(OUT, "frames.jpg"), quality=80)
open(os.path.join(OUT, "log.txt"), "w").write(f"picked {pick}\ngif {os.path.getsize(os.path.join(OUT, 'hover.gif'))//1024} KB")
