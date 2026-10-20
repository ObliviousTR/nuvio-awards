"""Check the Wikipedia winner parser against winners we already know (2025 and 2026 events) -> data/selftest.md"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from wiki_winners import winner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
events = {k: v for k, v in json.load(open(os.path.join(ROOT, "data", "events.json"))).items() if not k.startswith("_")}
known = {}
for line in open(os.path.join(ROOT, "data", "additions.txt"), encoding="utf-8"):
    if line.strip() and not line.startswith("#"):
        cid, year, imdb, _, title = line.rstrip("\n").split("|", 4)
        known.setdefault(cid, set()).add(imdb)
for cid in events:
    for line in open(os.path.join(ROOT, "data", "base", f"{cid}.txt"), encoding="utf-8"):
        known.setdefault(cid, set()).add(line.split("|", 1)[0])
out, ok, bad = ["# Wikipedia parser self-test", ""], 0, 0
for cid, cfg in events.items():
    for year in (2025, 2026):
        try:
            w = winner(cfg, year)
            hit = w["imdb"] in known.get(cid, set())
            ok += hit; bad += not hit
            out.append(f"- {'OK ' if hit else 'NEW'} {cid} {year}: {w['title']} {w['imdb']}  ({w['page']})")
        except Exception as e:
            bad += 1
            out.append(f"- ERR {cid} {year}: {e}")
out.insert(1, f"{ok} matched known winners, {bad} not matched/errors")
open(os.path.join(ROOT, "data", "selftest.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
