#!/bin/sh
# Break a reference video down before copying its style.
# Usage: analyze_reference.sh <video> <out_dir>
# Writes: contact sheets (every 2 s), dense strips around soft transitions, two full-res frames,
# and prints cuts, loudness and silences. Read the sheets with your image viewer / Read tool.
set -e
V="$1"; OUT="${2:-ref}"
[ -f "$V" ] || { echo "usage: $0 <video> [out_dir]"; exit 1; }
mkdir -p "$OUT/frames"

echo "== streams"
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact "$V"

echo "== contact sheets (one frame every 2 s, 24 per sheet)"
ffmpeg -v error -y -i "$V" -vf "fps=1/2,scale=640:-1" "$OUT/frames/f_%03d.jpg"
N=$(ls "$OUT/frames" | wc -l | tr -d ' ')
i=1; s=1
while [ $i -le $N ]; do
  ffmpeg -v error -y -start_number $i -i "$OUT/frames/f_%03d.jpg" -vf "scale=240:-1,tile=8x3" -frames:v 1 "$OUT/sheet$s.jpg" || true
  i=$((i + 24)); s=$((s + 1))
done

echo "== hard cuts (scene score > 0.25); none means every transition is soft (dissolve, morph, camera move)"
ffmpeg -v error -i "$V" -vf "scale=180:-1,select='gt(scene,0.25)',metadata=print" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*" | tr '\n' ' '; echo
echo "== soft changes (scene score > 0.08)"
ffmpeg -v error -i "$V" -vf "scale=180:-1,select='gt(scene,0.08)',metadata=print" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*" | tr '\n' ' '; echo

echo "== loudness (social video sits near -14 LUFS)"
ffmpeg -hide_banner -i "$V" -af ebur128 -vn -f null - 2>&1 | grep -E "^ +I:" || true
echo "== silences below -40 dB (few or none = a music bed runs under the voice)"
ffmpeg -hide_banner -i "$V" -af "silencedetect=noise=-40dB:d=0.4" -vn -f null - 2>&1 | grep -o "silence_[a-z]*: [0-9.]*" | tr '\n' ' '; echo

echo "== two full-res frames (texture check: 3D render vs AI video vs photo)"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
for f in 0.08 0.4; do
  T=$(python3 -c "print(round($D*$f,2))")
  ffmpeg -v error -y -ss "$T" -i "$V" -frames:v 1 "$OUT/full_$T.png"
done
echo "Next: make dense strips around any moment that looks like a transition, e.g."
echo "  ffmpeg -ss 12 -t 4 -i \"$V\" -vf 'fps=2.5,scale=200:-1,tile=10x1' -frames:v 1 $OUT/strip_12.jpg"
echo "Done -> $OUT"
