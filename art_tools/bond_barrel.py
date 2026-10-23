"""007 James Bond (Universes & Franchises): the Quantum of Solace gun barrel, ending on the 007 mark instead of the
film's title, built as a loop.
  cover   red barrel dot with Bond inside, a thin white sight ring round it, the 007 mark and JAMES BOND COLLECTION
  hover   the mark fades to black -> the two dots cross the screen -> Bond walks, turns, fires -> blood runs down ->
          the camera pulls back and the white rifling streaks swing round -> they close into the sight ring round
          the red dot -> a streak of light writes the 007 mark under it -> the cover again (so it loops seamlessly)
Footage: the Craig-era gun-barrel compilation Ozzy sent (QoS part, 6.9s-15.4s); its burned-in caption is cut away.
Mark: Wikimedia Commons "007 Logo.svg" (public domain), white, in nuvio-art art/logos/bond/007.png.
usage: python3 art_tools/bond_barrel.py VIDEO OUT_DIR
"""
import math, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFilter
from reletter import f as font, tracked, width

W, H, OW, OH, FPS = 1280, 720, 512, 288, 20
MARK = "/home/claude/nuvio-art/art/logos/bond/007.png"
T0, T1 = 6.9, 15.45                  # the part of the clip we use
DISC_SRC = (14.2, 644.5, 356.5, 218.5)   # a frame where the red dot is whole: t, cx, cy, r
END_C, END_R = (640, 236), 88        # where the dot settles on the cover
RING = 14                            # sight ring gap round the dot
MARK_W, MARK_Y = 500, 452            # mark width, centre line
TEXT_Y = 556


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def amul(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: round(v * max(0.0, a))))
    return im


def clip(video):
    """All frames of the used part at 20 fps, keyed by source time."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(T0 - 0.05), "-t", str(T1 - T0 + 0.3), "-i", video,
                          "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    n = len(out) // (W * H * 3)
    fr = np.frombuffer(out[:n * W * H * 3], np.uint8).reshape(n, H, W, 3)
    return [(T0 + i / FPS, fr[i]) for i in range(n)]


# letterbox clean-up: the picture sits in y 94..630; the caption starts at y 599 -> fade the picture out above it
_fade = np.ones((H, 1, 1), np.float32)
for y in range(H):
    if y < 94 or y >= 598:
        _fade[y] = 0
    elif y < 128:
        _fade[y] = ease((y - 94) / 34)
    elif y > 560:
        _fade[y] = ease((598 - y) / 38)


def clean(a):
    return Image.fromarray((a.astype(np.float32) * _fade).astype(np.uint8))


def frame_at(frames, t):
    i = min(range(len(frames)), key=lambda k: abs(frames[k][0] - t))
    return frames[i][1]


def disc_sprite(frames):
    t, cx, cy, r = DISC_SRC
    a = frame_at(frames, t)
    pad = 6
    box = (round(cx - r - pad), round(cy - r - pad), round(cx + r + pad), round(cy + r + pad))
    im = Image.fromarray(a).crop(box).convert("RGBA")
    m = Image.new("L", (im.width * 4, im.height * 4), 0)
    ImageDraw.Draw(m).ellipse((pad * 4, pad * 4, (pad + 2 * r) * 4, (pad + 2 * r) * 4), fill=255)
    m = m.resize(im.size, Image.LANCZOS)
    im.putalpha(m)
    return im, r + pad


def place_disc(cv, spr, half, c, r, a=1.0, glow=0.0):
    k = r / (half - 6)
    s = spr.resize((max(1, round(spr.width * k)), max(1, round(spr.height * k))), Image.LANCZOS)
    if glow > 0:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((c[0] - r * 1.25, c[1] - r * 1.25, c[0] + r * 1.25, c[1] + r * 1.25), fill=(150, 8, 8, 255))
        cv.alpha_composite(amul(g.filter(ImageFilter.GaussianBlur(r * 0.55)), glow * a))
    cv.alpha_composite(amul(s, a), (round(c[0] - s.width / 2), round(c[1] - s.height / 2)))


def glow_lines(draw_fn, a=1.0):
    """White streaks with a soft bloom, drawn by draw_fn(ImageDraw, scale)."""
    S = 2
    m = Image.new("L", (W * S, H * S), 0)
    draw_fn(ImageDraw.Draw(m), S)
    m = m.resize((W, H), Image.LANCZOS)
    core = m.filter(ImageFilter.GaussianBlur(1.2))
    bloom = m.filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, v * 2))
    lay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    lay.putalpha(Image.fromarray(np.clip(np.asarray(core, np.float32) + np.asarray(bloom, np.float32) * 0.55, 0, 255).astype(np.uint8)))
    return amul(lay, a)


def arcs(c, R, close, rot, a=1.0, lw=6, grow=1.0):
    """Meridian streaks of a sphere of radius R round c; close 0..1 folds them all into one ring; grow 0..1 brings
    them in one after another (the footage hands over with two or three streaks, not a whole cage)."""
    def fn(d, S):
        for k in (2, 4, 0, 5, 1, 3):
            ak = ease(grow * 6 - [2, 4, 0, 5, 1, 3].index(k) * 0.8)
            if ak <= 0:
                continue
            ph = rot + k * math.pi / 6
            wx = R * (abs(math.cos(ph)) * (1 - close) + close)
            wy = R
            box = ((c[0] - wx) * S, (c[1] - wy) * S, (c[0] + wx) * S, (c[1] + wy) * S)
            if wx * S > 2:
                d.ellipse(box, outline=round(255 * ak), width=max(1, round(lw * S * (1 - 0.4 * close))))
    return glow_lines(fn, a)


def ring(c, r, a=1.0, lw=4):
    def fn(d, S):
        d.ellipse(((c[0] - r) * S, (c[1] - r) * S, (c[0] + r) * S, (c[1] + r) * S), outline=255, width=lw * S)
    return glow_lines(fn, a)


def mark_layers():
    mk = Image.open(MARK).convert("RGBA")
    mk = mk.resize((MARK_W, round(mk.height * MARK_W / mk.width)), Image.LANCZOS)
    pos = (round(W / 2 - mk.width / 2), round(MARK_Y - mk.height / 2))
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    t = "JAMES BOND COLLECTION"
    fn = font("SemiBold", 27)
    tw = width(t, fn, 11)
    tracked(d, (W / 2 - tw / 2, TEXT_Y), t, fn, (236, 236, 236, 255), 11)
    return mk, pos, txt


def mark_reveal(cv, mk, pos, p):
    """A streak of light runs left to right along the mark's centre line and leaves the mark behind it."""
    if p <= 0:
        return
    x0, x1 = pos[0] - 60, pos[0] + mk.width + 60
    sx = x0 + (x1 - x0) * ease(p)
    edge = 50
    xs = np.arange(mk.width, dtype=np.float32) + pos[0]
    ramp = np.clip((sx - xs) / edge, 0, 1)
    m = Image.fromarray((np.broadcast_to(ramp, (mk.height, mk.width)) * 255).astype(np.uint8))
    m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(mk.getchannel("A"))))
    shown = mk.copy()
    shown.putalpha(m)
    cv.alpha_composite(shown, pos)
    if p < 1:
        def fn(d, S):
            y = MARK_Y
            d.line(((x0 - 200) * S, y * S, sx * S, y * S), fill=255, width=3 * S)
            d.ellipse(((sx - 7) * S, (y - 7) * S, (sx + 7) * S, (y + 7) * S), fill=255)
        tail = 1 - ease((p - 0.75) / 0.25)
        cv.alpha_composite(glow_lines(fn, tail))


def build(video, out):
    os.makedirs(out, exist_ok=True)
    frames = clip(video)
    spr, half = disc_sprite(frames)
    mk, pos, txt = mark_layers()

    def cover_frame(fade=1.0, sc=1.0):
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        place_disc(cv, spr, half, END_C, END_R, fade, glow=0.55)
        cv.alpha_composite(ring(END_C, END_R + RING, 0.9 * fade))
        m = mk if sc == 1 else mk.resize((round(mk.width * sc), round(mk.height * sc)), Image.LANCZOS)
        cv.alpha_composite(amul(m, fade), (round(W / 2 - m.width / 2), round(MARK_Y - m.height / 2)))
        cv.alpha_composite(amul(txt, fade))
        return cv

    cover = cover_frame().convert("RGB")
    # timeline: (output frames, what)
    seq = []
    seq += [("cover", None)] * 8
    seq += [("out", i / 10) for i in range(10)]
    # footage, each part at its own pace (source seconds per output frame)
    t = T0
    for t_end, step in ((9.6, 0.1), (13.0, 0.065), (15.1, 0.05)):
        while t < t_end - 1e-6:
            seq.append(("clip", t))
            t += step
    CONV = 20
    seq += [("conv", i / CONV) for i in range(CONV)]
    REV = 18
    seq += [("rev", i / REV) for i in range(REV)]
    seq += [("cover", None)] * 6
    # the dot and streaks at the hand-over (from the measurements of the clip): r 124 at (649, 336)
    C0, R0 = (649, 336), 124
    out_frames = []
    for kind, v in seq:
        if kind == "cover":
            cv = cover.copy()
        elif kind == "out":         # the mark and the ring go, the dot drains to black
            cv = cover_frame(1 - ease(v), 1 - 0.05 * ease(v)).convert("RGB")
        elif kind == "clip":
            cv = clean(frame_at(frames, v))
        elif kind == "conv":        # the streaks swing round and fold into the sight ring round the dot
            u = ease(v)
            c = (C0[0] + (END_C[0] - C0[0]) * u, C0[1] + (END_C[1] - C0[1]) * u)
            r = R0 + (END_R - R0) * u
            base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            if v < 0.3:              # hand over from the footage, which keeps running under it
                base = Image.blend(clean(frame_at(frames, 15.1 + v * 1.0)).convert("RGBA"), base, ease(v / 0.3))
            place_disc(base, spr, half, c, r, 1.0, glow=0.55 * u)
            Rs = 760 * (1 - u) + (END_R + RING) * u
            base.alpha_composite(arcs(c, Rs, ease((v - 0.15) / 0.75), 0.6 + 4.2 * v, a=1 - 0.1 * u, grow=v / 0.45))
            cv = base.convert("RGB")
        elif kind == "rev":         # the ring settles; the light writes the mark; the line of text comes up
            base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            place_disc(base, spr, half, END_C, END_R, 1.0, glow=0.55)
            base.alpha_composite(ring(END_C, END_R + RING, 0.9 + 0.1 * (1 - ease(v / 0.3))))
            mark_reveal(base, mk, pos, v / 0.8)
            base.alpha_composite(amul(txt, ease((v - 0.55) / 0.45)))
            cv = base.convert("RGB")
        out_frames.append(cv.resize((OW, OH), Image.LANCZOS))
    out_frames[0].save(os.path.join(out, "hover.webp"), save_all=True, append_images=out_frames[1:],
                       duration=[1000 // FPS] * len(out_frames), loop=0, quality=82, method=6, kmin=0, kmax=1)
    cover.save(os.path.join(out, "cover.jpg"), quality=92)
    sheet = Image.new("RGB", (6 * 256, 4 * 144))
    for i in range(24):
        sheet.paste(out_frames[int(i * len(out_frames) / 24)].resize((256, 144)), ((i % 6) * 256, (i // 6) * 144))
    sheet.save(os.path.join(out, "frames.jpg"), quality=85)
    return len(out_frames)


if __name__ == "__main__":
    print("frames", build(sys.argv[1], sys.argv[2]))
