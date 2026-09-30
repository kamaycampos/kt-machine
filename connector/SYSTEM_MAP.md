# SYSTEM MAP

Every project in the system, where it lives, and the fence around it.
Last full sweep: 30 Sept 2026.

## Projects

| # | Project | Whose | Chat | Repo | Status |
|---|---|---|---|---|---|
| 1 | **Kevin Trudeau Wisdom** (KT affiliate content) | Kamay | "Billionaire empire content creation" | `kt-machine` (public) — everything not prefixed `AR_` | Live. Posts 6/day to IG, FB, YT, TikTok from GitHub Actions. Link: links.fans/wealthfrequency |
| 2 | **Awakened Rise** (@theawakenedrise) | Yaren | "Awakened Rise brand setup" | `kt-machine` — `AR_*`, `ar_*.json`, `ar_source_plan.json`, `AR_PLANNING.md` | Live. Same machinery, own account, own lane, inverted hook rule |
| 3 | **VSC — GIN Project 15** ("Classified" interviews for the Affiliate Portal) | Kamay's job | "VSC Video Production" | `vsc-factory` (public, active) · `vsc-machine` (private, older) | Live. Clips go to Frame.io for GIN reviewers |
| 4 | **The Connector** | Kamay | this chat | `kt-machine/connector/` | Started 30 Sept 2026 |
| 5 | **Project 5** | — | not opened yet | — | Waiting on Kamay |
| ? | **Trading system** | Kamay | "Trading portfolio and Engine 3 status" | `kamay-trading-bot` | Not yet confirmed as part of this system — see OPEN_QUESTIONS |

## What is shared (one home: `kt-machine/shared/`)

Pulled by every factory at setup and hash-checked against `shared/MANIFEST.json`.

| Module | Job |
|---|---|
| `kt_words.py`, `vsc_words.py`, `vsc_v2_time.py` | word timings, caption timing anchored to the sound |
| `kt_burn.py`, `kt_render.py`, `vsc_v2_onscreen.py` | caption breaks, rendering, on-screen read-back |
| `kt_snap.py`, `vsc_frame.py` | face framing |
| `vsc_edges.py`, `kt_lock.py` | clean openings and endings, silence |
| `kt_qc.py` + `QC_AGENT.md` | the quality gate before anything reaches an account |
| `FIRST_3_SECONDS.md` | the law the planner works under (30 Sept 2026) |

## What is fenced (never shared)

| | KT | Awakened Rise | VSC |
|---|---|---|---|
| Hooks | Kamay states the benefit | inverse of Kamay's rule | one-idea hook, GIN-approved |
| Plans | `factory/plans/ep_*.json` | `factory/plans/ar_*.json` | `vsc-factory/plans/` |
| Source episodes | `source_plan.json` | `ar_source_plan.json` | Classified series (not Rumble) |
| Style | house style | her style | DIN Condensed Bold (encrypted) |
| Accounts / secrets | KT set | AR set | none — delivered to Frame.io |

Enforced in code: `poster` refuses to post a clip to the wrong account, `kt_fence.py`
refuses a source episode that serves both brands.

## Data flow

```
Rumble / Mac sources ─► factory (Actions) ─► kt_qc gate ─► queue ─► post.yml ─► 4 platforms
                              ▲                                          │
                     shared/ engine ◄── improvements from any project     ▼
                              │                               measure.py / tiktok_stats
                     vsc-factory pulls it ─► Frame.io        └─► MASTERY.md (living record)
```

## Where the truth lives

| What | Where | Reachable from cloud? |
|---|---|---|
| Chief aim / unified empire playbook | `~/Kamay/KAMAY_EMPIRE_UNIFIED.md` on the Mac | **No** |
| Earnings (RULE #1 score) | `~/Kamay/private/earnings.json` | No (by design — private) |
| What works on Kamay's account | `factory/MASTERY.md` | Yes |
| Quality gate memory | `shared/QC_AGENT.md` | Yes |
