#!/bin/bash
# Fonts for the badge lettering (OFL, Google Fonts) -> inputs/fonts (*.ttf is git-ignored repo-wide).
set -e
D="$(dirname "$0")/inputs/fonts"; mkdir -p "$D"
for f in zenmarugothic/ZenMaruGothic-Black.ttf "nunito/Nunito%5Bwght%5D.ttf" "notosanssc/NotoSansSC%5Bwght%5D.ttf" "notosanskr/NotoSansKR%5Bwght%5D.ttf"; do
  out="$D/$(basename "$f" | sed 's/%5B/[/;s/%5D/]/')"; [ -s "$out" ] || curl -sL --fail "https://github.com/google/fonts/raw/main/ofl/$f" -o "$out"
done
ls -la "$D"
