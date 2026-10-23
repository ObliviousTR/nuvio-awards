"""Organize Isler: Karun Hazinesi on TMDB - is there a fuller entry than 339300?"""
import json, os, urllib.parse, urllib.request
K = os.environ["TMDB_API_KEY"].strip()
OUT = "refs/trproxy"; os.makedirs(OUT, exist_ok=True)
def t(p, **q):
    q["api_key"] = K
    return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{p}?" + urllib.parse.urlencode(q), timeout=60).read())
rep = []
for q in ("Organize İşler", "Money Trap", "Karun"):
    for kind in ("tv", "movie"):
        for r in t(f"search/{kind}", query=q)["results"][:8]:
            d = t(f"{kind}/{r['id']}", append_to_response="external_ids")
            rep.append(f"{q!r} {kind} {r['id']}: {d.get('name') or d.get('title')} / {d.get('original_name') or d.get('original_title')} "
                       f"date {d.get('first_air_date') or d.get('release_date')} poster {'yes' if d.get('poster_path') else 'no'} "
                       f"backdrop {'yes' if d.get('backdrop_path') else 'no'} eps {d.get('number_of_episodes')} "
                       f"imdb {d.get('external_ids', {}).get('imdb_id')} lang {d.get('original_language')} networks {[n['name'] for n in d.get('networks', [])]}")
txt = "\n".join(dict.fromkeys(rep)).replace(K, "***")
open(f"{OUT}/organize2.txt", "w").write(txt + "\n"); print(txt)
