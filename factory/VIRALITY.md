# WHAT REALLY MAKES A CLIP GO VIRAL - research notes (3 Nov 2026)

Kamay, 3 Nov: "same way you research it, why can't we do it for going viral? what are the real
deep hidden causes of going stratospheric viral? all this is so we can go viral and hit our numbers."

Confidence: [Certain] = the platform said it / peer-reviewed. [Likely] = consistent across many
sources. [Guessing] = inference for us.

## 1. THE HIDDEN GATE: originality (could be capping us right now)
- **[Certain] April 2026, Instagram (Mosseri):** accounts that MAINLY post content they did not
  create, or did not meaningfully transform, are **no longer recommended to non-followers** -
  Reels, feed, Explore. Followers still see them. Virality IS non-follower reach, so an account
  under this rule cannot go viral no matter how good the clip is.
  ([TechCrunch](https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/),
  [PetaPixel](https://petapixel.com/2026/04/30/new-instagram-policies-target-reposted-content/))
- What does NOT count as original: minor edits, watermarks, credits. What keeps reach: remixing,
  real commentary, Instagram's repost tools, **collab posts**, and accounts with a licence or the
  creator's permission. [Likely, secondary coverage]
- **[Guessing] Why this matters for us:** KT, WB and AR post Kevin Trudeau's own footage. Our
  hooks, captions and grade may count as "minor edits". Trial reels go ONLY to non-followers, so
  if an account is flagged they show nothing at all.
- **CHECK FIRST:** each account's reach split followers vs non-followers (Insights / API). If
  non-follower reach collapsed after late April 2026, this is the cause, not the hooks.
- Ways out, in order: (1) written permission or licence from Kevin's side (GIN affiliate terms?);
  (2) collab posts with his account; (3) real transformation: our own voice-over or on-screen
  commentary, a lesson card, a reaction format - not just a caption.

### MEASURED 3 Nov 2026 (reach_audit.yml, Instagram's own numbers) - WE ARE NOT CAPPED [Certain]
| Account | Followers | Reach, last 14 days | From non-followers |
|---|---|---|---|
| KT @kevin_trudeau_student | 4,593 | 18,601 | 96% |
| AR @theawakenedrise | 215 | 8,661 | 99% (growing every window: 1.1K -> 8.7K) |
| WB @wb_organics | 16 | 2,118 | 100% (growing: 762 -> 2,118) |
Instagram IS recommending all three to strangers. The originality rule is not the problem today.
**The real KT problem:** reach per 14 days 77K -> **103K** (9-23 Sept) -> 30K -> 16K -> 19K, with the
non-follower share unchanged. Fewer clips get pushed, not a block. Over the same weeks **shares per
reel fell from 9.4 to ~3** (state/metrics.json) while skip rate stayed ~48-50% - the drop is in
SENDS, Mosseri's strongest signal with non-followers. [Likely] The next lever is clips people send.

## 2. The three signals Instagram ranks by [Certain - Mosseri, Jan 2025]
- **Watch time** (matters on every surface), **likes per reach**, **sends per reach**.
- Likes weigh slightly more with followers; **sends weigh more with non-followers**. Mosseri:
  sends per reach "correlate more ... with overall reach than anything else."
  ([Social Media Today](https://www.socialmediatoday.com/news/instagram-shares-algorithm-insights-2025/738034/))
- So the viral clip is the one people **DM to a friend**. Ask of every clip: who would someone
  send this to, and why? ("this is so you", "we need to do this", "told you so").

## 3. Why people share: high-arousal emotion [Certain - Berger & Milkman, J. Marketing Research]
- Content that triggers **high-arousal** emotions spreads most: **awe** (positive), **anger** and
  **anxiety** (negative). Low-arousal emotions (sadness, contentment) spread least. Arousal, not
  positive vs negative, decides it.
  ([paper](https://www.blueclaw.co.uk/aboutama/documents/jmr_forthcoming/online_content_viral.pdf),
  [APA podcast](https://www.apa.org/news/podcasts/speaking-of-psychology/viral))
- Berger's STEPPS: **Social currency** (sharing makes ME look smart), **Triggers** (everyday cues
  bring it back), **Emotion** (high arousal), **Public**, **Practical value** (useful = shared),
  **Stories** (the lesson rides inside a story).
- For Kevin: awe = "a billionaire did THIS"; anger = "they hid this from you"; anxiety = "you are
  losing money every day you don't know this"; practical value = a step the viewer can do today.

## 4. The first seconds and the finish [Likely - consistent across creator analyses; no official spec]
- The first 2-3 seconds are the main filter (swipe-away). Completion rate and **rewatches** are
  the strongest positive signals on TikTok and Shorts. Endings that loop back to the start get
  rewatched. ([summary](https://dev.to/kyle_clipspeedai/youtube-shorts-algorithm-in-2026-what-actually-determines-whether-your-clip-gets-pushed-1g3g))
- Our own numbers already say it (FIRST_3_SECONDS.md): top clips skip 36.8%, the rest 47.8%.

## 5. What this means for the machine - candidate builds, none started
1. **Measure the gate:** non-follower reach % per account per week, before/after April 2026.
2. **Score clips by sends, not likes:** sends per reach from Insights into the scoreboard and
   the trial-reel winner (today trials score views only).
3. **Planner rule:** every clip names its share reason (who would you send it to) and its
   high-arousal emotion (awe / anger / anxiety) - same as the hook test, one level deeper.
4. **Transformation:** prototype a format with our own commentary (voice or on-screen lesson),
   shown to Kamay first, for the originality rule.
5. **Loops:** end on a line that sends the viewer back to the hook.
