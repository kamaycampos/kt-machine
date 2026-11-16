#!/usr/bin/env python3
"""READ-ONLY (16 Nov 2026): what would Meta's comment PUSH (webhooks) need on KT's keys?
Prints the app behind each key, its permissions, and which apps the Page is subscribed to.
Never prints a key. Sends nothing, changes nothing."""
import os
import requests

G = "https://graph.facebook.com/v21.0"


def get(url, **p):
    try:
        return requests.get(url, params=p, timeout=30).json()
    except Exception as e:
        return {"error": {"message": type(e).__name__}}


for name in ("FB_ACCESS_TOKEN", "IG_ACCESS_TOKEN"):
    tok = os.environ.get(name, "")
    if not tok:
        print(name, "- not set")
        continue
    d = get(f"{G}/debug_token", input_token=tok, access_token=tok).get("data") or {}
    print(f"{name}: app '{d.get('application')}' id {d.get('app_id')} type {d.get('type')} "
          f"valid {d.get('is_valid')} expires {d.get('expires_at')}")
    print("   scopes:", ", ".join(sorted(d.get("scopes") or [])) or d)
    for g in d.get("granular_scopes") or []:
        print("   granular:", g.get("scope"), "targets", len(g.get("target_ids") or []))
page, ptok = os.environ.get("FB_PAGE_ID", ""), os.environ.get("FB_ACCESS_TOKEN", "")
s = get(f"{G}/{page}/subscribed_apps", access_token=ptok)
print("page subscribed_apps:", [(a.get("name"), a.get("id"), a.get("subscribed_fields")) for a in s.get("data", [])]
      or s.get("error", {}).get("message"))
ig = get(f"{G}/{page}", fields="instagram_business_account{id,username}", access_token=ptok)
print("page -> instagram account linked:", bool(ig.get("instagram_business_account")))
