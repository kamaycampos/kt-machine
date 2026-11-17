#!/usr/bin/env python3
"""KT's keys after @kevin_trudeau_student moves to the Page "What do you want?" - pasted into
THIS prompt, never into a chat.

    python3 kt_page_move.py            (run inside kt-machine)

17 Nov 2026. Facebook suspended "Kevin Trudeau Wisdom" on 8 Oct ("no se enviaran las respuestas
automaticas", no ads). The KT Instagram is moved to the healthy Page "What do you want?", so
Meta's own comment rule, the inbox and ads work again. Every KT key hung on the old Page:
FB_PAGE_ID + FB_ACCESS_TOKEN (the DM bot) and IG_ACCESS_TOKEN (all Instagram posting). This makes
all three from ONE extended user token of app KT_Student, after the Instagram is linked.

Paste a LONG-LIVED user token (Graph API Explorer, app KT_Student -> Generate Access Token with
"What do you want?" and @kevin_trudeau_student ticked -> the blue "i" -> Open in Access Token
Tool -> Extend Access Token -> copy). A Page token made from it never expires.

It refuses to store anything unless: the Page is "What do you want?", the Instagram linked to it
is KT's own (IG_USER_ID stays 17841442646984686), the key never expires, and it carries every
permission posting and the DM bot use. Then it stores the three secrets and runs check_keys.
Prints only names and yes/no - never a key.
"""
import getpass
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

G = "https://graph.facebook.com/v21.0"
KT_IG = "17841442646984686"            # @kevin_trudeau_student - the account does not change
WANT = "what do you want"
NEED = {"instagram_basic", "instagram_content_publish", "instagram_manage_comments",
        "instagram_manage_messages", "instagram_manage_insights", "pages_read_engagement",
        "pages_show_list"}

u = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout
REPO = re.search(r"github\.com[:/]+([^/]+/[^/.]+?)(?:\.git)?/?$", u.strip()).group(1)
GH = "gh"
for cand in ("/Users/yarengul/Kamay/bin/gh",):
    try:
        subprocess.run([cand, "--version"], capture_output=True, check=True)
        GH = cand
    except (OSError, subprocess.CalledProcessError):
        pass


def get(path, **q):
    try:
        return json.load(urllib.request.urlopen(f"{G}/{path}?" + urllib.parse.urlencode(q), timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit("  Meta refused: " + json.load(e).get("error", {}).get("message", str(e)))


print("\n  PASTE THE EXTENDED TOKEN (Access Token Tool -> Extend Access Token -> copy), then Enter.")
USER = getpass.getpass("  (nothing shows) > ").strip()
if len(USER) < 50:
    sys.exit("  That was empty. Run this again.")

pages = [p for p in get("me/accounts", fields="name,id,access_token", access_token=USER).get("data", [])
         if p.get("access_token") and WANT in p["name"].lower()]
if len(pages) != 1:
    sys.exit(f"  Found {len(pages)} Page(s) called 'What do you want?' on this token. "
             "Generate it again with that Page ticked.")
p = pages[0]
print(f"  Page: {p['name']}")

ig = get(p["id"], fields="instagram_business_account{id,username}",
         access_token=p["access_token"]).get("instagram_business_account") or {}
if ig.get("id") != KT_IG:
    sys.exit(f"  The Instagram linked to this Page is {ig.get('username') or 'NONE'}, not "
             "@kevin_trudeau_student. Link it first (Page settings -> Linked accounts), then run this again.")
print(f"  Instagram linked: @{ig.get('username')}  (same account, same id)")

d = get("debug_token", input_token=p["access_token"], access_token=p["access_token"]).get("data", {})
if d.get("expires_at"):
    sys.exit("  This key would expire. Click Extend Access Token first, then run this again.")
missing = NEED - set(d.get("scopes") or [])
if missing:
    sys.exit("  Missing permission(s): " + ", ".join(sorted(missing)) +
             ". Tick them in Graph API Explorer, generate again, extend, and run this again.")
print("  Key: never expires, every permission present")

for k, v in (("FB_PAGE_ID", p["id"]), ("FB_ACCESS_TOKEN", p["access_token"]),
             ("IG_ACCESS_TOKEN", p["access_token"])):
    subprocess.run([GH, "secret", "set", k, "-R", REPO], input=v.encode(), check=True)
    print(f"  stored {k}")
subprocess.run([GH, "workflow", "run", "check_keys.yml", "-R", REPO], check=False)
print("\n  Done. KT now posts and answers comments through 'What do you want?'.")
print("  Proof: Actions -> check_keys (running now). IG_USER_ID did not change.")
