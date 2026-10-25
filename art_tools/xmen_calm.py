"""X-Men card, the approved Cerebro ident (xmen_cerebro.py) without its stacked second act: Cerebro alone. It powers up
from the first frames, the pulses race along the fibres to the title, the minds blink on round it and the cold core
swells behind the letters; the camera moves in on the title while Cerebro reads and back as it powers down. No split
title, no helix, no flash, no light sweep. THE COLLECTION gets a shade behind it.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/xmen_calm.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]   (SRC_DIR as for xmen_cerebro.py)
"""
import math, os, sys, subprocess
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import xmen_cerebro as xc

W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250
xc.T_ON = (3, 44); xc.T_OFF = (192, 238)
xc.T_OPEN = (10 ** 6, 10 ** 6 + 1); xc.T_SHUT = (10 ** 6, 10 ** 6 + 1); xc.T_SWEEP = (10 ** 6, 10 ** 6 + 1)


def smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


class Scene(xc.Scene):
    def frame(self, k):
        im = np.asarray(super().frame(k), np.float32)
        # a shade behind THE COLLECTION so the lit fibres never cross it, then the letters again on top
        sa = np.zeros((H, W), np.float32)
        x0 = round(W / 2 - self.sub.width / 2); y0 = self.suby
        sa[y0:y0 + self.sub.height, x0:x0 + self.sub.width] = np.asarray(self.sub, np.float32)[..., 3] / 255
        shade = np.clip(cv2.GaussianBlur(sa, (0, 0), 14) * 3.0, 0, 1) * 0.85
        im = im * (1 - shade[..., None])
        o = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).convert("RGBA"); o.alpha_composite(self.sub, (x0, y0))
        im = np.asarray(o.convert("RGB"), np.float32)
        on = xc.seg(k, xc.T_ON) * (1 - xc.seg(k, xc.T_OFF))
        z = 1.0 + 0.06 * smooth(on)
        cy = self.ly + self.lh / 2
        if z > 1.0005:
            M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, cy * (1 - z)]])
            im = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))


def render(src, out, only=None, mp4=None):
    s = Scene(src, 1.0)
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
