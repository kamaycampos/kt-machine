"""READ-ONLY (15 Nov 2026): does ANOTHER key see comments the DM bot's key is not given?
Instagram said 3 comments on a post and gave the bot's key 1. Counts only, no names, no text."""
import os, requests
ig, page_tok, ig_tok = os.environ.get("IG_USER_ID"), os.environ.get("FB_ACCESS_TOKEN"), os.environ.get("IG_ACCESS_TOKEN")
T = 30
def top(base, tok, mid):
    r = requests.get(f"{base}/{mid}/comments", params={"fields": "id,timestamp,hidden,replies{id}", "limit": 50, "access_token": tok}, timeout=T).json()
    if "error" in r:
        return "error: " + r["error"].get("message", "")[:90]
    d = r.get("data", [])
    return f"{len(d)} top-level, {sum(len((c.get('replies') or {}).get('data', [])) for c in d)} replies, hidden flags {[c.get('hidden') for c in d]}"
m = requests.get(f"https://graph.facebook.com/v21.0/{ig}/media", params={"fields": "id,timestamp,comments_count", "limit": 6, "access_token": page_tok}, timeout=T).json().get("data", [])
for p in m:
    if not p.get("comments_count"):
        continue
    print(f"POST {p['timestamp'][:16]} Instagram says {p['comments_count']} comments")
    print("   page key  (graph.facebook.com):", top("https://graph.facebook.com/v21.0", page_tok, p["id"]))
    if ig_tok:
        print("   IG key    (graph.facebook.com):", top("https://graph.facebook.com/v21.0", ig_tok, p["id"]))
        print("   IG key    (graph.instagram.com):", top("https://graph.instagram.com/v21.0", ig_tok, p["id"]))
