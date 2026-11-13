"""READ-ONLY (13 Nov 2026): "this person commented RISE and got no message" - why?
The person is named by the sha256 of their lowercase username (WHO_SHA), so no username is
written into this public repo or its logs. Sends nothing.

Prints every comment AND reply of the last DAYS days on the newest 50 Instagram posts as the AR
key sees it, marks the person's own as TARGET, and says what the DM bot's state holds for each."""
import hashlib, json, os, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DM_BRAND"] = "AR_"
import dm_reply as m

WHO = (os.environ.get("WHO_SHA") or "").strip().lower()
DAYS = int(os.environ.get("WHO_DAYS") or 0)
d = json.load(open(m.STATE))
kws = m.keywords()
ig, tok = m.env("IG_USER_ID"), m.env("FB_ACCESS_TOKEN")
mine = m._get(f"{m.G}/{ig}", {"fields": "username", "access_token": tok}).get("username", "")
cut = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%S")


def tag(name):
    if not name:
        return "NO-NAME"
    if name == mine:
        return "US"
    return "TARGET" if hashlib.sha256(name.lower().encode()).hexdigest() == WHO else "other"


def state(cid):
    return "SENT" if cid in d["sent"] else ("seen " + d["seen"][cid][:16] if cid in d["seen"] else "NEVER SEEN BY BOT")


print(f"keywords {kws} | bot skips comments before {m.SINCE} | now {datetime.now(timezone.utc).isoformat()[:16]}")
media = m._get(f"{m.G}/{ig}/media", {"fields": "id,timestamp,comments_count,caption,media_product_type",
                                     "limit": 100, "access_token": tok}).get("data", [])
found = 0
for n, p in enumerate(media, 1):
    if not p.get("comments_count"):
        continue
    cs, url, params = [], f"{m.G}/{p['id']}/comments", {
        "fields": "id,text,timestamp,username,hidden,replies{id,text,timestamp,username}",
        "limit": 50, "access_token": tok}
    pages = 0
    while url and pages < 6:
        j = m._get(url, params)
        cs += j.get("data", [])
        url, params, pages = (j.get("paging") or {}).get("next"), {}, pages + 1
    recent = [c for c in cs if c["timestamp"][:19] >= cut
              or any(r["timestamp"][:19] >= cut for r in (c.get("replies") or {}).get("data", []))
              or tag(c.get("username")) == "TARGET"
              or any(tag(r.get("username")) == "TARGET" for r in (c.get("replies") or {}).get("data", []))]
    if not recent:
        continue
    print(f"POST #{n} of newest (bot reads 25) {p['timestamp'][:16]} {p.get('media_product_type')} "
          f"says {p.get('comments_count')} comments, API gave {len(cs)} in {pages} page(s)"
          f" | {(p.get('caption') or '')[:50]!r}")
    for c in recent:
        t = tag(c.get("username"))
        found += t == "TARGET"
        reps = (c.get("replies") or {}).get("data", [])
        print(f"   {c['timestamp'][:16]} ...{c['id'][-5:]} [{t}] text={(c.get('text') or '')[:24]!r} "
              f"kw={m.matched(c.get('text'), kws)} hidden={c.get('hidden')} "
              f"we_replied={any(r.get('username') == mine for r in reps)} -> {state(c['id'])}")
        for r in reps:
            t = tag(r.get("username"))
            found += t == "TARGET"
            print(f"       REPLY {r['timestamp'][:16]} ...{r['id'][-5:]} [{t}] text={(r.get('text') or '')[:24]!r} "
                  f"kw={m.matched(r.get('text'), kws)} (the bot never reads replies)")
print(f"TARGET comments found: {found}" + ("" if WHO else " (no WHO_SHA given)"))
