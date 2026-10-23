"""Organize Isler (tmdb:339300): what does AIOMetadata return directly vs through the worker?"""
import json, os, urllib.parse, urllib.request
AIO = os.environ["AIOMETADATA_URL"].strip()
u = urllib.parse.urlsplit(AIO)
PATH = u.path.rsplit("/manifest.json", 1)[0]
DIRECT = f"{u.scheme}://{u.netloc}{PATH}"
acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip()
sub = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/subdomain",
      headers={"Authorization": "Bearer " + tok}), timeout=60).read())["result"]["subdomain"]
WORK = f"https://nuvio-tr.{sub}.workers.dev{PATH}"
TMDB = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/trproxy"; os.makedirs(OUT, exist_ok=True)


def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"}), timeout=90).read())


def short(m):
    m = dict(m or {})
    v = m.pop("videos", None) or []
    for k in list(m):
        if isinstance(m[k], str) and len(m[k]) > 140:
            m[k] = m[k][:140] + "..."
    m["videos(count)"] = len(v)
    m["videos(first)"] = v[:2]
    return m


rep = []
for t, i in (("series", "tmdb:339300"), ("series", "tt39397536")):
    for lab, base in (("direct", DIRECT), ("worker", WORK)):
        try:
            rep.append(f"== {i} {lab}\n" + json.dumps(short(get(f"{base}/meta/{t}/{i}.json").get("meta")), ensure_ascii=False, indent=1))
        except Exception as e:
            rep.append(f"== {i} {lab}: {e}")
ext = json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/tv/339300?api_key={TMDB}&append_to_response=external_ids", timeout=60).read())
rep.append(f"TMDB 339300: {ext.get('name')} / {ext.get('original_name')} first_air {ext.get('first_air_date')} seasons {[ (s.get('season_number'), s.get('episode_count')) for s in ext.get('seasons', [])]} ext {ext.get('external_ids')}")
nf = get(f"{DIRECT}/catalog/series/flixpatrol.netflix.tr.series.json")["metas"][:1]
rep.append("catalog item direct: " + json.dumps(nf, ensure_ascii=False)[:900])
txt = "\n".join(rep).replace(PATH, "<path>").replace(u.netloc, "<aio-host>").replace(TMDB, "***")
open(f"{OUT}/organize.txt", "w").write(txt + "\n"); print(txt)
