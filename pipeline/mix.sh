#!/bin/bash
# Usage: pipeline/mix.sh <episode_dir> <duration_s>
# voice: light echo + loudnorm -15 LUFS; music (pipeline/music.py) at 0.18 with sidechain ducking; final loudnorm -14.5.
set -e
EP=$1; DUR=$2; HERE=$(cd "$(dirname "$0")" && pwd)
cd "$EP"
python3 "$HERE/music.py" $(python3 -c "print($DUR+3)")
ffmpeg -v error -y -i voice_raw.wav -i music_raw.wav -filter_complex "\
[0:a]aresample=44100,aecho=0.8:0.6:60|120:0.18|0.10,loudnorm=I=-15:TP=-1.5:LRA=11,apad,asplit=2[v][vsc];\
[1:a]volume=0.18[m];\
[m][vsc]sidechaincompress=threshold=0.04:ratio=6:attack=20:release=400[md];\
[v][md]amix=inputs=2:duration=first:normalize=0,atrim=0:$DUR,afade=t=out:st=$(python3 -c "print($DUR-1.2)"):d=1.2,loudnorm=I=-14.5:TP=-1.5:LRA=11[out]" \
 -map "[out]" -ar 48000 mix.wav
echo "mixed $EP/mix.wav"
