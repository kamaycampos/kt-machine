"""Make every transcript readable with TRANSCRIPT_KEY (the planning agent's key).

Transcripts made before 22 Sept 2026 were encrypted with FACTORY_KEY (the video
key). The weekly planning agent must never hold that one, so any transcript that
does not open with TRANSCRIPT_KEY is re-encrypted with it. Runs in tmark (single
writer), where both keys exist.
"""
import json, os, subprocess
R = os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine")
sh = lambda *a: subprocess.run(list(a), capture_output=True, text=True)
assets = [a["name"] for a in json.loads(sh("gh", "release", "view", "sources", "-R", R, "--json", "assets").stdout)["assets"]
          if a["name"].endswith(".srt.enc")]
n = 0
for a in assets:
    sh("gh", "release", "download", "sources", "-R", R, "-p", a, "-D", "/tmp", "--clobber")
    ok = sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:TRANSCRIPT_KEY", "-in", f"/tmp/{a}", "-out", "/tmp/t.srt")
    if ok.returncode == 0 and open("/tmp/t.srt", errors="ignore").read(200).strip()[:1].isdigit():
        continue
    old = sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:FACTORY_KEY", "-in", f"/tmp/{a}", "-out", "/tmp/t.srt")
    if old.returncode:
        print("cannot open", a); continue
    sh("openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:TRANSCRIPT_KEY", "-in", "/tmp/t.srt", "-out", f"/tmp/{a}")
    sh("gh", "release", "upload", "sources", f"/tmp/{a}", "--clobber", "-R", R); n += 1
print(f"re-keyed {n} of {len(assets)} transcript(s)")
