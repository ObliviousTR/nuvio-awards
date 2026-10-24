Batman card work in progress (not approved). Kept so a later session can pick it up.
- src/: inputs for art_tools/batman_signal.py on this branch. bat.json (1989 emblem bat outline + ellipse, made by
  tools/batjson.py from emblem_268_1.png = TMDB logo of film 268), title.png (TMDB 268 logo), stills/NN_*.jpg + .json
  framing. Oswald-VF.ttf: copy from nuvio-art/art/universes/dc/_src/.
- candidates_index.json: name -> full-size URL of every candidate backdrop (TMDB textless >=1920 px + fanart.tv);
  names are <tmdb movie id>_t<n> (TMDB) / _f<n> (fanart). Image lists themselves: design-refs branch, refs/batman2/.
- tools/thumbs.py downloads thumbnails for the index; tools/sheet.py makes labelled contact sheets.
