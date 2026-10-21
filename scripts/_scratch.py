import os, io, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from PIL import Image, ImageSequence, ImageEnhance
os.makedirs("refs/sticker", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
b = urllib.request.urlopen(urllib.request.Request("https://media.giphy.com/media/st8Zsj32VefZ4mBlPZ/giphy.gif", headers=UA), timeout=60).read()
open("refs/sticker/source.gif", "wb").write(b)
g = Image.open(io.BytesIO(b))
frames, durs = [], []
for f in ImageSequence.Iterator(g):
    frames.append(f.convert("RGBA").copy()); durs.append(f.info.get("duration", 60))
log = [f"sticker {g.size} {len(frames)} frames, durations {sorted(set(durs))}"]
W, H = 640, 360
def sticker_frame(fr, scale=0.62):
    bb = frames[-1].getchannel("A").getbbox() or (0, 0, *fr.size)
    s = fr.crop(bb)
    k = min(W * scale / s.width, H * 0.42 / s.height)
    return s.resize((round(s.width * k), round(s.height * k)), Image.LANCZOS)
BG = {
 "gotham": ["/jz1eErpJSx7ToDVDgV9HKFv4hAa.jpg"],
 "eras": ["/rhc7OF7tC9HPu0X8DBKQJzaGRbu.jpg", "/9FE5eD92WfVCiivM9Pq9GVSrlWk.jpg", "/rvtdN5XkWAfGX6xDuPL6yYS2seK.jpg", "/hw1CwteUFGjcWXwjGhKk8UJpWeA.jpg"],
 "rain": ["/IYUD7rAIXzBM91TT3Z5fILUS7n.jpg"],
}
for name, paths in BG.items():
    bgs = [ImageEnhance.Brightness(art.graded(art.fetch(p), 0.9, 1.05)).enhance(0.55) for p in paths]
    n = len(frames)
    total = max(n, 48)
    out = []
    for i in range(total):
        t = i / total
        seg = min(len(bgs) - 1, int(t * len(bgs)))
        local = t * len(bgs) - seg
        bg = art.zoomed(bgs[seg], 0.03 + 0.07 * local)
        if len(bgs) > 1 and local > 0.8:
            bg = Image.blend(bg, art.zoomed(bgs[(seg + 1) % len(bgs)], 0.03), (local - 0.8) / 0.2)
        bg = bg.resize((W, H), Image.LANCZOS).convert("RGBA")
        st = sticker_frame(frames[min(i, n - 1)])
        bg.alpha_composite(st, ((W - st.width) // 2, (H - st.height) // 2))
        out.append(bg.convert("RGB"))
    pal = Image.new("RGB", (W, H * 3))
    for j, k in enumerate((n - 1, total // 2, total - 1)):
        pal.paste(out[min(k, total - 1)], (0, H * j))
    pal = pal.convert("P", palette=Image.ADAPTIVE, colors=200)
    q = [f.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG) for f in out]
    q[0].save(f"refs/sticker/{name}.gif", save_all=True, append_images=q[1:], duration=[durs[min(i, n - 1)] if i < n else 90 for i in range(total)], loop=0, optimize=True)
    out[-1].resize((1280, 720), Image.LANCZOS).save(f"refs/sticker/{name}-cover.jpg", quality=90)
    log.append(f"{name}: {total} frames {os.path.getsize(f'refs/sticker/{name}.gif')//1024} KB")
open("refs/sticker/log.txt", "w").write("\n".join(log))
