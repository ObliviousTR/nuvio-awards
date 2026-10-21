#!/usr/bin/env bash
# Rebuild the whole collection from the original backup, step by step.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out/tmp
python3 build_streaming.py         orig.json        out/tmp/02.json out/report-02-streaming.txt
python3 build_networks.py          out/tmp/02.json  out/tmp/03.json out/report-03-networks.txt
python3 build_genres_decades.py    out/tmp/03.json  out/tmp/04.json out/report-04-genres-decades.txt
python3 build_themes.py            out/tmp/04.json  out/tmp/05.json out/report-05-themes.txt
python3 build_discover.py          out/tmp/05.json  out/tmp/055.json out/report-10-discover.txt
python3 build_international.py     out/tmp/055.json out/tmp/056.json out/report-06-international.txt
python3 build_kids.py              out/tmp/056.json out/tmp/057.json out/report-07-kids.txt
python3 build_anime.py             out/tmp/057.json out/tmp/058.json out/report-08-anime.txt
python3 build_awards.py            out/tmp/058.json out/tmp/059.json out/report-09-awards.txt
python3 build_spotlight.py         out/tmp/059.json out/tmp/0595.json out/report-11-spotlight.txt
python3 build_favourites.py        out/tmp/0595.json out/tmp/0596.json
python3 build_reality.py           out/tmp/0596.json out/tmp/0597.json out/report-12-reality.txt
python3 build_studios.py           out/tmp/0597.json out/tmp/0598.json out/report-13-studios.txt
python3 build_library.py           out/tmp/0598.json out/tmp/06.json out/report-14-library.txt
python3 build_sitcoms.py           out/tmp/06.json  out/tmp/065.json
python3 apply_language_policy.py   out/tmp/065.json out/tmp/07.json
python3 apply_no_animation.py      out/tmp/07.json  out/tmp/08.json
python3 apply_order.py             out/tmp/08.json  out/tmp/085.json
python3 apply_own_art.py           out/tmp/085.json out/tmp/087.json
python3 apply_art_mirror.py        out/tmp/087.json out/tmp/09.json
python3 user_layer.py apply        out/tmp/09.json  "out/${1:-nuvio-latest.json}"
rm -rf out/tmp
