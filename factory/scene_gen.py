#!/usr/bin/env python3
"""A MOVING SCENE FROM A SENTENCE, IN THE CLOUD, AT $0 (13 Nov 2026).

Kamay, 13 Nov: "the way to go fully automatic and making the clips in this most awesome way
with all things and without limits its there, you must build that and find the way."

Found and proven the same day, from this Mac with no account and no browser:
  1. the picture  - a public FLUX.1-schnell Space        (4 s,  1344x768, film-quality)
  2. the movement - a public Wan 2.2 image-to-video Space (19 s, 832x480, 16 fps, 3.5 s clip:
                    the young man turned the page and looked up)
  3. fallback     - a public LTX-Video Space, text straight to video (10 s, 960x544)
These are Hugging Face Spaces on free shared GPUs, spoken to over plain HTTP (the Gradio call
protocol). They are other people's free services: any of them can be busy, change or vanish.
So every stage has a list, each call is retried, a finished scene is kept beside the spec
(never generated twice), and a failure returns None so the builder falls back to a still or
skips the scene - a missing scene must never cost the clip.

HF_TOKEN (optional, a free Hugging Face account's read token) raises the daily GPU quota and
makes it this account's own instead of the runner's shared address.

    make("picture prompt", "out.mp4", motion="what moves")  -> path or None
    python factory/scene_gen.py "picture prompt" out.mp4 ["what moves"]
"""
import json
import os
import re
import sys
import time
import urllib.request
import uuid

STYLE = ("Cinematic 35mm film still, low-key warm lighting, shallow depth of field, moody, "
         "photorealistic, no text, no watermark: ")
NEG = "blurry, low quality, chaotic, deformed, watermark, text, bad anatomy, shaky camera view point"
IMAGE_SPACES = ["https://black-forest-labs-flux-1-schnell.hf.space"]
I2V_SPACES = ["https://saravutw-wan2-2-i2v-lightning-4-8step-custom.hf.space"]
T2V_SPACES = ["https://lightricks-ltx-video-distilled.hf.space"]


def _hdr(extra=None):
    h = dict(extra or {})
    if os.environ.get("HF_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["HF_TOKEN"]
    return h


def _call(base, endpoint, data, timeout=420):
    """One Gradio call: post the inputs, read the event stream to its end, return the outputs."""
    b = base + "/gradio_api"
    r = urllib.request.Request(f"{b}/call/{endpoint}", data=json.dumps({"data": data}).encode(),
                               headers=_hdr({"Content-Type": "application/json"}))
    ev = json.load(urllib.request.urlopen(r, timeout=60))["event_id"]
    out = urllib.request.urlopen(urllib.request.Request(f"{b}/call/{endpoint}/{ev}", headers=_hdr()),
                                 timeout=timeout).read().decode("utf-8", "ignore")
    events = [l for l in out.split("\n") if l.startswith("event:")]
    if not events or "complete" not in events[-1]:
        raise RuntimeError("space answered " + (events[-1] if events else "nothing") + ": " + out[-200:])
    return json.loads(out[out.rindex("data: ") + 6:])


def _upload(base, path):
    bd = uuid.uuid4().hex
    body = (f'--{bd}\r\nContent-Disposition: form-data; name="files"; filename="scene.jpg"\r\n'
            f'Content-Type: image/jpeg\r\n\r\n').encode() + open(path, "rb").read() + f"\r\n--{bd}--\r\n".encode()
    r = urllib.request.Request(base + "/gradio_api/upload", data=body,
                               headers=_hdr({"Content-Type": "multipart/form-data; boundary=" + bd}))
    return json.load(urllib.request.urlopen(r, timeout=120))[0]


def _save(url, dest):
    data = urllib.request.urlopen(urllib.request.Request(url, headers=_hdr()), timeout=180).read()
    if len(data) < 5000:
        raise RuntimeError(f"file too small ({len(data)} bytes)")
    open(dest, "wb").write(data)
    return dest


def _urls(obj, ext):
    return re.findall(r'https://[^"\s]+?\.' + ext, json.dumps(obj))


def _try(fn, what, tries=2, wait=20, log=print):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:                       # busy, over quota, asleep, changed
            log(f"    {what}: {type(e).__name__}: {str(e)[:160]}" + ("" if i == tries - 1 else f" - again in {wait}s"))
            if i < tries - 1:
                time.sleep(wait)
    return None


def picture(prompt, dest, log=print):
    """A film still for the prompt (WebP/PNG as served; ffmpeg reads either)."""
    for base in IMAGE_SPACES:
        def go():
            out = _call(base, "infer", [STYLE + prompt, 0, True, 1344, 768, 4], timeout=180)
            return _save(_urls(out, "(?:webp|png|jpg|jpeg)")[0], dest)
        if _try(go, "picture " + base.split("//")[1].split(".")[0], log=log):
            return dest
    return None


def animate(image, motion, dest, seconds=3.5, log=print):
    for base in I2V_SPACES:
        def go():
            p = _upload(base, image)
            img = {"path": p, "meta": {"_type": "gradio.FileData"}}
            out = _call(base, "generate_video",
                        [img, None, motion, 4, NEG, seconds, 1, 1, 42, True, 5, "UniPCMultistep", 3.0, 16, False, True])
            return _save(_urls(out, "mp4")[-1], dest)
        if _try(go, "movement " + base.split("//")[1].split(".")[0], log=log):
            return dest
    return None


def text_to_video(prompt, dest, seconds=4, log=print):
    for base in T2V_SPACES:
        def go():
            out = _call(base, "text_to_video",
                        [STYLE.replace("film still", "film scene") + prompt,
                         "worst quality, inconsistent motion, blurry, jittery, distorted",
                         None, None, 544, 960, "text-to-video", seconds, 9, 42, True, 1, True])
            return _save(_urls(out, "mp4")[-1], dest)
        if _try(go, "text-to-video " + base.split("//")[1].split(".")[0], log=log):
            return dest
    return None


def make(prompt, dest, motion=None, log=print):
    """prompt -> a moving scene at dest (mp4). Returns dest, or None when every route failed.

    The still is kept as dest + '.jpg': a builder can fall back to it (a slow push on a still)
    and a cover can be made from it (kt_cover.from_image)."""
    if os.path.exists(dest) and os.path.getsize(dest) > 20000:
        return dest
    still = dest + ".src"
    motion = motion or "slow cinematic camera push in, natural subtle movement, light flickers"
    if picture(prompt, still, log=log):
        if animate(still, motion + ". Smooth, cinematic.", dest, log=log):
            return dest
    if text_to_video(prompt + ". " + motion, dest, log=log):
        return dest
    return None


if __name__ == "__main__":
    a = sys.argv
    print(make(a[1], a[2], a[3] if len(a) > 3 else None))
