"""Godzilla & Kong card: Godzilla x Kong: The New Empire's Hollow Earth gravity zone, where the fight goes weightless.
The film's still (Kong and the Skar King clash in the air over Godzilla and the Titan below them, in the crystal
light) is cut into its Titans and the cave. GODZILLA x KONG in steel stands in it, lit by the crystal light.
On hover gravity lets go: the Titans drift up a little in the air, each letter of the title lifts off on its own and
floats, turning slightly, while the light swells; then gravity comes back, the letters drop onto their line and
settle, the Titans sink back and the frame is the cover again. The camera moves in a little and back.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/gk_gravity.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]
  SRC_DIR: logo.png, BarlowCondensed-Medium.ttf, hollow.jpg (the TMDB still), hollow_mask.png (its Titans, rembg)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
from gk_mural import Steel, collection, smooth, seg, blur, bigblur, noise

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
RELEASE = (4, 46)                                                        # gravity lets go
RETURN = (186, 214)                                                      # and comes back


def damped(k, k0, amp=1.0):
    """A drop that lands at k0 and settles: 0 before, a short decaying bounce after."""
    j = k - k0
    if j < 0:
        return 0.0
    return amp * math.exp(-j / 5.0) * math.sin(j * 0.75)


class Gravity:
    def __init__(self, src):
        im = cv2.cvtColor(cv2.imread(os.path.join(src, "hollow.jpg")), cv2.COLOR_BGR2RGB)
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        m = cv2.imread(os.path.join(src, "hollow_mask.png"), cv2.IMREAD_GRAYSCALE)
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        m = np.clip((m - 0.12) / 0.3, 0, 1)
        self.plate = im
        # the cave behind the Titans, filled in where they were (only thin edges of it ever show)
        hole = (cv2.dilate((m > 0.2).astype(np.uint8), np.ones((15, 15), np.uint8)) * 255)
        small = cv2.resize((im * 255).astype(np.uint8), (W // 2, H // 2))
        hs = cv2.resize(hole, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
        fill = cv2.inpaint(small, hs, 9, cv2.INPAINT_TELEA)
        fill = cv2.resize(fill, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
        hb = blur(hole.astype(np.float32) / 255, 3)[..., None]
        self.cave = im * (1 - hb) + fill * hb
        # three Titan layers: the pair in the air, the Titan on the left, Godzilla on the right
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.xx, self.yy = xx, yy
        air = smooth((300 - yy) / 30)
        left = (1 - air) * smooth((650 - xx) / 30)
        right = (1 - air) * (1 - smooth((650 - xx) / 30))
        self.layers = []
        for reg, amp, ph, rot in ((air, 9.0, 0.0, 0.6), (left, 6.0, 0.9, -0.4), (right, 7.0, 1.7, 0.5)):
            a = (m * reg).astype(np.float32)
            ys, xs = np.nonzero(a > 0.3)
            c = (float(xs.mean()), float(ys.mean()))
            self.layers.append((a, amp, ph, rot, c))
        # the title in the lower third, lit by the crystal light above the fight
        self.t = Steel(src, 760, 588)
        import gk_ident
        steel = gk_ident.Title(src, 760, 588)                            # the storm card's brushed steel
        self.face = (steel.face / 255.0 * np.array([0.88, 1.0, 0.97], np.float32)).astype(np.float32)
        la = self.t.la
        n, lab, st, cen = cv2.connectedComponentsWithStats((la > 0.08).astype(np.uint8))
        rng = np.random.default_rng(4)
        self.letters = []
        order = np.argsort(cen[1:, 0]) + 1
        for j, i in enumerate(order):
            x, y, w, h, area = st[i]
            if area < 30:
                continue
            pad = 6
            x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
            msk = (lab[y0:y1, x0:x1] == i).astype(np.float32)
            msk = cv2.dilate(msk, np.ones((3, 3), np.uint8))
            a = la[y0:y1, x0:x1] * msk
            f = self.face[y0:y1, x0:x1] * a[..., None]
            lift = rng.uniform(9, 17); turn = rng.uniform(-2.4, 2.4)
            t0 = RELEASE[0] + j * 2.5 + rng.uniform(0, 3)
            bob = rng.uniform(0, 2 * math.pi)
            self.letters.append(((x0, y0, x1, y1), a, f, lift, turn, t0, bob, (x + w / 2 - x0, y + h / 2 - y0), j))
        self.sub = collection(src, 52, 28)
        self.sub_y = self.t.y0 + self.t.lh + 26
        self.grain = noise(H * 2, W * 2, 0.0, 7)
        rr = np.sqrt(((xx - 640) / 330) ** 2 + ((yy - 260) / 300) ** 2)
        self.shaft = np.exp(-rr ** 2).astype(np.float32)

    def weight(self, k):
        """0 with gravity on (the cover), 1 weightless."""
        return seg(k, *RELEASE) * (1 - seg(k, *RETURN))

    def frame(self, k):
        k = k % N
        ph = 2 * math.pi * k / N
        c = (1 - math.cos(ph)) / 2
        g = self.weight(k)
        # camera: in a little and back
        z = 1.0 + 0.045 * c
        Mc = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, 330 * (1 - z)]])
        img = self.cave.copy()
        for a, amp, phs, rot, (cx, cy) in self.layers:
            up = g * amp + g * 2.0 * math.sin(ph * 2 + phs)
            M = cv2.getRotationMatrix2D((cx, cy), rot * g * math.sin(ph + phs), 1.0)
            M[1, 2] -= up
            la = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR)
            lr = cv2.warpAffine(self.plate * a[..., None], M, (W, H), flags=cv2.INTER_LINEAR)
            img = img * (1 - la[..., None]) + lr
        # the crystal light swells while the zone is weightless
        img = img * (1 + 0.10 * g * self.shaft)[..., None] + (self.shaft * 0.02 * g)[..., None] * np.array([0.7, 1.0, 0.9], np.float32)
        img = cv2.warpAffine(img, Mc, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # ground the lower third so the lockup reads
        img = img * (1 - 0.62 * smooth((self.yy - 430) / 260))[..., None]
        # the letters: lift off one by one, float and turn, drop back and settle
        zt = 1.0 + 0.06 * c
        placed = []
        la_all = np.zeros((H, W), np.float32)
        for (x0, y0, x1, y1), a, f, lift, turn, t0, bob, (lx, ly), j in self.letters:
            rise = seg(k, t0, t0 + 24) * (1 - seg(k, RETURN[0] + j * 0.8, RETURN[0] + j * 0.8 + 10))
            dy = -lift * rise - 2.5 * rise * math.sin(ph * 2 + bob)
            dy += damped(k, RETURN[0] + j * 0.8 + 10, 3.0)
            ang = turn * rise * (0.7 + 0.3 * math.sin(ph * 3 + bob))
            M = cv2.getRotationMatrix2D((lx, ly), ang, 1.0)
            gx0 = W / 2 + (x0 - W / 2) * zt; gy0 = self.t.cy + (y0 + dy - self.t.cy) * zt
            M = M * zt
            M[0, 2] += gx0; M[1, 2] += gy0
            aw = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR)
            fw = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR)
            placed.append((aw, fw)); la_all = np.maximum(la_all, aw)
        img = img * (1 - 0.55 * bigblur(la_all, 18))[..., None]
        for aw, fw in placed:                                            # premultiplied: over, letter by letter
            img = img * (1 - aw[..., None]) + fw
        sa = np.zeros((H, W), np.float32)
        sh_, sw_ = self.sub.shape
        x0 = round(W / 2 - sw_ / 2); y0 = round(self.t.cy + (self.sub_y - self.t.cy) * zt)
        sa[y0:y0 + sh_, x0:x0 + sw_] = self.sub
        img = img * (1 - np.clip(bigblur(sa, 14) * 3.0, 0, 1) * 0.7)[..., None]
        img = img * (1 - sa[..., None]) + np.array([0.80, 0.88, 0.86], np.float32) * sa[..., None]
        rr = np.sqrt(((self.xx - W / 2) / (W * 0.62)) ** 2 + ((self.yy - H / 2) / (H * 0.66)) ** 2)
        img = img * (1 - 0.4 * np.clip(rr - 0.45, 0, 1))[..., None]
        img = img + (self.grain[:H, :W] - 0.5)[..., None] * 0.015
        return Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))


def render(src, out, only=None, mp4=None):
    s = Gravity(src)
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
    only = [int(x) for x in a[a.index("--frames") + 1].split(",")] if "--frames" in a else None
    mp4 = a[a.index("--mp4") + 1] if "--mp4" in a else None
    render(a[1], a[2], only, mp4)
