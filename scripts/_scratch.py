import os, io, json, urllib.request, concurrent.futures as cf
from PIL import Image, ImageSequence, ImageDraw
os.makedirs("refs/gif", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
C = {
 "mcu": "10ADhj1QPawFna NUsKoYiGm1RPHl1eWM PmFpJVVXjbZl4iRwWK Nk5GOMLGMPB6g IhOZQhKKVkQyCvYRSS LA2CdQtSj0KfOuZ0Wh 3ov9kbNvyGQt71EVJ6",
 "bond": "3o85xmm5dm9dUOV1Re 5ub8PQ6NYXuCgnmF9p QiSA2VfUsQgu1emmN9 3o6fIYxb0CXpYAEZMI fSSTnNq8ZKKc0 26uf2rIZX5fhKaIrm",
 "wizarding": "H6Epdyz7fjCCBNUW80",
 "starwars": "l1uguGf2RVIsTXNDO GoeAgxrr0lkqI dvD7tyzx38ccrCkSQN 5wikad3qSOqAg 3oEdv03nb7yaQQJfEY d2Z833qjHtEIfxD2",
 "batman": "fZ9HskQBBeBhe SgBFcIje2WNkk 3o7aDdcQx11g5eSG9q KJgUXGbWZ4NNHao2DO",
 "spiderman": "W2u4SUQ4C9zP18B9Na 2cfdgTni5AkHm k0oQX8bo3BFumjnSKK Af9SdN3B8xblEobPln HZMTEoz9K9Mxa dB4mmxqxAHbWkMX91U nR4f2N4SOARyM",
 "xmen": "RfjVSLS9ngamagRc6V hVIRzkRs1UcYi70Z05 NnDYDoc9XVXhkigHPn 3o85g3kVp71g6i42ly",
 "lotr": "W4bPsfAh9iYfe XgE4LlECZjw6k KOi0Y5N1BWQJG RB7HBNCuzR0fzjv8Rj 2XflxzGoMXkpe9bvyk8",
 "startrek": "3og0ILocFFVTlrRAbu g1Xx49lSthethnAbcu URphtArd9IVtSsqk3Z 3o7aCXdmWiaMCOFIpG Xa3t5TBdH7Kak7ftcv",
 "mi": "AT1qsBCUcEHj2rBziM xUA7aY5OvnxIo5idY4",
 "dc": "3c5rvyUlKpdBcNV6PU vN3Ec0hJ2iagjTLHmF",
}
def get(gid):
    try:
        return gid, urllib.request.urlopen(urllib.request.Request(f"https://media.giphy.com/media/{gid}/giphy.gif", headers=UA), timeout=60).read()
    except Exception as e:
        return gid, None
info = {}
for u, ids in C.items():
    ids = ids.split()
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(get, ids))
    rows = []
    for gid, b in res:
        if not b: continue
        g = Image.open(io.BytesIO(b)); fr = [f.convert("RGB").copy() for f in ImageSequence.Iterator(g)]
        info[gid] = dict(u=u, w=g.width, h=g.height, n=len(fr), kb=len(b) // 1024)
        pick = [fr[min(len(fr) - 1, round(i * (len(fr) - 1) / 5))] for i in range(6)]
        row = Image.new("RGB", (6 * 260, 170), (40, 40, 40)); d = ImageDraw.Draw(row)
        for i, f in enumerate(pick):
            f.thumbnail((256, 150)); row.paste(f, (i * 260, 0))
        d.text((4, 152), f"{gid}  {g.width}x{g.height}  {len(fr)}fr  {len(b)//1024}KB", fill=(255, 255, 0))
        rows.append(row)
    if rows:
        sheet = Image.new("RGB", (6 * 260, 170 * len(rows)))
        for i, r in enumerate(rows): sheet.paste(r, (0, 170 * i))
        sheet.save(f"refs/gif/{u}.jpg", quality=80)
json.dump(info, open("refs/gif/info.json", "w"), indent=1)
