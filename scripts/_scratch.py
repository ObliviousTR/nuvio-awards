import os, sys, json, datetime as dt
# Spotlight hovers: for each card's current subject, the cover arguments and the hover films (TMDB paths only).
sys.path.insert(0, "scripts")
import spotlight as S
OUT = "refs/spotlight"; os.makedirs(OUT, exist_ok=True)
S.IMDB = S.ImdbCache(); S.AUTO = json.load(open("spotlight/pool_auto.json"))
today = dt.datetime.utcnow().date()
pool = json.load(open("spotlight/pool.json", encoding="utf-8")); pool["prestige"] = S.prestige_pool()
for slot in S.ROTATING:
    pool[slot] = pool[slot] + S.AUTO.get(slot, [])
state = json.load(open("spotlight/state.json"))
res = {}
for slot in S.ROTATING:
    subj = state["cards"][slot]["subject"]
    _, m, s, a, notes = S.build_rotating(slot, pool, state, today, state["cards"][slot]["period"], [], False, subj)
    a["backdrop"] = state["backdrops"][slot]
    films = S.hover_films(slot, a, m, s)
    a.pop("picks", None)
    res[slot] = dict(a=a, films=films)
    print(slot, subj, [f["title"] for f in films])
t = S.pulse_theme(pool, today, state.get("pulse_override"))
m, s, a, notes = S.pulse_card(t, today)
a["backdrop"] = state["backdrops"]["pulse"]
res["pulse"] = dict(a=a, films=S.hover_films("pulse", a, m, s))
print("pulse", [f["title"] for f in res["pulse"]["films"]])
json.dump(res, open(f"{OUT}/hover_inputs.json", "w"), ensure_ascii=False, indent=1)
