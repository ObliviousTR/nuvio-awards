"""X-Men card, as a title ident after the X-Men (2000) opening: the steel X-MEN title on a deep navy dark, a faint
Cerebro web of nerve fibres behind it, THE COLLECTION in wide steel letters below.
Hover (10 s): Cerebro switches on - the fibres light up ice blue and pulses race along them towards the title, the
points of every mind on Cerebro's map blink on around it and a cold core of light swells behind the letters. The title
opens along its middle, a DNA double helix turns through the gap, the halves clamp shut on it with a flash and a
light sweep runs across the steel; Cerebro powers down and the card settles on the cover. The title never leaves the screen.
First frame = last frame = cover: everything that moves is switched off at both ends (pulses run a whole number of
laps over the loop anyway).
usage: python3 art_tools/xmen_cerebro.py SRC_DIR OUT_DIR [--frames a,b,...] [--scale s] [--mp4 path]
  SRC_DIR: logo.png (X-Men 2000 title logo, TMDB film 36657), Michroma-Regular.ttf
"""
import math, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

GW, GH, MS, N = 512, 288, 40, 250
T_ON = (14, 70)            # Cerebro powers up
T_OFF = (186, 232)         # ... and down
T_OPEN = (100, 120)        # the title opens along its middle
T_SHUT = (166, 176)        # ... and clamps shut
T_SWEEP = (172, 204)       # light sweep across the steel
NAVY = np.array([6, 10, 20], np.float32)
ICE = np.array([150, 215, 255], np.float32)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(k, ab):
    a, b = ab; return smooth((k - a) / max(1, b - a))


def pnoise(h, w, beta, seed):
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    fq = np.sqrt(fx * fx + fy * fy); fq[0, 0] = 1
    sp = (r.normal(size=fq.shape) + 1j * r.normal(size=fq.shape)) / fq ** beta; sp[0, 0] = 0
    n = np.fft.irfft2(sp, s=(h, w)); return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


class Scene:
    def __init__(self, src, sc=1.0):
        self.sc = sc
        W, H = self.W, self.H = round(1280 * sc), round(720 * sc)
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        lg = Image.open(os.path.join(src, "logo.png")).convert("RGBA"); lg = lg.crop(lg.getbbox())
        LW = round(720 * sc); LH = round(lg.height * LW / lg.width)
        lg = lg.resize((LW, LH), Image.LANCZOS)
        self.lx, self.ly = (W - LW) // 2, round(300 * sc) - LH // 2
        a = np.asarray(lg, np.float32) / 255
        # the X is the first glyph: find it and its middle (narrowest column of the crossing)
        al = (a[..., 3] > 0.4).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(al)
        ix = 1 + int(np.argmin([s[0] for s in st[1:]]))
        x0, y0, w0, h0 = st[ix][:4]
        xm = (lab == ix)
        cols = xm.sum(0)
        mid = x0 + w0 // 2 - w0 // 6 + int(np.argmin(cols[x0 + w0 // 2 - w0 // 6: x0 + w0 // 2 + w0 // 6]))
        xmask = cv2.dilate(xm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        xmask[:, x0 + w0 + 3:] = 0
        self.xmid = self.lx + mid; self.xw = w0; self.xcy = self.ly + y0 + h0 / 2; self.xh = h0
        cut = LH // 2
        top = a.copy(); top[cut:, :, 3] = 0
        bot = a.copy(); bot[:cut, :, 3] = 0
        self.L = {"top": top, "bot": bot}
        self.lw, self.lh = LW, LH
        self.alpha_all = a[..., 3]
        # THE COLLECTION, wide steel letters
        f = ImageFont.truetype(os.path.join(src, "Michroma-Regular.ttf"), round(21 * sc) * 2)
        txt = "THE COLLECTION"; tr = round(13 * sc) * 2
        m = Image.new("L", (int(sum(f.getlength(c) for c in txt) + tr * len(txt)) + 40, round(21 * sc) * 4), 0)
        d = ImageDraw.Draw(m); x = 20
        for c in txt:
            d.text((x, round(21 * sc) * 3), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + tr
        m = m.crop(m.getbbox()); m = m.resize((m.width // 2, m.height // 2), Image.LANCZOS)
        g = np.linspace(232, 150, m.height)[:, None] * np.ones((1, m.width))
        self.sub = Image.merge("RGBA", (Image.fromarray(g.astype(np.uint8)), Image.fromarray((g * 1.04).clip(0, 255).astype(np.uint8)),
                                        Image.fromarray((g * 1.1).clip(0, 255).astype(np.uint8)), m))
        self.suby = self.ly + LH + round(34 * sc)
        # Cerebro web: ridged noise veins (static) + fibres converging on the title (with pulses)
        n1 = pnoise(H, W, 1.05, 3); n2 = pnoise(H, W, 1.3, 8); n3 = pnoise(H, W, 1.8, 5)
        self.veins = (np.clip(1 - np.abs(n1 - 0.5) * 14, 0, 1) ** 2 * 0.5 + np.clip(1 - np.abs(n2 - 0.5) * 10, 0, 1) ** 3 * 0.5) * (0.4 + 0.9 * n3)
        r = np.random.default_rng(12)
        cx, cy = W / 2, self.ly + LH / 2
        self.fibres = []
        for i in range(90):
            ang = r.uniform(0, 2 * math.pi)
            R0 = r.uniform(0.75, 1.05) * math.hypot(W, H) / 2
            sx, sy = cx + math.cos(ang) * R0, cy + math.sin(ang) * R0 * 0.75
            t = np.linspace(0, 1, 160)
            bend = r.uniform(-0.9, 0.9); wig = r.uniform(10, 40) * sc; fq = r.uniform(2, 5); ph = r.uniform(0, 6.3)
            ex, ey = cx + math.cos(ang) * r.uniform(60, 150) * sc, cy + math.sin(ang) * r.uniform(20, 50) * sc
            px = sx + (ex - sx) * t; py = sy + (ey - sy) * t
            nx, ny = -(ey - sy), (ex - sx); nl = math.hypot(nx, ny); nx /= nl; ny /= nl
            off = bend * np.sin(np.pi * t) * R0 * 0.35 + wig * np.sin(t * fq * 2 * np.pi + ph) * (1 - t)
            px += nx * off; py += ny * off
            self.fibres.append(dict(p=np.stack([px, py], -1), w=r.uniform(0.4, 1.1), laps=int(r.integers(2, 5)),
                                    ph=r.uniform(0, 1), br=r.uniform(0.25, 0.8)))
        fl = np.zeros((H * 2, W * 2), np.uint8)
        for fb in self.fibres:
            cv2.polylines(fl, [np.round(fb["p"] * 2 * 4).astype(np.int32)], False, int(140 * fb["br"]), max(1, round(fb["w"] * 2 * sc)), cv2.LINE_AA, 2)
        self.fib = cv2.resize(fl, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        self.fib_glow = cv2.GaussianBlur(self.fib, (0, 0), 6 * sc)
        # Cerebro's map: minds around the title
        k = 260
        ang = r.uniform(0, 2 * math.pi, k); rad = np.sqrt(r.uniform(0.05, 1, k))
        self.dots = np.stack([cx + np.cos(ang) * rad * W * 0.55, cy + np.sin(ang) * rad * H * 0.55], -1)
        self.dot_on = r.uniform(T_ON[0] + 10, T_ON[1] + 40, k); self.dot_sz = r.uniform(0.8, 2.2, k) * sc
        self.dot_bl = r.uniform(0, 6.3, k)
        self.core = np.exp(-(((self.xx - cx) / (W * 0.3)) ** 2 + ((self.yy - cy) / (H * 0.22)) ** 2))
        vg = np.sqrt(((self.xx - W / 2) / (W * 0.6)) ** 2 + ((self.yy - H / 2) / (H * 0.62)) ** 2)
        self.vig = (1 - 0.45 * np.clip(vg - 0.4, 0, 1) ** 1.3)
        self.cx, self.cy = cx, cy

    def helix(self, img, k, op):
        """A DNA double helix running through the opened title, left to right, turning."""
        sc = self.sc; H, W = self.H, self.W
        x0 = self.lx - 30 * sc; wid = self.lw + 60 * sc
        amp = self.lh * 0.25 * op
        lay = np.zeros((H * 2, W * 2), np.uint8); back = np.zeros((H * 2, W * 2), np.uint8)
        t = np.linspace(0, 1, 600); ph = -k * 0.13
        xs = x0 + t * wid
        taper = np.clip(np.sin(np.pi * t) * 1.6, 0, 1)
        for s_ in (0, math.pi):
            a = t * 5 * 2 * math.pi + ph + s_
            ys = self.cy + np.sin(a) * amp * taper
            front = np.cos(a) > 0
            P = np.round(np.stack([xs, ys], -1) * 8).astype(np.int32)
            for i in range(len(t) - 1):
                cv2.line(lay if front[i] else back, tuple(P[i]), tuple(P[i + 1]), 255, max(1, round(2.6 * sc * 2)), cv2.LINE_AA, 2)
        for j in range(0, len(t), 12):
            a = t[j] * 5 * 2 * math.pi + ph
            y1 = self.cy + math.sin(a) * amp * taper[j]; y2 = self.cy - math.sin(a) * amp * taper[j]
            cv2.line(back, (int(xs[j] * 8), int(y1 * 8)), (int(xs[j] * 8), int(y2 * 8)), 170, max(1, round(1.4 * sc * 2)), cv2.LINE_AA, 2)
        lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        back = cv2.resize(back, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        v = (lay + back * 0.5) * min(1.0, op * 1.5)
        img += cv2.GaussianBlur(v, (0, 0), 6 * sc)[..., None] * ICE * 1.5
        img += v[..., None] * np.array([215, 240, 255], np.float32)
        return img

    def frame(self, k):
        W, H, sc = self.W, self.H, self.sc
        on = seg(k, T_ON) * (1 - seg(k, T_OFF))
        img = np.zeros((H, W, 3), np.float32) + NAVY
        img += self.veins[..., None] * np.array([30, 60, 95], np.float32) * (0.25 + 0.75 * on)
        img += (self.fib * (0.18 + 0.82 * on))[..., None] * np.array([110, 170, 225], np.float32)
        img += (self.fib_glow * on)[..., None] * ICE * 0.5
        # pulses racing along the fibres to the title
        if on > 0.01:
            pl = np.zeros((H, W), np.float32)
            for fb in self.fibres:
                for j in range(1):
                    u = (k / N * fb["laps"] + fb["ph"] + j * 0.5) % 1.0
                    p = fb["p"]; i = int(u * (len(p) - 1)); i0 = max(0, i - 14)
                    seg_ = np.round(p[i0:i + 1]).astype(np.int32)
                    if len(seg_) > 1:
                        cv2.polylines(pl, [seg_], False, float(fb["br"]), max(1, round(1.6 * sc)), cv2.LINE_AA)
                    cv2.circle(pl, tuple(np.round(p[i]).astype(int)), max(1, round(2.2 * sc)), 1.4 * fb["br"], -1, cv2.LINE_AA)
            pl *= on
            img += cv2.GaussianBlur(pl, (0, 0), 4 * sc)[..., None] * ICE * 1.6 + pl[..., None] * np.array([200, 235, 255], np.float32)
        # minds on Cerebro's map
        dl = np.zeros((H, W), np.float32)
        for (x, y), t0, s, b in zip(self.dots, self.dot_on, self.dot_sz, self.dot_bl):
            v = smooth((k - t0) / 8) * (1 - seg(k, T_OFF)) * (0.6 + 0.4 * math.sin(k * 0.3 + b))
            if v > 0.02:
                cv2.circle(dl, (int(x), int(y)), max(1, int(round(s))), float(v), -1, cv2.LINE_AA)
        img += cv2.GaussianBlur(dl, (0, 0), 2.5 * sc)[..., None] * ICE * 1.2 + dl[..., None] * np.array([170, 210, 240], np.float32)
        # cold core behind the title: swells while Cerebro reads, flashes when the X shuts
        flash = math.exp(-((k - T_SHUT[1]) / 5.0) ** 2)
        img += (self.core * (0.55 * on + 0.9 * flash) * (0.85 + 0.15 * math.sin(k * 0.4)))[..., None] * np.array([90, 160, 230], np.float32)
        # the title opens along its middle; the helix turns in the gap
        op = seg(k, T_OPEN) * (1 - seg(k, T_SHUT))
        if op > 0.01:
            img = self.helix(img, k, op)
        img *= self.vig[..., None]
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        # the title (shadow first so it reads on the core)
        dy = op * self.lh * 0.36
        sh = Image.fromarray((cv2.GaussianBlur(self.alpha_all, (0, 0), 8 * sc) * 200 * (1 - op)).astype(np.uint8))
        shadow = Image.merge("RGBA", (Image.new("L", sh.size, 0),) * 3 + (sh,))
        out.alpha_composite(shadow, (self.lx, self.ly + round(4 * sc)))
        sw = seg(k, T_SWEEP)
        for name, off in (("top", -dy), ("bot", dy)):
            a = self.L[name].copy()
            if 0 < sw < 1:
                xs = np.arange(self.lw)[None, :]; ys = np.arange(self.lh)[:, None]
                band = np.exp(-(((xs + ys * 0.5) - (-0.2 + 1.5 * sw) * self.lw) / (self.lw * 0.05)) ** 2)
                a[..., :3] = np.clip(a[..., :3] + band[..., None] * 0.55, 0, 1)
            if flash > 0.02:
                a[..., :3] = np.clip(a[..., :3] * (1 + 0.35 * flash) + np.array([0.0, 0.05, 0.1]) * flash, 0, 1)
            im = Image.fromarray((a * 255).astype(np.uint8), "RGBA")
            out.alpha_composite(im, (self.lx, self.ly + int(round(off))))
        if op > 0.01:
            # light leaking from the cut edges
            o = np.asarray(out, np.float32)
            col = (self.alpha_all[self.lh // 2 - 2:self.lh // 2 + 3].max(0) > 0.3).astype(np.float32)
            col = cv2.GaussianBlur(col[None, :], (0, 0), 3 * sc)[0]
            for yc in (self.ly + self.lh // 2 - dy, self.ly + self.lh // 2 + dy):
                yi = np.arange(H, dtype=np.float32)[:, None]
                ln = np.exp(-((yi - yc) / (1.6 * sc)) ** 2) * 0.9 + np.exp(-((yi - yc) / (9 * sc)) ** 2) * 0.35
                cx0 = np.zeros(W, np.float32); cx0[self.lx:self.lx + self.lw] = col
                o[..., :3] += (ln * cx0[None, :] * min(1.0, op * 2))[..., None] * np.array([170, 225, 255], np.float32)
            out = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8), "RGBA")
        out.alpha_composite(self.sub, (round(W / 2 - self.sub.width / 2), self.suby + int(round(dy))))
        return out.convert("RGB")


def render(src, out, only=None, sc=1.0, mp4=None):
    s = Scene(src, sc)
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
        encode([f.resize((GW, GH), Image.LANCZOS) for f in frames], [MS] * N, os.path.join(out, "hover.webp"), quality=70)
        print("kb", os.path.getsize(os.path.join(out, "hover.webp")) // 1024)
    seam = float(np.abs(np.asarray(frames[0], float) - np.asarray(frames[-1], float)).mean())
    print("seam(last->first)", round(seam, 2))


if __name__ == "__main__":
    a = sys.argv
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    sc = float(a[a.index("--scale") + 1]) if "--scale" in a else 1.0
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], only, sc, mp4)
