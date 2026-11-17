# Daily Short — playbook

One run = one finished Short, uploaded here and scheduled on YouTube via Metricool for 20:00 Europe/Sofia the same day.
The owner does nothing by hand. Never ask them to; if something blocks, still finish everything you can and report.

## House style (keep every video consistent)
- Niche: true dark history / unsolved mysteries. Facts must be checked against 2+ reputable sources (History.com,
  Britannica, Smithsonian, BBC, museum/university pages). Hedge anything disputed ("reportedly", "it's said").
  No gore, no graphic deaths, no living private people, nothing NSFW, no alcohol/drug focus.
- Length 45–58 s (hard max 59 s). ~16–19 short phrases. Open with place + year hook, end with a question to the viewer.
- Voice: Kokoro TTS, blend 0.8 bm_george + 0.2 bm_fable, en-gb. Per-phrase speed 0.85–1.0 and gain −2..+1.5 dB for a
  *little* emotion: slow + quiet on eerie lines, slightly faster on tense facts, short dramatic pauses before reveals.
  Write years as words ("fifteen eighteen") so they are read correctly.
- Visuals: 1080×1920, 30 fps, drawn in code with pycairo (no stock footage, no AI images, no copyrighted characters).
  "Shadow-puppet" look: near-black silhouettes against a moonlit sepia/charcoal sky, warm amber windows/lanterns,
  ONE red accent colour (#CC121F) for the key object, fog bands, vignette, flicker, film grain (ffmpeg noise).
  New scenes every episode, matching the story beat by beat; slow push-ins; scenes cut on phrase starts.
- Captions: Anton, uppercase, ≤3 words per group, white with black stroke, current word red, centred at y≈1060.
  Keep the key subject of each scene out of the y 990–1130 band where possible.
- Titles over picture: Cinzel (place/year, labels), Anton for big numbers.
- Music: pipeline/music.py (music-box waltz + drone). Fine to vary the progression/tempo per episode for mood.
- Mix: voice loudnorm −15 LUFS, music 0.18 with sidechain ducking; final ≈ −14/−15 LUFS integrated.

## Steps
```bash
# 0. setup (fresh workspace every run)
pip install --break-system-packages -q kokoro-onnx soundfile pycairo
mkdir -p /home/claude/models && cd /home/claude/models
for f in kokoro-v1.0.int8.onnx voices-v1.0.bin; do curl -sSL -o $f https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f; done
mkdir -p ~/.fonts && cd ~/.fonts
curl -sSLo Anton-Regular.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf
curl -sSLo 'Cinzel[wght].ttf' 'https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf'
fc-cache -f

# 1. episode folder:  episodes/dayNNN_slug/   (NNN = next number in TOPICS.md)
# 2. research + write episodes/dayNNN_slug/script.py   (copy the format of day001)
python3 pipeline/tts_gen.py episodes/dayNNN_slug /home/claude/models      # prints phrase start times
# 3. write episodes/dayNNN_slug/render.py: copy day001's render.py (helpers, captions, render loop) and replace
#    SCENES + the scene_* functions with new ones for this story. Scene starts = phrase indices.
export EP=$PWD/episodes/dayNNN_slug; mkdir -p $EP/stills
python3 $EP/render.py still 2 10 20 30 40 50          # look at the stills (pipeline/grid.py makes a contact sheet)
#    Fix anything unreadable/overlapping/ugly BEFORE the full render.
(for i in 0 1 2 3; do python3 $EP/render.py $i; done) & (for i in 4 5 6 7; do python3 $EP/render.py $i; done); wait
# 4. audio
python3 pipeline/music.py <duration+3>  (writes music_raw.wav) then the ffmpeg echo / loudnorm / sidechain mix as in day001
# 5. concat scenes (-c copy), mux audio, final encode: -c:v libx264 -crf 27 -preset veryfast -c:a aac -b:a 192k -movflags +faststart
#    -> videos/dayNNN_slug.mp4  (keep < 40 MB). Check 8 frames from the FINAL file + duration < 59 s.
# 6. commit (don't commit out/, stills/, wav files) and push to main.
# 7. schedule with Metricool createScheduledPost: blogId 8169232, network youtube, type "short",
#    media = https://raw.githubusercontent.com/AvaDiason/shorts-channel/main/videos/dayNNN_slug.mp4
#    date today 20:00 Europe/Sofia (if already past, tomorrow 20:00), madeForKids false, isAiGeneratedContent true,
#    category EDUCATION, privacy public, title ≤ 70 chars + " #shorts", description 1–2 lines + 5 hashtags.
# 8. tick the topic in TOPICS.md (date + file), add a row to README.md, commit + push.
```
