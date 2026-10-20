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
