import sys, numpy as np, cv2
from PIL import Image
# remove thin structures (poles, wires, lightning) and colour blobs (sun), keep the creature
p, k = sys.argv[1], float(sys.argv[2])
sun = len(sys.argv) > 3 and sys.argv[3] == "sun"
im = Image.open(f"el/{p}.png").convert("RGBA"); a = np.asarray(im).astype(np.float32)
al = a[..., 3] / 255
if sun:
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    warm = (r > 150) & (r > b + 50)
    al[warm] = 0
m = (al > 0.5).astype(np.uint8)
ks = max(3, int(min(m.shape) * k)) | 1
op = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks)))
n, lab, st, _ = cv2.connectedComponentsWithStats(op)
if n > 1:
    big = st[1:, cv2.CC_STAT_AREA].max(); keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 0.15 * big]
    op = np.isin(lab, keep).astype(np.uint8)
grow = cv2.dilate(op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks + 4, ks + 4)))
al = al * grow
a[..., 3] = al * 255
out = Image.fromarray(a.astype(np.uint8), "RGBA"); out = out.crop(out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox())
out.save(f"el/{p}_c.png"); print(p, out.size)
