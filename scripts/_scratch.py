"""Posters Plus: which parameters does it take (language / logo / background)?"""
import os, re, urllib.request, urllib.parse
OUT = "refs/pplus"; os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 nuvio-awards"}
seen, queue, log = set(), ["https://postersplus.slokker.cc/"], []
while queue and len(seen) < 25:
    u = queue.pop(0)
    if u in seen: continue
    seen.add(u)
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60)
        body = r.read().decode("utf-8", "replace")
    except Exception as e:
        log.append(f"{u} -> {e}"); continue
    name = re.sub(r"[^a-z0-9]+", "_", urllib.parse.urlsplit(u).path.lower()).strip("_") or "index"
    open(f"{OUT}/{name}.txt", "w").write(body)
    log.append(f"{u} -> {len(body)} bytes")
    for m in re.findall(r'(?:src|href)="([^"]+)"', body):
        v = urllib.parse.urljoin(u, m)
        if v.startswith("https://postersplus.slokker.cc/") and re.search(r"\.(js|html?)$|/$|/docs|/api|/config", v) and v not in seen:
            queue.append(v)
hits = set()
for f in os.listdir(OUT):
    t = open(f"{OUT}/{f}", encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"[\"'`]?([a-z_]*(?:lang|locale|language|logo_src|logo_source|bg_src|background|textless|poster_src|art_lang)[a-z_]*)[\"'`]?\s*[:=]", t):
        hits.add(m.group(1))
open(f"{OUT}/_log.txt", "w").write("\n".join(log) + "\n\nparams:\n" + "\n".join(sorted(hits)))
print("\n".join(log)); print(sorted(hits))
