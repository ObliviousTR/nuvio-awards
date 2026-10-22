"""Emmy statuette from the Television Academy press downloads: raw + rembg cut-outs."""
import io, os, sys, subprocess, urllib.request
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rembg[cpu]", "onnxruntime", "psd-tools"], capture_output=True)
from PIL import Image
from rembg import remove
os.makedirs("refs/emmy", exist_ok=True)
B = "https://www.televisionacademy.com/files/assets/Downloads/"
log = ""
for n in ["Emmy-2.jpg", "Emmy-3.jpg", "t-emmy_statuette_upd2008.jpg", "emmy-statuette-800x1600.psd", "Emmy-Statuette.psd"]:
    try:
        b = urllib.request.urlopen(urllib.request.Request(B + n, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
        if n.endswith(".psd"):
            from psd_tools import PSDImage
            psd = PSDImage.open(io.BytesIO(b))
            im = psd.composite()
            log += f"{n} layers: {[l.name for l in psd]}\n"
            im.save(f"refs/emmy/{n}.png")
            for k, l in enumerate(psd):
                try:
                    li = l.composite()
                    if li: li.save(f"refs/emmy/{n}.layer{k}.png")
                except Exception as e:
                    log += f" layer {k} {e}\n"
        else:
            im = Image.open(io.BytesIO(b)).convert("RGB")
            im.save(f"refs/emmy/{n}.png")
            remove(im).save(f"refs/emmy/{n}.cut.png")
        log += f"ok {n} {im.size} {im.mode}\n"
    except Exception as e:
        log += f"FAIL {n} {e}\n"
open("refs/emmy/log.txt", "w").write(log)
