#!/usr/bin/env python3
"""Awakened Rise DM key, pasted into THIS prompt - never into a chat.

    python3 ar_dm_key.py            (run inside kt-machine)

2 Nov 2026. Her captions ask for RISE/LUCKY and nobody got the link: AR_FB_ACCESS_TOKEN
was made without instagram_manage_messages / instagram_manage_comments, so the DM bot
(dm/dm_reply.py, DM_BRAND=AR_) is refused. Same fix as Kevin's D7 on 14 Oct.

3 Nov 2026, Yaren: everything under HER OWN Meta account, not Kamay's. The key now comes
from her app "Awakened Rise Replies" (1199712782379494, her Awakened Rise business,
published) and replaces BOTH AR_FB_ACCESS_TOKEN and AR_IG_ACCESS_TOKEN, so her posting,
stats and DMs all run on her app.

Paste a LONG-LIVED user token (Graph API Explorer on her app -> Generate Access Token with
her Page ticked -> the blue "i" -> Open in Access Token Tool -> Extend Access Token -> copy).
The script picks her Page, refuses unless the Page key keeps EVERY permission her posting
already uses plus the DM, comment, Facebook-message and stats ones, never expires and is
linked to her Instagram, then stores it. Prints only names and id endings - never a key.
"""
import getpass, json, os, re, subprocess, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GH = os.path.expanduser("~/Kamay/bin/gh")
GH = GH if os.path.exists(GH) else "gh"
u = subprocess.run(["git", "-C", HERE, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
REPO = re.search(r"github\.com[:/]+([^/]+/[^/.]+?)(?:\.git)?/?$", u).group(1)
G = "https://graph.facebook.com/v21.0"
PAGE_ENDS = "4857"                       # AR_FB_PAGE_ID ends with this (read 2 Nov 2026)
# what her posting key already had (2 Nov) + what the DM bot needs
NEED = {"instagram_basic", "instagram_content_publish", "pages_manage_posts", "pages_read_engagement",
        "pages_show_list", "instagram_manage_messages", "instagram_manage_comments",
        "instagram_manage_insights", "pages_messaging", "pages_read_user_content",
        "pages_manage_engagement"}
APP = "1199712782379494"                 # Awakened Rise Replies - hers


def get(path, **q):
    try:
        return json.load(urllib.request.urlopen(f"{G}/{path}?" + urllib.parse.urlencode(q), timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit("  Meta refused: " + json.load(e).get("error", {}).get("message", str(e)))


print("\n  PASTE THE EXTENDED TOKEN (Access Token Tool -> Extend Access Token -> copy), then Enter.")
USER = getpass.getpass("  (nothing shows) > ").strip()
if len(USER) < 50:
    sys.exit("  That was empty. Run this again.")
pages = get("me/accounts", fields="name,id,access_token", access_token=USER).get("data", [])
pick = [p for p in pages if p.get("access_token") and p["id"].endswith(PAGE_ENDS)]
if len(pick) != 1:
    print("  Pages this login gave:", ", ".join(f"{p['name']} (...{p['id'][-4:]})" for p in pages) or "none")
    sys.exit(f"  Her Page (id ending {PAGE_ENDS}) was not in it. Generate again and tick her Page.")
p = pick[0]
d = get("debug_token", input_token=p["access_token"], access_token=p["access_token"]).get("data", {})
missing = NEED - set(d.get("scopes", []))
if missing:
    sys.exit(f"  Nothing saved. The key is missing: {', '.join(sorted(missing))}. Add them in Explorer and Generate again.")
if d.get("expires_at"):
    sys.exit("  Nothing saved. This key would expire. Click Extend Access Token first, then run this again.")
if str(d.get("app_id")) != APP:
    sys.exit("  Nothing saved. This key was made on a different app - pick Awakened Rise Replies in Explorer.")
ig = get(p["id"], fields="instagram_business_account{username}", access_token=p["access_token"]).get(
    "instagram_business_account") or {}
if not ig.get("id"):
    sys.exit("  Nothing saved. This Page has no Instagram account linked to it.")
for k in ("AR_FB_ACCESS_TOKEN", "AR_IG_ACCESS_TOKEN"):
    subprocess.run([GH, "secret", "set", k, "-R", REPO], input=p["access_token"].encode(), check=True)
print(f"\n  SAVED for {p['name']} (...{p['id'][-4:]}) and Instagram @{ig.get('username')} (...{ig['id'][-4:]}):")
print("  your own app, never expires, posts, reads stats, replies to comments and sends DMs.")
print("  You can close this tab. Claude takes it from here.\n")
