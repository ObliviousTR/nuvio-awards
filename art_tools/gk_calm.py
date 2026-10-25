"""Godzilla & Kong card, the approved storm ident (gk_ident.py --mode storm) with the title on its own plane: it comes
slowly forward over the storm and goes back over the loop (parallax against the clouds), and each thunder after a
strike shakes the frame a little. Everything else is the storm card as it was.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/gk_calm.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]   (SRC_DIR as for gk_ident.py)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import gk_ident as gk

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
ATTRS = ["la", "face", "rim", "g1", "g2", "g3", "g4", "nx", "v"]


class Storm(gk.Storm):
    def __init__(self, src):
        super().__init__(src)
        t = self.t
        self.orig = {a: getattr(t, a).copy() for a in ATTRS}
        self.opts = t.pts.copy()
        self.oxm, self.oym, self.oxt = t.xm, t.ym, t.xm_top

    def place_title(self, k):
        t = self.t
        ph = 2 * math.pi * k / N
        z = 1.0 + 0.07 * (1 - math.cos(ph)) / 2
        cx, cy = W / 2, t.cy
        M = np.float32([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]])
        for a in ATTRS:
            src = self.orig[a]
            bv = 0.0 if a != "v" else float(src[0, 0])
            setattr(t, a, cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=bv))
        t.pts = (self.opts - [cx, cy]) * z + [cx, cy]
        t.xm = (self.oxm - cx) * z + cx; t.ym = (self.oym - cy) * z + cy; t.xm_top = (self.oxt - cy) * z + cy

    def shake(self, k):
        amp = 0.0
        for k0, x, ye, s, st, ti in self.events:
            j = k - (k0 + 3)
            if 0 <= j < 14:
                amp = max(amp, (1 - j / 14) ** 2 * 3.5 * st)
        j = k - (self.T_STRIKE + 3)
        if 0 <= j < 16:
            amp = max(amp, (1 - j / 16) ** 2 * 5.0)
        rng = np.random.default_rng(5000 + k)
        return rng.normal() * amp, rng.normal() * amp * 0.6

    def frame(self, k):
        self.place_title(k)
        im = super().frame(k)
        sx, sy = self.shake(k)
        if abs(sx) + abs(sy) > 0.05:
            a = np.asarray(im, np.float32)
            a = cv2.warpAffine(a, np.float32([[1, 0, sx], [0, 1, sy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
            im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        return im


def render(src, out, only=None, mp4=None):
    s = Storm(src)
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
