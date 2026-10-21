"""Universes & Franchises art: a landscape cover (1280x720), a hover GIF and a hero backdrop per folder.

Cover: the universe's sub-series side by side in slanted panels (one image per era / sub-series, so Wizarding World
is Hogwarts *and* Fantastic Beasts, not one Harry Potter poster), a light bottom fade (Favourites style, no heavy
vignette) and the universe's logo, or its name set in type when no single logo covers the folder.
Hover GIF: the same images one after another, full frame, slow push-in with crossfades, logo held.
Images: TMDB (textless backdrops), logos from TMDB or Wikimedia Commons.
usage: python3 scripts/universe_art.py OUT_DIR [ids...]
"""
import io, json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

W, H = art.W, art.H
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) nuvio-awards"}

# id -> panels (TMDB backdrop paths, left to right), logo source, optional typeset name
SPECS = {
    "wizarding": dict(
        panels=["/4gV0rKUjB1nLUdZB4zIltLvNZZr.jpg", "/slW0M2G9txC0aUbftCTm1nYX1K8.jpg",
                "/7j7eBhReCRafAYdCr5XaJzNAIDz.jpg", "/bS043RNCoBf9UoPjv4EMzKbyAnZ.jpg"],
        logo=("commons", "File:Wizarding World logo.svg")),
    "mcu": dict(
        panels=["/cKvDv2LpwVEqbdXWoQl4XgGN6le.jpg", "/uLtVbjvS1O7gXL8lUOwsFOH4man.jpg",
                "/b6ZJZHUdMEFECvGiDpJjlfUWela.jpg", "/qUv51IFUvVRAP2379ThmA3eLJx6.jpg",
                "/9wXPKruA6bWYk2co5ix6fH59Qr8.jpg"],
        logo=("tmdb", "/hUzeosd33nzE5MCNsZxCGEKTXaQ.png")),
    "batman": dict(
        panels=["/rhc7OF7tC9HPu0X8DBKQJzaGRbu.jpg", "/jz1eErpJSx7ToDVDgV9HKFv4hAa.jpg",
                "/rvtdN5XkWAfGX6xDuPL6yYS2seK.jpg", "/hw1CwteUFGjcWXwjGhKk8UJpWeA.jpg"],
        name="BATMAN & GOTHAM"),
}


def commons_png(title, width=1400):
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url",
                                "iiurlwidth": width, "format": "json"})
    d = json.loads(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + q,
                                                                 headers=UA), timeout=30).read())
    info = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
    url = info.get("thumburl") or info["url"]
    return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()))


def get_logo(spec):
    kind, ref = spec
    im = commons_png(ref) if kind == "commons" else art.fetch(ref)
    im = im.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im


def typeset(name, size=(W, H)):
    """The folder name as a logo: heavy caps, wide tracking, white."""
    f = art.font("ExtraBold", 96)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    sp = 14
    w = sum(probe.textlength(ch, font=f) + sp for ch in name) - sp
    im = Image.new("RGBA", (round(w) + 20, 130), (0, 0, 0, 0))
    art.spaced(ImageDraw.Draw(im), (10, 6), name, f, (255, 255, 255, 255), sp)
    return im.crop(im.getchannel("A").getbbox())


def panels_image(imgs, skew=110, gap=7):
    n = len(imgs)
    base = Image.new("RGB", (W, H), (8, 8, 10))
    step = W / n
    for i, im in enumerate(imgs):
        x0, x1 = i * step, (i + 1) * step
        tile = art.graded(im, 0.9, 1.06, (round(step + skew + 40), H))
        left = x0 - skew / 2 - 20
        poly = [(x0 + skew / 2 + (gap / 2 if i else -skew), 0), (x1 + skew / 2 - (gap / 2 if i < n - 1 else -skew), 0),
                (x1 - skew / 2 - (gap / 2 if i < n - 1 else -skew), H), (x0 - skew / 2 + (gap / 2 if i else -skew), H)]
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(poly, fill=255)
        layer = Image.new("RGB", (W, H))
        layer.paste(tile, (round(left), 0))
        base = Image.composite(layer, base, m)
    return base


def build(uid, out_dir):
    s = SPECS[uid]
    imgs = [art.fetch(p) for p in s["panels"]]
    lg = get_logo(s["logo"]) if s.get("logo") else typeset(s["name"])
    d = os.path.join(out_dir, uid)
    os.makedirs(d, exist_ok=True)
    # cover
    cov = art.soft_fade(panels_image(imgs), start=0.45, top=200)
    cov = art.put_logo(cov, lg, maxw=620, maxh=170, bottom=54)
    cov.save(os.path.join(d, "cover.jpg"), quality=90)
    # hero backdrop: the first panel image, full frame, with the logo
    art.graded(imgs[0], 0.95, 1.03, (1920, 1080)).save(os.path.join(d, "backdrop.jpg"), quality=88)
    # hover: each image in turn, push-in, crossfade, logo held
    frames, per, fade = [], 14, 5
    full = [art.soft_fade(art.graded(im, 0.92, 1.05), 0.45, 200) for im in imgs]
    for i, im in enumerate(full):
        nxt = full[(i + 1) % len(full)]
        for k in range(per):
            z = 0.02 + 0.06 * k / per
            fr = art.zoomed(im, z)
            if k >= per - fade:
                a = (k - (per - fade) + 1) / (fade + 1)
                fr = Image.blend(fr, art.zoomed(nxt, 0.02), a)
            frames.append(art.put_logo(fr, lg, maxw=620, maxh=170, bottom=54).resize((640, 360), Image.LANCZOS))
    pal = Image.new("RGB", (640, 360 * 3))
    for j, idx in enumerate((0, len(frames) // 3, 2 * len(frames) // 3)):
        pal.paste(frames[idx], (0, 360 * j))
    pal = pal.convert("P", palette=Image.ADAPTIVE, colors=200)
    q = [f.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG) for f in frames]
    q[0].save(os.path.join(d, "hover.gif"), save_all=True, append_images=q[1:], duration=110, loop=0, optimize=True)
    return d


if __name__ == "__main__":
    out = sys.argv[1]
    for uid in (sys.argv[2:] or SPECS):
        print("built", build(uid, out))
