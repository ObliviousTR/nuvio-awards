"""Film Collections row: Kaptain's cards (a table strewn with collection posters, the genre on a coloured band) deal
three of the genre's best-known film series onto the table on hover:
  the pile blurs and darkens, the band glides up to the top, three textless series posters are dealt one after
  another (fanned, each with its shadow), the card edge breathes in the band colour, then the posters are swept away,
  the band slides back and the pile comes back into focus (seamless loop).
Series that have their own card in Universes & Franchises are left out here. Picks are fixed (no monthly change).
usage: python3 art_tools/collection_art.py OUT_DIR [titles...]
"""
import io, math, os, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import spotlight_art as art
from spotlight import tmdb
from keyframe_webp import encode
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

W, H = 720, 1080          # work (2:3, as the app shows the card)
OW, OH = 340, 510         # out (under 512 px for Nuvio Desktop)
N, MS = 100, 50           # 5 s
KAPTAIN = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/mirror/files/"

# title: Kaptain's cover, three TMDB collections (or ("movie", id) for a film list)
CARDS = {
    "Action Collections": ("76/76e45137f3eec020.jpg", [1570, 31562, 391860]),          # Die Hard, Bourne, Kingsman
    "Sci-Fi Collections": ("af/af10ed20fe336309.jpg", [264, 422837, 87096]),            # Back to the Future, Blade Runner, Avatar
    "Fantasy Collections": ("f0/f0339cb440448d4c.jpg", [295, 420, 2980]),               # Pirates, Narnia, Ghostbusters
    "Comedy Collections": ("e2/e242a7e48e594b22.jpg", [1006, 86119, 93791]),            # Austin Powers, The Hangover, Anchorman
    "Family & Animation Collections": ("dc/dc24d05e2a6c8dda.jpg", [10194, 2150, 86066]),  # Toy Story, Shrek, Despicable Me
    "Drama Collections": ("18/18683f8dfa1d29cd.jpg", [230, 1575, ("movie", 76)]),       # The Godfather, Rocky, Before Sunrise
    "Crime Collections": ("19/1984f21190e0cbea.jpg", [304, 945, 85861]),                # Ocean's, Lethal Weapon, Beverly Hills Cop
    "Horror Collections": ("75/754524a1a3546541.jpg", [91361, 2602, 8581]),             # Halloween, Scream, Nightmare on Elm Street
    "Mystery Collections": ("c6/c681599d8926e49a.jpg", [722971, 102322, 115776]),       # Knives Out, Sherlock Holmes, Robert Langdon
    "Thriller Collections": ("51/51744e5ed43d77dc.jpg", [9743, 496796, 43064]),         # Hannibal Lecter, Sicario, Speed
    "War Collections": ("4e/4e206b38d228711c.jpg", [5039, 285564, 14246]),              # Rambo, Jarhead, Sniper
}


def get(url):
    for _ in range(3):
        try:
            return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}),
                                                                timeout=60).read())).convert("RGB")
        except Exception:
            continue
    raise RuntimeError("could not fetch " + url)


def textless_poster(ref):
    """A series' textless poster: the collection's own, else its first film's; English only as a last resort."""
    rank = lambda p: (-p.get("vote_count", 0), -p.get("vote_average", 0))
    films = []
    if isinstance(ref, tuple):
        films = [ref[1]]
    else:
        im = tmdb(f"/collection/{ref}/images", include_image_language="null") or {}
        ps = sorted([p for p in im.get("posters", []) if not p.get("iso_639_1")], key=rank)
        if ps:
            return ps[0]["file_path"]
        info = tmdb(f"/collection/{ref}") or {}
        films = [p["id"] for p in sorted(info.get("parts", []), key=lambda p: p.get("release_date") or "9999")]
    for fid in films[:3]:
        im = tmdb(f"/movie/{fid}/images", include_image_language="null") or {}
        ps = sorted([p for p in im.get("posters", []) if not p.get("iso_639_1")], key=rank)
        if ps:
            return ps[0]["file_path"]
    fid = films[0] if films else None
    im = tmdb(f"/movie/{fid}/images", include_image_language="en") or {} if fid else {}
    ps = sorted(im.get("posters", []), key=rank)
    return ps[0]["file_path"] if ps else None


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def out_back(x, k=1.3):
    x = min(1.0, max(0.0, x)) - 1
    return 1 + x * x * ((k + 1) * x + k)


def band_rows(a):
    """Rows of Kaptain's band: the flat, single-colour stretch around the card's middle."""
    s = a[:, : a.shape[1] // 8].std(1).mean(1)
    mid = a.shape[0] // 2
    ys = [y for y in range(int(a.shape[0] * 0.25), int(a.shape[0] * 0.7)) if s[y] < 4]
    runs, start, yset = [], None, set(ys)
    for y in range(int(a.shape[0] * 0.25), int(a.shape[0] * 0.7) + 1):
        if y in yset:
            start = y if start is None else start
        elif start is not None:
            runs.append((start, y)); start = None
    y0, y1 = max(runs, key=lambda r: r[1] - r[0])
    # the band's lighter rims sit just outside the flat run
    return max(0, y0 - 6), min(a.shape[0], y1 + 10)


def build(title, out_dir):
    kcov, refs = CARDS[title]
    full = get(KAPTAIN + kcov)
    cov = art.cover_fit(full, W, H)                         # the card as the app shows it (centre crop to 2:3)
    a = np.asarray(cov, dtype=np.int32)
    y0, y1 = band_rows(a)
    band = cov.crop((0, y0, W, y1)).convert("RGBA")
    col = tuple(int(v) for v in np.median(a[(y0 + y1) // 2, : W // 10], 0))
    # the pile without the band (rows filled from just above and below), blurred and darkened for the hover
    pile = np.asarray(cov).copy()
    above, below = pile[max(0, y0 - (y1 - y0)):y0], pile[y1:y1 + (y1 - y0)]
    fill = np.concatenate([above[: (y1 - y0) // 2], below[: (y1 - y0) - (y1 - y0) // 2]])
    pile[y0:y1] = fill[: y1 - y0]
    soft = ImageEnhance.Brightness(Image.fromarray(pile).filter(ImageFilter.GaussianBlur(16))).enhance(0.38)
    paths = [textless_poster(r) for r in refs]
    posters = []
    pw, ph = round(W * 0.56), round(W * 0.56 * 1.5)
    for p in paths:
        if not p:
            continue
        im = art.cover_fit(art.fetch(p, "w780").convert("RGB"), pw, ph).convert("RGBA")
        m = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw - 1, ph - 1), 14, fill=255)
        im.putalpha(m)
        frame_ = Image.new("RGBA", (pw + 8, ph + 8), (0, 0, 0, 0))
        ImageDraw.Draw(frame_).rounded_rectangle((0, 0, pw + 7, ph + 7), 17, fill=(245, 245, 245, 255))
        frame_.alpha_composite(im, (4, 4))
        posters.append(frame_)
    # fanned places (left, right, then the centre one on top), each dealt in from below
    places = [(0.27, 0.60, -12), (0.73, 0.60, 12), (0.50, 0.575, 0)][: len(posters)]
    deal_at = [14, 24, 34]
    top_y = round(H * 0.07)
    frames = []
    for i in range(N):
        blur = ease(i / 6) if i < 88 else 1 - ease((i - 88) / 11)
        bg = Image.blend(cov, soft, blur).convert("RGBA")
        sweep = ease((i - 78) / 9)                            # posters leave
        for k, (poster, (px, py, rot)) in enumerate(zip(posters, places)):
            p = out_back((i - deal_at[k]) / 9)
            if p <= 0 or sweep >= 1:
                continue
            x = px * W + (1 - p) * W * 0.55 + sweep * (k - 1) * W * 0.9
            y = py * H + (1 - p) * H * 0.75 + sweep * H * 0.15
            r = rot + (1 - p) * 28 + sweep * (k - 1) * 25
            im = poster.rotate(r, resample=Image.BICUBIC, expand=True)
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
            sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: v * 150 // 255))
            a_ = min(1.0, p * 1.5) * (1 - sweep)
            if a_ < 1:
                im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v, a_=a_: round(v * a_)))
                sh.putalpha(sh.getchannel("A").point(lambda v, a_=a_: round(v * a_)))
            bg.alpha_composite(sh, (round(x - im.width / 2 + 10), round(y - im.height / 2 + 16)))
            bg.alpha_composite(im, (round(x - im.width / 2), round(y - im.height / 2)))
        up = ease((i - 4) / 12) if i < 80 else 1 - ease((i - 80) / 12)
        by = round(y0 + (top_y - y0) * up)
        bg.alpha_composite(band, (0, by))
        # the card edge breathes in the band colour while the posters are on the table
        br = math.sin(math.pi * min(1.0, max(0.0, (i - 10) / 72))) ** 1.5
        if br > 0.01:
            e = Image.new("L", (W, H), 0)
            ImageDraw.Draw(e).rounded_rectangle((3, 3, W - 4, H - 4), 26, outline=255, width=5)
            gl = Image.new("RGBA", (W, H), col + (0,))
            gl.putalpha(e.filter(ImageFilter.GaussianBlur(10)).point(lambda v, br=br: min(255, round(v * 2.2 * br))))
            bg.alpha_composite(gl)
            ln = Image.new("RGBA", (W, H), col + (0,))
            ln.putalpha(e.point(lambda v, br=br: round(v * br)))
            bg.alpha_composite(ln)
        frames.append(bg.convert("RGB").resize((OW, OH), Image.LANCZOS))
    os.makedirs(out_dir, exist_ok=True)
    encode(frames, [MS] * N, os.path.join(out_dir, "hover.webp"), quality=80)
    strip = Image.new("RGB", (OW * 6, OH))
    for j, fi in enumerate((0, 10, 20, 40, 70, 90)):
        strip.paste(frames[fi], (j * OW, 0))
    strip.save(os.path.join(out_dir, "frames.jpg"), quality=82)
    return [p for p in paths]


def slug(t):
    import re
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


if __name__ == "__main__":
    out = sys.argv[1]
    for t in sys.argv[2:] or CARDS:
        try:
            print("built", t, build(t, os.path.join(out, slug(t))))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", t, e)
