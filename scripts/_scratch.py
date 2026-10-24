"""What does avid.wiki hold for our franchises: hosted videos, YouTube embeds, images, licence notes."""
import os, re, urllib.parse, urllib.request
OUT = "refs/avid"; os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) nuvio-awards research"}
pages = ["Marvel_Studios", "DC_Studios", "DC_Films", "DC_Entertainment", "Wizarding_World", "Warner_Bros._Pictures",
         "New_Line_Cinema", "Lucasfilm", "Legendary_Pictures", "Universal_Pictures", "Paramount_Pictures",
         "Eon_Productions", "20th_Century_Studios", "Amblin_Entertainment"]
rep = []
for p in pages:
    u = f"https://www.avid.wiki/{p}"
    try:
        h = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        rep.append(f"{p}: {e}"); continue
    vids = sorted(set(re.findall(r'(https?:[^"\' ]+?\.(?:mp4|webm|ogv|gif))', h)))
    vids += sorted(set("https:" + v if v.startswith("//") else v for v in re.findall(r'["\'](//?[^"\' ]*/images/[^"\' ]+?\.(?:mp4|webm|ogv))', h)))
    yt = sorted(set(re.findall(r'(?:youtube\.com/embed/|youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})', h)))
    heads = re.findall(r'<span class="mw-headline" id="([^"]+)"', h)
    lic = re.findall(r'(?i)(creative commons[^<]{0,80}|fair use[^<]{0,120}|copyright[^<]{0,120})', h)[:3]
    rep.append(f"== {p}: {len(h)} bytes; sections {len(heads)}: {heads[:25]}")
    rep.append(f"   hosted videos {len(vids)}: {vids[:12]}")
    rep.append(f"   youtube {len(yt)}: {yt[:12]}")
    rep.append(f"   licence text: {lic}")
open(f"{OUT}/report.txt", "w").write("\n".join(rep) + "\n"); print("\n".join(rep))
