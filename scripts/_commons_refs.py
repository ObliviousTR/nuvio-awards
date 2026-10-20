"""Temporary: list free-licence sports photos on Wikimedia Commons, download thumbnails for review."""
import json, os, urllib.parse, urllib.request
UA = {"User-Agent": "nuvio-awards design refs (github.com/ObliviousTR/nuvio-awards)"}
API = "https://commons.wikimedia.org/w/api.php"
CATS = ["Featured pictures of association football", "Featured pictures of basketball", "Featured pictures of motorsport",
        "Featured pictures of tennis", "Featured pictures of sports", "Featured pictures of stadiums",
        "Quality images of association football stadiums", "Featured pictures of Formula One"]
os.makedirs("refs/commons", exist_ok=True)
out = []
for cat in CATS:
    q = {"action": "query", "generator": "categorymembers", "gcmtitle": "Category:" + cat, "gcmtype": "file",
         "gcmlimit": "200", "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": "480",
         "iiextmetadatafilter": "LicenseShortName|Artist", "format": "json"}
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers=UA), timeout=60).read())
    except Exception as e:
        print("fail", cat, e); continue
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 1)
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        if w < 1800 or w / h < 1.3 or not any(x in lic.lower() for x in ("cc by", "cc0", "public domain", "pd")):
            continue
        out.append({"cat": cat, "title": p["title"], "w": w, "h": h, "license": lic, "url": ii["url"], "thumb": ii.get("thumburl")})
print(len(out))
for i, o in enumerate(out[:120]):
    fn = f"refs/commons/{i:03d}.jpg"
    try:
        open(fn, "wb").write(urllib.request.urlopen(urllib.request.Request(o["thumb"], headers=UA), timeout=60).read())
        o["file"] = fn
    except Exception as e:
        print("thumb fail", o["title"], e)
json.dump(out[:120], open("refs/commons/index.json", "w"), indent=1)
