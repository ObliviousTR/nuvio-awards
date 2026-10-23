"""International Cinema, look B "the flight": the card shows the country on a dark map with its flag; on hover the
camera pulls back until Istanbul is in view, a plane flies the great-circle route from IST to the country's main
airport, the camera follows it down and dives into the country, and its films play; then back out to the card.
Map: Natural Earth 1:50m countries (public domain), drawn live per frame. Films and flags as in intl_art.py.
usage: python3 art_tools/intl_flight.py OUT_DIR [folder titles...]     (INTL_TEST=1: no TMDB / flag download)
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import intl_art as I
from PIL import Image, ImageDraw, ImageFilter
from reletter import f as font, tracked, width

W, H, OW, OH = I.W, I.H, I.OW, I.OH
ease = I.ease
IST = (28.98, 41.01)
# folder -> (airport code, lon, lat)
ROUTES = {
    "Türkiye": ("NAV", 34.53, 38.77), "South Korea": ("ICN", 126.45, 37.46), "Japan": ("HND", 139.78, 35.55),
    "Greater China": ("PEK", 116.6, 40.08), "India": ("BOM", 72.87, 19.09), "UK & Ireland": ("LHR", -0.45, 51.47),
    "France": ("CDG", 2.55, 49.01), "Spain": ("MAD", -3.57, 40.47), "Italy": ("FCO", 12.25, 41.8),
    "Germany": ("BER", 13.5, 52.36), "Nordic Noir": ("ARN", 17.92, 59.65), "Central & Eastern Europe": ("PRG", 14.26, 50.1),
    "Latin America": ("MEX", -99.07, 19.44),
}

FEATS = None


def feats():
    """Every country's rings as numpy arrays, with bounding boxes and ISO codes."""
    global FEATS
    if FEATS is None:
        I.rings_of(["TR"], (-180, -90, 180, 90))  # loads the geojson
        FEATS = []
        for f in I.GEO["features"]:
            pr = f["properties"]
            iso = pr.get("ISO_A2_EH") if pr.get("ISO_A2_EH") not in (None, "-99") else pr.get("ISO_A2")
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                r = np.array(poly[0], np.float32)
                FEATS.append((iso, r, (r[:, 0].min(), r[:, 1].min(), r[:, 0].max(), r[:, 1].max())))
    return FEATS


def cam_of(box, fill=0.8):
    """Camera (lon, lat, px per degree) that fits a lon/lat box."""
    w, s, e, n = box
    clon, clat = (w + e) / 2, (s + n) / 2
    k = math.cos(math.radians(clat))
    sc = min(W * fill / max(0.1, (e - w) * k), H * fill / max(0.1, n - s))
    return (clon, clat, sc)


def lerp_cam(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * t))


def proj(cam):
    clon, clat, sc = cam
    k = math.cos(math.radians(clat))
    return lambda lon, lat: (W / 2 + (lon - clon) * k * sc, H / 2 - (lat - clat) * sc)


def draw_map(cam, dest_isos, cols, dest_a=1.0, home_a=0.0):
    clon, clat, sc = cam
    k = math.cos(math.radians(clat))
    vw, vh = W / (k * sc) / 2 + 2, H / sc / 2 + 2
    land = Image.new("L", (W, H), 0)
    border = Image.new("L", (W, H), 0)
    dest = Image.new("L", (W, H), 0)
    home = Image.new("L", (W, H), 0)
    dl, db, dd, dh = (ImageDraw.Draw(x) for x in (land, border, dest, home))
    bw = 1 if sc < 12 else 2
    for iso, r, (x0, y0, x1, y1) in feats():
        if x1 < clon - vw or x0 > clon + vw or y1 < clat - vh or y0 > clat + vh:
            continue
        xs = W / 2 + (r[:, 0] - clon) * k * sc
        ys = H / 2 - (r[:, 1] - clat) * sc
        pts = list(zip(xs.tolist(), ys.tolist()))
        if len(pts) < 3:
            continue
        if iso in dest_isos:
            dd.polygon(pts, fill=255)
        elif iso == "TR":
            dh.polygon(pts, fill=255)
        dl.polygon(pts, fill=255)
        db.line(pts + [pts[0]], fill=255, width=bw)
    cv = Image.new("RGB", (W, H), (7, 8, 11))
    cv.paste((24, 26, 33), (0, 0), land)
    cv.paste((205, 46, 58), (0, 0), home.point(lambda v: round(v * 0.35 * home_a)))
    # destination: a lit fill in the flag's colours (top to bottom) and its glowing border
    ramp = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    c0, c1 = np.array(cols[0], np.float32), np.array(cols[1] if len(cols) > 1 else cols[0], np.float32)
    rgb = np.repeat(c0 * (1 - ramp) + c1 * ramp, W, 1)
    fill = Image.fromarray(np.dstack([rgb * 0.55, np.asarray(dest, np.float32) * 0.55 * dest_a]).astype(np.uint8), "RGBA")
    cv = cv.convert("RGBA")
    cv.alpha_composite(fill)
    bl = Image.new("RGBA", (W, H), (70, 74, 90, 0))
    bl.putalpha(border.point(lambda v: round(v * 0.8)))
    cv.alpha_composite(bl)
    from PIL import ImageChops
    edge = ImageChops.subtract(dest.filter(ImageFilter.MaxFilter(5)), dest)
    glow = Image.fromarray(np.dstack([rgb, np.asarray(edge.filter(ImageFilter.GaussianBlur(6)), np.float32) * 1.6 * dest_a]).clip(0, 255).astype(np.uint8), "RGBA")
    cv.alpha_composite(glow)
    line = Image.fromarray(np.dstack([rgb, np.asarray(edge, np.float32) * dest_a]).astype(np.uint8), "RGBA")
    cv.alpha_composite(line)
    return cv, dest


def great_circle(a, b, n=200):
    def v(lon, lat):
        lo, la = math.radians(lon), math.radians(lat)
        return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
    p, q = v(*a), v(*b)
    om = math.acos(max(-1, min(1, float(p @ q))))
    out = []
    for t in np.linspace(0, 1, n):
        if om < 1e-6:
            x = p
        else:
            x = (math.sin((1 - t) * om) * p + math.sin(t * om) * q) / math.sin(om)
        out.append((math.degrees(math.atan2(x[1], x[0])), math.degrees(math.asin(x[2]))))
    return out


def plane(size, ang):
    """A small airliner silhouette pointing along ang (radians, screen space)."""
    s = size
    im = Image.new("RGBA", (4 * s, 4 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = 2 * s
    body = [(c + 1.6 * s, c), (c + 1.2 * s, c - 0.18 * s), (c - 1.4 * s, c - 0.16 * s), (c - 1.6 * s, c), (c - 1.4 * s, c + 0.16 * s),
            (c + 1.2 * s, c + 0.18 * s)]
    wing = [(c + 0.3 * s, c - 0.1 * s), (c - 0.5 * s, c - 1.3 * s), (c - 0.85 * s, c - 1.3 * s), (c - 0.45 * s, c), (c - 0.85 * s, c + 1.3 * s),
            (c - 0.5 * s, c + 1.3 * s), (c + 0.3 * s, c + 0.1 * s)]
    tail = [(c - 1.1 * s, c), (c - 1.55 * s, c - 0.6 * s), (c - 1.75 * s, c - 0.6 * s), (c - 1.5 * s, c), (c - 1.75 * s, c + 0.6 * s),
            (c - 1.55 * s, c + 0.6 * s)]
    for poly in (wing, tail, body):
        d.polygon(poly, fill=(255, 255, 255, 255))
    return im.rotate(-math.degrees(ang), resample=Image.BICUBIC)


def board(code, a=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    fo = font("ExtraBold", 30)
    x = 150
    tracked(d, (x, 46), "IST", fo, (255, 255, 255, round(255 * a)), 4)
    x2 = x + width("IST", fo, 4) + 26
    d.line((x2, 64, x2 + 40, 64), fill=(255, 255, 255, round(200 * a)), width=3)
    d.polygon([(x2 + 40, 56), (x2 + 52, 64), (x2 + 40, 72)], fill=(255, 255, 255, round(200 * a)))
    tracked(d, (x2 + 70, 46), code, fo, (255, 255, 255, round(255 * a)), 4)
    return lay


def build(folder, out):
    name, isos, box, fiso, cols, _ = I.CARDS[folder]
    code, alon, alat = ROUTES[folder]
    films = I.films_of(folder)
    reals = [I.cover_fit(I.load(p)) for _, _, p in films]
    fl = None if not fiso else I.flag_img(fiso)
    nm = I.name_layer(name, H * 0.72 if fiso else H * 0.8)
    labels = [I.film_label(t, y) for t, y, _ in films]
    fall_ = I.fall()
    route = great_circle(IST, (alon, alat))
    C0 = cam_of(box, 0.78)                                         # the card: the country
    lons = [p[0] for p in route] + [box[0], box[2]]
    lats = [p[1] for p in route] + [box[1], box[3]]
    C1 = cam_of((min(lons) - 3, min(lats) - 3, max(lons) + 3, max(lats) + 3), 0.82)   # the trip
    C1 = (C1[0], C1[1], min(C1[2], C0[2]))
    C2 = (alon, alat, C0[2] * 14)                                  # the dive

    def flag_layer(sc, cx, cy, t=0, amp=0, a=1.0):
        if fl is None:
            return None, 0, 0
        f = I.framed_flag(I.waving(fl, t, amp))
        f = f.resize((max(1, round(f.width * sc)), max(1, round(f.height * sc))), Image.LANCZOS)
        return I.amul(f, a), round(cx - f.width / 2), round(cy - f.height / 2)

    def card(cam, extra_a=1.0, home_a=0.0, dest_a=1.0):
        cv, _ = draw_map(cam, isos, cols, dest_a=dest_a, home_a=home_a)
        f, x, y = flag_layer(1.0, W / 2, H * 0.37, a=extra_a)
        if f is not None:
            cv.alpha_composite(f, (x, y))
        cv.alpha_composite(I.amul(nm, extra_a))
        return cv

    cover = card(C0).convert("RGB")
    HOLD, OUTZ, FLY, INZ, DIVE, SEG, BACK = 6, 16, 40, 16, 12, 40, 20
    T1 = HOLD + OUTZ
    T2 = T1 + FLY
    T3 = T2 + INZ
    T4 = T3 + DIVE
    S = len(films)
    T5 = T4 + SEG * S
    N_ = T5 + BACK
    P_ist = None
    frames = []
    for i in range(N_):
        if i < HOLD:
            frames.append(cover.resize((OW, OH), Image.LANCZOS))
            continue
        if i < T4:
            if i < T1:      # pull back until Istanbul is in view
                u = ease((i - HOLD) / OUTZ)
                cam = lerp_cam(C0, C1, u)
                cv = card(cam, extra_a=1 - ease(u * 2), home_a=u)
                q = 0.0
            elif i < T2:    # the flight
                cam = C1
                cv, _ = draw_map(cam, isos, cols, home_a=1.0)
                q = ease((i - T1) / FLY)
            elif i < T3:    # follow it down
                u = ease((i - T2) / INZ)
                cam = lerp_cam(C1, C0, u)
                cv, _ = draw_map(cam, isos, cols, home_a=1 - u)
                q = 1.0
            else:           # dive into the country: the film comes up through it
                u = ease((i - T3) / DIVE)
                cam = lerp_cam(C0, C2, u)
                cv, dmask = draw_map(cam, isos, cols)
                film = I.zoomed(reals[0], 0.01).convert("RGBA")
                film.putalpha(dmask.point(lambda v: round(v * min(1.0, u * 1.6))))
                cv.alpha_composite(film)
                full = I.zoomed(reals[0], 0.01)
                cv = Image.blend(cv.convert("RGB"), full, ease((u - 0.5) / 0.5)).convert("RGBA")
                q = None
            if q is not None and i >= T1:
                P = proj(cam)
                pts = [P(*p) for p in route]
                n = max(2, int(len(pts) * q))
                trail = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                td = ImageDraw.Draw(trail)
                for j in range(0, n - 1, 3):  # dashed trail
                    td.line([pts[j], pts[min(j + 2, n - 1)]], fill=(255, 255, 255, 200), width=3)
                for (x, y), r in ((P(*IST), 7), (P(alon, alat), 7)):
                    td.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))
                    td.ellipse((x - 2.5 * r, y - 2.5 * r, x + 2.5 * r, y + 2.5 * r), outline=(255, 255, 255, 120), width=2)
                cv.alpha_composite(trail)
                if q < 1:
                    a_, b_ = pts[max(0, n - 2)], pts[min(len(pts) - 1, n)]
                    ang = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
                    pl = plane(14, ang)
                    x, y = pts[n - 1]
                    cv.alpha_composite(pl, (round(x - pl.width / 2), round(y - pl.height / 2)))
                cv.alpha_composite(board(code, ease((i - T1) / 8)))
            elif i >= T3:
                cv.alpha_composite(board(code, 1.0))
        elif i < T5:
            kf, t = divmod(i - T4, SEG)
            pic = I.zoomed(reals[kf], 0.01 + 0.05 * t / SEG)
            if kf > 0 and t < 8:
                pic = Image.blend(I.zoomed(reals[kf - 1], 0.06), pic, ease(t / 8))
            cv = pic.convert("RGBA")
            cv.alpha_composite(fall_)
            cv.alpha_composite(board(code))
            f, x, y = flag_layer(0.42, 40 + 50, 64, t=i, amp=5)
            if f is not None:
                cv.alpha_composite(f, (x, y))
            la = ease((t - 2) / 6) if t < 8 else (1 - ease((t - (SEG - 5)) / 5) if t >= SEG - 5 else 1.0)
            cv.alpha_composite(I.amul(labels[kf], la))
        else:               # back to the card
            u = ease((i - T5) / BACK)
            base = card(C0, extra_a=ease((u - 0.3) / 0.7)).convert("RGB")
            cv = Image.blend(I.zoomed(reals[-1], 0.06), base, u).convert("RGBA")
            cv.alpha_composite(I.amul(board(code), 1 - u))
        frames.append(cv.convert("RGB").resize((OW, OH), Image.LANCZOS))
    I.save_reel(frames, cover, folder, out, "-b")
    return [f"{t} ({y})" for t, y, _ in films]


if __name__ == "__main__":
    out = sys.argv[1]
    bad = False
    for fo in sys.argv[2:] or ROUTES:
        try:
            print("built", fo, "·", ", ".join(build(fo, out)), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("FAILED", fo, e)
            bad = True
    sys.exit(1 if bad else 0)
