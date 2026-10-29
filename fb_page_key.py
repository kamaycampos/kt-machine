#!/usr/bin/env python3
"""Facebook POSTING key for a second Page, pasted into THIS prompt - never into a chat.

    python3 fb_page_key.py            (run inside kt-machine)

29 Oct 2026. Kamay's old Page (Kevin Trudeau Wisdom) was restricted; he posts to a new
Page ("What do you want?") by hand. FB_ACCESS_TOKEN must stay the old Page's token - the
DM bot reads @kevin_trudeau_student's comments with it - so the new Page gets its own
pair, FB_POST_PAGE_ID + FB_POST_ACCESS_TOKEN (engine/poster.py fb_post_cfg).

Paste a LONG-LIVED user token (Graph API Explorer -> Generate Access Token with the new
Page ticked -> the blue "i" -> Open in Access Token Tool -> Extend Access Token -> copy).
A Page token made from it never expires. The script picks the Page, stores the pair,
turns Facebook back on for Kamay (removes it from KT_PLATFORMS_OFF) and runs check_keys.
Prints only the Page name - never a key.
"""
import getpass, json, os, re, subprocess, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
u = subprocess.run(["git", "-C", HERE, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
REPO = re.search(r"github\.com[:/]+([^/]+/[^/.]+?)(?:\.git)?/?$", u).group(1)
G = "https://graph.facebook.com/v21.0"
WANT = (sys.argv[1] if len(sys.argv) > 1 else "what do you want").lower()


def get(path, **q):
    try:
        return json.load(urllib.request.urlopen(f"{G}/{path}?" + urllib.parse.urlencode(q), timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit("  Meta refused: " + json.load(e).get("error", {}).get("message", str(e)))


print("\n  PASTE THE EXTENDED TOKEN (Access Token Tool -> Extend Access Token -> copy), then Enter.")
USER = getpass.getpass("  (nothing shows) > ").strip()
if len(USER) < 50:
    sys.exit("  That was empty. Run this again.")
pages = get("me/accounts", fields="name,id,access_token,tasks", access_token=USER).get("data", [])
if not pages:
    try:
        for b in get("me/businesses", fields="id", access_token=USER).get("data", []):
            pages += get(f"{b['id']}/owned_pages", fields="name,id,access_token", access_token=USER).get("data", [])
    except SystemExit:
        pass
pages = [p for p in pages if p.get("access_token")]
pick = [p for p in pages if WANT in p["name"].lower()]
if len(pick) != 1:
    for i, p in enumerate(pages, 1):
        print(f"  {i}. {p['name']}")
    if not pages:
        sys.exit("  No Page came with this token. Generate it again and tick the new Page.")
    pick = [pages[int(input("  Which number is the NEW page? ").strip()) - 1]]
p = pick[0]
if "CREATE_CONTENT" not in p.get("tasks", ["CREATE_CONTENT"]):
    sys.exit(f"  This login cannot post on {p['name']} (no Create content role).")
d = get("debug_token", input_token=p["access_token"], access_token=p["access_token"]).get("data", {})
if d.get("expires_at"):
    sys.exit("  This key would expire within hours. Click Extend Access Token first, then run this again.")
for k, v in (("FB_POST_PAGE_ID", p["id"]), ("FB_POST_ACCESS_TOKEN", p["access_token"])):
    subprocess.run(["gh", "secret", "set", k, "-R", REPO], input=v.encode(), check=True)
off = subprocess.run(["gh", "variable", "get", "KT_PLATFORMS_OFF", "-R", REPO], capture_output=True, text=True).stdout.strip()
left = ",".join(x for x in off.split(",") if x.strip() and x.strip() != "facebook")
subprocess.run(["gh", "variable", "set", "KT_PLATFORMS_OFF", "-R", REPO, "--body", left or " "], check=True)
subprocess.run(["gh", "workflow", "run", "check_keys.yml", "-R", REPO], check=False)
print(f"\n  Done. Kamay's clips now post to Facebook: {p['name']} (never expires).")
print(f"  Still off for Kamay: {left or 'nothing'}. Proof: Actions -> check_keys (running now).")
