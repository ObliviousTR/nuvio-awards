"""Is the MDBLIST_API_KEY secret there and working? (prints no key)"""
import json, os, urllib.request
os.makedirs("refs/mdbkey", exist_ok=True)
k = os.environ.get("MDBLIST_API_KEY", "")
log = [f"secret present: {bool(k)}, length {len(k)}"]
if k:
    for u in ("https://api.mdblist.com/user", "https://api.mdblist.com/lists/198591/items?limit=5"):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u + ("&" if "?" in u else "?") + "apikey=" + k,
                                                             headers={"User-Agent": "nuvio-awards"}), timeout=40)
            b = json.loads(r.read())
            if isinstance(b, dict):
                b = {x: (y if x in ("limits", "api_requests", "api_requests_count", "patron_status") else "...") for x, y in b.items()}
            log.append(f"OK {u.split('?')[0]}: {json.dumps(b)[:300]}")
        except Exception as e:
            log.append(f"FAIL {u.split('?')[0]}: {e}")
open("refs/mdbkey/log.txt", "w").write("\n".join(log).replace(k, "<key>") if k else "\n".join(log))
