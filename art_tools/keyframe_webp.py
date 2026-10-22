"""Re-encode animated images so every frame is a keyframe (a full, independent frame).

Why: Nuvio Desktop plays hover animations with Skia's Codec.readPixels(bitmap, i) and no prior frame, so a frame
that depends on the previous one makes Skia decode the whole chain back to the last keyframe, every frame: a 5 s
animation then runs 10-15 s and stutters. Mobile (Android's decoder) streams frames and is unaffected.
usage: python3 art_tools/keyframe_webp.py SRC [DST]   (GIF or WebP in, WebP out; DST defaults to SRC for .webp)
"""
import io, sys
from PIL import Image


def frames_of(path):
    im = Image.open(path)
    out, dur = [], []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        im.load()
        out.append(im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") and "transparency" in im.info or im.mode == "RGBA" else "RGB"))
        dur.append(max(20, int(im.info.get("duration", 100) or 100)))
    return out, dur


def encode(frames, dur, dst, quality=82):
    b = io.BytesIO()
    frames[0].save(b, "WEBP", save_all=True, append_images=frames[1:], duration=dur, loop=0, quality=quality, method=4,
                   kmin=0, kmax=1)
    open(dst, "wb").write(b.getvalue())


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    f, d = frames_of(src)
    encode(f, d, dst)
