import os, json, re, subprocess, urllib.request, urllib.parse
# Ozzy's poster settings, read back for him: the Posters+ address AIOMetadata uses now and the TR proxy's base. Both
# carry private parts (the AIOMetadata config path), so the output is encrypted to a one-off public key
# (scripts/_scratch_pub.pem); nothing readable is written or printed.
OUT = "refs/posters"; os.makedirs(OUT, exist_ok=True)
aio = os.environ["AIOMETADATA_URL"].strip()
base = aio.rsplit("/manifest.json", 1)[0]
path = urllib.parse.urlsplit(base).path


def get(u, headers=None):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", **(headers or {})}), timeout=120).read())


lines = []
try:
    tok, acc = os.environ["CLOUDFLARE_API_TOKEN"], os.environ["CLOUDFLARE_ACCOUNT_ID"]
    sub = get(f"https://api.cloudflare.com/client/v4/accounts/{acc}/workers/subdomain", {"Authorization": "Bearer " + tok})["result"]["subdomain"]
    proxy = f"https://nuvio-tr.{sub}.workers.dev{path}"
    lines.append("TR proxy manifest: " + proxy + "/manifest.json")
except Exception as e:
    proxy = None
    lines.append("TR proxy: could not read the workers.dev subdomain: " + type(e).__name__)
for t, cid, genre in (("movie", "tmdb.trending", "Day"), ("series", "tmdb.trending", "Week")):
    try:
        metas = get(f"{base}/catalog/{t}/{cid}/genre={genre}.json").get("metas", [])
        for m in metas[:2]:
            lines.append(f"AIOMetadata poster ({t}, {m.get('name')}, {m.get('id')}): {m.get('poster')}")
    except Exception as e:
        lines.append(f"AIOMetadata {t}: {type(e).__name__}")
if proxy:
    try:
        metas = get(f"{proxy}/catalog/movie/tmdb.trending/genre=Day.json").get("metas", [])
        lines.append(f"via TR proxy, poster of {metas[0].get('name')}: {metas[0].get('poster')}")
    except Exception as e:
        lines.append("via TR proxy: " + type(e).__name__)
open("/tmp/p.txt", "w").write("\n".join(lines) + "\n")
subprocess.run("openssl rand -hex 32 > /tmp/k && openssl enc -aes-256-cbc -pbkdf2 -pass file:/tmp/k -in /tmp/p.txt "
               f"-out {OUT}/p.enc && openssl pkeyutl -encrypt -pubin -inkey scripts/_scratch_pub.pem "
               f"-pkeyopt rsa_padding_mode:oaep -in /tmp/k -out {OUT}/k.enc && rm -f /tmp/p.txt /tmp/k", shell=True, check=True)
print("written", len(lines), "lines (encrypted)")
