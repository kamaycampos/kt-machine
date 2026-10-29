#!/usr/bin/env python3
"""TikTok: clips land in the member's TikTok INBOX (drafts); they paste the caption and tap Post.

Proven on WB Organics, 15 Oct 2026. TikTok does not approve personal posting apps, so the
member's own TikTok developer app stays in SANDBOX, with their own TikTok account added
as a sandbox "target user". Sandbox + "Upload to TikTok" (video.upload) = inbox drafts.

    python3 tiktok_key.py

1. Asks for the SANDBOX client key and secret (TikTok for Developers -> app -> Sandbox ->
   Credentials). The secret is hidden while pasted.
2. Writes the consent link to .tt_auth_url (their Claude opens it in their Chrome).
3. They tap Authorize, land on their control panel, copy the address bar and paste it here.
4. Stores TT_CLIENT_KEY, TT_CLIENT_SECRET, TT_REFRESH_TOKEN in their repository's secrets
   and prints the TikTok account it reached. Nothing secret is ever printed.

The redirect is their control panel (https://OWNER.github.io/REPO/). It must be listed
under Sandbox -> Login Kit -> Redirect URI before running this.
"""
import getpass, hashlib, json, os, re, secrets, subprocess, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URLFILE = os.path.join(HERE, ".tt_auth_url")
SCOPES = "user.info.basic,user.info.profile,user.info.stats,video.list,video.upload"

url = subprocess.run(["git", "-C", HERE, "remote", "get-url", "origin"],
                     capture_output=True, text=True).stdout.strip()
m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+?)(?:\.git)?/?$", url) or re.search(r"/([^/]+)/([^/.]+?)(?:\.git)?/?$", url)
if not m:
    sys.exit("  Could not tell this repository's name from git.")
OWNER, NAME = m.group(1), m.group(2)
REPO = f"{OWNER}/{NAME}"
REDIRECT = f"https://{OWNER.lower()}.github.io/{NAME}/"

print(f"\n  TikTok inbox for {REPO}. Redirect URI to register in the Sandbox: {REDIRECT}")
CK = sys.argv[1] if len(sys.argv) > 1 else input("  PASTE THE SANDBOX CLIENT KEY, then Enter: ").strip()
CS = getpass.getpass("  PASTE THE SANDBOX CLIENT SECRET (nothing shows), then Enter: ").strip()
if len(CK) < 8 or len(CS) < 8:
    sys.exit("  One of them was empty. Run this again.")

ver = secrets.token_urlsafe(48)
state = "tt" + secrets.token_hex(5)
open(URLFILE, "w").write("https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": CK, "response_type": "code", "scope": SCOPES, "redirect_uri": REDIRECT,
    "state": state, "code_challenge": hashlib.sha256(ver.encode()).hexdigest(),
    "code_challenge_method": "S256"}))
print("\n  1. In Chrome, tap Authorize on TikTok (Claude opens the page).")
print("  2. You land on your control panel. Click its address bar, Cmd+A (Ctrl+A), copy.")
print("  3. Click back here, paste, Enter.\n")
landed = input("  > ").strip()
os.path.exists(URLFILE) and os.remove(URLFILE)
q = urllib.parse.parse_qs(urllib.parse.urlparse(landed).query)
if q.get("state", [""])[0] != state or "code" not in q:
    sys.exit("  That address has no fresh TikTok code. Run this again.")
req = urllib.request.Request("https://open.tiktokapis.com/v2/oauth/token/",
                             headers={"Content-Type": "application/x-www-form-urlencoded"},
                             data=urllib.parse.urlencode({
                                 "client_key": CK, "client_secret": CS, "code": q["code"][0],
                                 "grant_type": "authorization_code", "redirect_uri": REDIRECT,
                                 "code_verifier": ver}).encode())
r = json.loads(urllib.request.urlopen(req, timeout=30).read())
if not r.get("refresh_token"):
    sys.exit(f"  TikTok refused: {r.get('error')} {r.get('error_description')}")
if "video.upload" not in (r.get("scope") or ""):
    sys.exit("  TikTok did not grant video.upload: add Content Posting API to the Sandbox and re-run.")
for k, v in (("TT_CLIENT_KEY", CK), ("TT_CLIENT_SECRET", CS), ("TT_REFRESH_TOKEN", r["refresh_token"])):
    subprocess.run(["gh", "secret", "set", k, "-R", REPO], input=v.encode(), check=True)
u = urllib.request.Request("https://open.tiktokapis.com/v2/user/info/?fields=display_name,username",
                           headers={"Authorization": "Bearer " + r["access_token"]})
who = json.loads(urllib.request.urlopen(u, timeout=30).read()).get("data", {}).get("user", {})
print(f"\n  Done. TikTok key stored for {REPO}. Account: {who.get('display_name')} (@{who.get('username')})")
# KT (29 Oct 2026): Kamay's TikTok was switched off while @kt_student was flagged. Once the
# NEW account's key is stored, inbox delivery comes back on for him.
off = subprocess.run(["gh", "variable", "get", "KT_PLATFORMS_OFF", "-R", REPO], capture_output=True, text=True).stdout.strip()
if off:
    left = ",".join(x for x in off.split(",") if x.strip() and x.strip() != "tiktok")
    subprocess.run(["gh", "variable", "set", "KT_PLATFORMS_OFF", "-R", REPO, "--body", left or " "], check=True)
    print(f"  TikTok drafts are back on for {REPO}. Still off: {left or 'nothing'}")
