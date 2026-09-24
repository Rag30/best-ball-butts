#!/bin/bash
# usage: run_engine.sh <engine> [proj file]  -> result_<e>_{base,gci}.json (Weeks 1-2 locked) + _nolock variants
e=$1; f=${2:-proj_$1.json}
D=$(dirname "$0"); L0=$(python3 -c "import json;print(json.load(open('week.json'))['start']-1)")
for L in $L0 0; do sfx=""; [ $L = 0 ] && sfx=_nolock
  uv run -q --with numpy --with scipy python "$D/sim4.py" --proj $f --lock $L --out result_${e}_base$sfx.json >/dev/null
  uv run -q --with numpy --with scipy python "$D/sim4.py" --proj $f --lock $L --noise gamma --corr 0.25 --injury 1 --out result_${e}_gci$sfx.json >/dev/null
done; echo "done $e"
