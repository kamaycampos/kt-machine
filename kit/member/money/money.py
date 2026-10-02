#!/usr/bin/env python3
"""THE MONEY LINE - affiliate earnings, encrypted, in a public repository.

Kamay, 2 Oct 2026: their Claude should "have access to all of their numbers and
accounts so it can know everything, like their portal". The affiliate portal
has no API, so the member's Claude reads it in their own logged-in Chrome and
records what it saw here.

THE REPOSITORY IS PUBLIC, SO EARNINGS ARE NEVER WRITTEN IN THE CLEAR. They live in
state/money.enc, encrypted with a passphrase only the member knows (never saved
anywhere in the repo). The control panel's Money room asks for it and decrypts
in the member's own browser. Same openssl format the factory already uses
(AES-256-CBC, PBKDF2-SHA256, 100,000 rounds), so the browser can open it with
WebCrypto and nothing else.

    MONEY_PASS=... python3 money/money.py add '{"date":"2026-10-02","brand":"GIN","clicks":41,"sales":2,"commission":95.70}'
    MONEY_PASS=... python3 money/money.py show
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENC = os.path.join(ROOT, "state", "money.enc")
ITER = "100000"


def _ssl(args, data):
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", ITER, "-md", "sha256",
                        "-pass", "env:MONEY_PASS", *args], input=data, capture_output=True)
    if r.returncode:
        sys.exit("wrong passphrase, or the money file is damaged" if "-d" in args
                 else r.stderr.decode()[-200:])
    return r.stdout


def load():
    if not os.path.exists(ENC):
        return {"entries": []}
    return json.loads(_ssl(["-d", "-a", "-A"], open(ENC, "rb").read()))


def save(d):
    os.makedirs(os.path.dirname(ENC), exist_ok=True)
    out = _ssl(["-salt", "-a", "-A"], json.dumps(d, separators=(",", ":")).encode())
    open(ENC, "wb").write(out)


def main():
    if not os.environ.get("MONEY_PASS"):
        sys.exit("set MONEY_PASS (the member's money passphrase) first")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    d = load()
    if cmd == "add":
        e = json.loads(sys.argv[2])
        for k in ("date", "brand"):
            if not e.get(k):
                sys.exit(f"an entry needs '{k}'")
        # one row per date + brand: reading the portal twice in a day replaces, never doubles
        d["entries"] = [x for x in d["entries"]
                        if not (x["date"] == e["date"] and x["brand"] == e["brand"])] + [e]
        d["entries"].sort(key=lambda x: (x["date"], x["brand"]))
        save(d)
        print(f"recorded {e['brand']} {e['date']}: {len(d['entries'])} rows, encrypted")
    else:
        tot = sum(float(x.get("commission") or 0) for x in d["entries"])
        print(json.dumps(d, indent=1))
        print(f"total commission recorded: {tot:.2f}")


if __name__ == "__main__":
    main()
