"""Can MDBList lists be read without an API key? Try the public endpoints for a few lists."""
import json, os, urllib.request
os.makedirs("refs/mdb", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 nuvio-awards"}
tests = ["https://mdblist.com/lists/mr.psmst/anime-hidden-gems/json",
         "https://mdblist.com/lists/mr.psmst/anime-hidden-gems/json/",
         "https://api.mdblist.com/lists/230335/items",
         "https://api.mdblist.com/lists/198591/items",
         "https://mdblist.com/api/lists/198591/items",
         "https://mdblist.com/?list=198591",
         "https://mdblist.com/lists/thomas.gobin/",
         "https://api.mdblist.com/lists/198591"]
log = []
for u in tests:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40)
        b = r.read()
        log.append(f"OK {r.status} {u} {len(b)} bytes: {b[:300]!r}")
    except Exception as e:
        body = getattr(e, "read", lambda: b"")()[:200]
        log.append(f"FAIL {u} {e} {body!r}")
open("refs/mdb/log.txt", "w").write("\n".join(log))
