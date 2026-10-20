"""Find award winners on English Wikipedia event pages and resolve them to IMDb ids through Wikidata.

winner(catalog_cfg, year) -> {"title", "imdb", "page"} or raises LookupError with a reason.
Stdlib only; meant to run in GitHub Actions (Wikipedia/Wikidata are reachable there).
"""
import json, re, time, urllib.parse, urllib.request

UA = "nuvio-awards/2.0 (https://github.com/ObliviousTR/nuvio-awards)"
WP = "https://en.wikipedia.org/w/api.php"


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


LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ITALIC_LINK = re.compile(r"''+\s*\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
BOLD_ITALIC_LINK = re.compile(r"'''''\s*\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def _norm(s):
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    return re.sub(r"[\s'’\-–—]+", " ", s).strip().lower()


def _table_winner(text, labels):
    """Ceremony pages: header row(s) of category names, next row has one cell per category; the winner is
    the first bold (or first) italic link in that cell."""
    want = [_norm(l) for l in labels]
    rows = re.split(r"\n\|-[^\n]*", text)
    for i, row in enumerate(rows):
        headers = [c for c in re.split(r"\n!|!!", "\n" + row) if c.strip()]
        headers = [h.split("|", 1)[-1] if "[[" not in h.split("|", 1)[0] else h for h in headers]
        hnorm = [_norm(h) for h in headers]
        for w in want:
            for col, h in enumerate(hnorm):
                if h == w or h.endswith(" " + w) or h.startswith(w + " ") and len(h) - len(w) < 4:
                    if i + 1 >= len(rows):
                        continue
                    cells = [c for c in re.split(r"\n\|(?!\})", "\n" + rows[i + 1]) if c.strip()]
                    cells = [c for c in cells if not re.fullmatch(r"\s*(valign|style|align)[^|\n]*\|?\s*", c)]
                    if col >= len(cells):
                        continue
                    cell = cells[col]
                    m = BOLD_ITALIC_LINK.search(cell) or ITALIC_LINK.search(cell)
                    if m:
                        return m.group(1).strip()
    raise LookupError(f"no winners table for {labels}")


def _line_winner(text, labels, section=None):
    """Festival pages: '* [[Palme d'Or]]: ''[[Film]]'' by Director' style lists."""
    if section:
        idx = text.find(section)
        text = text[idx:] if idx >= 0 else text
    lines = text.split("\n")
    for label in labels:
        for i, line in enumerate(lines):
            plain = _norm(line)
            if _norm(label) not in plain or plain.startswith("=") or "nominee" in plain:
                continue
            chunk = "\n".join(lines[i:i + 3])
            m = ITALIC_LINK.search(chunk[chunk.find(label) if label in chunk else 0:])
            if m:
                return m.group(1).strip()
    raise LookupError(f"no '{labels[0]}' line")


def imdb_for(title):
    q = urllib.parse.urlencode({"action": "query", "titles": title, "redirects": 1, "prop": "pageprops",
                                "ppprop": "wikibase_item", "format": "json", "formatversion": 2})
    pages = _get(f"{WP}?{q}")["query"]["pages"]
    qid = pages[0].get("pageprops", {}).get("wikibase_item")
    if not qid:
        raise LookupError(f"no Wikidata item for '{title}'")
    q = urllib.parse.urlencode({"action": "wbgetentities", "ids": qid, "props": "claims|labels",
                                "languages": "en", "format": "json"})
    ent = _get(f"https://www.wikidata.org/w/api.php?{q}")["entities"][qid]
    ids = [c["mainsnak"]["datavalue"]["value"] for c in ent.get("claims", {}).get("P345", [])
           if c["mainsnak"].get("datavalue")]
    ids = [i for i in ids if i.startswith("tt")]
    if not ids:
        raise LookupError(f"no IMDb id on Wikidata for '{title}' ({qid})")
    label = ent.get("labels", {}).get("en", {}).get("value", pages[0]["title"])
    return ids[0], label


def winner(cfg, year):
    title = page_title(cfg, year)
    text = wikitext(title)
    if cfg["mode"] == "table":
        work = _table_winner(text, cfg["label"])
    else:
        work = _line_winner(text, cfg["label"], cfg.get("section"))
    imdb, label = imdb_for(work)
    return {"title": label, "imdb": imdb, "page": title}
