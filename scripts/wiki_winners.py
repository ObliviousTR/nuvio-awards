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
        if not re.search(r"\{\{\s*Award category\s*\|[^\n]*$", text[max(0, m.start() - 250):m.start()], re.I):
            continue
        rest = text[m.end():]
        bullet = re.search(r"^\*(?!\*)(.*)$", rest, re.M)
        if not bullet:
            continue
        line = bullet.group(1)
        if "'''" not in line:  # not announced yet: nominees are listed without bold
            continue
        hit = ITALIC_LINK.search(line) or ANY_LINK.search(line)
        if hit:
            return [hit.group(1).strip()]
    return None


def _nearest_italic(text, award):
    """Festival style: the work link closest to the award link on the same line (list and infobox lines first).
    An award line with no work on it ('* Jury Prize:') takes the works on the '**' lines below (ties)."""
    best = None
    for m in _award_link(award).finditer(text):
        ls, le = text.rfind("\n", 0, m.start()) + 1, text.find("\n", m.end())
        line = text[ls:le if le >= 0 else len(text)]
        if line.lstrip()[:1] not in "*|#":  # prose ("competing for the Palme d'Or") is never a result
            continue
        rank = 0
        pos = m.start() - ls
        works = list(ITALIC_LINK.finditer(line))
        if not works and line.lstrip().startswith("*"):
            subs = []
            for nxt in text[le + 1:].split("\n"):
                if not nxt.startswith("**"):
                    break
                w = ITALIC_LINK.search(nxt)
                if w:
                    subs.append(w.group(1).strip())
            if subs:
                return subs
        for w in works:
            dist = min(abs(w.start() - pos), abs(w.end() - pos))
            cand = (rank, dist, w.group(1).strip())
            if best is None or cand < best:
                best = cand
    return [best[2]] if best else None


def _infobox(text, award):
    """Ceremony infobox: | awardN_type = [[Award|..]] / | awardN_winner = ''[[Work]]'' (or plain ''Work'')."""
    for m in re.finditer(r"\|\s*award(\d+)_type\s*=\s*(.*)", text):
        if not _award_link(award).search(m.group(2)):
            continue
        w = re.search(r"\|\s*award" + m.group(1) + r"_winner\s*=\s*(.*)", text)
        if not w:
            continue
        link = ITALIC_LINK.search(w.group(1)) or ANY_LINK.search(w.group(1))
        if link:
            return [link.group(1).strip()]
        plain = re.search(r"''([^'\[\]]+)''", w.group(1))
        if plain:
            return ["plain:" + plain.group(1).strip()]
    return None


def _section_bold(text, section):
    i = text.find(section)
    if i < 0:
        return None
    end = re.search(r"\n==", text[i + len(section):])
    chunk = text[i: i + len(section) + (end.start() if end else len(text))]
    hit = BOLD_ITALIC_LINK.search(chunk)
    return [hit.group(1).strip()] if hit else None


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


TV_KINDS = {"tvSeries", "tvMiniSeries"}


def _imdb_suggest(title, year, tv=False):
    q = urllib.parse.quote(title.lower())
    data = _get(f"https://v3.sg.media-imdb.com/suggestion/x/{q}.json")
    hits = [d for d in data.get("d", []) if d.get("id", "").startswith("tt") and _norm(d.get("l", "")) == _norm(title)]
    if tv:
        hits = [d for d in hits if d.get("qid") in TV_KINDS and (not d.get("y") or int(d["y"]) <= year)]
        hits.sort(key=lambda d: -(d.get("y") or 0))  # the most recent show of that name that existed by then
    else:
        hits = [d for d in hits if not d.get("y") or abs(int(d["y"]) - year) <= 2]
    return hits[0]["id"] if hits else None


def imdb_for(article, year, tv=False):
    if article.startswith("plain:"):
        title = article[6:]
        imdb = _imdb_suggest(title, year, tv)
        if imdb:
            return imdb, title
        raise LookupError(f"no IMDb id for '{title}'")
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
    imdb = _imdb_suggest(label, year, tv)
    if imdb:
        return imdb, label
    raise LookupError(f"no IMDb id for '{article}'")


def winners(cfg, year):
    """All winners of the catalog's award at that year's event (more than one on a tie)."""
    title = page_title(cfg, year)
    text = wikitext(title)
    works = None
    for award in cfg["award"]:
        if cfg["mode"] == "section_bold":
            works = _section_bold(text, cfg["section"]) or _nearest_italic(text, award)
        elif cfg["mode"] == "table":
            works = _from_award_category(text, award) or _infobox(text, award) or _nearest_italic(text, award)
        else:
            works = _nearest_italic(text, award)
        if works:
            break
    if not works:
        raise LookupError(f"winner not found on '{title}'")
    out = []
    for work in works:
        imdb, label = imdb_for(work, year, tv=cfg.get("type") == "series")
        out.append({"title": label, "imdb": imdb, "page": title, "article": work})
    return out
