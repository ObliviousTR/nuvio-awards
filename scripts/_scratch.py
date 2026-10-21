import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageSequence
import universe_art as U
out = "refs/uni-samples"
for uid in U.SPECS:
    d = U.build(uid, out)
    g = Image.open(os.path.join(d, "hover.gif"))
    fr = [f.convert("RGB").copy() for f in ImageSequence.Iterator(g)]
    pick = fr[::max(1, len(fr) // 8)][:8]
    strip = Image.new("RGB", (512 * 4, 288 * 2))
    for i, f in enumerate(pick):
        strip.paste(f, ((i % 4) * 512, (i // 4) * 288))
    strip.save(os.path.join(d, "hover-frames.jpg"), quality=80)
    print(uid, len(fr), os.path.getsize(os.path.join(d, "hover.gif")) // 1024, "KB")
