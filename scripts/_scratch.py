import os, io, json, urllib.request, urllib.parse, concurrent.futures as cf
from PIL import Image, ImageSequence, ImageDraw
os.makedirs("refs/stk", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
C = {
 "mcu": "dC3uDJazzlM4z3lZJ5 Icublt25bLylLYkEoJ Wq8vY2NXRelQhH9ms3 1J5Ce6euWsIeFnzGL9 amEVoCvmwcg16iq4bD FhvN60LfpI3cfoAASs jlPH3quqJcl6znyQUB mlBKGLcvaoricmSwQe gHGT75v6PA7UsE3cpf RQGkK9ghHmfD0l770g",
 "dc": "MdSd5OVojIyK8EjaqQ ensd2k3UXTw2ErdEet 46zn5FmNndXaJVjgdG Jo7y6XHW6LOeTZvF5b z3qq00Cz77qTIcdsvj VQ5NEzr3L1yxrQFbIY",
 "batman": "st8Zsj32VefZ4mBlPZ egQM3Haen3USd5ZfZf IhUQ2JDDfJWDBcoj8X LoffmNN2wQYKc erg5dWNomXlY8K4sxu XaM4wAdWJcPI7ZUjeF",
 "spiderman": "9JnLOdu5vJMyTownZ0 YUC8azgE2nMfglemEQ u6pM24wf1j8xq3wUPQ 74xxT5XDbV4ZXGB4Ui YT9QSPPlVYFKJV7MCl Ztv7Qo2A1vORm6hKif qKi3EYKiJfHrPA8Mkl",
 "xmen": "0sifJvGCjI0tXVcnhM UtujL2pHBabPgrn9BP ahCA01dpCAO2vroQVf MeP4BTnthn5ARSqZEA fxZURB2yokEKJzYCA5 rfi9aRnWaQhWupr89J",
 "lotr": "roCYoqkBIcQ39NIvhF xEJiLFc9Dyx59pzeV9 o7LIsNZps764LzPhBy o0Xk8O9VjxvVwOvH9b vuAiRyEsDrvdSZh7Kl 2FNeJK51K7NT5Li34L 0mPcwymeze1UoCGP37 v8b0W5d3yqjMLc8xw5 cbeCrpFIraSTi9WraU jU8YU7i8WJFLMMDrEb",
 "starwars": "qH3BFJya6c5So uLPD8xcYi28nhFfG0k RLflocYLauiJ2 b2TN3U2d2sS1nK1kqX dAomfPOGBO6p4AafEl",
 "wizarding": "yB7BWZfXO0yKbz0BrC FmHgJyM1POBFnyHw0j njXmRe8VZLH6jjy4SW VaXCnPEfhfuv1K1WUo cAfOx3wPbzSFVoq6wq 0ZWaLhDdf0J5CZ6SBT JjBvbEtBR962Y3HMRQ AZ53MYC6Kn0Oodv2Gs aMekitrqwKMqby2JBG hC5efgkjkUlNhpfRKA L2lkyiSIYFq6f4gAqq",
 "dune": "V5EflugpxzxrYL0MEE XH8C2ytOgOvRRGaDcZ dz8ejXAgUpwNrYpuZN ftzkV9qsFtZDYsEWyg o7I6lASU0YMcQBVIHI lRbKT3eo4CyQmiNtRp r99Ws47ytUTOzmUwtK",
 "startrek": "l4jVKzgVNFncwl37Fl JtBbQlcLJHdCCeKM4O ZdgaNVCdqFmQVdcccg MCcDJHgn4DjVL0X4O7 wsSIDWwDaiszDCf0nH",
 "bond": "d9TufEgiVsQuqiJYkq 8BniThs4FH4YbS5J90 MvmtHk2HcWAjYqw3Di",
 "mi": "L9yhg3jRezyYvzKz91 Znclz38sX4JBsdUvX3 410Ytf774ydyYYqz1D UFMiPcr91nXMH5TRYz 1ysmspasd9tdpYsUIT Q94c9LjC4pyvGGd5zq 4BMfHbofnYtoRl4IoI uXjPIfCZOnnMgdd2ya",
 "johnwick": "eHF8NfJarCa3nKUo97 iaS1QNDEfz1FCWwAo8 Y1BQIHr3QtpT486CP4",
 "fast": "CQuKVBcvaduOXVK6sz SEFT2l4m1O3XEk78ip IIm772o7MQyF8SQQT6 IWD1nZpcCJtYMXfMfp",
 "madmax": "f2ihFclPjyT77nDeYg GuCYRjQm8HHv6xch4u fa3aApcjHYRtVhfQ0K",
 "indiana": "XHXdqu8y3TzIF0aayR BfB1xwdtTONyhNvtPF zNtobwNBLVYxHj04AR 4UByrOdbimr7JzZp1t gINW8U1PCEq8CeZrLD YEiiKCnGwHkZW5Nxun",
 "matrix": "me0QlO2gKbqBuhFWB8 NJRnk63JCZ4BvCi6ZQ MWP8heXQeUX7ESHis6 xULW8l2gXuRPmsQe8U",
 "alienpred": "B2TP1WvvNS6dEAlelS 7aTa2lDN9CR46MyhiI W6ctY9ig0VavqsIqoW",
 "godzilla": "PpCRVKdGCclKKgeos9 neM93gY5n8S6trjziC Op1VE6lbqtGVBjn4dT hBLT0fBDhK6WcD5gzT IGhU5sVBcodWDP0aB7 RXV5PMfGPd19Rsrv6q gfIJa0nL0MExR5cQut",
 "jurassic": "ScKrxMN0mkXg2nGJ7c FUy4jLKH9gTREgxOqD Kapoly1qtbJ95aXZnE 63kNg2yEEW9uUnFDpG 3ohzdPbvIlusvgwaQw hyMlhZw4mDguJnnPth",
 "apes": "KyNZmLcl8W00pGcreL",
 "terminator": "S8lOY2EXWNdasstiPi SwI5T0cssBR1phwF35 fXDL0YSqaHC8XvELaY 0JgP4J3D0nstRAGx3i",
 "transformers": "mpvtRkRFx3z2HZE2uk dBRgrc9HFUPf8c5JG5 XOI8qT75hJe04vgAcL Ui0lQn1xEL9YLOTaWH ztTr2EQndrO1DHFAOi 5jEFAlzroKlgv72gpg QTXviefMF70DSHKSwF",
 "conjuring": "eduIIYs5LLUGXKb04U 8cSOgFE8wlqYTVMv5F 8JsEd81eATzilHzR0E M8N5F6Asuu8Om31STS A3RTJqJIs6udoonRPZ",
}
def get(gid):
    for u in (f"https://media.giphy.com/media/{gid}/giphy.gif", f"https://i.giphy.com/{gid}.gif"):
        try:
            return gid, urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
        except Exception:
            continue
    return gid, None
def checker(w, h, s=12):
    im = Image.new("RGB", (w, h), (70, 70, 70)); d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2: d.rectangle((x, y, x + s - 1, y + s - 1), fill=(100, 100, 100))
    return im
info = {}
for u, ids in C.items():
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(get, ids.split()))
    rows = []
    for gid, b in res:
        if not b: continue
        g = Image.open(io.BytesIO(b)); fr = [f.convert("RGBA").copy() for f in ImageSequence.Iterator(g)]
        info[gid] = dict(u=u, w=g.width, h=g.height, n=len(fr), kb=len(b) // 1024)
        pick = [fr[min(len(fr) - 1, round(i * (len(fr) - 1) / 5))] for i in range(6)]
        row = Image.new("RGB", (6 * 210, 176), (30, 30, 30)); d = ImageDraw.Draw(row)
        for i, f in enumerate(pick):
            f.thumbnail((200, 150)); bg = checker(f.width, f.height); bg.paste(f, (0, 0), f); row.paste(bg, (i * 210, 0))
        d.text((4, 158), f"{gid}  {g.width}x{g.height}  {len(fr)}fr  {len(b)//1024}KB", fill=(255, 255, 0))
        rows.append(row)
    if rows:
        sheet = Image.new("RGB", (6 * 210, 176 * len(rows)))
        for i, r in enumerate(rows): sheet.paste(r, (0, 176 * i))
        sheet.save(f"refs/stk/{u}.jpg", quality=78)
json.dump(info, open("refs/stk/info.json", "w"), indent=1)
# clean-art sources: Wallhaven (public API, SFW) and fanart.tv (key?) reachability
out = []
for q in ("batman", "wizarding world", "james bond", "star wars"):
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request("https://wallhaven.cc/api/v1/search?" + urllib.parse.urlencode(
            {"q": q, "categories": "010", "purity": "100", "ratios": "16x9", "sorting": "toplist", "atleast": "1920x1080"}), headers=UA), timeout=30).read())
        out.append(f"wallhaven {q}: {r['meta']['total']} results; first: " + ", ".join(x["path"] for x in r["data"][:4]))
    except Exception as e:
        out.append(f"wallhaven {q}: ERR {e}")
try:
    urllib.request.urlopen(urllib.request.Request("https://webservice.fanart.tv/v3/movies/155", headers=UA), timeout=30)
    out.append("fanart.tv: open without key")
except Exception as e:
    out.append(f"fanart.tv without key: {e}")
open("refs/stk/sources.txt", "w").write("\n".join(out))
