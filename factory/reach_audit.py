#!/usr/bin/env python3
"""IS INSTAGRAM SHOWING US TO STRANGERS? Read-only (3 Nov 2026).

Since April 2026 Instagram stops recommending accounts that mainly post content they did not
create or meaningfully transform - to non-followers only (VIRALITY.md). Going viral IS reach
among non-followers, so this measures it per account: followers, and reach split by follow type
in 14-day windows. Nothing is posted or changed.

    python factory/reach_audit.py          # needs IG_USER_ID/IG_ACCESS_TOKEN (+ AR_ pair)
"""
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

G = "https://graph.facebook.com/v21.0"


def get(path, **params):
    url = f"{G}/{path}?" + urllib.parse.urlencode(params)
    try:
        return json.load(urllib.request.urlopen(url, timeout=30))
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.load(e).get("error", {})}
        except Exception:
            return {"error": {"message": str(e)}}


SAVE = {}


def audit(name, ig, tok):
    print(f"\n== {name}")
    rec = SAVE.setdefault(name, {"windows": []})
    me = get(ig, fields="username,followers_count,media_count", access_token=tok)
    if me.get("error"):
        print("  account:", me["error"].get("message", "")[:160]); return
    print(f"  @{me.get('username')}  followers {me.get('followers_count')}  posts {me.get('media_count')}")
    rec.update(username=me.get("username"), followers=me.get("followers_count"), posts=me.get("media_count"))
    today = dt.date.today()
    print("  window                    reach   followers  non-followers  non-follower share")
    for k in range(6, 0, -1):
        a = today - dt.timedelta(days=14 * k)
        b = a + dt.timedelta(days=14)
        d = get(f"{ig}/insights", metric="reach", period="day", metric_type="total_value",
                breakdown="follow_type", since=a.isoformat(), until=b.isoformat(), access_token=tok)
        if d.get("error"):
            print(f"  {a} - {b}: {d['error'].get('message', '')[:140]}"); continue
        row = (d.get("data") or [{}])[0].get("total_value") or {}
        split = {}
        for bd in row.get("breakdowns") or []:
            for r in bd.get("results") or []:
                split[(r.get("dimension_values") or ["?"])[0]] = r.get("value", 0)
        tot = row.get("value") or sum(split.values())
        fo, nf = split.get("FOLLOWER", 0), split.get("NON_FOLLOWER", 0)
        share = f"{nf / (fo + nf):.0%}" if fo + nf else "-"
        print(f"  {a} - {b}  {tot:7}  {fo:9}  {nf:13}  {share:>8}")
        rec["windows"].append({"from": a.isoformat(), "to": b.isoformat(), "reach": tot,
                               "followers": fo, "non_followers": nf})


if __name__ == "__main__":
    for name, pre in (("KT (Kamay)", ""), ("AR (Yaren)", "AR_")):
        ig, tok = os.environ.get(pre + "IG_USER_ID", ""), os.environ.get(pre + "IG_ACCESS_TOKEN", "")
        if ig and tok:
            audit(name, ig, tok)
        else:
            print(f"\n== {name}: not configured")
    if "--save" in os.sys.argv:              # the strategist reads it (MASTERY.md: the score is sends)
        SAVE["measured"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "reach.json")
        json.dump(SAVE, open(p, "w"), indent=1)
        print("saved", p)
