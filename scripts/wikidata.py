"""Wikidata helpers for the award catalogs (stdlib only, runs in GitHub Actions)."""
import json, time, urllib.parse, urllib.request

UA = "nuvio-awards/2.0 (https://github.com/ObliviousTR/nuvio-awards)"


def _get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def search(text, limit=5):
    q = urllib.parse.urlencode({"action": "wbsearchentities", "search": text, "language": "en",
                                "format": "json", "limit": limit, "type": "item"})
    return [(r["id"], r.get("label", ""), r.get("description", "")) for r in _get(f"https://www.wikidata.org/w/api.php?{q}")["search"]]


def winners(qid):
    """Works that received the award (directly, or via a person's 'for work' qualifier) with an IMDb id."""
    sparql = f"""
    SELECT DISTINCT ?imdb ?label ?date WHERE {{
      {{ ?work p:P166 ?st . ?st ps:P166 wd:{qid} . OPTIONAL {{ ?st pq:P585 ?date }} }}
      UNION
      {{ ?who p:P166 ?st . ?st ps:P166 wd:{qid} ; pq:P1686 ?work . OPTIONAL {{ ?st pq:P585 ?date }} }}
      ?work wdt:P345 ?imdb . FILTER(STRSTARTS(?imdb, "tt"))
      OPTIONAL {{ ?work rdfs:label ?label FILTER(LANG(?label) = "en") }}
    }}"""
    q = urllib.parse.urlencode({"query": sparql, "format": "json"})
    rows = _get(f"https://query.wikidata.org/sparql?{q}")["results"]["bindings"]
    out = []
    for b in rows:
        date = b.get("date", {}).get("value", "")
        out.append(dict(imdb=b["imdb"]["value"], title=b.get("label", {}).get("value", b["imdb"]["value"]),
                        year=int(date[:4]) if date[:4].isdigit() else None))
    return out
