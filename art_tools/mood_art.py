"""Moods & Vibes row: Kaptain's mood cards (one film still graded in the mood's colour, bold title, tracked subtitle,
accent bar), rebuilt so they move like the Genres row:
  cover   Kaptain's own still (the textless source of his card, found by matching) in his grade, with the type
  hover   the type rises in, bar and subtitle fill with the mood colour, the bar counts the pictures (a segment each, name and year top right) while three
          iconic films for the mood play behind it - every one graded exactly like Kaptain graded his card, so the
          card keeps one look whatever plays; breath, back to the cover.
Kaptain's grade is learnt per card: a least-squares colour transform from the source still to his finished cover.
The trio moves on every month through each mood's list (.github/workflows/mood-art.yml -> mood-art branch).
usage: python3 art_tools/mood_art.py OUT_DIR [titles...]
"""
import io, json, os, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import genre_art as g
from PIL import Image

KAPTAIN = "https://raw.githubusercontent.com/ObliviousTR/nuvio-art/main/mirror/files/"

# title: card title, subtitle, accent (Kaptain's hover colour), Kaptain's cover, its textless source, iconic pool
MOODS = {
    "Feel-Good": ("FEEL-GOOD", "HEARTWARMING, UPLIFTING & JOYFUL TALES", (242, 182, 38),
                  "45/45720700a11bc407.jpg", "/qJeU7KM4nT2C1WpOrwPcSDGFUWE.jpg",
                  [("Paddington 2", 2017), ("The Secret Life of Walter Mitty", 2013), ("Little Miss Sunshine", 2006),
                   ("Mamma Mia!", 2008), ("School of Rock", 2003), ("The Greatest Showman", 2017),
                   ("Sing Street", 2016), ("Chef", 2014)]),
    "Cozy & Comforting": ("COZY & COMFORTING", "GENTLE, RELAXING & SOUL-WARMING CINEMA", (241, 150, 70),
                          "5e/5ee512bfb04bc7b2.jpg", "/sylBlnpwqI9LAcyw7jH3oqazbAx.jpg",
                          [("You've Got Mail", 1998), ("The Holiday", 2006), ("About Time", 2013), ("Little Women", 2019),
                           ("Julie & Julia", 2009), ("Chocolat", 2000), ("When Harry Met Sally...", 1989),
                           ("Paddington", 2014)]),
    "Adrenaline Rush": ("ADRENALINE RUSH", "NON-STOP ACTION, CHASES & COMBAT", (251, 44, 85),
                        "9f/9f64f57574827abd.jpg", "/c7E5hEg90JiGauNHI0KF83kPLCb.jpg",
                        [("Speed", 1994), ("Baby Driver", 2017), ("Point Break", 1991), ("Ford v Ferrari", 2019),
                         ("Rush", 2013), ("Edge of Tomorrow", 2014), ("Crank", 2006), ("The Fast and the Furious", 2001)]),
    "Epic & Sweeping": ("EPIC & SWEEPING", "GRAND SCALE STORIES THAT FILL THE FRAME", (205, 160, 75),
                        "d2/d224e5f5a179c038.jpg", "/6wmemKdbkOIaWfzz607K21R6qOh.jpg",
                        [("Braveheart", 1995), ("Ben-Hur", 1959), ("Interstellar", 2014),
                         ("The Lord of the Rings: The Return of the King", 2003), ("Kingdom of Heaven", 2005),
                         ("Troy", 2004), ("The Revenant", 2015), ("The Last of the Mohicans", 1992)]),
    "Mind-Bending": ("MIND-BENDING", "PSYCHOLOGICAL THRILLERS & REALITY SHIFTERS", (13, 194, 238),
                     "b4/b4ee6d73ada0c7f8.jpg", "/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg",
                     [("Memento", 2000), ("Arrival", 2016), ("Donnie Darko", 2001), ("The Prestige", 2006),
                      ("Eternal Sunshine of the Spotless Mind", 2004), ("Tenet", 2020),
                      ("Everything Everywhere All at Once", 2022), ("Being John Malkovich", 1999)]),
    "Slow Burn": ("SLOW BURN", "PATIENCE, DREAD & DELAYED PAYOFF", (161, 90, 69),
                  "bd/bdd80b9bd68167c3.jpg", "/8LRcCJjbQI552BMCuGgYqph8USS.jpg",
                  [("No Country for Old Men", 2007), ("Drive", 2011), ("Sicario", 2015),
                   ("The Assassination of Jesse James by the Coward Robert Ford", 2007), ("Nightcrawler", 2014),
                   ("Enemy", 2013), ("The Witch", 2015), ("Under the Skin", 2013)]),
    "Dark & Gritty": ("DARK & GRITTY", "RAW, INTENSE & UNCOMPROMISING DRAMAS", (229, 70, 39),
                      "ec/ecf2ae62f61e7f67.jpg", "/tRS6jvPM9qPrrnx2KRp3ew96Yot.jpg",
                      [("The Dark Knight", 2008), ("Sin City", 2005), ("Training Day", 2001), ("Children of Men", 2006),
                       ("Léon: The Professional", 1994), ("Mystic River", 2003), ("Gone Baby Gone", 2007),
                       ("Mad Max: Fury Road", 2015)]),
    "Spooky & Creepy": ("SPOOKY & CREEPY", "EERIE ATMOSPHERES & HAUNTING NIGHTMARES", (140, 221, 69),
                        "70/705342b6a61cfc62.jpg", "/AmR3JG1VQVxU8TfAvljUhfSFUOx.jpg",
                        [("The Shining", 1980), ("The Thing", 1982), ("The Babadook", 2014), ("The Others", 2001),
                         ("Sleepy Hollow", 1999), ("The Ring", 2002), ("Insidious", 2010), ("The Witch", 2015)]),
    "Tearjerkers": ("TEARJERKERS", "STORIES THAT STAY WITH YOU", (121, 151, 201),
                    "90/9059e4f14e5e82ce.jpg", "/4gviR5E8xEiooxFbFqHLrg5gPeN.jpg",
                    [("Schindler's List", 1993), ("Marley & Me", 2008), ("The Fault in Our Stars", 2014),
                     ("Million Dollar Baby", 2004), ("Atonement", 2007), ("A Star Is Born", 2018),
                     ("Hachi: A Dog's Tale", 2009), ("Brokeback Mountain", 2005)]),
    "80s & 90s Vibes": ("80S & 90S VIBES", "NEON, NOSTALGIA & TAPE-ERA COOL", (253, 80, 159),
                        "72/7262c18ca103862b.jpg", "/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg",
                        [("Back to the Future", 1985), ("The Breakfast Club", 1985), ("E.T. the Extra-Terrestrial", 1982),
                         ("Ghostbusters", 1984), ("Jurassic Park", 1993), ("The Terminator", 1984), ("Top Gun", 1986),
                         ("Dirty Dancing", 1987)]),
}


def get(url):
    for _ in range(3):
        try:
            return Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nuvio-awards"}),
                                                                timeout=60).read())).convert("RGB")
        except Exception:
            continue
    raise RuntimeError("could not fetch " + url)


def feats(a):
    """Per-pixel features for the grade: RGB, luminance curve terms, constant."""
    a = a.reshape(-1, 3) / 255.0
    L = a @ np.array([0.299, 0.587, 0.114])
    return np.column_stack([a, L ** 2, L ** 3, np.sqrt(np.clip(L, 0, 1)), np.ones(len(a))])


def learn_grade(src, kaptain):
    """Least-squares colour transform src -> Kaptain's cover, fitted above the type, dropping the worst-fitting
    pixels (vignettes, letters) in a second pass."""
    w, h = 320, 180
    s = np.asarray(g.art.cover_fit(src, w, h), dtype=np.float32)[: int(h * 0.62)]
    k = np.asarray(kaptain.resize((w, h), Image.BILINEAR), dtype=np.float32)[: int(h * 0.62)] / 255.0
    X, Y = feats(s), k.reshape(-1, 3)
    keep = np.ones(len(X), bool)
    for _ in range(2):
        M, *_ = np.linalg.lstsq(X[keep], Y[keep], rcond=None)
        err = np.abs(X @ M - Y).sum(1)
        keep = err <= np.quantile(err, 0.8)
    return M


def apply_grade(im, M):
    a = np.asarray(im, dtype=np.float32)
    out = (feats(a) @ M).reshape(a.shape)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


# the film of each mood's cover picture (Kaptain's), for its label
COVER_FILM = {"Feel-Good": ("Midnight in Paris", 2011), "Cozy & Comforting": ("Amélie", 2001),
              "Adrenaline Rush": ("Top Gun: Maverick", 2022), "Epic & Sweeping": ("Lawrence of Arabia", 1962),
              "Mind-Bending": ("Inception", 2010), "Slow Burn": ("There Will Be Blood", 2007),
              "Dark & Gritty": ("The Batman", 2022), "Spooky & Creepy": ("Alien", 1979),
              "Tearjerkers": ("Manchester by the Sea", 2016), "80s & 90s Vibes": ("Pulp Fiction", 1994)}


def cover_label(t, src_path):
    name, year = COVER_FILM[t]
    tid, _ = g.find_movie(name, year)
    if tid:
        bd = (g.tmdb(f"/movie/{tid}/images") or {}).get("backdrops", [])
        if src_path not in [b["file_path"] for b in bd]:
            print(f"note: {t}: cover picture not among {name}'s backdrops - check COVER_FILM", flush=True)
        return g.labels_of([(tid, name, None)])[0]
    return (name, year)


def build_one(job):
    t, picks, out = job
    title, sub, accent, kcov, src_path, _ = MOODS[t]
    try:
        src = g.load_img(src_path)
        M = learn_grade(src, get(KAPTAIN + kcov))
        imgs = [apply_grade(g.art.cover_fit(src, 1600, 900), M)]
        for _, _, p in picks:
            imgs.append(apply_grade(g.art.cover_fit(g.load_img(p), 1600, 900), M))
        labels = [cover_label(t, src_path)] + g.labels_of(picks)
        frame = g.make(title, sub, accent, imgs, labels=labels)
        dd = os.path.join(out, g.slug_of(t))
        os.makedirs(dd, exist_ok=True)
        n = frame.n
        frames = [frame(i, n).resize((g.OW, g.OH), Image.LANCZOS) for i in range(n)]
        frames[0].save(os.path.join(dd, "hover.webp"), save_all=True, append_images=frames[1:], duration=[50] * n,
                       loop=0, quality=80, method=4, kmin=0, kmax=1)
        frame.cover().save(os.path.join(dd, "cover.jpg"), quality=90)
        strip = Image.new("RGB", (g.OW * 3, g.OH * 2))
        for jj, idx in enumerate([0, n // 6, n // 3, n // 2, 2 * n // 3, n - 1]):
            strip.paste(frames[idx], ((jj % 3) * g.OW, (jj // 3) * g.OH))
        strip.save(os.path.join(dd, "frames.jpg"), quality=80)
        return t, [(x[0], x[1]) for x in picks], None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return t, [], str(e)


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    only = set(args)
    # films already behind a Genres card or on a Kaptain mood cover stay off the mood cards
    used = set()
    for name, year in [x for pool in g.ICONIC.values() for x in pool]:
        tid, _ = g.find_movie(name, year)
        if tid:
            used.add(tid)
    used |= {v[3] for v in g.GENRES.values() if v[3]}
    # ...and no film of a series already on another card (Genres, Kids, the mood covers, the moods picked before)
    used_coll = {c for c in (g.collection_of(i) for i in used) if c}
    try:
        import kids_art
        for v in kids_art.CARDS.values():
            for it in ([v[3]] if v[3] else []) + list(v[4] or []):
                if it[0] == "movie":
                    tid, _ = g.find_movie(it[1], it[2])
                    c = g.collection_of(tid) if tid else None
                    if c:
                        used_coll.add(c)
    except Exception as e:
        print("kids pools not read:", e)
    for t, (name, year) in COVER_FILM.items():
        tid, _ = g.find_movie(name, year)
        c = g.collection_of(tid) if tid else None
        if c:
            used_coll.add(c)
    for t, v in MOODS.items():
        g.ICONIC[t] = v[5]
    jobs = []
    for t in MOODS:
        if only and t not in only:
            continue
        try:
            pk = g.iconic(t, 3, avoid=used, avoid_coll=used_coll)
        except Exception as e:
            print("pick failed", t, e)
            pk = []
        used |= {x[0] for x in pk}
        jobs.append((t, pk, out))
    from multiprocessing import Pool
    with Pool(4) as pool:
        res = pool.map(build_one, jobs)
    picks, failed = {}, []
    for t, pk, err in res:
        if err:
            failed.append(t)
            print("FAILED", t, err)
        else:
            picks[t] = pk
            print("built", t, "·", ", ".join(str(x[1]) for x in pk))
    import datetime as dt
    os.makedirs(out, exist_ok=True)
    json.dump({"date": dt.date.today().isoformat(), "picks": picks}, open(os.path.join(out, "picks.json"), "w"),
              indent=1, ensure_ascii=False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
