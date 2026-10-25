"""Dune card, the approved worm ident (dune_ident.py --mode worm) with the title on its own plane and the action brought
forward: the sand trail starts in the first frames, the worm rises sooner, and the title comes slowly forward over the
desert and back over the loop (parallax against the dunes).
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/dune_calm.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]   (SRC_DIR as for dune_ident.py)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import dune_ident as du

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


class Worm(du.Worm):
    T_SIGN = (4, 80)
    T_RISE = (76, 132)
    T_SINK = (180, 218)

    def __init__(self, src):
        super().__init__(src)
        self.o_la, self.o_rgb, self.o_sub, self.o_dot = self.la.copy(), self.rgb.copy(), self.sub.copy(), self.dot

    def frame(self, k):
        ph = 2 * math.pi * k / N
        z = 1.0 + 0.06 * (1 - math.cos(ph)) / 2
        cx, cy = W / 2, self.cy + 20
        M = np.float32([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]])
        self.la = cv2.warpAffine(self.o_la, M, (W, H), flags=cv2.INTER_LINEAR)
        self.rgb = cv2.warpAffine(self.o_rgb, M, (W, H), flags=cv2.INTER_LINEAR)
        self.sub = cv2.warpAffine(self.o_sub, M, (W, H), flags=cv2.INTER_LINEAR)
        self.dot = ((self.o_dot[0] - cx) * z + cx, int(round((self.o_dot[1] - cy) * z + cy)))
        return super().frame(k)


def render(src, out, only=None, mp4=None):
    s = Worm(src)
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
