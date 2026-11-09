#!/bin/sh
# v2 build: regenerate every composition, then grade the portrait layers identically.
set -e
python3 tools/gen2.py
GJ='{"adjust":{"exposure":-0.35,"contrast":0.1,"highlights":-0.2},"details":{"vignette":0.45}}'
GC='{"adjust":{"exposure":-0.35,"contrast":0.1,"highlights":-0.2}}'
npx hyperframes media-treatment --file compositions/james.html --selector "#james-photo" --grading "$GJ" --apply --json >/dev/null
npx hyperframes media-treatment --file compositions/james.html --selector "#james-cut" --grading "$GC" --apply --json >/dev/null
echo built
