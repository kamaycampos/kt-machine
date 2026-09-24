# What actually works - the living record

Measured on Kamay's own account. **Never rewritten from scratch**: each pass confirms a pattern
(adds evidence), weakens one (lowers confidence, explaining why), or adds a new one, and leaves a
dated line at the end. Every pattern carries its confidence and the `n` behind it. Nothing reaches
HIGH on fewer than ~5 cases a side.

A **hook** is the text burned into the video; a **caption** is the text posted beside it. They are
measured from different places and a caption finding never transfers to a hook. Hooks live in
`state/manifest.json` (field `hook`, written when the clip is made, never edited).

## Patterns

| # | Pattern | Confidence | n |
|---|---|---|---|
| 1 | A **method** beats a **warning** on the same material. "How rich people actually buy houses" (180,796 views) beat "Why a mortgage is a scam" from the same source video. | MEDIUM | 2 clips, one source |
| 2 | What separated the 180K clip was **shares and saves (30-40x)**, not watch time. Write for "someone needs to see this", not for retention alone. | MEDIUM | same pair |
| 3 | **Homes, and the daily habits of wealthy people**, out-reach everything else on both Instagram and TikTok. | HIGH | 203K IG + 26K TikTok vs a median near 1K |
| 4 | Speaking **to the viewer** in the caption beats naming Kevin; a **question** CTA beats a sell CTA (76 sell-CTA posts never beat 31 with a question). | HIGH | 107 posts |
| 5 | **Full-bleed 9:16** beat letterboxed by 20-100x. The format rebuild took median YouTube views from 2 to ~984. | HIGH | 36 videos |
| 6 | YouTube is the reach channel (~10x Instagram per post at a fraction of the followers), and it sits at a **~1,000 view ceiling**: the bottleneck is retention, not reach. Length is NOT the cause - that was tested and I was wrong. | HIGH | 36 videos |
| 7 | **Six-word hooks** outperform long ones; the single best clip's hook was six words. Longer hooks cannot be read before they fade. | MEDIUM | 1 outlier + readability |
| 8 | Clips that open mid-sentence or end before the payoff get rejected by Kamay on sight, and the ones that slipped out underperformed. Edges are now named in words and machine-checked. | HIGH | 37 of 75 clips once opened mid-sentence |

| 9 | **The hook moves TikTok, not YouTube.** Across every grouping below, YouTube's median sits at ~940 views whatever the hook says - that is the ceiling (retention), not the hook. TikTok's median swings by 10-60x on the same clips. So test hooks on TikTok and Instagram; do not judge a hook by YouTube. | MEDIUM | 62 clips with hook + numbers |
| 10 | Hooks that say **rich / wealthy** when it is true: TikTok median **1,029** vs **16** for the rest. | LOW-MEDIUM | 6 vs 56 |
| 11 | Openers, TikTok median: **What... 293** > **Why... 61** > **How... 13**. "How" is not banned - it is the plainest promise and it wins on Instagram - but on TikTok prefer What/Why. | LOW | 6 / 20 / 22 |
| 12 | A number in the hook helps TikTok (106 vs 22) and the best single hook we have is `The 30% rule every wealthy person follows` (12,081 TikTok views, 20x the next). | LOW | 8 vs 54 |
| 13 | Instagram engagement does NOT follow TikTok/YouTube reach: "Why a mortgage is a scam" is bottom on both (22 YT, 0 TT) and top on Instagram (211 likes, 57 comments). Rank each platform separately - never pool them. | MEDIUM | 62 clips |
| 14 | **TikTok throttles personal-finance instruction; Instagram does not.** Six clips sit at 7-26 TikTok views against a median of 335 and winners at 13K-34K, while the same clips are normal on Instagram: the debt settlement trick, cutting a bill in half, "what is keeping you poor", plus three weak-hook clips. The shape that wins on TikTok is a story or a wealth habit (`What every billionaire's home has` 34,214; `Wealthy people live below` 13,085). Keep the how-to-save-money clips - they do fine on Instagram and YouTube - but do not expect TikTok reach from them. | MEDIUM | 6 throttled vs 48 measured |
| 15 | **The hook must take the clip's strongest fact.** `What a stranger told him` (24 Sept) was chosen over "changed one word", "$1M before 18" and "$180M in 18 months" - all inside the same clip. Nothing about it tells a scrolling stranger what they get. Rule added to both playbooks. | ASSERTED (act on it, measure it) | 1 |
| 16 | **The hook needs a concrete, picturable thing in it.** Kamay rejected "One word made him millions" and "He changed one word in a newspaper ad" outright - they tell the viewer nothing - and kept "A million dollars before he turned 18". Number, age, amount, name. A mechanism tease is a riddle, and riddles were already measured as our weakest shape. | ASSERTED (his call, act on it) | - |

## Open questions (not yet answered by data)
- Does a **cinematic caption style** (colour drawn from the clip, one hero word, words placed around Kevin) beat the current house style? To be tested as Trial Reels, full-screen vs card.
- Does the comment-keyword CTA convert better than the question CTA? Needs **comments per 1,000 views**, not view rate - they measure different things.
- Do Trial Reels hook variants (7 a day, same clip) move view rate? Never run.

## Changelog
- **22 Sept 2026** - created. Hook text is now stored with every clip (175 past clips recovered), so the next pass can rank hooks for the first time. Worn-out-word check added to the plan checker: any hook word appearing in over a third of the last 40 posts is refused.
- **23 Sept 2026** - first hook ranking ever possible (62 clips). Findings 9-13 added. Best hook to date: "The 30% rule every wealthy person follows". Worst-performing shape: a bare belief claim with no subject ("Why your beliefs are not yours", 7 YT views).
- **23 Sept 2026** - TikTok suppression measured for the first time (finding 14). Board cleaning and 6 posts a day shipped the same day.
