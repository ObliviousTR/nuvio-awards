"""MCU card, as the Marvel Studios ident: the logo stays on screen and the films play inside its letters.
Two layouts:
  studios  - the Marvel Studios logo (official SVG), CINEMATIC UNIVERSE and THE COLLECTION under it; the films flip
             inside the MARVEL letters of the red box.
  universe - the framed "Marvel Studios Cinematic Universe" box of the phase box sets: the small Marvel Studios logo
             on the frame, CINEMATIC UNIVERSE inside it, THE COLLECTION on the bottom bar where the phase name goes;
             the films flip inside CINEMATIC UNIVERSE.
Hover (10 s): the white letters turn like a page into the first film, and from there the films (one still each, in
release order) flip through the letters like the pages of a comic, slowly at first and faster and faster, while the
camera eases in a little; the last page turns back to white, the letters flash and a light sweep runs over the logo.
The logo never leaves the screen. First frame = last frame = cover.
usage: python3 art_tools/mcu_ident.py SRC_DIR OUT_DIR --layout studios|universe [--frames a,b] [--scale s] [--mp4 p]
  SRC_DIR: marvel-studios.svg, Oswald-VF.ttf, stills/NN_*.jpg (one official backdrop per film, release order)
"""
import glob, io, math, os, re, sys
import numpy as np
import cv2
import cairosvg
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

GW, GH, MS, N = 512, 288, 40, 250
RED = np.array([229, 11, 20], np.float32)
T_FLIPS = (16, 196)          # first page turn .. last page turn (back to white)
T_FLASH = 198
T_SWEEP = (200, 232)
T_ZOOM = (14, 236)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab; return smooth((k - a) / max(1, b - a))


def svg_masks(path, width):
    """the Marvel Studios SVG at a given width: masks of the red box, the MARVEL letters and STUDIOS + rules"""
    svg = open(path).read()
    svg = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r"\1", svg, count=1)
    svg = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r"\1", svg, count=1)

    def variant(keep):
        m = {"#e50b14": "none", "#ffffff": "none", "#000000": "none"}; m.update(keep)
        return re.sub(r"fill:(#[0-9a-fA-F]{6})", lambda g: "fill:" + m.get(g.group(1).lower(), "none"), svg)
    out = {}
    for name, keep in (("letters", {"#ffffff": "#ffffff", "#e50b14": "#000000"}),
                       ("box", {"#e50b14": "#ffffff", "#ffffff": "#000000"}),
                       ("studios", {"#000000": "#ffffff"})):
        png = cairosvg.svg2png(bytestring=variant(keep).encode(), output_width=width * 2, background_color="black")
        a = np.asarray(Image.open(io.BytesIO(png)).convert("L"), np.float32) / 255
        h = a.shape[0] // 2 * 2
        out[name] = a[:h].reshape(h // 2, 2, width, 2).mean((1, 3))
    return out


def text_mask(text, font, wght, size, track):
    f = ImageFont.truetype(font, size * 2)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    ws = [f.getlength(c) for c in text]
    im = Image.new("L", (round(sum(ws) + track * 2 * len(text)) + 40, size * 3), 0)
    d = ImageDraw.Draw(im); x = 20
    for c, w in zip(text, ws):
        d.text((x, size * 2.4), c, font=f, fill=255, anchor="ls"); x += w + track * 2
    im = im.crop(im.getbbox())
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


class Scene:
    def __init__(self, src, layout, sc=1.0):
        W, H = self.W, self.H = round(1280 * sc), round(720 * sc)
        self.sc = sc
        z = lambda: np.zeros((H, W), np.float32)
        self.red, self.white, self.fill = z(), z(), z()
        osw = os.path.join(src, "Oswald-VF.ttf")

        def put(dst, m, x, y):
            x, y = int(round(x)), int(round(y)); h, w = m.shape
            dst[y:y + h, x:x + w] = np.maximum(dst[y:y + h, x:x + w], m)
        if layout == "studios":
            lw = round(900 * sc)
            m = svg_masks(os.path.join(src, "marvel-studios.svg"), lw)
            lh = m["box"].shape[0]; x0, y0 = (W - lw) / 2, round(282 * sc) - lh / 2
            put(self.red, m["box"], x0, y0); put(self.fill, m["letters"], x0, y0); put(self.white, m["studios"], x0, y0)
            t1 = text_mask("CINEMATIC UNIVERSE", osw, 500, round(40 * sc), round(13 * sc))
            t2 = text_mask("THE COLLECTION", osw, 400, round(22 * sc), round(15 * sc))
            y1 = y0 + lh + round(38 * sc)
            put(self.white, t1, (W - t1.shape[1]) / 2, y1)
            put(self.white, t2 * 0.82, (W - t2.shape[1]) / 2, y1 + t1.shape[0] + round(24 * sc))
            self.sweep_mask = np.maximum(self.red, self.white * 0.4)
        else:
            big = text_mask("CINEMATIC UNIVERSE", osw, 600, round(118 * sc), round(1 * sc))
            bw, bh = big.shape[1], big.shape[0]
            bx, by = (W - bw) / 2, round(330 * sc) - bh / 2
            put(self.fill, big, bx, by)
            # the frame: chamfered box round the big letters, broken at the top for the logo and at the bottom bar
            padx, pady, ch, lwid = round(34 * sc), round(40 * sc), round(34 * sc), max(2, round(6 * sc))
            L, R, T, B = bx - padx, bx + bw + padx, by - pady, by + bh + pady
            lw_ = round(300 * sc)
            m = svg_masks(os.path.join(src, "marvel-studios.svg"), lw_)
            mh = m["box"].shape[0]
            put(self.red, m["box"], (W - lw_) / 2, T - mh / 2); put(self.white, m["letters"], (W - lw_) / 2, T - mh / 2)
            put(self.white, m["studios"], (W - lw_) / 2, T - mh / 2)
            sub = text_mask("THE COLLECTION", osw, 700, round(30 * sc), round(16 * sc))
            sw_, sh_ = sub.shape[1], sub.shape[0]
            put(self.white, sub, (W - sw_) / 2, B - sh_ / 2)
            fr = Image.new("L", (W * 4, H * 4), 0); d = ImageDraw.Draw(fr)
            gt = (lw_ / 2 + round(22 * sc)); gb = (sw_ / 2 + round(26 * sc)); cx = W / 2
            pts = [(cx + gt, T), (R - ch, T), (R, T + ch), (R, B - ch), (R - ch, B), (cx + gb, B)]
            pts2 = [(cx - gb, B), (L + ch, B), (L, B - ch), (L, T + ch), (L + ch, T), (cx - gt, T)]
            for p in (pts, pts2):
                d.line([(x * 4, y * 4) for x, y in p], fill=255, width=lwid * 4, joint="curve")
            # the bottom bar: short rules either side of the name, like the phase box sets
            for s in (-1, 1):
                d.line([((cx + s * (gb - round(8 * sc))) * 4, B * 4), ((cx + s * (gb - round(8 * sc))) * 4, B * 4)], fill=255, width=lwid * 4)
            fr = np.asarray(fr.resize((W, H), Image.LANCZOS), np.float32) / 255
            self.white = np.maximum(self.white, fr)
            self.sweep_mask = np.maximum(self.white, self.fill) * 0.6 + self.red
        ys, xs = np.nonzero(self.fill > 0.5)
        self.fx0, self.fx1, self.fy0, self.fy1 = xs.min(), xs.max(), ys.min(), ys.max()
        self.stills = []
        for f in sorted(glob.glob(os.path.join(src, "stills", "*.jpg"))):
            im = Image.open(f).convert("RGB")
            k = max(W / im.width, H / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            self.stills.append(np.asarray(im.crop((x0, y0, x0 + W, y0 + H))))
        n = len(self.stills)
        # page turns: white -> film 1 -> ... -> film n -> white, slow first, faster and faster
        u = (np.arange(n + 1) / n) ** 0.62
        self.turns = T_FLIPS[0] + (T_FLIPS[1] - T_FLIPS[0]) * u
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((self.xx - W / 2) / W * 1.5) ** 2 + ((self.yy - H * 0.45) / H * 1.9) ** 2)
        self.bg = 7 + np.exp(-(d / 0.42) ** 2)[..., None] * np.array([26, 5, 6], np.float32)

    def page(self, i):
        if i < 0 or i >= len(self.stills):
            return None
        return self.stills[i].astype(np.float32) * 0.92

    def frame(self, k):
        W, H, sc = self.W, self.H, self.sc
        img = self.bg.copy()
        # which page is in the letters, and how far the next one has turned
        j = int(np.searchsorted(self.turns, k, side="right"))       # turns done
        cur = j - 1                                                  # page index shown (-1 = white)
        white = np.full((H, W, 3), 246, np.float32)
        a = self.page(cur); a = white if a is None else a
        fill = a
        if j < len(self.turns):
            t0 = self.turns[j]
            dur = min(7.0, (self.turns[j] - (self.turns[j - 1] if j > 0 else t0 - 7)) * 0.9)
            p = (k - (t0 - dur)) / dur
            if 0 < p < 1:
                b = self.page(j); b = white if b is None else b
                # a page turning right to left across the letters, with a lit edge and a shadow on the old page
                e = self.fx1 - (self.fx1 - self.fx0 + 60 * sc) * smooth(p) + (self.yy - (self.fy0 + self.fy1) / 2) * 0.18
                side = np.clip((self.xx - e) / (1.5 * sc) + 0.5, 0, 1)[..., None]
                shade = (1 - 0.45 * np.exp(-np.clip(e - self.xx, 0, None) / (40 * sc)))[..., None]
                fill = a * shade * (1 - side) + b * side
                edge = np.exp(-((self.xx - e) / (2.5 * sc)) ** 2)[..., None]
                fill = fill + edge * 120
        flash = math.exp(-((k - T_FLASH) / 4.0) ** 2)
        sw = seg(k, T_SWEEP)
        band = 0
        if 0 < sw < 1:
            sx = -0.3 * W + 1.6 * W * sw
            band = np.exp(-(((self.xx - sx) + (self.yy - H / 2) * 0.4) / (40 * sc)) ** 2)[..., None]
        red = RED * (1.06 - 0.12 * np.clip((self.yy - H * 0.3) / (H * 0.3), 0, 1))[..., None]
        red = red + band * np.array([255, 170, 160], np.float32) * 0.5 * self.sweep_mask[..., None]
        img = img * (1 - self.red[..., None]) + red * self.red[..., None]
        fill = fill + flash * 90 + band * 40
        img = img * (1 - self.fill[..., None]) + fill * self.fill[..., None]
        wcol = white + band * 9 + flash * 8
        img = img * (1 - self.white[..., None]) + wcol * self.white[..., None]
        # a faint red glow from the letters while the films play
        play = seg(k, (T_FLIPS[0], T_FLIPS[0] + 20)) * (1 - seg(k, (T_FLIPS[1] - 10, T_FLIPS[1] + 6)))
        if play > 0:
            g = cv2.GaussianBlur(self.fill, (0, 0), 30 * sc)[..., None]
            img += g * np.array([90, 20, 20], np.float32) * play
        # camera eases in a little and back
        zs = 1 + 0.06 * math.sin(math.pi * seg(k, T_ZOOM))
        img = np.clip(img, 0, 255).astype(np.uint8)
        if zs > 1.0005:
            M = np.array([[zs, 0, W / 2 * (1 - zs)], [0, zs, H / 2 * (1 - zs)]], np.float32)
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return Image.fromarray(img)


def render(src, out, layout, only=None, sc=1.0, mp4=None):
    s = Scene(src, layout, sc)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            s.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [s.frame(k) for k in range(N)]
    if mp4:
        import subprocess
        p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{s.W}x{s.H}",
                              "-r", "25", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", mp4], stdin=subprocess.PIPE)
        for _ in range(2):
            for f in frames:
                p.stdin.write(f.tobytes())
        p.stdin.close(); p.wait()
    if sc == 1.0:
        frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
        encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
        print("kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2))


if __name__ == "__main__":
    a = sys.argv
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    sc = float(a[a.index("--scale") + 1]) if "--scale" in a else 1.0
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], a[a.index("--layout") + 1], only, sc, mp4)
