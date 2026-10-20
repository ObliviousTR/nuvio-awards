# Nuvio Awards

A small static Stremio/Nuvio addon with award catalogs, newest first (48 catalogs):

- **Oscars:** every major category's winners, nominees for Picture / Director / the four acting categories /
  International / Animated, all of the latest ceremony's nominees, and all winning films
- **Golden Globes:** Picture (Drama, Musical or Comedy), Drama / Comedy / Limited Series, Director, Non-English Film
- **BAFTA:** Best Film · **Emmys:** Drama, Comedy, Limited Series
- **Festivals:** Cannes (Palme d'Or, Grand Prix, Jury Prize), Venice, Berlinale, Sundance, TIFF

Install in Nuvio with this manifest URL:

```
https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/main/manifest.json
```

## How it stays up to date

Everything runs inside this repo — no outside service needed.

- `.github/workflows/update.yml` runs **every Monday** (and on demand from the Actions tab):
  - **Oscars:** pulls the latest `oscars.csv` from [DLu/oscar_data](https://github.com/DLu/oscar_data)
    (every nomination with IMDb ids).
  - **Other awards:** reads each new ceremony / festival page on English Wikipedia (`data/events.json` says which
    page and award), takes the announced winner, resolves its IMDb id via Wikidata (IMDb search as a fallback)
    and appends it to `data/additions.txt`.
  - Rebuilds the addon (`scripts/build.py`), commits, and **opens an issue** listing what was added — or what it
    could not find two months after the event, so it can be fixed by hand.
- `.github/workflows/selftest.yml` (manual) checks the Wikipedia parser against known winners → `data/selftest.md`.

Manual fixes: add a line to `data/additions.txt` (`catalog|year|imdb_id|tmdb_id|title`), run
`python3 scripts/build.py`, commit and push. Nuvio picks changes up on its next refresh.

Seed lists in `data/base/` were copied from public MDBList lists and extended with recent winners.

## Spotlight (second addon in this repo)

```
https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/main/spotlight/manifest.json
```

`.github/workflows/spotlight.yml` runs **every day** (03:17 UTC) and rebuilds `spotlight/` from TMDB
(repo secret `TMDB_API_KEY`):

- **The Headliner** (actor), **The Visionary** (director), **The Powerhouse** (studio), **The Saga** (franchise):
  a new subject every 14 days from `spotlight/pool.json`. Entries with `months` are preferred in those months
  (October horror, December holidays); otherwise the least recently shown subject comes next.
- **Topical first (The Headliner, The Saga):** on a rotation day the star of a big film opening in cinemas
  (7 days ago → 21 days ahead), or the franchise a new film belongs to, comes before the pool order. Nothing shown
  in the last 365 days is picked this way. The card says why ("Now in theaters", "New chapter in theaters").
- **The pool grows by itself:** once a week `scripts/spotlight_live.py` adds up to 3 candidates per card to
  `spotlight/pool_auto.json` (stars and directors of popular new films, franchises with a new chapter; studios stay
  hand-picked because the box office credits financiers more often than real studios), each checked against the same minimums as the rotation. New entries have never been
  shown, so they come up soon. To drop one for good, move its name to `"removed"` in `pool_auto.json`.
- **The Cultural Pulse:** the seasonal calendar in `pool.json` (`pulse`), switching on each theme's start date.
- **Fresh Out of Theaters, Box Office Champions, Certified Fresh & Must-See:** rebuilt every day.
- Covers (`spotlight/art/<card>/cover.jpg`) and hero backdrops are generated when a subject changes; their URLs
  never change. `spotlight/STATUS.md` shows what is on now and when the next rotation is.

Run it by hand from the Actions tab (Spotlight → Run workflow):

- `next` + card: skip that card (or `all` four rotating cards) to its next subject now; `pulse` brings the next
  calendar theme forward.
- `build` + card + subject: show that subject now, e.g. `headliner` / `Pedro Pascal`, `powerhouse` / `A24`,
  `saga` / `Star Wars` (sagas must be in `pool.json`), `pulse` / `Halloween Night`. A hand-picked subject stays until
  the next rotation day (the Cultural Pulse: until the next calendar theme starts).
- `check` tests every pool entry → `spotlight/CHECK.md`; `redraw` regenerates all art.

To keep a subject across rotations, put it in `spotlight/state.json` → `"pin"`, e.g. `{"headliner": "Pedro Pascal"}`;
remove it to return to the rotation.
