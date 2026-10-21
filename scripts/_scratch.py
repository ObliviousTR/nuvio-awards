"""Temporary: what each proposed universe / franchise / person actually has on TMDB."""
import datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spotlight as S
from spotlight import tmdb, find_keywords, find_collection, norm

S.IMDB = S.ImdbCache()
OUT = "refs/franchises"
os.makedirs(OUT, exist_ok=True)
today = dt.date.today().isoformat()

UNIVERSES = {
 "Batman & Gotham": dict(cols=["The Dark Knight Collection", "Batman Collection", "The Batman Collection", "Joker Collection"], kw=["batman"]),
 "Spider-Man": dict(cols=["Spider-Man Collection", "The Amazing Spider-Man Collection", "Spider-Man (Avengers) Collection", "Spider-Man: Spider-Verse Collection", "Venom Collection"], kw=["spider-man"]),
 "X-Men & Mutants": dict(cols=["X-Men Collection", "Deadpool Collection", "Wolverine Collection"], kw=["x-men", "mutant"]),
 "Marvel Cinematic Universe": dict(cols=["The Avengers Collection"], kw=["marvel cinematic universe (mcu)"]),
 "DC Universe": dict(cols=["Superman Collection", "Man of Steel Collection", "Wonder Woman Collection", "Aquaman Collection", "Shazam! Collection"], kw=["dc extended universe (dceu)", "dc universe (dcu)", "superman", "justice league", "wonder woman"]),
 "Star Wars": dict(cols=["Star Wars Collection"], kw=["star wars"]),
 "Star Trek": dict(cols=["Star Trek: The Original Series Collection", "Star Trek: The Next Generation Collection", "Star Trek: Alternate Reality Collection"], kw=["star trek"]),
 "Middle-earth": dict(cols=["The Lord of the Rings Collection", "The Hobbit Collection"], kw=["middle-earth (tolkien)", "tolkien", "middle-earth"]),
 "MonsterVerse & Kaiju": dict(cols=["Godzilla (MonsterVerse) Collection", "Kong Collection", "Godzilla x Kong Collection", "Pacific Rim Collection"], kw=["monsterverse", "godzilla", "king kong", "kaiju"]),
 "Alien & Predator": dict(cols=["Alien Collection", "Predator Collection", "AVP Collection", "Alien vs. Predator Collection"], kw=["xenomorph", "predator"]),
}
SINGLES = {
 "Wizarding World": dict(cols=["Harry Potter Collection", "Fantastic Beasts Collection"], kw=["wizarding world"], tv=["Harry Potter"]),
 "007 James Bond": dict(cols=["James Bond Collection"], kw=["james bond"]),
 "Dune": dict(cols=["Dune Collection"], kw=["dune (franchise)", "arrakis"], tv=["Dune: Prophecy", "Frank Herbert's Dune", "Frank Herbert's Children of Dune"], movies=["Dune"]),
 "John Wick": dict(cols=["John Wick Collection"], tv=["The Continental: From the World of John Wick"], movies=["Ballerina"]),
 "Mission: Impossible": dict(cols=["Mission: Impossible Collection"], tv=["Mission: Impossible"]),
 "The Matrix": dict(cols=["The Matrix Collection"], movies=["The Animatrix"]),
 "Mad Max": dict(cols=["Mad Max Collection"], movies=["Furiosa: A Mad Max Saga"]),
 "Planet of the Apes": dict(cols=["Planet of the Apes (Original) Collection", "Planet of the Apes (Reboot) Collection"], tv=["Planet of the Apes", "Return to the Planet of the Apes"], movies=["Planet of the Apes"]),
 "The Conjuring & Insidious": dict(cols=["The Conjuring Collection", "Annabelle Collection", "The Nun Collection", "Insidious Collection"]),
 "Fast & Furious": dict(cols=["The Fast and the Furious Collection"], tv=["Fast & Furious: Spy Racers"], movies=["Hobbs & Shaw"]),
}
ACTORS = "Christian Bale, Gary Oldman, Daniel Day-Lewis, Leonardo DiCaprio, Brad Pitt, Joaquin Phoenix, Matthew McConaughey, Jake Gyllenhaal, Cillian Murphy, Mads Mikkelsen, Willem Dafoe, Christoph Waltz, Philip Seymour Hoffman, Bryan Cranston, Edward Norton, Al Pacino, Robert De Niro, Denzel Washington, Anthony Hopkins, Jack Nicholson, Morgan Freeman, Samuel L. Jackson, Emma Stone, Cate Blanchett, Amy Adams, Toni Collette, Margot Robbie, Anya Taylor-Joy, Florence Pugh, Natalie Portman, Tom Cruise, Keanu Reeves, Tom Hardy, Ryan Gosling, Jim Carrey, Robin Williams, Steve Carell, Simon Pegg, Jackie Chan, Song Kang-ho, Robert Pattinson, Meryl Streep, Anne Hathaway, Tilda Swinton, Javier Bardem, Oscar Isaac, Frances McDormand, Sam Rockwell, Ethan Hawke, Viola Davis".split(", ")
DIRECTORS = "Alfred Hitchcock, Stanley Kubrick, Christopher Nolan, Martin Scorsese, Quentin Tarantino, Denis Villeneuve, David Fincher, Steven Spielberg, Akira Kurosawa, Hayao Miyazaki, Bong Joon-ho, Park Chan-wook, Francis Ford Coppola, Ridley Scott, James Cameron, Paul Thomas Anderson, Joel Coen, Ethan Coen, Wes Anderson, Guillermo del Toro, Yorgos Lanthimos, Alfonso Cuarón, Alejandro González Iñárritu, Alex Garland, Jordan Peele, Robert Eggers, Ari Aster, David Lynch, Sergio Leone, Edgar Wright, Guy Ritchie".split(", ")


def label(r):
    return f"{r.get('title') or r.get('name')} ({(r.get('release_date') or r.get('first_air_date') or '')[:4]})"


def kw_items(kind, kws, toon):
    if not kws:
        return []
    ids = "|".join(i for k in kws for i in find_keywords([k]).split("|") if i)
    if not ids:
        return []
    q = {"with_keywords": ids, "sort_by": "vote_count.desc", "vote_count.gte": 20 if kind == "movie" else 5}
    q["with_genres" if toon else "without_genres"] = "16"
    res = []
    for page in (1, 2, 3):
        d = tmdb(f"/discover/{kind}", page=page, **q) or {}
        res += d.get("results", [])
        if page >= d.get("total_pages", 0):
            break
    return res


def section(name, spec, md):
    md.append(f"### {name}")
    parts, notes = [], []
    for c in spec.get("cols", []):
        col, exact = find_collection(c)
        if not col:
            notes.append(f"collection '{c}' NOT FOUND"); continue
        d = tmdb(f"/collection/{col['id']}") or {}
        p = [x for x in d.get("parts", [])]
        notes.append(f"{col['name']} ({col['id']}{'' if exact else ', inexact'}): {len(p)}")
        parts += p
    for t in spec.get("movies", []):
        r = ((tmdb("/search/movie", query=t) or {}).get("results") or [None])[0]
        if r: parts.append(r); notes.append(f"+movie {label(r)}")
    seen, live = set(), []
    for p in sorted(parts + kw_items("movie", spec.get("kw"), False), key=lambda x: x.get("release_date") or "9999"):
        if p["id"] in seen or 16 in (p.get("genre_ids") or []):
            continue
        seen.add(p["id"]); live.append(p)
    upcoming = [p for p in live if (p.get("release_date") or "9999") > today]
    tv = kw_items("tv", spec.get("kw"), False)
    for t in spec.get("tv", []):
        r = ((tmdb("/search/tv", query=t) or {}).get("results") or [None])[0]
        if r and r["id"] not in {x["id"] for x in tv}: tv.append(r)
    am, at = kw_items("movie", spec.get("kw"), True), kw_items("tv", spec.get("kw"), True)
    md.append("- sources: " + "; ".join(notes))
    md.append(f"- **live-action films {len(live)}** (upcoming {len(upcoming)}): " + ", ".join(label(x) for x in live[:40]))
    md.append(f"- **live-action series {len(tv)}**: " + ", ".join(label(x) for x in tv[:20]))
    md.append(f"- **animated films {len(am)}**: " + ", ".join(label(x) for x in am[:20]))
    md.append(f"- **animated series {len(at)}**: " + ", ".join(label(x) for x in at[:20]))
    md.append("")


md = ["# Universes"]
for k, v in UNIVERSES.items():
    section(k, v, md)
md.append("# Single franchises")
for k, v in SINGLES.items():
    section(k, v, md)
md.append("# People\n\n| Name | TMDB | Dept | Born–died | Films | Series | Latest film | Top 3 |\n|---|---|---|---|---:|---:|---|---|")
for name, director in [(a, False) for a in ACTORS] + [(d, True) for d in DIRECTORS]:
    try:
        m, s, a, notes = S.person_card({"name": name}, dt.date.today(), director)
        p = S.find_person(name, "Directing" if director else "Acting")
        det = tmdb(f"/person/{p['id']}") or {}
        latest = max((x["year"] for x in m if x["year"]), default="")
        md.append(f"| {name}{' (dir)' if director else ''} | {p['id']} | {det.get('known_for_department')} | {(det.get('birthday') or '')[:4]}–{(det.get('deathday') or '')[:4]} | {len(m)} | {len(s)} | {latest} | {', '.join(x['name'] for x in m[:3])} |")
    except Exception as e:
        md.append(f"| {name} | ERROR {e} |")
S.IMDB.save()
open(f"{OUT}/report.md", "w").write("\n".join(md))
