#!/usr/bin/env bash
# Erzeugt ein 3-Sekunden-Testvideo mit Bild und Ton — ohne Netz.
# Der Szenenwechsel bei Sekunde 1.5 gibt der Keyframe-Erkennung etwas zu finden.
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "testsrc=duration=1.5:size=320x240:rate=10" \
  -f lavfi -i "color=c=red:duration=1.5:size=320x240:rate=10" \
  -f lavfi -i "sine=frequency=440:duration=3" \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[v]" \
  -map "[v]" -map 2:a -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest sample.mp4
