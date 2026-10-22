"""Iconic Actors row: on hover the portrait starts to slide up like the first picture on a reel of film; behind it a
full-width strip of 35 mm film carries three of the actor's defining roles (frames where the actor is on screen: TMDB
images tagged with the person, else the film's textless key art); under the name, the title and year of the role in
the middle of the card; after the last role the portrait comes up again and settles (endless reel, 7 s). Kaptain's
own lettering is lifted off the cover and stays put; only the subtitle changes. Roles are fixed (no monthly change).
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
                key = (score > 0.45) * 1.0 + area * 6 - bool(b.get("iso_639_1")) * 2.0  # titled art only when no clean frame has the face
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


def name_layers(cover):
    """Kaptain's lettering lifted off the cover: (name layer, original subtitle layer, subtitle box, text mask).
    White top-hat on the dark bottom of the card finds the strokes; rows group into bands, the last band is the
    subtitle."""
    from scipy import ndimage as ndi
    L = np.asarray(cover.convert("L"), dtype=np.float32)
    y0 = int(H * 0.82)
    sub = L[y0:]
    th = sub - ndi.grey_opening(sub, size=(17, 17))
    m = th > 38
    m = ndi.binary_opening(m, iterations=1) | (th > 70)
    rows = m.sum(1) > 2
    bands, st = [], None
    for y, r in enumerate(rows):
        if r and st is None:
            st = y
        if not r and st is not None:
            if y - st > 3:
                bands.append((st, y))
            st = None
    if st is not None:
        bands.append((st, len(rows)))
    # merge bands closer than a few pixels (letters with descenders)
    merged = []
    for b_ in bands:
        if merged and b_[0] - merged[-1][1] < 6:
            merged[-1] = (merged[-1][0], b_[1])
        else:
            merged.append(b_)
    bands = [b_ for b_ in merged if b_[1] - b_[0] >= 6]
    if not bands:
        return None
    alpha = np.clip(th * 2.2, 0, 255) * ndi.binary_dilation(m, iterations=2)
    full = np.zeros_like(L)
    mask_all = np.zeros_like(L, dtype=bool)
    name_a, sub_a = np.zeros_like(L), np.zeros_like(L)
    for k, (a0, a1) in enumerate(bands):
        rr = slice(max(0, a0 - 3), min(len(rows), a1 + 3))
        band = np.zeros_like(alpha); band[rr] = alpha[rr]
        tgt = sub_a if k == len(bands) - 1 and len(bands) > 1 else name_a
        tgt[y0:] = np.maximum(tgt[y0:], band)
        mask_all[y0:][rr] |= m[rr]
    sb = bands[-1]
    cols = np.nonzero(m[sb[0]:sb[1]].any(0))[0]
    sub_box = (int(cols.min()) if len(cols) else round(W * 0.1), y0 + sb[0], y0 + sb[1])
    rgb = np.asarray(cover.convert("RGB"))
    def layer(a_):
        lay = Image.fromarray(rgb).convert("RGBA")
        lay.putalpha(Image.fromarray(a_.astype(np.uint8)))
        return lay
    return layer(name_a), layer(sub_a), sub_box, mask_all


def clean_plate(cover, mask):
    """The cover with its lettering painted out (the portrait as a picture in the reel)."""
    import cv2
    from scipy import ndimage as ndi
    m = ndi.binary_dilation(mask, iterations=4).astype(np.uint8) * 255
    bgr = cv2.cvtColor(np.asarray(cover.convert("RGB")), cv2.COLOR_RGB2BGR)
    out = cv2.inpaint(bgr, m, 6, cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


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
    nl = name_layers(cover)
    if nl is None:
        raise RuntimeError("no lettering found")
    name_lay, sub_orig, (sx0, sy0, sy1), tmask = nl
    plate = clean_plate(cover, tmask)
    # subtitles for the roles, set like Kaptain's (same cap height and left edge)
    cap = max(8, sy1 - sy0)
    fsz = max(10, round(cap / 0.72))
    sfont = font("SemiBold", fsz)
    sp = round(fsz * 0.34)

    def label(t, y):
        t = t.upper()
        for cut in (None, ",", ":", " ("):
            tt = t.split(cut)[0].strip() if cut else t
            if width(f"{tt} · {y}", sfont, sp) <= W - sx0 - W * 0.06:
                return f"{tt} · {y}"
        words = tt.split()
        while len(words) > 1:
            words = words[:-1]
            if width(f"{' '.join(words)} · {y}", sfont, sp) <= W - sx0 - W * 0.06:
                break
        return f"{' '.join(words)} · {y}"

    sub_lays = [sub_orig]
    asc = sfont.getbbox("A")[1]
    for t, y, _, _ in roles:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(lay), (sx0, sy0 - asc), label(t, y), sfont, (205, 205, 205, 255), sp)
        sub_lays.append(lay)
    # the reel: portrait, then the roles on a full-width strip of film, then the portrait again
    hole_w, hole_h, hole_gap = round(W * 0.045), round(W * 0.03), round(W * 0.062)
    margin = round(W * 0.11)
    fw = W - 2 * margin
    fh = round(fw * 0.66)
    gap = 26
    pitch = fh + gap
    seg_h = pitch * len(roles) + gap
    R = H + seg_h
    reel = Image.new("RGB", (W, R * 2 + H), (20, 16, 13))
    d = ImageDraw.Draw(reel)
    for rep in range(2):
        top = rep * R
        reel.paste(plate, (0, top))
        y = top + H
        for yy in range(y, y + seg_h, hole_gap):
            for x in (round(W * 0.03), W - round(W * 0.03) - hole_w):
                d.rounded_rectangle((x, yy + 8, x + hole_w, yy + 8 + hole_h), 3, fill=(208, 199, 184))
        for k, (_, _, p, cx) in enumerate(roles):
            reel.paste(strip_frame(g.load_img(p), fw, fh, cx), (margin, y + gap + k * pitch))
    reel.paste(plate, (0, 2 * R))
    # timeline: hold the portrait, then one smooth pass of the reel back to the portrait
    N_ = 140
    HOLD = 8

    def offset(i):
        if i < HOLD:
            return 0.0
        u = (i - HOLD) / (N_ - HOLD)
        a = 0.14                                            # ease in / constant / ease out
        if u < a:
            v = 0.5 * u * u / a
        elif u > 1 - a:
            v = (1 - a) - 0.5 * (1 - u) ** 2 / a
        else:
            v = 0.5 * a + (u - a)
        v /= (1 - a)
        return min(1.0, v) * R

    read_y = H * 0.45
    t_ = np.clip((np.arange(H) - H * 0.52) / (H * 0.48), 0, 1)
    grad = (t_ * t_ * (3 - 2 * t_)) * 0.93
    # soft black shadow behind the name, so it reads over bright frames too
    sh_a = name_lay.getchannel("A").filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(W // 45))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(sh_a.point(lambda v: min(255, round(v * 0.85))))
    frames = []
    for i in range(N_):
        o = offset(i)
        cv = reel.crop((0, round(o), W, round(o) + H))
        # dark fall under the name wherever the portrait's own dark bottom is not sitting behind it
        rows = (np.arange(H) + o) % R
        own = np.clip((rows - H * 0.62) / (H * 0.08), 0, 1) * (rows < H)
        a_rows = grad * (1 - own)
        if a_rows.max() > 0:
            fade = Image.fromarray((np.repeat(a_rows[:, None], W, 1) * 255).astype(np.uint8))
            cv = Image.composite(Image.new("RGB", (W, H), (10, 9, 9)), cv, fade)
        cv = cv.convert("RGBA")
        if a_rows.max() > 0.05:
            cv.alpha_composite(alpha_mul(shadow, float(a_rows[int(H * 0.85)]) / 0.93))
        cv.alpha_composite(name_lay)
        # subtitle of whatever sits on the reading line
        p_ = (read_y + o) % R
        if p_ < H:
            k, edge = 0, min(p_ - 0, H - p_)
        else:
            q = (p_ - H - gap / 2) / pitch
            k = 1 + min(len(roles) - 1, max(0, int(q)))
            edge = min(q - int(q), 1 - (q - int(q))) * pitch if 0 <= q < len(roles) else 0
        a_sub = min(1.0, max(0.0, edge / 60))
        cv.alpha_composite(alpha_mul(sub_lays[k], a_sub))
        frames.append(cv.convert("RGB").resize((OW, OH), Image.LANCZOS))
    dd = os.path.join(out, g.slug_of(name))
    os.makedirs(dd, exist_ok=True)
    frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * N_,
                   loop=0, quality=80, method=4, kmin=0, kmax=1)
    strip = Image.new("RGB", (OW * 6, OH))
    for j, k in enumerate((0, 25, 50, 75, 100, 125)):
        strip.paste(frames[k], (j * OW, 0))
    strip.save(os.path.join(dd, "frames.jpg"), quality=80)
    return [f"{t} ({y}){'' if cx != 0.5 else ' [no face match]'}" for t, y, _, cx in roles]


def alpha_mul(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return out


def covers():
    d = json.load(open(os.path.join(ROOT, "builder", "out", "delivered", "baseline.json"), encoding="utf-8"))
    out = {}
    for row in d:
        if row["title"] == "Iconic Actors":
            for i, f in enumerate(row["folders"]):
                out[f["title"]] = (f.get("coverImageUrl"), f.get("focusGifUrl") or None, i)
    ref = os.environ.get("ART_REF")  # pin our own portraits to a nuvio-art commit (fresh covers, no CDN lag)
    if ref:
        for k, (c, h, i) in out.items():
            if c and "/art/folders/iconic-actors/" in c:
                out[k] = (c.split("?")[0].replace("/nuvio-art/main/", f"/nuvio-art/{ref}/"), h, i)
    return out


def own_cover(name, ref="main"):
    return f"https://raw.githubusercontent.com/ObliviousTR/nuvio-art/{ref}/art/folders/iconic-actors/{g.slug_of(name)}/cover.jpg"


if __name__ == "__main__":
    outdir = sys.argv[1]
    cv = covers()
    names = sys.argv[2:] or list(cv)
    bad = False
    for n in names:
        if n not in cv:
            cv[n] = (own_cover(n, os.environ.get("ART_REF", "main")), None, len(cv))
        try:
            c, h, i = cv[n]
            print("built", n, "·", ", ".join(build(n, c, h, outdir, i)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", n, e)
            bad = True
    sys.exit(1 if bad else 0)
