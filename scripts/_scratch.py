"""Why do three MDBList lists fail through the API? (prints no key)"""
import json, os, urllib.request
os.makedirs("refs/mdbfail", exist_ok=True)
k = os.environ.get("MDBLIST_API_KEY", "")
log = []
for lid in (228941, 148283, 132014, 164980):
    for u in (f"https://api.mdblist.com/lists/{lid}", f"https://api.mdblist.com/lists/{lid}/items?limit=5"):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u + ("&" if "?" in u else "?") + "apikey=" + k, headers={"User-Agent": "nuvio-awards"}), timeout=60)
            b = r.read().decode()
            log.append(f"OK {lid} {u.split('/')[-1][:12]}: {b[:400]}")
        except Exception as e:
            body = getattr(e, "read", lambda: b"")()[:300]
            log.append(f"FAIL {lid} {u.split('/')[-1][:12]}: {e} {body!r}")
open("refs/mdbfail/log.txt", "w").write("\n".join(log).replace(k, "<key>") if k else "\n".join(log))
