import sys, json
from PIL import Image
import numpy as np, cv2
from scipy import ndimage
src, out, prev = sys.argv[1:4]
im = Image.open(src).convert("RGBA"); W0, H0 = im.size; sc = 2
a = np.asarray(im.resize((W0 // sc, H0 // sc), Image.LANCZOS)).astype(int)
dark = ((a[..., 3] > 200) & (a[..., :3].max(-1) < 60)).astype(np.uint8)
n, lab, st, cen = cv2.connectedComponentsWithStats(dark)
m = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
m = ndimage.binary_fill_holes(m).astype(np.uint8)
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
ys, xs = np.nonzero(m); cx = (xs.min() + xs.max()) / 2
mir = cv2.warpAffine(m, np.float32([[-1, 0, 2 * cx], [0, 1, 0]]), (m.shape[1], m.shape[0]), flags=cv2.INTER_NEAREST)
m = np.maximum(m, mir)
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2) > 0.5
cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
c = max(cs, key=cv2.contourArea)
poly = cv2.approxPolyDP(c, 0.8, True)[:, 0, :].astype(float)
hull = cv2.convexHull(c)[:, 0, :]
dense = c[:, 0, :]
d = np.array([abs(cv2.pointPolygonTest(hull, (float(p[0]), float(p[1])), True)) for p in dense])
(ex, ey), (aw, ah), ang = cv2.fitEllipse(dense[d < 1.5].astype(np.float32))
ell = [ex * sc, ey * sc, aw * sc / 2, ah * sc / 2]
if aw < ah: ell = [ex * sc, ey * sc, ah * sc / 2, aw * sc / 2]
E = np.zeros(m.shape, np.uint8)
cv2.ellipse(E, ((ell[0] / sc, ell[1] / sc), (ell[2] * 2 / sc * 0.997, ell[3] * 2 / sc * 0.997), 0), 1, -1)
lobes = cv2.morphologyEx(((E > 0) & ~m).astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
n2, l2, s2, _ = cv2.connectedComponentsWithStats(lobes)
lobes = np.isin(l2, [i for i in range(1, n2) if s2[i, 4] > 0.01 * E.sum()])
m2 = (E > 0) & ~lobes
cs, _ = cv2.findContours(m2.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
poly = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 0.8, True)[:, 0, :].astype(float)
json.dump({"ellipse": [round(v, 2) for v in ell], "bat": (poly * sc).round(2).tolist()}, open(out, "w"))
v = np.zeros((m.shape[0], m.shape[1], 3), np.uint8); v[..., 1] = 90
cv2.fillPoly(v, [poly.astype(np.int32)], (255, 255, 255))
cv2.ellipse(v, ((ell[0] / sc, ell[1] / sc), (ell[2] * 2 / sc, ell[3] * 2 / sc), 0), (0, 0, 255), 2)
cv2.imwrite(prev, cv2.resize(v, (800, int(800 * v.shape[0] / v.shape[1]))))
print("points", len(poly), "ellipse", ell, "angle", ang)
