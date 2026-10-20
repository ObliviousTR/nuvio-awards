"""Automatic update, run by .github/workflows/update.yml.

1. Oscars: refresh data/sources/oscars.csv from DLu/oscar_data.
2. Other awards: for every catalog in data/events.json, look at each event since last_event_year on English
   Wikipedia; when the winner is announced, append it to data/additions.txt and advance last_event_year.
   A winner still missing two months after the usual event month is reported once.
Writes a Turkish summary to the file given as argv[1] (empty when there is nothing to report).
"""
import csv, datetime, io, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from wiki_winners import winners

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
NAMES = {c["id"]: c["name"] for c in json.load(open(D("data", "catalogs.json"), encoding="utf-8"))["catalogs"]}


def known_ids(cid):
    ids = {l.split("|", 1)[0] for l in open(D("data", "base", f"{cid}.txt"), encoding="utf-8")}
    for l in open(D("data", "additions.txt"), encoding="utf-8"):
        if l.startswith(cid + "|"):
            ids.add(l.split("|")[2])
    return ids


def update_oscars(report):
    path = D("data", "sources", "oscars.csv")
    newest = lambda t: max(int(r["Ceremony"]) for r in csv.DictReader(io.StringIO(t), delimiter="\t"))
    old = open(path, encoding="utf-8").read()
    try:
        req = urllib.request.Request("https://raw.githubusercontent.com/DLu/oscar_data/main/oscars.csv",
                                     headers={"User-Agent": "nuvio-awards"})
        new = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    except Exception as e:
        print(f"oscars.csv download failed: {e!r}")
        return
    if new == old or newest(new) < newest(old):
        return
    open(path, "w", encoding="utf-8").write(new)
    a, b = newest(old), newest(new)
    report.append(f"- **Oscar:** veriler yenilendi ({a}. tören → {b}. tören)" if b > a
                  else f"- **Oscar:** {b}. tören verileri güncellendi (adaylar/kazananlar)")


def update_events(report, warnings):
    path = D("data", "events.json")
    events = json.load(open(path, encoding="utf-8"))
    today = datetime.date.today()
    added = []
    for cid, cfg in events.items():
        if cid.startswith("_"):
            continue
        for year in range(cfg["last_event_year"] + 1, today.year + 1):
            try:
                found = winners(cfg, year)
            except Exception as e:
                overdue = (today.year, today.month) >= (year + (cfg["month"] + 2 > 12), (cfg["month"] + 2 - 1) % 12 + 1)
                if overdue and year not in cfg.get("warned", []):
                    warnings.append(f"- **{NAMES.get(cid, cid)} {year}:** kazanan otomatik bulunamadı ({e}).")
                    cfg.setdefault("warned", []).append(year)
                break  # later events can't be in yet either
            have = known_ids(cid)
            for w in found:
                if w["imdb"] in have:
                    continue
                with open(D("data", "additions.txt"), "a", encoding="utf-8") as f:
                    f.write(f"{cid}|{year + cfg['year_offset']}|{w['imdb']}||{w['title']}\n")
                added.append(f"- **{NAMES.get(cid, cid)}:** {w['title']} ({year})")
            cfg["last_event_year"] = year
            cfg.pop("warned", None)
    json.dump(events, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    report.extend(added)


def main():
    report, warnings = [], []
    update_oscars(report)
    update_events(report, warnings)
    text = ""
    if report:
        text += "Nuvio Awards eklentisine eklenenler:\n\n" + "\n".join(report) + "\n\n"
        text += "Nuvio bir sonraki yenilemede bunları kendisi gösterir, senin bir şey yapman gerekmiyor.\n"
    if warnings:
        text += ("\n" if text else "") + "Kontrol edilmesi gerekenler:\n\n" + "\n".join(warnings) + "\n\n" \
                "Wikipedia sayfası henüz güncellenmemiş ya da biçimi değişmiş olabilir; sonraki çalışmalar yeniden dener.\n"
    out = sys.argv[1] if len(sys.argv) > 1 else D("summary.md")
    open(out, "w", encoding="utf-8").write(text)
    print(text or "nothing new")


if __name__ == "__main__":
    main()
