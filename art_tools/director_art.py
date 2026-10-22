"""Legendary Directors row: the viewfinder. On hover black bars close in from top and bottom and turn the card into a
2.39:1 cinema screen; on it three of the director's signature films play (fanart.tv's textless key art, slow push-in,
soft dissolves) under a camera viewfinder in the card's accent colour (corner marks, blinking REC, running timecode);
the subtitle under the name turns into "TITLE · YEAR"; then the bars open on the portrait again (endless, 7.5 s).
The lettering is lifted off the cover and stays put, as on the Iconic Actors row.
usage: python3 art_tools/director_art.py OUT_DIR [names...]        reels (needs TMDB_API_KEY, FANART_API_KEY)
       python3 art_tools/director_art.py --covers OUT_DIR CUTDIR  our cards re-lettered with the soft fade (local)
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import actor_art as A
from reletter import f as font, tracked, width
from PIL import Image, ImageDraw, ImageFilter

W, H = A.W, A.H
OW, OH = A.OW, A.OH

# director -> three signature films (title, year[, which fanart background]); the first is the one the card opens on
FILMS = {
    "Alfred Hitchcock": [("Psycho", 1960, 2), ("Vertigo", 1958), ("Rear Window", 1954)],
    "Stanley Kubrick": [("2001: A Space Odyssey", 1968), ("The Shining", 1980), ("A Clockwork Orange", 1971)],
    "Akira Kurosawa": [("Seven Samurai", 1954), ("Ran", 1985), ("Rashomon", 1950)],
    "Francis Ford Coppola": [("The Godfather", 1972), ("Apocalypse Now", 1979), ("The Conversation", 1974)],
    "Steven Spielberg": [("Jaws", 1975), ("Jurassic Park", 1993), ("Raiders of the Lost Ark", 1981)],
    "Martin Scorsese": [("Taxi Driver", 1976), ("Goodfellas", 1990), ("The Wolf of Wall Street", 2013)],
    "Sergio Leone": [("The Good, the Bad and the Ugly", 1966), ("Once Upon a Time in the West", 1968),
                     ("Once Upon a Time in America", 1984)],
    "Billy Wilder": [("Sunset Boulevard", 1950), ("Some Like It Hot", 1959), ("The Apartment", 1960)],
    "David Lynch": [("Mulholland Drive", 2001), ("Blue Velvet", 1986), ("Eraserhead", 1977)],
    "Hayao Miyazaki": [("Spirited Away", 2001), ("My Neighbor Totoro", 1988), ("Princess Mononoke", 1997)],
    "Ridley Scott": [("Blade Runner", 1982), ("Alien", 1979), ("Gladiator", 2000)],
    "James Cameron": [("Terminator 2: Judgment Day", 1991), ("Titanic", 1997), ("Avatar", 2009)],
    "Clint Eastwood": [("Unforgiven", 1992, 1), ("Million Dollar Baby", 2004), ("Gran Torino", 2008)],
    "Peter Jackson": [("The Lord of the Rings: The Fellowship of the Ring", 2001),
                      ("The Lord of the Rings: The Return of the King", 2003), ("King Kong", 2005)],
    "Tim Burton": [("Edward Scissorhands", 1990), ("Beetlejuice", 1988), ("Batman", 1989)],
    "Michael Mann": [("Heat", 1995), ("Collateral", 2004), ("The Insider", 1999)],
    "George Miller": [("Mad Max: Fury Road", 2015), ("Mad Max 2", 1981), ("Furiosa: A Mad Max Saga", 2024)],
    "Christopher Nolan": [("The Dark Knight", 2008), ("Inception", 2010), ("Interstellar", 2014)],
    "Quentin Tarantino": [("Pulp Fiction", 1994), ("Kill Bill: Vol. 1", 2003), ("Inglourious Basterds", 2009)],
    "David Fincher": [("Se7en", 1995), ("Fight Club", 1999), ("The Social Network", 2010)],
    "Denis Villeneuve": [("Dune", 2021), ("Blade Runner 2049", 2017), ("Arrival", 2016)],
    "Paul Thomas Anderson": [("There Will Be Blood", 2007), ("Boogie Nights", 1997), ("Magnolia", 1999)],
    "Joel & Ethan Coen": [("Fargo", 1996), ("No Country for Old Men", 2007), ("The Big Lebowski", 1998)],
    "Wes Anderson": [("The Grand Budapest Hotel", 2014), ("Moonrise Kingdom", 2012), ("The Royal Tenenbaums", 2001)],
    "Guillermo del Toro": [("Pan's Labyrinth", 2006), ("The Shape of Water", 2017), ("Crimson Peak", 2015)],
    "Bong Joon-ho": [("Parasite", 2019), ("Memories of Murder", 2003), ("Snowpiercer", 2013)],
    "Park Chan-wook": [("Oldboy", 2003), ("The Handmaiden", 2016), ("Decision to Leave", 2022)],
    "Alfonso Cuarón": [("Gravity", 2013), ("Children of Men", 2006), ("Roma", 2018)],
    "Alejandro González Iñárritu": [("The Revenant", 2015), ("Birdman", 2014), ("Babel", 2006)],
    "Darren Aronofsky": [("Black Swan", 2010), ("Requiem for a Dream", 2000), ("The Whale", 2022)],
    "Kathryn Bigelow": [("The Hurt Locker", 2008), ("Zero Dark Thirty", 2012), ("Point Break", 1991)],
    "Edgar Wright": [("Baby Driver", 2017), ("Shaun of the Dead", 2004), ("Scott Pilgrim vs. the World", 2010)],
    "Guy Ritchie": [("Snatch", 2000), ("Lock, Stock and Two Smoking Barrels", 1998), ("The Gentlemen", 2020)],
    "Sofia Coppola": [("Lost in Translation", 2003), ("Marie Antoinette", 2006), ("The Virgin Suicides", 1999)],
    "Yorgos Lanthimos": [("Poor Things", 2023), ("The Favourite", 2018), ("The Lobster", 2015)],
    "Alex Garland": [("Ex Machina", 2015), ("Annihilation", 2018), ("Civil War", 2024)],
    "Jordan Peele": [("Get Out", 2017, 1), ("Us", 2019), ("Nope", 2022)],
    "Robert Eggers": [("The Lighthouse", 2019), ("The Witch", 2015), ("Nosferatu", 2024)],
    "Ari Aster": [("Midsommar", 2019), ("Hereditary", 2018), ("Beau Is Afraid", 2023)],
    "Greta Gerwig": [("Barbie", 2023), ("Lady Bird", 2017), ("Little Women", 2019)],
}


def films_of(name):
    out = []
    for it in FILMS[name]:
        title, year = it[:2]
        tid, _ = A.g.find_movie(title, year)
        if not tid:
            continue
        fa = A.g.fanart_backgrounds(tid)
        p = fa[min(it[2] if len(it) > 2 else 0, len(fa) - 1)] if fa else A.g.textless_backdrop("movie", tid)
        if p:
            out.append((title, year, p))
    return out


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def build(name, cover_url, hover_url, out, idx=0):
    cover = A.g.art.cover_fit(A.get(cover_url), W, H)
    accent = None
    if hover_url:
        try:
            accent = A.accent_of(A.get(hover_url))
        except Exception:
            accent = None
    accent = accent or A.PALETTE[idx % len(A.PALETTE)]
    films = films_of(name)
    if len(films) < 2:
        raise RuntimeError("films missing")
    nl = A.name_layers(cover)
    if nl is None:
        raise RuntimeError("no lettering found")
    name_lay, sub_orig, (sx0, sy0, sy1), tmask = nl
    cap = max(8, sy1 - sy0)
    fsz = max(10, round(cap / 0.72))
    sfont = font("SemiBold", fsz)
    sp = round(fsz * 0.34)
    asc = sfont.getbbox("A")[1]

    def label(t, y):
        t = t.upper()
        for cut in (None, ":", ",", " ("):
            tt = t.split(cut)[0].strip() if cut else t
            if width(f"{tt} · {y}", sfont, sp) <= W - sx0 - W * 0.06:
                return f"{tt} · {y}"
        words = tt.split()
        while len(words) > 1 and width(f"{' '.join(words)} · {y}", sfont, sp) > W - sx0 - W * 0.06:
            words = words[:-1]
        return f"{' '.join(words)} · {y}"

    sub_lays = [sub_orig]
    for t, y, _ in films:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(lay), (sx0, sy0 - asc), label(t, y), sfont, (205, 205, 205, 255), sp)
        sub_lays.append(lay)

    # the screen: 2.39:1, full width, above the name
    bh = round(W / 2.39)
    cy = round(H * 0.47)
    b0, b1 = cy - bh // 2, cy - bh // 2 + bh
    shots = []
    for _, _, p in films:
        im = A.g.load_img(p)
        k = max(W * 1.12 / im.width, bh * 1.12 / im.height)
        shots.append(im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS))

    def shot(j, u):  # slow push-in, centred
        im = shots[j]
        z = 1.0 + 0.1 * u
        cw, ch = W * 1.12 / z, bh * 1.12 / z
        cw, ch = min(cw, im.width), min(ch, im.height)
        x, y = (im.width - cw) / 2, (im.height - ch) / 2
        return im.resize((W, bh), Image.LANCZOS, box=(x, y, x + cw, y + ch))

    # viewfinder layer (static part) and the bits that change
    vf = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(vf)
    m, L, t = round(W * 0.045), round(W * 0.07), max(3, round(W * 0.006))
    col = accent + (235,)
    for (x, y, sx, sy) in ((m, b0 + m * 0.6, 1, 1), (W - m, b0 + m * 0.6, -1, 1), (m, b1 - m * 0.6, 1, -1), (W - m, b1 - m * 0.6, -1, -1)):
        x, y = round(x), round(y)
        d.rectangle([min(x, x + sx * L), min(y, y + sy * t), max(x, x + sx * L), max(y, y + sy * t)], fill=col)
        d.rectangle([min(x, x + sx * t), min(y, y + sy * L), max(x, x + sx * t), max(y, y + sy * L)], fill=col)
    c = (W // 2, cy)  # centre cross
    d.rectangle((c[0] - L // 3, c[1] - 1, c[0] + L // 3, c[1] + 1), fill=accent + (150,))
    d.rectangle((c[0] - 1, c[1] - L // 3, c[0] + 1, c[1] + L // 3), fill=accent + (150,))
    hud = font("SemiBold", round(W * 0.03))
    hy = b0 - round(W * 0.06)
    tracked(d, (m + round(W * 0.04), hy), "REC", hud, (235, 235, 235, 230), round(W * 0.006))
    tracked(d, (W // 2 - round(W * 0.06), hy), "2.39 : 1", hud, accent + (220,), round(W * 0.004))
    rec_r = round(W * 0.012)
    rec_xy = (m + rec_r, hy + hud.getbbox("R")[1] + (hud.getbbox("R")[3] - hud.getbbox("R")[1]) // 2)

    N_ = 150
    CLOSE0, CLOSE1, OPEN0, OPEN1 = 6, 20, 128, 144
    seg = (OPEN0 - CLOSE1 + 10) / len(films)   # each film's share of the screen time
    XF = 9                                      # dissolve length
    frames = []
    for i in range(N_):
        cl = ease((i - CLOSE0) / (CLOSE1 - CLOSE0)) if i < OPEN0 else 1 - ease((i - OPEN0) / (OPEN1 - OPEN0))
        cv = cover.copy()
        if cl > 0:
            # what's on screen: the films, dissolving into each other; the portrait under it while the bars move
            tt = i - (CLOSE1 - 10)
            j = min(len(films) - 1, max(0, int(tt // seg)))
            u = (tt - j * seg) / seg
            pic = shot(j, min(1, max(0, (tt - j * seg + 10) / (seg + 20))))
            if j + 1 < len(films) and tt > (j + 1) * seg - XF:
                a = ease((tt - ((j + 1) * seg - XF)) / XF)
                pic = Image.blend(pic, shot(j + 1, min(1, max(0, (tt - (j + 1) * seg + 10) / (seg + 20)))), a)
            fade_in = ease((i - (CLOSE1 - 10)) / 12) if i < OPEN0 else 1 - ease((i - OPEN0) / (OPEN1 - OPEN0 - 4))
            band = Image.blend(cover.crop((0, b0, W, b1)), pic, fade_in)
            black = Image.new("RGB", (W, H), (0, 0, 0))
            cv = Image.blend(cover, black, 0.85 * cl)  # the portrait sinks into the dark as the bars come in
            top = round(b0 * cl)
            bot = round(H - (H - b1) * cl)
            cv.paste(band, (0, b0))
            dd = ImageDraw.Draw(cv)
            dd.rectangle((0, 0, W, top), fill=(0, 0, 0))
            dd.rectangle((0, bot, W, H), fill=(0, 0, 0))
        cv = cv.convert("RGBA")
        hv = ease((i - CLOSE1 + 2) / 8) if i < OPEN0 else 1 - ease((i - OPEN0 + 6) / 8)
        if hv > 0:
            layer = vf.copy()
            ld = ImageDraw.Draw(layer)
            if (i // 10) % 2 == 0:
                ld.ellipse((rec_xy[0] - rec_r, rec_xy[1] - rec_r, rec_xy[0] + rec_r, rec_xy[1] + rec_r), fill=(230, 40, 40, 240))
            fr = i * 24 // 20 + 7 * 24
            tc = f"{fr // (24 * 3600):02d}:{fr // (24 * 60) % 60:02d}:{fr // 24 % 60:02d}:{fr % 24:02d}"
            tw = width(tc, hud, round(W * 0.004))
            tracked(ld, (W - m - round(tw), hy), tc, hud, (235, 235, 235, 230), round(W * 0.004))
            cv.alpha_composite(A.alpha_mul(layer, hv))
        cv.alpha_composite(name_lay)
        # subtitle: the film on screen (with a short fade at each change), the original one outside the hover
        if cl < 0.5 or i < CLOSE1 - 4 or i >= OPEN0 + 2:
            k, a_sub = 0, 1.0 if (i < CLOSE1 - 10 or i > OPEN1 - 4) else max(abs(1 - 2 * cl), 0.0)
        else:
            tt = i - (CLOSE1 - 10)
            j = min(len(films) - 1, max(0, int((tt + XF / 2) // seg)))
            pos = (tt + XF / 2) - j * seg
            k = 1 + j
            a_sub = min(1.0, pos / 5, (seg - pos) / 5 if j + 1 < len(films) else 1.0)
            if i > OPEN0 - 6:
                a_sub = min(a_sub, (OPEN0 + 2 - i) / 8)
        cv.alpha_composite(A.alpha_mul(sub_lays[k], max(0.0, a_sub)))
        frames.append(cv.convert("RGB").resize((OW, OH), Image.LANCZOS))
    dd_ = os.path.join(out, A.g.slug_of(name))
    os.makedirs(dd_, exist_ok=True)
    frames[0].save(os.path.join(dd_, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * N_,
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    strip = Image.new("RGB", (OW * 6, OH))
    for jj, k in enumerate((0, 14, 40, 75, 110, 136)):
        strip.paste(frames[k], (jj * OW, 0))
    strip.save(os.path.join(dd_, "frames.jpg"), quality=80)
    return [f"{t} ({y})" for t, y, _ in films]


def covers():
    d = json.load(open(os.path.join(ROOT, "builder", "out", "delivered", "baseline.json"), encoding="utf-8"))
    out = {}
    for row in d:
        if row["title"] == "Legendary Directors":
            for i, f in enumerate(row["folders"]):
                out[f["title"]] = (f.get("coverImageUrl"), f.get("focusGifUrl") or None, i)
    ref = os.environ.get("ART_REF")
    if ref:
        for k, (c, h, i) in out.items():
            if c and "/art/folders/" in c:
                out[k] = (c.split("?")[0].replace("/nuvio-art/main/", f"/nuvio-art/{ref}/"), h, i)
    return out


# ---------------------------------------------------------------- our cards, re-lettered with the soft fade
RELETTER = {  # folder -> (name lines, subtitle); Kaptain's own picture, his lettering painted out
    "Billy Wilder": (["BILLY", "WILDER"], "DIRECTOR"),
    "George Miller": (["GEORGE", "MILLER"], "DIRECTOR"),
    "Alejandro González Iñárritu": (["ALEJANDRO", "GONZÁLEZ IÑÁRRITU"], "DIRECTOR"),
    "Joel & Ethan Coen": (["JOEL & ETHAN", "COEN"], "DIRECTORS"),
    "Clint Eastwood": (["CLINT", "EASTWOOD"], "DIRECTOR"),
}


def our_covers(out, cutdir):
    from reletter import letter
    import folder_art as fa
    art = os.environ.get("NUVIO_ART", "/home/claude/nuvio-art")
    mp = json.load(open(os.path.join(art, "mirror", "map.json")))
    orig = json.load(open(os.path.join(ROOT, "builder", "orig.json"), encoding="utf-8"))
    alias = {"Joel Coen": "Joel & Ethan Coen"}
    src = {alias.get(f["title"], f["title"]): f.get("coverImageUrl") for r in orig for f in r.get("folders", [])}
    for t, (lines, sub) in RELETTER.items():
        im = Image.open(os.path.join(art, mp[src[t]])).convert("RGB").resize((1000, 1500), Image.LANCZOS)
        a = np.asarray(im, dtype=np.float32)
        # paint out Kaptain's lettering: the grey caps (+ their shadow) in the bottom band, found by their box
        from scipy import ndimage as ndi
        import cv2
        g_ = a.mean(2)
        y0, y1 = int(1500 * 0.8), int(1500 * 0.97)
        bright = np.zeros_like(g_, dtype=bool)
        bright[y0:y1] = g_[y0:y1] > 85
        rows = np.nonzero(bright.sum(1) > 25)[0]
        m = np.zeros_like(bright)
        if len(rows):
            r0, r1 = rows.min(), rows.max()
            cols = np.nonzero(bright[r0:r1 + 1].sum(0) > 0)[0]
            c0, c1 = cols.min(), cols.max()
            box = np.zeros_like(bright)
            box[max(0, r0 - 14):r1 + 22, max(0, c0 - 14):c1 + 22] = True
            m = ndi.binary_dilation(bright & box, iterations=9) & ndi.binary_dilation(box, iterations=9)
            m |= ndi.binary_dilation((g_ > 55) & box, iterations=4)
        clean = cv2.inpaint(a.astype(np.uint8), (m * 255).astype(np.uint8), 15, cv2.INPAINT_TELEA)
        im = Image.fromarray(clean)
        d = os.path.join(out, fa.slug(t))
        os.makedirs(d, exist_ok=True)
        letter(im, lines, sub, tint=(6, 6, 7), soft=(0.5, 0.88)).save(os.path.join(d, "cover.jpg"), quality=90)
        print("re-lettered", t)
    cut = Image.open(os.path.join(cutdir, "sofia-coppola.png")).convert("RGBA")
    d = os.path.join(out, "sofia-coppola")
    os.makedirs(d, exist_ok=True)
    fa.compose(cut, ["SOFIA", "COPPOLA"], "DIRECTOR").save(os.path.join(d, "cover.jpg"), quality=90)
    print("portrait Sofia Coppola")


if __name__ == "__main__":
    if sys.argv[1] == "--covers":
        our_covers(sys.argv[2], sys.argv[3])
        sys.exit(0)
    outdir = sys.argv[1]
    cv = covers()
    names = sys.argv[2:] or list(cv)
    bad = False
    for n in names:
        try:
            c, h, i = cv[n]
            print("built", n, "·", ", ".join(build(n, c, h, outdir, i)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", n, e)
            bad = True
    sys.exit(1 if bad else 0)
