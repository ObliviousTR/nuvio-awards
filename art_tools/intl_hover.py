"""International Cinema hover: the flag inside the borders turns into the country's first film, the camera flies
through the map until the film fills the card, and the card's name docks in the lower left next to a small flag map,
the film's title under it; three films play; then the camera pulls back out into the map and the flag returns.
Cards from intl_cover.py, films from intl_art.py (TMDB stills, a new three every month).
usage: python3 art_tools/intl_hover.py OUT_DIR [folder titles...]     (INTL_TEST=1: local stills)
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import intl_art as I
import intl_cover as C
from PIL import Image, ImageDraw, ImageFilter
from reletter import f as font, tracked, width

W, H, OW, OH = I.W, I.H, I.OW, I.OH
ease = I.ease
DOCK_H = 84            # height of the docked title / mini map
DX = 56
DY = H - 214           # centre line of the dock


def scaled(im, s, ax, ay):
    if s <= 1.0001:
        return im
    return im.transform((W, H), Image.AFFINE, (1 / s, 0, ax - ax / s, 0, 1 / s, ay - ay / s), resample=Image.BILINEAR)


def build(folder, out):
    p = C.parts(folder)
    tint = p["tint"]
    films = I.films_of(folder)
    reals = [I.cover_fit(I.load(q)) for _, _, q in films]
    mask = p["mask"]
    from scipy import ndimage as ndi
    dist = ndi.distance_transform_edt(np.asarray(mask) > 128)
    ay, ax = np.unravel_index(np.argmax(dist), dist.shape)
    depth = float(dist[ay, ax])
    smax = max(30.0, min(W, H) / max(depth, 4) * 1.8)
    # the title block (cropped) and where it docks
    tl = p["title"]
    tb = tl.getchannel("A").getbbox()
    tcrop = tl.crop(tb)
    ds = min(DOCK_H / tcrop.height, (W * 0.5) / tcrop.width)
    # the mini map for the dock: flag fill + border, cropped to the map
    mini_full = C.compose(p, title_a=0, shadow_a=0)
    mb = mask.getbbox()
    pad = 8
    mb = (max(0, mb[0] - pad), max(0, mb[1] - pad), min(W, mb[2] + pad), min(H, mb[3] + pad))
    mini = mini_full.crop(mb)
    mm = Image.new("L", (W, H), 0)
    mm.paste(mask.filter(ImageFilter.MaxFilter(9)).crop(mb), (mb[0], mb[1]))
    mini.putalpha(mm.crop(mb))
    k = min(DOCK_H * 1.15 / mini.height, 170 / mini.width)
    mini = mini.resize((max(1, round(mini.width * k)), max(1, round(mini.height * k))), Image.LANCZOS)
    title_x1 = DX + mini.width + 22
    fall_ = I.fall()

    def title_at(cv, m, a=1.0):
        e = ease(m)
        sc = 1 + (ds - 1) * e
        im = tcrop.resize((max(1, round(tcrop.width * sc)), max(1, round(tcrop.height * sc))), Image.LANCZOS)
        x = tb[0] + (title_x1 - tb[0]) * e
        y = tb[1] + ((DY - im.height / 2) - tb[1]) * e
        cv.alpha_composite(I.amul(im, a), (round(x), round(y)))

    def dock_mini(cv, a):
        if a > 0:
            cv.alpha_composite(I.amul(mini, a), (DX, round(DY - mini.height / 2)))

    def film_label(t, y):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        tt = t.upper()
        fn = font("ExtraBold", 44)
        while width(tt, fn, 3) > W - 140 and fn.size > 24:
            fn = font("ExtraBold", fn.size - 2)
        top = DY + DOCK_H / 2 + 18
        tracked(d, (DX - 2, top), tt, fn, (255, 255, 255, 255), 3)
        lite = tuple(min(255, int(v * 0.6 + 110)) for v in tint)
        tracked(d, (DX, top + fn.size + 12), str(y), font("SemiBold", 21), lite + (255,), 8)
        return lay

    labels = [film_label(t, y) for t, y, _ in films]
    cover = C.compose(p).convert("RGB")
    HOLD, MORPH, DIVE, SEG, RISE, UNMORPH = 6, 14, 16, 40, 16, 12
    S = len(films)
    T1 = HOLD + MORPH
    T2 = T1 + DIVE
    T3 = T2 + SEG * S
    T4 = T3 + RISE
    N_ = T4 + UNMORPH
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < T1:      # the flag turns into the film inside the borders
            u = ease((i - HOLD) / MORPH)
            content = Image.blend(p["fill"], I.zoomed(reals[0], 0.01), u)
            cv = C.compose(p, content=content, title_a=0)
            title_at(cv, 0)
        elif i < T2:    # fly through the map; the name docks
            u = (i - T1) / DIVE
            s = math.exp(math.log(smax) * (u ** 2.2))
            m = scaled(mask, s, ax, ay)
            cv = p["bg"].convert("RGBA")
            c = I.zoomed(reals[0], 0.01).convert("RGBA")
            c.putalpha(m)
            cv.alpha_composite(c)
            cv.alpha_composite(I.amul(scaled(p["border"], s, ax, ay), 1 - ease(u * 1.5)))
            cv.alpha_composite(I.amul(fall_, ease(u)))
            title_at(cv, u)
            dock_mini(cv, ease((u - 0.5) / 0.5))
            cv.alpha_composite(I.amul(labels[0], ease((u - 0.7) / 0.3)))
        elif i < T3:
            kf, t = divmod(i - T2, SEG)
            pic = I.zoomed(reals[kf], 0.01 + 0.05 * t / SEG)
            if kf > 0 and t < 8:
                pic = Image.blend(I.zoomed(reals[kf - 1], 0.06), pic, ease(t / 8))
            cv = pic.convert("RGBA")
            cv.alpha_composite(fall_)
            title_at(cv, 1)
            dock_mini(cv, 1)
            if kf == 0:
                la = 1.0 if t < SEG - 5 else 1 - ease((t - (SEG - 5)) / 5)
            elif kf == S - 1:
                la = ease(t / 6) if t < 6 else (1 - ease((t - (SEG - 4)) / 4) if t >= SEG - 4 else 1.0)
            else:
                la = ease(t / 6) if t < 6 else (1 - ease((t - (SEG - 5)) / 5) if t >= SEG - 5 else 1.0)
            cv.alpha_composite(I.amul(labels[kf], la))
        elif i < T4:    # pull back out into the map
            u = (i - T3) / RISE
            s = math.exp(math.log(smax) * ((1 - u) ** 2.2))
            m = scaled(mask, s, ax, ay)
            cv = p["bg"].convert("RGBA")
            c = I.zoomed(reals[-1], 0.06).convert("RGBA")
            c.putalpha(m)
            cv.alpha_composite(c)
            cv.alpha_composite(I.amul(scaled(p["border"], s, ax, ay), ease((u - 0.4) / 0.6)))
            cv.alpha_composite(I.amul(fall_, 1 - ease(u)))
            title_at(cv, 1 - u)
            dock_mini(cv, 1 - ease(u * 2))
        else:           # and the flag comes back
            u = ease((i - T4) / UNMORPH)
            content = Image.blend(I.zoomed(reals[-1], 0.06), p["fill"], u)
            cv = C.compose(p, content=content, shadow_a=u, title_a=0)
            title_at(cv, 0)
        frames.append(cv.convert("RGB").resize((OW, OH), Image.LANCZOS))
    I.save_reel(frames, cover, folder, out)
    return [f"{t} ({y})" for t, y, _ in films]


if __name__ == "__main__":
    out = sys.argv[1]
    bad = False
    for fo in sys.argv[2:] or C.TITLES:
        try:
            print("built", fo, "·", ", ".join(build(fo, out)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", fo, e)
            bad = True
    sys.exit(1 if bad else 0)
