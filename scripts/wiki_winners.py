"""Find award winners on English Wikipedia event pages and resolve them to IMDb ids.

winner(catalog_cfg, year) -> {"title", "imdb", "page", "article"}, or raises LookupError with a reason.
Categories are recognised by the link to the award's own article (e.g. [[Golden Globe Award for Best Director|...]]),
which is far more stable than the visible label. Stdlib only; runs in GitHub Actions.
"""
import json, re, time, urllib.parse, urllib.request

UA = "nuvio-awards/2.0 (https://github.com/ObliviousTR/nuvio-awards)"
WP = "https://en.wikipedia.org/w/api.php"
LINK_BODY = r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]"
ITALIC_LINK = re.compile(r"(?<!')(?:''|''''')(?!')\s*" + LINK_BODY)   # ''[[Work]] or '''''[[Work]] (not '''[[Person]])
BOLD_ITALIC_LINK = re.compile(r"'''''\s*" + LINK_BODY)
ANY_LINK = re.compile(LINK_BODY)


def _get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(4 * (i + 1))


def ordinal(n):
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def page_title(cfg, year):
    edition = year - cfg["edition_base"] if "edition_base" in cfg else None
    return cfg["page"].format(year=year, ord=ordinal(edition) if edition else "")


def wikitext(title):
    q = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext", "redirects": 1,
                                "format": "json", "formatversion": 2})
    d = _get(f"{WP}?{q}")
    if "error" in d:
        raise LookupError(f"page '{title}' not found")
    return d["parse"]["wikitext"]


def _award_link(award):
    a = re.escape(award).replace(r"\ ", r"[ _]")
    return re.compile(r"\[\[\s*" + a + r"\s*(?:\|[^\]]*)?\]\]", re.I)


def _from_award_category(text, award):
    """{{Award category|color|[[Award article|Label]]}} followed by '* '''''[[Winner]]'''''..."""
    for m in _award_link(award).finditer(text):
        head = text.rfind("{{", 0, m.start())
        if head < 0 or not re.match(r"\{\{\s*Award category", text[head:m.start()], re.I):
            continue
        rest = text[m.end():]
        bullet = re.search(r"^\*(?!\*)(.*)$", rest, re.M)
        if not bullet:
            continue
        line = bullet.group(1)
        hit = ITALIC_LINK.search(line) or ANY_LINK.search(line)
        if hit:
            return hit.group(1).strip()
    return None


def _nearest_italic(text, award):
    """Festival style: the work link closest to the award link on the same line (lists and infobox lines first)."""
    best = None
    for m in _award_link(award).finditer(text):
        ls, le = text.rfind("\n", 0, m.start()) + 1, text.find("\n", m.end())
        line = text[ls:le if le >= 0 else len(text)]
        rank = 0 if line.lstrip()[:1] in "*|#" else 1
        pos = m.start() - ls
        for w in ITALIC_LINK.finditer(line):
            dist = min(abs(w.start() - pos), abs(w.end() - pos))
            cand = (rank, dist, w.group(1).strip())
            if best is None or cand < best:
                best = cand
    return best[2] if best else None


def _section_bold(text, section):
    i = text.find(section)
    if i < 0:
        return None
    end = re.search(r"\n==", text[i + len(section):])
    chunk = text[i: i + len(section) + (end.start() if end else len(text))]
    hit = BOLD_ITALIC_LINK.search(chunk)
    return hit.group(1).strip() if hit else None


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _imdb_suggest(title, year):
    q = urllib.parse.quote(title.lower())
    data = _get(f"https://v3.sg.media-imdb.com/suggestion/x/{q}.json")
    for d in data.get("d", []):
        if d.get("id", "").startswith("tt") and _norm(d.get("l", "")) == _norm(title) and \
                (not d.get("y") or abs(int(d["y"]) - year) <= 2):
            return d["id"]
    return None


def imdb_for(article, year):
    q = urllib.parse.urlencode({"action": "query", "titles": article, "redirects": 1, "prop": "pageprops",
                                "ppprop": "wikibase_item", "format": "json", "formatversion": 2})
    page = _get(f"{WP}?{q}")["query"]["pages"][0]
    label = re.sub(r"\s*\((?:[^()]*\b(?:film|TV series|series|miniseries)\b[^()]*)\)$", "", page.get("title", article))
    qid = page.get("pageprops", {}).get("wikibase_item")
    if qid:
        q = urllib.parse.urlencode({"action": "wbgetentities", "ids": qid, "props": "claims|labels",
                                    "languages": "en", "format": "json"})
        ent = _get(f"https://www.wikidata.org/w/api.php?{q}")["entities"][qid]
        ids = [c["mainsnak"]["datavalue"]["value"] for c in ent.get("claims", {}).get("P345", [])
               if c["mainsnak"].get("datavalue")]
        ids = [i for i in ids if i.startswith("tt")]
        label = ent.get("labels", {}).get("en", {}).get("value", label)
        if ids:
            return ids[0], label
    imdb = _imdb_suggest(label, year)
    if imdb:
        return imdb, label
    raise LookupError(f"no IMDb id for '{article}'")


def winner(cfg, year):
    title = page_title(cfg, year)
    text = wikitext(title)
    work = None
    for award in cfg["award"]:
        if cfg["mode"] == "section_bold":
            work = _section_bold(text, cfg["section"]) or _nearest_italic(text, award)
        elif cfg["mode"] == "table":
            work = _from_award_category(text, award) or _nearest_italic(text, award)
        else:
            work = _nearest_italic(text, award)
        if work:
            break
    if not work:
        raise LookupError(f"winner not found on '{title}'")
    imdb, label = imdb_for(work, year)
    return {"title": label, "imdb": imdb, "page": title, "article": work}
