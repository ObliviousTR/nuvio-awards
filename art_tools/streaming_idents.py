"""Streaming Services row: Exxen, GAİN and tabii get their own platform idents, the way Kaptain's cards carry Netflix's
and HBO Max's: the hover is the platform's original splash (cut to the ident, black tails trimmed, Exxen's long hold
shortened), the cover is the ident's held logo frame.
usage: python3 art_tools/streaming_idents.py VIDEO_DIR OUT_DIR [ids...]
  VIDEO_DIR: exxen.mp4 (EXXEN alternative intro), gain.webm (GAİN TV splash, 4K), tabii.mp4 (tabii splash)
  OUT_DIR/<id>/ receives cover.jpg (1280x720) and hover.webp (512x288, 25 fps, every frame a keyframe)
"""
import os, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode

GW, GH, MS = 512, 288, 40
# source frames (25 fps) kept for the hover, in order, and the frame used for the cover
CUTS = {
    "exxen": ("exxen.mp4", [(9, 75), (95, 160)], 80),        # border + dot, letters build, hold (shortened), out
    "gain": ("gain.webm", [(3, 97)], 50),                    # G A I N with the balloon, the door, the girl, out
    "tabii": ("tabii.mp4", [(8, 94)], 50),                   # the star turns in, wordmark, the star opens, out
}


def frames(path, size):
    w, h = size
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", "-vf", f"scale={w}:{h}:flags=lanczos",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, 3)


def build(vdir, out, pid):
    name, cuts, cov = CUTS[pid]
    path = os.path.join(vdir, name)
    big = frames(path, (1280, 720))
    small = frames(path, (GW, GH))
    os.makedirs(os.path.join(out, pid), exist_ok=True)
    Image.fromarray(big[cov]).save(os.path.join(out, pid, "cover.jpg"), quality=92)
    keep = [i for a, b in cuts for i in range(a, min(b, len(small)))]
    hov = [Image.fromarray(small[i]) for i in keep]
    dst = os.path.join(out, pid, "hover.webp")
    encode(hov, [MS] * len(hov), dst, quality=72)
    print(pid, len(hov), "frames", len(hov) * MS / 1000, "s", os.path.getsize(dst) // 1024, "KB")


if __name__ == "__main__":
    vdir, out = sys.argv[1], sys.argv[2]
    for pid in (sys.argv[3:] or list(CUTS)):
        build(vdir, out, pid)
