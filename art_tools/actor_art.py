"""Iconic Actors row: hovering a portrait lights the card up, the portrait fades away and a strip of 35 mm film runs
upwards through the card showing three of the actor's defining roles (frames where the actor is on screen: TMDB
images tagged with the person, else the film's textless key art); under the name, the title and year of the role in
the middle of the strip; then the portrait comes back (seamless loop, 6 s). Roles are fixed (no monthly change).
usage: python3 art_tools/actor_art.py OUT_DIR [names...]   (reads builder/out/delivered/baseline.json for the covers)
"""
import io, json, math, os, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import genre_art as g
from spotlight import tmdb
from reletter import letter, f as font, tracked, width
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageStat

W, H = 720, 1080
OW, OH = 340, 510
N = 120

# roles that the automatic pick would miss or get wrong: name -> [(title, year), ...]
ROLES = {
    "Al Pacino": [("The Godfather", 1972), ("Scarface", 1983), ("Heat", 1995)],
    "Robert De Niro": [("Taxi Driver", 1976), ("Raging Bull", 1980), ("Goodfellas", 1990)],
    "Jack Nicholson": [("The Shining", 1980), ("One Flew Over the Cuckoo's Nest", 1975), ("The Departed", 2006)],
    "Anthony Hopkins": [("The Silence of the Lambs", 1991), ("The Father", 2020), ("Legends of the Fall", 1994)],
    "Meryl Streep": [("The Devil Wears Prada", 2006), ("Mamma Mia!", 2008), ("Kramer vs. Kramer", 1979)],
    "Tom Hanks": [("Forrest Gump", 1994), ("Cast Away", 2000), ("Saving Private Ryan", 1998)],
    "Harrison Ford": [("Raiders of the Lost Ark", 1981), ("Blade Runner", 1982), ("The Fugitive", 1993)],
    "Denzel Washington": [("Training Day", 2001), ("Man on Fire", 2004), ("Glory", 1989)],
    "Daniel Day-Lewis": [("There Will Be Blood", 2007), ("Gangs of New York", 2002), ("Lincoln", 2012)],
    "Morgan Freeman": [("The Shawshank Redemption", 1994), ("Se7en", 1995), ("Million Dollar Baby", 2004)],
    "Robin Williams": [("Good Will Hunting", 1997), ("Dead Poets Society", 1989), ("Mrs. Doubtfire", 1993)],
    "Gary Oldman": [("Léon: The Professional", 1994), ("Darkest Hour", 2017), ("Tinker Tailor Soldier Spy", 2011)],
    "Samuel L. Jackson": [("Pulp Fiction", 1994), ("Django Unchained", 2012), ("Jackie Brown", 1997)],
    "Jim Carrey": [("The Truman Show", 1998), ("The Mask", 1994), ("Eternal Sunshine of the Spotless Mind", 2004)],
    "Jackie Chan": [("Police Story", 1985), ("Rush Hour", 1998), ("Drunken Master II", 1994)],
    "Frances McDormand": [("Fargo", 1996), ("Nomadland", 2020), ("Three Billboards Outside Ebbing, Missouri", 2017)],
    "Leonardo DiCaprio": [("The Wolf of Wall Street", 2013), ("The Revenant", 2015), ("Catch Me If You Can", 2002)],
    "Brad Pitt": [("Fight Club", 1999), ("Once Upon a Time... in Hollywood", 2019), ("Moneyball", 2011)],
    "Christian Bale": [("American Psycho", 2000), ("The Dark Knight", 2008), ("The Prestige", 2006)],
    "Tom Cruise": [("Top Gun: Maverick", 2022), ("Collateral", 2004), ("Edge of Tomorrow", 2014)],
    "Keanu Reeves": [("The Matrix", 1999), ("John Wick", 2014), ("Speed", 1994)],
    "Joaquin Phoenix": [("Joker", 2019), ("Her", 2013), ("Walk the Line", 2005)],
    "Matt Damon": [("The Martian", 2015), ("Good Will Hunting", 1997), ("The Bourne Identity", 2002)],
    "Robert Downey Jr.": [("Iron Man", 2008), ("Oppenheimer", 2023), ("Sherlock Holmes", 2009)],
    "Cate Blanchett": [("Tár", 2022), ("Blue Jasmine", 2013), ("Elizabeth", 1998)],
    "Nicole Kidman": [("The Others", 2001), ("Moulin Rouge!", 2001), ("Eyes Wide Shut", 1999)],
    "Kate Winslet": [("Titanic", 1997), ("Eternal Sunshine of the Spotless Mind", 2004), ("The Reader", 2008)],
    "Matthew McConaughey": [("Interstellar", 2014), ("Dallas Buyers Club", 2013), ("The Wolf of Wall Street", 2013)],
    "Hugh Jackman": [("Logan", 2017), ("The Prestige", 2006), ("Prisoners", 2013)],
    "Charlize Theron": [("Mad Max: Fury Road", 2015), ("Monster", 2003), ("Atomic Blonde", 2017)],
    "Natalie Portman": [("Black Swan", 2010), ("Léon: The Professional", 1994), ("V for Vendetta", 2006)],
    "Scarlett Johansson": [("Lost in Translation", 2003), ("Marriage Story", 2019), ("Lucy", 2014)],
    "Tom Hardy": [("Mad Max: Fury Road", 2015), ("Legend", 2015), ("Warrior", 2011)],
    "Ryan Gosling": [("Drive", 2011), ("Blade Runner 2049", 2017), ("La La Land", 2016)],
    "Jake Gyllenhaal": [("Nightcrawler", 2014), ("Donnie Darko", 2001), ("Prisoners", 2013)],
    "Cillian Murphy": [("Oppenheimer", 2023), ("28 Days Later", 2002), ("Batman Begins", 2005)],
    "Edward Norton": [("Fight Club", 1999), ("American History X", 1998), ("Primal Fear", 1996)],
    "Philip Seymour Hoffman": [("Capote", 2005), ("The Master", 2012), ("Magnolia", 1999)],
    "Viola Davis": [("Fences", 2016), ("The Woman King", 2022), ("The Help", 2011)],
    "Amy Adams": [("Arrival", 2016), ("Enchanted", 2007), ("The Fighter", 2010)],
    "Anne Hathaway": [("The Devil Wears Prada", 2006), ("Les Misérables", 2012), ("Interstellar", 2014)],
    "Emma Stone": [("La La Land", 2016), ("Poor Things", 2023), ("Easy A", 2010)],
    "Margot Robbie": [("Barbie", 2023), ("I, Tonya", 2017), ("The Wolf of Wall Street", 2013)],
    "Bryan Cranston": [("Breaking Bad", 2008, "tv"), ("Trumbo", 2015), ("Drive", 2011)],
    "Willem Dafoe": [("The Lighthouse", 2019), ("Platoon", 1986), ("The Florida Project", 2017)],
    "Christoph Waltz": [("Inglourious Basterds", 2009), ("Django Unchained", 2012), ("Spectre", 2015)],
    "Mads Mikkelsen": [("Another Round", 2020), ("The Hunt", 2012), ("Casino Royale", 2006)],
    "Javier Bardem": [("No Country for Old Men", 2007), ("Skyfall", 2012), ("Biutiful", 2010)],
    "Tilda Swinton": [("Michael Clayton", 2007), ("We Need to Talk About Kevin", 2011), ("Snowpiercer", 2013)],
    "Toni Collette": [("Hereditary", 2018), ("Little Miss Sunshine", 2006), ("The Sixth Sense", 1999)],
    "Ethan Hawke": [("Training Day", 2001), ("Before Sunrise", 1995), ("First Reformed", 2017)],
    "Sam Rockwell": [("Moon", 2009), ("Three Billboards Outside Ebbing, Missouri", 2017), ("The Green Mile", 1999)],
    "Steve Carell": [("The Office", 2005, "tv"), ("Foxcatcher", 2014), ("The 40 Year Old Virgin", 2005)],
    "Simon Pegg": [("Shaun of the Dead", 2004), ("Hot Fuzz", 2007), ("The World's End", 2013)],
    "Song Kang-ho": [("Parasite", 2019), ("Memories of Murder", 2003), ("Snowpiercer", 2013)],
    "Oscar Isaac": [("Inside Llewyn Davis", 2013), ("Ex Machina", 2015), ("Dune", 2021)],
    "Pedro Pascal": [("The Last of Us", 2023, "tv"), ("The Mandalorian", 2019, "tv"), ("Gladiator II", 2024)],
    "Robert Pattinson": [("The Batman", 2022), ("Good Time", 2017), ("The Lighthouse", 2019)],
    "Florence Pugh": [("Midsommar", 2019), ("Little Women", 2019), ("Oppenheimer", 2023)],
    "Anya Taylor-Joy": [("The Queen's Gambit", 2020, "tv"), ("The Witch", 2015), ("Furiosa: A Mad Max Saga", 2024)],
    "Timothée Chalamet": [("Dune: Part Two", 2024), ("Call Me by Your Name", 2017), ("A Complete Unknown", 2024)],
    "Zendaya": [("Challengers", 2024), ("Euphoria", 2019, "tv"), ("Dune: Part Two", 2024)],
    "Tom Holland": [("Spider-Man: No Way Home", 2021), ("The Impossible", 2012), ("Cherry", 2021)],
    "Austin Butler": [("Elvis", 2022), ("The Bikeriders", 2024), ("Once Upon a Time... in Hollywood", 2019)],
}
PALETTE = [(232, 80, 70), (90, 170, 255), (240, 190, 70), (120, 210, 120), (200, 120, 240), (250, 140, 60), (70, 200, 200)]


def get(url):
    for _ in range(3):
        try:
            return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}),
                                                                timeout=60).read())).convert("RGB")
        except Exception:
            continue
    raise RuntimeError("fetch " + url)


def person_id(name):
    r = (tmdb("/search/person", query=name) or {}).get("results", [])
    r = sorted(r, key=lambda x: -x.get("popularity", 0))
    return r[0]["id"] if r else None


def find_title(title, year, kind):
    if kind == "movie":
        return g.find_movie(title, year)[0]
    r = (tmdb("/search/tv", query=title) or {}).get("results", [])
    near = [x for x in r if (x.get("first_air_date") or "0000")[:4].isdigit() and abs(int(x["first_air_date"][:4]) - year) <= 1]
    return (near or r or [{}])[0].get("id")


_FACE = {}


def face_models():
    """OpenCV's YuNet face detector and SFace recogniser (opencv_zoo), fetched once."""
    if not _FACE:
        import cv2
        cache = os.path.join(ROOT, "scripts", ".cache")
        os.makedirs(cache, exist_ok=True)
        base = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
        paths = {}
        for k, rel in (("det", "face_detection_yunet/face_detection_yunet_2023mar.onnx"),
                       ("rec", "face_recognition_sface/face_recognition_sface_2021dec.onnx")):
            p = os.path.join(cache, os.path.basename(rel))
            if not os.path.exists(p):
                open(p, "wb").write(urllib.request.urlopen(base + rel, timeout=120).read())
            paths[k] = p
        _FACE["det"] = cv2.FaceDetectorYN.create(paths["det"], "", (320, 320), 0.8)
        _FACE["rec"] = cv2.FaceRecognizerSF.create(paths["rec"], "")
    return _FACE["det"], _FACE["rec"]


def faces(img):
    """[(feature, box)] for the faces in a PIL image."""
    import cv2
    det, rec = face_models()
    a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = a.shape[:2]
    det.setInputSize((w, h))
    _, fs = det.detect(a)
    out = []
    for fc in (fs if fs is not None else []):
        crop = rec.alignCrop(a, fc)
        out.append((rec.feature(crop), fc[:4]))
    return out


def same(f1, f2):
    import cv2
    _, rec = face_models()
    return rec.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE)


def actor_faces(pid):
    profs = (tmdb(f"/person/{pid}/images") or {}).get("profiles", [])[:6]
    feats = []
    for p in profs:
        try:
            fs = faces(g.art.fetch(p["file_path"], "w500"))
        except Exception:
            continue
        if fs:
            feats.append(max(fs, key=lambda x: x[1][2] * x[1][3])[0])
    return feats


def role_image(pid, kind, tid, refs):
    """A frame of the role where the actor's face is on screen: the title's backdrops (textless first) are checked
    against the actor's profile photos with a face recogniser; the best match with the biggest face wins. Returns
    (image path, horizontal centre of the face 0..1) - else the title's textless key art, centred."""
    im = tmdb(f"/{kind}/{tid}/images", include_image_language="null,en") or {}
    bds = sorted(im.get("backdrops", []), key=lambda b: (bool(b.get("iso_639_1")), -b["vote_count"]))[:40]
    tagged = []
    for page in (1, 2, 3):
        r = tmdb(f"/person/{pid}/tagged_images", page=page) or {}
        tagged += [x for x in r.get("results", []) if (x.get("media") or {}).get("id") == tid and x.get("aspect_ratio", 0) > 1.3]
        if page >= r.get("total_pages", 1):
            break
    best = None
    for b in tagged + bds:
        try:
            pic = g.art.fetch(b["file_path"], "w780").convert("RGB")
        except Exception:
            continue
        for feat, box in faces(pic):
            score = max((same(feat, r_) for r_ in refs), default=0)
            if score >= 0.36:
                area = box[2] * box[3] / (pic.width * pic.height)
                key = (score > 0.45) * 1.0 + area * 6 - bool(b.get("iso_639_1")) * 0.3
                if best is None or key > best[0]:
                    best = (key, b["file_path"], (box[0] + box[2] / 2) / pic.width)
        if best and best[0] > 1.25:
            break
    if best:
        return best[1], best[2]
    if kind == "movie":
        fa = g.fanart_backgrounds(tid)
        if fa:
            return fa[0], 0.5
    bd = [b for b in bds if not b.get("iso_639_1")]
    return (bd[0]["file_path"], 0.5) if bd else (None, 0.5)


def roles_of(name):
    pid = person_id(name)
    refs = actor_faces(pid)
    out = []
    for item in ROLES.get(name, []):
        title, year = item[0], item[1]
        kind = item[2] if len(item) > 2 else "movie"
        tid = find_title(title, year, kind)
        p, cx = role_image(pid, kind, tid, refs) if tid else (None, 0.5)
        if p:
            out.append((title, year, p, cx))
    return out


def accent_of(hover):
    """Kaptain's frame colour on his selected card (the saturated pixels along the edge)."""
    a = np.asarray(hover.resize((200, 300)), dtype=np.int32)
    edge = np.concatenate([a[2:6].reshape(-1, 3), a[-6:-2].reshape(-1, 3), a[:, 2:6].reshape(-1, 3), a[:, -6:-2].reshape(-1, 3)])
    sat = edge.max(1) - edge.min(1)
    e = edge[sat > 60]
    return tuple(int(v) for v in np.median(e, 0)) if len(e) > 40 else None


def strip_frame(img, fw, fh, cx=0.5):
    """Crop to the strip frame keeping the actor's face (at cx) inside."""
    k = max(fw / img.width, fh / img.height)
    im = img.resize((max(fw, round(img.width * k)), max(fh, round(img.height * k))), Image.LANCZOS)
    x = min(max(0, round(cx * im.width - fw / 2)), im.width - fw)
    y = (im.height - fh) // 2
    im = im.crop((x, y, x + fw, y + fh))
    return ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.05)).enhance(1.05)


def build(name, cover_url, hover_url, out, idx=0):
    cover = g.art.cover_fit(get(cover_url), W, H)
    accent = None
    if hover_url:
        try:
            accent = accent_of(get(hover_url))
        except Exception:
            accent = None
    accent = accent or PALETTE[idx % len(PALETTE)]
    roles = roles_of(name)
    if not roles:
        raise RuntimeError("no roles")
    parts = name.upper().split(" ")
    lines = [" ".join(parts[:-1]), parts[-1]] if len(parts) > 1 else parts
    # the dark card under the strip; the name block is set in Kaptain's style (reletter), one per subtitle
    base = Image.new("RGB", (W, H), (12, 11, 12))
    gl = Image.new("L", (W, H), 0)
    ImageDraw.Draw(gl).ellipse((-W * 0.2, -H * 0.1, W * 1.2, H * 0.8), fill=255)
    base = Image.composite(Image.new("RGB", (W, H), (40, 38, 40)), base, gl.filter(ImageFilter.GaussianBlur(200)))
    def label(t, y):
        t = t.upper()
        for cut in (None, ",", ":", " ("):
            tt = t.split(cut)[0].strip() if cut else t
            if width(f"{tt} · {y}", font("SemiBold", round(26 * W / 1000)), round(9 * W / 1000)) <= W * 0.8:
                return f"{tt} · {y}"
        return f"{tt[:22].strip()} · {y}"
    subs = ["FEATURED FILMOGRAPHY"] + [label(t, y) for t, y, _, _ in roles]
    blocks = []
    for s_ in subs:
        b = letter(Image.new("RGB", (W, H), (0, 0, 0)), lines, s_, tint=(12, 11, 12))
        blocks.append(b)
    # name block mask: the lettered area at the bottom
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).rectangle((0, int(H * 0.70), W, H), fill=255)
    bm = bm.filter(ImageFilter.GaussianBlur(30))
    # film strip
    sw = round(W * 0.84)
    fw = round(sw * 0.80)
    fh = round(fw * 0.62)
    gap = 30
    pitch = fh + gap
    frames_img = [strip_frame(g.load_img(p), fw, fh, cx) for _, _, p, cx in roles]
    n_r = len(frames_img)
    strip_h = pitch * n_r
    film = Image.new("RGBA", (sw, strip_h * 2), (22, 17, 14, 255))
    d = ImageDraw.Draw(film)
    hole_w, hole_h, hole_gap = round(sw * 0.045), round(sw * 0.03), round(sw * 0.065)
    for y in range(0, strip_h * 2, hole_gap):
        for x in (round(sw * 0.035), sw - round(sw * 0.035) - hole_w):
            d.rounded_rectangle((x, y + 6, x + hole_w, y + 6 + hole_h), 3, fill=(205, 196, 180, 255))
    for k in range(n_r * 2):
        fr = frames_img[k % n_r]
        film.paste(fr, ((sw - fw) // 2, k * pitch + gap // 2))
    view_top, view_bot = 0, int(H * 0.74)
    center_y = (view_top + view_bot) / 2
    sx = (W - sw) // 2
    T_BRIGHT, T_OUT, T_STRIP1, T_BACK = 6, 16, 104, 119
    out_frames = []
    for i in range(N):
        if i < T_BRIGHT:
            cv = ImageEnhance.Brightness(cover).enhance(1 + 0.18 * g.ease(i / T_BRIGHT))
        else:
            # strip position: constant speed upward; each role passes the middle once while it plays
            q = (i - T_BRIGHT) / (T_STRIP1 - T_BRIGHT)
            off = q * strip_h + pitch * 0.5 - center_y + gap / 2 + fh / 2
            off = off % strip_h
            sc = base.copy().convert("RGBA")
            crop = film.crop((0, round(off), sw, round(off) + view_bot))
            sc.alpha_composite(crop, (sx, view_top))
            # light falls off at the top and bottom of the strip window
            fade = Image.new("L", (W, H), 0)
            fd = ImageDraw.Draw(fade)
            for y in range(H):
                dd = abs(y - center_y) / (view_bot / 2)
                fd.line((0, y, W, y), fill=round(255 * min(1.0, max(0.0, (dd - 0.55) / 0.45)) ** 1.2) if y < view_bot else 255)
            sc = Image.composite(Image.new("RGB", (W, H), (12, 11, 12)), sc.convert("RGB"), fade)
            # which role sits in the middle -> its title under the name
            mid = (off + center_y - gap / 2) / pitch
            k = int(mid) % n_r
            frac = mid - int(mid)
            blk = blocks[1 + k]
            if frac < 0.12 or frac > 0.88:                     # crossfade the titles as frames change
                nk = (k + 1) % n_r if frac > 0.88 else (k - 1) % n_r
                w_ = (0.12 - frac) / 0.24 if frac < 0.12 else (frac - 0.88) / 0.24
                blk = Image.blend(blk, blocks[1 + nk], min(0.5, w_))
            if i < T_OUT + 8:                                 # the subtitle starts as FEATURED FILMOGRAPHY
                blk = Image.blend(blocks[0], blk, g.ease((i - T_OUT) / 8))
            if i > T_STRIP1 - 6:
                blk = Image.blend(blk, blocks[0], g.ease((i - (T_STRIP1 - 6)) / 6))
            # the lettered name block (drawn on black) is laid over the scene's dark bottom
            txt = Image.fromarray(np.maximum(np.asarray(sc), np.asarray(blk)))
            sc = Image.composite(txt, sc, bm)
            if i < T_OUT:                                     # the lit portrait fades out
                lit = ImageEnhance.Brightness(cover).enhance(1.18)
                sc = Image.blend(lit, sc, g.ease((i - T_BRIGHT) / (T_OUT - T_BRIGHT)))
            elif i >= T_STRIP1:                               # and comes back
                sc = Image.blend(sc, cover, g.ease((i - T_STRIP1) / (T_BACK - T_STRIP1)))
            cv = sc
        # the card's accent frame breathes while the roles play
        a_ = 0.0
        if T_BRIGHT <= i < T_STRIP1:
            a_ = min(1.0, (i - T_BRIGHT) / 8) * min(1.0, (T_STRIP1 - i) / 8)
        if a_ > 0:
            cv = cv.convert("RGBA")
            e = Image.new("L", (W, H), 0)
            ImageDraw.Draw(e).rounded_rectangle((4, 4, W - 5, H - 5), 22, outline=255, width=5)
            gl_ = Image.new("RGBA", (W, H), accent + (0,))
            gl_.putalpha(e.filter(ImageFilter.GaussianBlur(10)).point(lambda v, a_=a_: min(255, round(v * 1.8 * a_))))
            cv.alpha_composite(gl_)
            ln = Image.new("RGBA", (W, H), accent + (0,))
            ln.putalpha(e.point(lambda v, a_=a_: round(v * a_)))
            cv.alpha_composite(ln)
            cv = cv.convert("RGB")
        out_frames.append(cv.resize((OW, OH), Image.LANCZOS))
    dd = os.path.join(out, g.slug_of(name))
    os.makedirs(dd, exist_ok=True)
    out_frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=out_frames[1:], duration=[50] * N,
                       loop=0, quality=80, method=4, kmin=0, kmax=1)
    strip = Image.new("RGB", (OW * 6, OH))
    for j, k in enumerate((0, 10, 30, 55, 80, 112)):
        strip.paste(out_frames[k], (j * OW, 0))
    strip.save(os.path.join(dd, "frames.jpg"), quality=80)
    return [f"{t} ({y}){'' if cx != 0.5 else ' [no face match]'}" for t, y, _, cx in roles]


def covers():
    d = json.load(open(os.path.join(ROOT, "builder", "out", "delivered", "baseline.json"), encoding="utf-8"))
    out = {}
    for row in d:
        if row["title"] == "Iconic Actors":
            for i, f in enumerate(row["folders"]):
                out[f["title"]] = (f.get("coverImageUrl"), f.get("focusGifUrl") or None, i)
    return out


if __name__ == "__main__":
    outdir = sys.argv[1]
    cv = covers()
    names = sys.argv[2:] or list(cv)
    bad = False
    for n in names:
        if n not in cv:
            print("no card for", n); continue
        try:
            c, h, i = cv[n]
            print("built", n, "·", ", ".join(build(n, c, h, outdir, i)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", n, e)
            bad = True
    sys.exit(1 if bad else 0)
