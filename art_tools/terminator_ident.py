"""Terminator card. The 1984 THE TERMINATOR title (blue-silver metal, TMDB) and two things only this series has.

--mode vision  Termovision: the T-800's red sight from The Terminator (1984), its readouts Apple II 6502 listings. The
               cover is the 1984 title card; the view drops into the machine's sight: red, the scan lines of its video,
               the listing running down the side, an analysis column; a target frame finds the title, a scan passes
               over it, it locks and reads MATCH, the sight zooms a step; it lets go and the cover is back.
--mode liquid  The T-1000's mimetic polyalloy (Terminator 2): the title is liquid metal. Shots hit it; each opens a crater
               in the metal like a flower, the chrome mirroring its surroundings into it, and the metal flows shut again
               with a ripple; a single round, then a burst of three, then five; the title is whole again on the cover.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/terminator_ident.py SRC_DIR OUT_DIR [--mode vision|liquid] [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png (TMDB logo 6hBVMofGYDOC20yYiQeOnuHmK9d, film 218), Michroma-Regular.ttf, MPLUS1Code.ttf
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def smooth(x):
    x = np.clip(x, 0.0, 1.0); return x * x * (3 - 2 * x)


def seg(k, a, b):
    return float(smooth((k - a) / (b - a)))


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0.05 else a


def bigblur(a, s):
    h, w = a.shape[:2]
    sm = cv2.resize(a, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), s / 4)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)


def noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    spec = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** beta; spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w))
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


def spaced(font, size, txt, track):
    f = ImageFont.truetype(font, size)
    m = Image.new("L", (round(sum(f.getlength(c) for c in txt) + track * len(txt)) + 40, size * 2), 0)
    d = ImageDraw.Draw(m); x = 20
    for c in txt:
        d.text((x, size * 1.5), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + track
    m = m.crop(m.getbbox())
    return np.asarray(m.resize((m.width // 2, m.height // 2), Image.LANCZOS), np.float32) / 255


def to_image(img, k, grain, amt=0.03):
    gx = (k * 37) % W; gy = (k * 53) % H
    img = img + (grain[gy:gy + H, gx:gx + W] - 0.5)[..., None] * amt
    return Image.fromarray(np.clip(img * 255, 0, 255).astype("uint8"), "RGB")


class Card:
    """the 1984 title card: the metal title on deep blue-black, THE COLLECTION under it"""

    def __init__(self, src, lw=1000, top=268):
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA")
        lh = round(lg.height * lw / lg.width)
        lg = np.asarray(lg.resize((lw, lh), Image.LANCZOS), np.float32) / 255
        self.x0 = (W - lw) // 2; self.top = top; self.lw, self.lh = lw, lh
        self.a = np.zeros((H, W), np.float32); self.rgb = np.zeros((H, W, 3), np.float32)
        self.a[top:top + lh, self.x0:self.x0 + lw] = lg[..., 3]; self.rgb[top:top + lh, self.x0:self.x0 + lw] = lg[..., :3]
        col = spaced(os.path.join(src, "Michroma-Regular.ttf"), 30, "THE COLLECTION", 15)
        self.col = np.zeros((H, W), np.float32)
        cy = top + lh + 40; cx = (W - col.shape[1]) // 2
        self.col[cy:cy + col.shape[0], cx:cx + col.shape[1]] = col
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        r = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2)
        self.bg = (np.clip(1 - r, 0, 1) ** 1.5)[..., None] * np.array([0.03, 0.05, 0.12], np.float32) + np.array([0.004, 0.006, 0.012], np.float32)

    def compose(self, face=None, alpha=None):
        a = self.a if alpha is None else alpha
        f = self.rgb if face is None else face
        img = self.bg * (1 - a[..., None]) + f * a[..., None]
        img = img * (1 - self.col[..., None]) + np.array([0.70, 0.76, 0.88], np.float32) * self.col[..., None]
        return img


# --------------------------------------------------------------------------------------------------------- vision
def listing(n, seed=3):
    """an Apple II style 6502 listing: address, bytes, mnemonic (real opcodes and encodings)"""
    rng = np.random.default_rng(seed)
    ops = [("LDA #$%02X", 0xA9, 1), ("STA $%04X", 0x8D, 2), ("LDX #$%02X", 0xA2, 1), ("JSR $%04X", 0x20, 2),
           ("LDA $%04X,X", 0xBD, 2), ("CMP #$%02X", 0xC9, 1), ("BNE $%04X", 0xD0, 1), ("INX", 0xE8, 0), ("DEY", 0x88, 0),
           ("STA $%02X", 0x85, 1), ("LDY #$%02X", 0xA0, 1), ("RTS", 0x60, 0), ("CLC", 0x18, 0), ("ADC #$%02X", 0x69, 1),
           ("BEQ $%04X", 0xF0, 1), ("JMP $%04X", 0x4C, 2), ("ORA $%02X", 0x05, 1), ("AND #$%02X", 0x29, 1)]
    addr = 0x0300; out = []
    for _ in range(n):
        m, op, nb = ops[rng.integers(len(ops))]
        if nb == 0:
            b = [op]; txt = m
        elif nb == 1:
            v = int(rng.integers(256)); b = [op, v]
            txt = m % ((addr + 2 + (v - 256 if v > 127 else v)) & 0xFFFF) if "B" == m[0] and m[1] in "NE" else m % v
        else:
            v = int(rng.integers(0x0200, 0xFFFF)); b = [op, v & 0xFF, v >> 8]; txt = m % v
        out.append(f"{addr:04X}-   {' '.join(f'{x:02X}' for x in b):<9} {txt}")
        addr += len(b)
    return out


def text_block(lines, font, size, width, lh):
    im = Image.new("L", (width * 2, (len(lines) * lh + 10) * 2), 0); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font, size * 2)
    for i, l in enumerate(lines):
        d.text((0, i * lh * 2), l, font=f, fill=255)
    return np.asarray(im.resize((width, len(lines) * lh + 10), Image.LANCZOS), np.float32) / 255


class Vision:
    def __init__(self, src):
        self.c = Card(src)
        mono = os.path.join(src, "MPLUS1Code.ttf")
        self.code = text_block(listing(160), mono, 11, 300, 15)
        ana = ["ANALYSIS:", "", "CONTOUR  MAPPING", "PROFILE  1984-T", "", "SCAN  MODE  43984", "SIZE  ASSESSMENT",
               "ASSESSMENT  COMPLETE", "", "FIT  PROBABILITY  0.99", "", "RESET  TO  ACQUISITION", "MODE  SPEECH  LEVEL  78"]
        self.ana = text_block(ana, mono, 13, 300, 18)
        self.match = text_block(["MATCH"], mono, 22, 120, 26)
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        self.scan = (0.86 + 0.14 * (np.arange(H) % 3 != 0)).astype(np.float32)[:, None]

    def reticle(self, k):
        """the target frame: hunts, then locks on the title"""
        c = self.c
        tx, ty, tw, th = c.x0 - 18, c.top - 22, c.lw + 36, c.lh + 44
        u = seg(k, 34, 82)
        wob = (1 - u)
        x = tx + wob * (260 * math.sin(k * 0.11) - 120); y = ty + wob * (110 * math.cos(k * 0.13) + 60)
        w = tw * (0.45 + 0.55 * u); h = th * (0.7 + 0.3 * u)
        return x, y, w, h, u

    def frame(self, k):
        k = k % N
        c = self.c
        on = seg(k, 6, 12) * (1 - seg(k, 198, 212))
        zoom = 1.0 + 0.07 * seg(k, 98, 102) * (1 - seg(k, 186, 196))
        img = c.compose()
        if on <= 0.001:
            return to_image(img, k, self.grain)
        if zoom > 1.0005:
            M = cv2.getRotationMatrix2D((W / 2, c.top + c.lh / 2), 0, zoom)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        lum = (img * np.array([0.3, 0.5, 0.2], np.float32)).sum(2)
        lum = np.clip(lum * 1.5 + 0.05, 0, 1)
        red = np.dstack([lum ** 0.8, lum ** 2.4 * 0.55, lum ** 2.6 * 0.5]) * self.scan[..., None]
        red += bigblur(red, 18) * 0.25
        # overlays: listing scrolling on the left, analysis on the right, the target frame
        ov = np.zeros((H, W), np.float32)
        off = int((k * 4) % (self.code.shape[0] - 200))
        blk = self.code[off:off + 190]
        ov[38:38 + blk.shape[0], 40:40 + blk.shape[1]] = np.maximum(ov[38:38 + blk.shape[0], 40:40 + blk.shape[1]], blk * 0.85)
        off2 = int((k * 3 + 700) % (self.code.shape[0] - 200))
        blk2 = self.code[off2:off2 + 150]
        ov[540:540 + blk2.shape[0], 40:40 + blk2.shape[1]] = np.maximum(ov[540:540 + blk2.shape[0], 40:40 + blk2.shape[1]], blk2 * 0.6)
        nl = int(np.clip((k - 20) / 4, 0, 13))
        if nl > 0:
            a = self.ana[:nl * 18 + 6]
            ov[38:38 + a.shape[0], 960:960 + a.shape[1]] = np.maximum(ov[38:38 + a.shape[0], 960:960 + a.shape[1]], a)
        x, y, w, h, u = self.reticle(k)
        rm = np.zeros((H, W), np.uint8); L = int(26 + 20 * u)
        pts = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
        for (px, py), (sx, sy) in zip(pts, [(1, 1), (-1, 1), (1, -1), (-1, -1)]):
            px, py = int(px), int(py)
            cv2.line(rm, (px, py), (px + sx * L, py), 255, 2, cv2.LINE_AA); cv2.line(rm, (px, py), (px, py + sy * L), 255, 2, cv2.LINE_AA)
        cxr, cyr = int(x + w / 2), int(y + h / 2)
        cv2.line(rm, (cxr - 12, cyr), (cxr + 12, cyr), 160, 1, cv2.LINE_AA); cv2.line(rm, (cxr, cyr - 12), (cxr, cyr + 12), 160, 1, cv2.LINE_AA)
        ov = np.maximum(ov, rm.astype(np.float32) / 255)
        # a scan passes over the title before the lock
        sp = (k - 84) / 14.0
        if 0 <= sp <= 1:
            sy = c.top - 20 + sp * (c.lh + 40)
            band = np.exp(-((c.yy - sy) / 3.0) ** 2) * (np.abs(c.xx - W / 2) < c.lw / 2 + 20)
            ov = np.maximum(ov, band * 0.9)
        if 102 <= k < 190 and ((k - 102) // 6) % 2 == 0 or 110 <= k < 190:
            mx, my = int(W / 2 - 50), int(y - 44)
            if 0 <= mx < W - 130 and my > 0:
                m = self.match; ov[my:my + m.shape[0], mx:mx + m.shape[1]] = np.maximum(ov[my:my + m.shape[0], mx:mx + m.shape[1]], m)
        ovc = ov[..., None] * np.array([1.0, 0.86, 0.84], np.float32)
        vis = red * (1 - ov[..., None] * 0.6) + ovc * 0.95
        img = img * (1 - on) + vis * on
        return to_image(img, k, self.grain, 0.05 * on + 0.03)


# --------------------------------------------------------------------------------------------------------- liquid
# hits: (frame, [(x offset along the title 0..1, y 0..1 within the TERMINATOR line), ...])
HITS = [(26, [(0.30, 0.55)]),
        (78, [(0.55, 0.45), (0.63, 0.66), (0.58, 0.30)]),
        (132, [(0.12, 0.52), (0.19, 0.30), (0.81, 0.58), (0.88, 0.40), (0.74, 0.70)])]
OPEN, HEAL = 4, 34


class Liquid:
    def __init__(self, src):
        self.c = c = Card(src)
        solid = (c.a > 0.85).astype(np.uint8)
        dist = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
        self.bevel = blur(np.clip(dist / 6.0, 0, 1), 1.0)
        # the room the metal mirrors: dark, a warm light low (the mill), a cold one high
        ey, ex = np.mgrid[0:H, 0:W].astype(np.float32)
        env = np.zeros((H, W, 3), np.float32) + np.array([0.02, 0.03, 0.05], np.float32)
        env += (np.exp(-(((ex - 300) / 260) ** 2 + ((ey - 700) / 160) ** 2)))[..., None] * np.array([1.0, 0.55, 0.22], np.float32) * 1.3
        env += (np.exp(-(((ex - 960) / 420) ** 2 + ((ey - 60) / 140) ** 2)))[..., None] * np.array([0.6, 0.75, 1.0], np.float32) * 1.1
        env += (np.exp(-(((ey - 300) / 30) ** 2)))[..., None] * np.array([0.5, 0.55, 0.6], np.float32) * 0.5   # a horizon line
        for (bx, by, bw, bh) in [(380, 150, 60, 26), (640, 120, 110, 20), (900, 170, 50, 30), (640, 520, 300, 14)]:
            env += (np.exp(-(((ex - bx) / bw) ** 4 + ((ey - by) / bh) ** 4)))[..., None] * np.array([1.0, 1.0, 1.0], np.float32) * 1.6
        self.env = blur(env, 6)
        # the hits on the TERMINATOR line (the lower 62 % of the title)
        self.holes = []
        rng = np.random.default_rng(11)
        line_top = c.top + c.lh * 0.38; line_h = c.lh * 0.6
        for k0, pts in HITS:
            for j, (u, v) in enumerate(pts):
                x = c.x0 + u * c.lw; y = line_top + v * line_h
                # move onto metal if it landed in a gap
                yy0, xx0 = int(y), int(x)
                best = None
                deep = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
                for r in range(0, 60, 2):
                    for t in np.linspace(0, 2 * math.pi, 24, endpoint=False):
                        px, py = int(xx0 + r * math.cos(t)), int(yy0 + r * math.sin(t))
                        if deep[py, px] >= 7.5:
                            best = (px, py); break
                    if best:
                        break
                if best:
                    self.holes.append((k0 + j * 2, best[0], best[1], float(rng.uniform(8.5, 10.5)), float(rng.uniform(0, 6.28))))
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        self.recoil = [k0 for k0, _ in HITS]

    def height(self, k):
        h = self.bevel * 2.0
        dmax = np.zeros((H, W), np.float32); pierce = np.zeros((H, W), np.float32); splash = np.zeros((H, W), np.float32)
        for k0, x, y, R, rot in self.holes:
            t = k - k0
            if t < 0 or t > OPEN + HEAL + 12:
                continue
            if t <= OPEN:
                s = smooth(t / OPEN); r = R * (0.4 + 0.6 * s); depth = 3.2 * s; rim = 1.2 * s; rip = 0.0
            else:
                u = (t - OPEN) / HEAL
                s = 1 - smooth(u); r = R * (0.35 + 0.65 * s); depth = 3.2 * s; rim = 1.2 * s
                rip = 0.5 * math.exp(-u * 3) * math.sin(u * 18) * (1 - smooth(u))
            x0, x1 = int(max(0, x - 3 * R)), int(min(W, x + 3 * R)); y0, y1 = int(max(0, y - 3 * R)), int(min(H, y + 3 * R))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dx, dy = xx - x, yy - y
            rr = np.sqrt(dx * dx + dy * dy); th = np.arctan2(dy, dx)
            petals = 1 + 0.28 * np.cos(6 * th + rot) + 0.12 * np.cos(11 * th + rot * 2)
            crater = -depth * np.exp(-(rr / (r * 0.75)) ** 2)
            ring = rim * petals * np.exp(-((rr - r) / (r * 0.28)) ** 2)
            wave = rip * np.sin(rr / (R * 0.35)) * np.exp(-(rr / (2.2 * R)) ** 2)
            h[y0:y1, x0:x1] += crater + ring + wave
            # the hole goes through the metal; its lips curl out past the letter like petals
            hole_r = r * 0.5 * s
            pierce[y0:y1, x0:x1] = np.maximum(pierce[y0:y1, x0:x1], smooth((hole_r - rr * (1 + 0.15 * np.cos(6 * th + rot))) / 1.5))
            lip = smooth((r * 1.12 * petals - rr) / 1.5) * smooth((rr - hole_r) / 1.5) * s
            splash[y0:y1, x0:x1] = np.maximum(splash[y0:y1, x0:x1], lip)
            # the blow runs through the metal: a ripple out along the letters
            if t > 0:
                rr2 = np.sqrt((self.c.xx - x) ** 2 + (self.c.yy - y) ** 2)
                front = 11.0 * t
                h += 0.9 * math.exp(-t / 16) * np.sin((rr2 - front) / 7) * np.exp(-((rr2 - front) / 40) ** 2) * self.bevel
            dmax[y0:y1, x0:x1] = np.maximum(dmax[y0:y1, x0:x1], depth / 3.2 * np.exp(-(rr / (r * 0.6)) ** 2))
        return h, dmax, pierce, splash

    def frame(self, k):
        k = k % N
        c = self.c
        h, dmax, pierce, splash = self.height(k)
        nx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3); ny = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
        # chrome: what the surface mirrors, looked up along its normal
        mx = c.xx + nx * 70; my = c.yy + ny * 70
        refl = cv2.remap(self.env, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        tilt = np.clip(np.sqrt(nx * nx + ny * ny) / 3.0, 0, 1)[..., None]
        face = c.rgb * (1 - 0.6 * tilt) + refl * (0.35 + 0.9 * tilt)
        face *= (1 - 0.45 * dmax)[..., None]                             # deep in a crater it is dark
        alpha = np.clip(np.maximum(c.a, splash) * (1 - pierce), 0, 1)
        face = np.where((splash > c.a)[..., None], refl * 1.1 + 0.05, face)
        img = c.compose(face=face, alpha=alpha)
        z = 1.0 + 0.16 * seg(k, 14, 40) * (1 - seg(k, 172, 214))          # the camera moves in on the metal
        if z > 1.0005:
            M = cv2.getRotationMatrix2D((W / 2, c.top + c.lh / 2), 0, z)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        # the title staggers a little with each hit
        sx = 0.0
        for k0 in self.recoil:
            t = k - k0
            if 0 <= t < 14:
                sx += 4.0 * math.exp(-t / 3.0) * math.cos(t * 1.4)
        if abs(sx) > 0.02:
            img = cv2.warpAffine(img, np.float32([[1, 0, sx], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        img = img / (1 + 0.25 * img) * 1.25
        return to_image(img, k, self.grain)


def render(src, out, mode, only=None, mp4=None):
    s = Vision(src) if mode == "vision" else Liquid(src)
    os.makedirs(out, exist_ok=True)
    if only:
        for k in only:
            s.frame(k).save(os.path.join(out, f"f{k:03d}.jpg"), quality=90)
        return
    frames = [s.frame(k) for k in range(N)]
    if mp4:
        p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", "25", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", mp4],
                             stdin=subprocess.PIPE)
        for _ in range(2):
            for f in frames:
                p.stdin.write(f.tobytes())
        p.stdin.close(); p.wait()
    frames[0].save(os.path.join(out, "cover.jpg"), quality=92)
    encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=72)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2), "kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)


if __name__ == "__main__":
    a = sys.argv
    mode = a[a.index("--mode") + 1] if "--mode" in a else "vision"
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], mode, only, mp4)
