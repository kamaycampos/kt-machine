# THE EDITOR: content production and editing agent (charter, 17 Oct 2026)

Kamay, 17 Oct 2026: our clips must be **#1 in 1. quality, 2. value, 3. quantity, 4. positive impact,
5. reach**, with cinematic ultra-HD openings and an unlimited supply of images and effects. A clip with
a great teaching and a bad picture (the "What Michael Jordan missed the most" Short: dark red frame,
blurred, a stray name label) does not get deleted; it gets a **cinematic living opening** over Kevin's
voice, and the teaching follows.

Serves KT (`kt-machine`), WB (`wb-factory`) and, once proven, every member of the Affiliate Factory.
Governed by `shared/FIRST_3_SECONDS.md`. Nothing reaches the queue until it was rendered on a real clip
and SHOWN to Kamay (that rule stands).

## What the numbers already settle
- **Skip rate decides reach.** KT, 180 clips: skip <40% -> median 995 views; >50% -> 284. Median today 48%.
  The opener is the product; everything here serves the first 3 seconds.
- **Full-bleed 9:16, never letterboxed.** MASTERY #5 (HIGH, 36 videos): full-bleed beat letterbox 20-100x.
  The reference account (@kevins_apprentice, 6.4K followers) letterboxes 16:9 on black. Take its
  b-roll-per-noun and its serif key words; do not take its frame.
- **No film or TV footage, ever.** The reference account cuts in movie scenes; that is a copyright strike
  waiting to happen and a takedown costs a young account more than ten good posts earn.

## Status, 17 Oct 2026 (night)
- **BUILT + pushed** (kt `b1f5101`, wb `9eb202e`): opener (`shared/kt_opener.py`), podcast-layout lock
  (`shared/kt_layout.py`), both in the full clip and the YouTube 59s cut; the story inherits them.
  The planner names the shot per clip (`"opener"`, PLANNING.md); `check_plan.py` validates it.
- **OFF until Kamay approves the first automatic clip:** repo variable `OPENER_LIVE` = on switches it
  on for every build; until then only test plans render openers (`OPENER_PREVIEW`).
- Known: the YouTube cut still draws its hook as plain mid-screen text near the captions (older code).

## The build, in order (each one rendered, shown, then measured)
1. **Opening visual gate.** Score the first 3 s of every render: brightness, sharpness, colour cast,
   face clear and lit, stray overlays. Below the bar -> flag `BAD OPENING VISUAL` and route the clip to
   layer 2 (never silently ship it).
2. **Cinematic opener.** First 2-4 s = an HD/4K moving shot that IS the hook's noun (tap water pouring,
   a mansion at dusk, a jet on snow), Kevin's voice already speaking under it, slow push-in, hook card
   coloured from that frame, a low sting under the voice. Then cut to Kevin. Every WB clip gets one;
   KT clips get one when layer 1 flags them, and A/B on the rest.
3. **Name-the-thing inserts** (RULES #17): 1-2 s cutaways when Kevin names a thing, number or place.
4. **Kinetic key word:** one serif accent word per line on the key idea, tested against today's captions.
5. **Voice-led format for low-resolution sources.** Kevin's voice over full HD visuals with a small face
   inset. Unlocks the 226 h of Kevin's library that sit at 240-360p (WB: 21 h of health episodes
   against 5.6 h at 1080p). This is WB's supply from week 3.

## Assets, at $0
- **Pexels + Pixabay APIs**: free, HD/4K stock video and photos, commercial use, no attribution. Each needs
  one free key: Kamay makes the account and pastes the key into the key script (never in chat).
- **AI images**: Canva is connected for hand-made covers. Generated images inside the cloud pipeline cost
  money per image; that is Kamay's decision (RULES #10, D1 "$0").
- Every asset is logged per clip (source, id, licence) so nothing un-licensed can ship.

## How it is judged
Skip rate per clip, opener vs no opener on matched clips (Trial Reels, `trial.py`), weekly. A layer that
does not lower skip rate is removed, however good it looks.
