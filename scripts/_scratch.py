import os, json, urllib.request
os.makedirs("refs/fa", exist_ok=True)
k = os.environ.get("FANART_API_KEY", "")
out = [f"key present: {bool(k)} len {len(k)}"]
for mid in (671, 11):  # Harry Potter 1, Star Wars
    try:
        d = json.loads(urllib.request.urlopen(f"https://webservice.fanart.tv/v3/movies/{mid}?api_key={k}", timeout=30).read())
        out.append(f"{mid} {d.get('name')}: " + ", ".join(f"{t}={len(v)}" for t, v in d.items() if isinstance(v, list)))
    except Exception as e:
        out.append(f"{mid} ERR {e}")
open("refs/fa/out.txt", "w").write("\n".join(out))
