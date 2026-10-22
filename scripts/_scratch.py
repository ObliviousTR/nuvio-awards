"""Iconic Actors: rembg cut-outs of our portrait actors (graded locally)."""
import os, sys, subprocess, traceback
os.makedirs("refs/cut", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rembg[cpu]", "onnxruntime"], capture_output=True, text=True).stderr[-800:]
sys.path.insert(0, "art_tools")
import folder_art as fa
for n in ["Frances McDormand", "Edward Norton", "Philip Seymour Hoffman", "Bryan Cranston", "Tilda Swinton", "Toni Collette",
          "Ethan Hawke", "Sam Rockwell", "Simon Pegg", "Robert Pattinson", "Tom Holland", "Sofia Coppola"]:
    try:
        img, _ = fa.person(n)
        img.save(f"refs/cut/{fa.slug(n)}-src.jpg", quality=95)
        fa.cutout(img).save(f"refs/cut/{fa.slug(n)}.png")
        log += f"ok {n}\n"
    except Exception:
        log += f"FAIL {n}\n" + traceback.format_exc()
open("refs/cut/log.txt", "w").write(log)
