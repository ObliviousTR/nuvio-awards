"""Middle-earth card, the approved Ring ident (middleearth_ident.py --title ring) without what it simulated: no embers,
no heat shimmer. The inscription heats letter by letter from the first frames (from its gap) to a hot gold and cools
again; the title takes the warm light and comes forward, waits and goes back.
250 frames at 40 ms, first frame = last frame = cover.
usage: python3 art_tools/middleearth_calm.py SRC_DIR OUT_DIR [--frames a,b] [--mp4 path]   (SRC_DIR as for middleearth_ident.py)
"""
import os, sys, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframe_webp import encode
import middleearth_ident as me

me.T_HEAT = (3, 136); me.T_HOLD = (136, 176); me.T_COOL = (176, 232); me.T_ZOOM = (30, 70, 140, 190)
W, H, GW, GH, MS, N = 1280, 720, 512, 288, 40, 250


def render(src, out, only=None, mp4=None):
    s = me.Scene(src, "ring", 1.0)
    s.ne = 0; s.shimmer = False
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
