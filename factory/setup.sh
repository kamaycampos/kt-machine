#!/bin/bash
# Rebuild Kamay's Mac layout (~/Kamay) on a GitHub server, so the clip pipeline
# runs here UNCHANGED - every script finds its tools and files where it expects.
# 19 Sept 2026: the cloud clip factory, so clips get made with the Mac shut.
set -euo pipefail
K="$HOME/Kamay"
mkdir -p "$K/bin" "$K/Kamay Content/1_RAW/KT_SOURCE" "$K/POST_TODAY" "$K/work/proposals" \
         "$K/transcripts" "$K/logs" "$K/whisper.cpp/build/bin" "$K/whisper.cpp/models"

sudo apt-get -qq update >/dev/null
sudo apt-get -qq install -y ffmpeg fonts-liberation cmake >/dev/null
pip install -q opencv-python-headless numpy pillow

ln -sf /usr/bin/ffmpeg  "$K/bin/ffmpeg"
ln -sf /usr/bin/ffprobe "$K/bin/ffprobe"
ln -sf "$(command -v gh)" "$K/bin/gh"
cp factory/assets/mont_black.ttf factory/assets/yunet.onnx "$K/bin/"
# Liberation Sans is metrically identical to Arial and free to ship; Apple's
# Arial file is not ours to publish in a public repository.
ln -sf /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf "$K/bin/arial_bold.ttf"
# THE SHARED ENGINE FIRST, then this project's own files. One canonical copy of the
# parts no brand owns (word timings, caption breaks, caption timing anchored to the
# sound, face framing, the read-back check) lives in shared/ and every factory pulls
# it, so an improvement made for one project is live in all of them on the next run.
# Kamay, 27 Sept 2026: "make it automatic, at all times, and vice versa."
cp shared/*.py "$K/"
cp factory/pipeline/*.py "$K/"
python3 - <<'EOF'
import hashlib, json, os
d = "shared"
man = json.load(open(os.path.join(d, "MANIFEST.json")))["files"]
bad = [f for f, h in man.items()
       if hashlib.sha1(open(os.path.join(d, f), "rb").read()).hexdigest() != h]
if bad:
    raise SystemExit(f"shared engine drifted, MANIFEST does not match: {bad}")
print(f"shared engine ok, {len(man)} modules")
EOF
cp factory/kt_series.json "$K/kt_series.json"
# A MEMBER'S OWN STYLE (Affiliate Factory, 2 Oct 2026). Only a member's copy has
# my_brand/style.json; without it the renderer keeps every house default.
if [ -f my_brand/style.json ]; then cp my_brand/style.json "$K/style.json"; fi
ln -sfn "$GITHUB_WORKSPACE" "$K/kt-machine"

# whisper.cpp pinned to the exact commit the Mac runs, so word timings match.
W="$HOME/wcache"
if [ ! -x "$W/whisper-cli" ]; then
  mkdir -p "$W"
  git clone -q https://github.com/ggml-org/whisper.cpp /tmp/whisper.cpp
  git -C /tmp/whisper.cpp checkout -q 2ca53bb45e38748d07b310eeb36245a7157ac882
  # BUILD IT PORTABLE, NOT FAST. The binary is built once and CACHED, and GitHub hands
  # out runners with different CPUs - so a build tuned to the machine that made it dies
  # with SIGILL on the next machine that restores it. Seven of ten shards died that way
  # in a sister repository while three succeeded in the same run. Here it would be
  # quieter and worse: the word pass returns nothing, the renderer falls back to the old
  # caption path, and the clips come out with cruder timing and nobody notices.
  cmake -S /tmp/whisper.cpp -B /tmp/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release \
        -DGGML_NATIVE=OFF -DBUILD_SHARED_LIBS=OFF -DWHISPER_BUILD_TESTS=OFF >/dev/null
  cmake --build /tmp/whisper.cpp/build -j"$(nproc)" --config Release --target whisper-cli >/dev/null
  cp /tmp/whisper.cpp/build/bin/whisper-cli "$W/"
fi
[ -s "$W/ggml-small.en.bin" ] || curl -sL -o "$W/ggml-small.en.bin" \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
ln -sf "$W/whisper-cli" "$K/whisper.cpp/build/bin/whisper-cli"
ln -sf "$W/ggml-small.en.bin" "$K/whisper.cpp/models/ggml-small.en.bin"
"$K/whisper.cpp/build/bin/whisper-cli" --help >/dev/null 2>&1 && echo "setup ok: whisper, ffmpeg, fonts, pipeline"
