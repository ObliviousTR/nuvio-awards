#!/bin/bash
# Mark a built file as delivered: it becomes the baseline that Ozzy's next export is compared with.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out/delivered
cp "out/$1" "out/delivered/$1"
cp "out/$1" out/delivered/baseline.json
echo "baseline <- $1"
