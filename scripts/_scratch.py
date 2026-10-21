import os, subprocess, json, glob
from PIL import Image, ImageDraw
os.makedirs("refs/yt", exist_ok=True)
Q = {"wizarding": "ytsearch3:Wizarding World logo intro 4K", "mcu": "ytsearch3:Marvel Studios intro 2016 logo 4K",
     "bond": "ytsearch3:James Bond gun barrel sequence Daniel Craig HD", "matrix": "ytsearch3:The Matrix opening code rain logo"}
log = []
for k, q in Q.items():
    r = subprocess.run(["yt-dlp", "--print", "%(id)s | %(title)s | %(duration)s | %(height)s", "--skip-download", q],
                       capture_output=True, text=True, timeout=300)
    log.append(f"== {k}\n{r.stdout}\n{r.stderr[-600:]}")
    first = r.stdout.split(" | ")[0].strip() if r.stdout.strip() else None
    if not first:
        continue
    out = f"refs/yt/{k}.mp4"
    r2 = subprocess.run(["yt-dlp", "-f", "bv*[height<=720][ext=mp4]/b[height<=720]", "--download-sections", "*0-20",
                         "-o", out, f"https://www.youtube.com/watch?v={first}"], capture_output=True, text=True, timeout=600)
    log.append(r2.stdout[-400:] + r2.stderr[-600:])
    if os.path.exists(out):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-vf", "fps=1/2.5,scale=320:-1", f"refs/yt/{k}-%02d.jpg"])
        fr = sorted(glob.glob(f"refs/yt/{k}-*.jpg"))
        if fr:
            ims = [Image.open(f) for f in fr]
            sheet = Image.new("RGB", (330 * len(ims), ims[0].height + 10))
            for i, im in enumerate(ims): sheet.paste(im, (i * 330, 0))
            sheet.save(f"refs/yt/{k}-sheet.jpg", quality=80)
            for f in fr: os.remove(f)
        os.remove(out)
open("refs/yt/log.txt", "w").write("\n".join(log))
