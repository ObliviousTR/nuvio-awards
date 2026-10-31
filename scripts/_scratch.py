import os, sys, json
sys.path.insert(0, "scripts")
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
import spotlight as S
import home_lists as NEW, _old_home_lists as OLD
S.IMDB = S.ImdbCache()
# a plausible history (not Ozzy's: no Simkl here) to exercise both versions
mv = [(27205, "2026-10-20", 9, "Inception"), (146233, "2026-09-30", 9, "Prisoners"), (273481, "2026-09-01", 8, "Sicario"),
      (438631, "2026-08-15", 8, "Dune"), (872585, "2026-07-01", 9, "Oppenheimer"), (546554, "2026-06-01", 8, "Knives Out"),
      (299536, "2026-05-01", 7, "Infinity War"), (1124, "2026-04-01", 10, "The Prestige"), (49026, "2026-03-01", None, "TDKR"),
      (335984, "2026-02-01", 8, "Blade Runner 2049"), (11324, "2025-12-01", 9, "Shutter Island"), (155, "2025-10-01", 10, "TDK"),
      (419430, "2026-10-01", 4, "Get Out (low)")]
tv = [(1396, "2026-10-01", 10, "Breaking Bad"), (60059, "2026-09-01", 9, "Better Call Saul"), (95396, "2026-08-01", 9, "Severance"),
      (66732, "2026-07-01", 8, "Stranger Things"), (87108, "2026-06-01", 9, "Chernobyl"), (1405, "2026-05-01", 7, "Dexter"),
      (76479, "2026-04-01", 8, "The Boys"), (100088, "2026-10-10", 9, "The Last of Us"), (46648, "2026-03-01", 9, "True Detective")]
seen = {("movie", t[0]) for t in mv} | {("tv", t[0]) for t in tv}
res = {}
for name, mod in (("old", OLD), ("new", NEW)):
    res[name] = {k: [f"{x.get('title') or x.get('name')} ({x.get('year', '')})" for x in mod.for_you(k, seen, s)]
                 for k, s in (("movie", mv), ("tv", tv))}
json.dump(res, open(f"{OUT}/foryou_test.json", "w"), ensure_ascii=False, indent=1)
for n in res:
    for k in res[n]:
        print(n, k, " | ".join(res[n][k][:40]))
