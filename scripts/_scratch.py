"""MDBList: find the public slug of each list we use (by its numeric id on the author's pages) and count its items."""
import json, os, re, urllib.request, time
os.makedirs("refs/mdb", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 nuvio-awards"}
cfg = json.load(open("builder/aio/setup-2026-10-23-in.json"))
WANT = [228941, 164980, 164919, 198591, 148283, 230335, 122821, 34134, 146624, 146622, 146625, 146627, 32972, 32970,
        13676, 13675, 13674, 132014, 205902, 207869, 205811]
author = {c.get("listId") or int(c["id"].split(".")[1]): (c.get("metadata") or {}).get("author") for c in cfg["catalogs"] if c["id"].startswith("mdblist.")}
def get(u):
    for k in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            err = e; time.sleep(3)
    raise err
out, log = {}, []
pages = {}
for lid in WANT:
    a = author.get(lid)
    if not a:
        log.append(f"{lid}: no author"); continue
    if a not in pages:
        html = get(f"https://mdblist.com/lists/{a}/")
        pages[a] = sorted(set(re.findall(rf'href="/lists/{re.escape(a)}/([^"/?#]+)', html)))
        log.append(f"{a}: {len(pages[a])} lists")
    found = None
    for slug in pages[a]:
        html = get(f"https://mdblist.com/lists/{a}/{slug}")
        if re.search(rf'\b{lid}\b', html):
            found = slug
            break
    if not found:
        log.append(f"{lid}: slug not found among {pages[a][:20]}"); continue
    items = json.loads(get(f"https://mdblist.com/lists/{a}/{found}/json"))
    out[lid] = {"author": a, "slug": found, "count": len(items)}
    log.append(f"{lid}: {a}/{found} {len(items)} items, first: {items[0].get('title') if items else None} keys {list(items[0].keys()) if items else []}")
json.dump(out, open("refs/mdb/slugs.json", "w"), indent=1)
open("refs/mdb/log.txt", "w").write("\n".join(log))
