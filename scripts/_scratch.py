"""Catalog poster URLs for Turkish items: what form do they take (worker vs direct)?"""
import json, os, re, urllib.parse, urllib.request
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
D = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
sub = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain",
      headers={"Authorization": "Bearer " + tok}), timeout=60).read())["result"]["subdomain"]
W = f"https://nuvio-tr.{sub}.workers.dev{PATH}"
OUT = "refs/tracc"; os.makedirs(OUT, exist_ok=True)
def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=60).read())
rep = []
for t, c in (("movie", "flixpatrol.netflix.tr.movie"), ("series", "flixpatrol.netflix.tr.series")):
    a, b = get(f"{W}/catalog/{t}/{c}.json"), get(f"{D}/catalog/{t}/{c}.json")
    for x, y in zip(a["metas"], b["metas"]):
        if x.get("name") != y.get("name"):
            rep.append(f"{y['id']} {y['name']!r} -> {x['name']!r}")
            for f in ("poster", "logo", "background"):
                rep.append(f"   {f} worker: {str(x.get(f))[:260]}")
                rep.append(f"   {f} direct: {str(y.get(f))[:260]}")
            rep.append(f"   keys: {sorted(x)}")
txt = "\n".join(rep)
for s in (PATH, urllib.parse.quote(PATH, safe=""), PATH.split("/")[-1], u.netloc):
    txt = txt.replace(s, "<x>")
open(f"{OUT}/catposter.txt", "w").write(txt + "\n"); print(txt)
