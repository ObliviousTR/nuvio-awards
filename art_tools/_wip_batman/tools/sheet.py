import sys, glob, os
from PIL import Image, ImageDraw

files = sorted(glob.glob(sys.argv[1]))
cw, ch, cols = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
ims = []
for f in files:
    try:
        ims.append((f, Image.open(f).convert("RGBA")))
    except Exception:
        pass
rows = (len(ims) + cols - 1) // cols
sh = Image.new("RGB", (cols * cw, rows * (ch + 16)), (60, 60, 60))
d = ImageDraw.Draw(sh)
for i, (f, im) in enumerate(ims):
    im.thumbnail((cw, ch))
    bg = Image.new("RGBA", im.size, (90, 90, 110, 255))
    bg.alpha_composite(im)
    x, y = (i % cols) * cw, (i // cols) * (ch + 16)
    sh.paste(bg.convert("RGB"), (x, y + 16))
    d.text((x + 3, y + 2), os.path.basename(f), fill=(255, 255, 0))
sh.save(sys.argv[2], quality=85)
