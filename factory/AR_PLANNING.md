# Weekly clip planning for AWAKENED RISE (Yaren's account)

This is a different person's account from the one `PLANNING.md` serves. Yaren's brand is
**Awakened Rise** (@theawakenedrise). Her lane, her voice, her hooks, her episodes. Nothing here is
shared with Kamay's account except the machinery.

**The fence, first.** A source episode is cut for ONE account, ever. Her list is
`factory/ar_source_plan.json`; his is `factory/source_plan.json`. Never plan an episode from his
list, never touch a file named `ep_*.json`, never write a `KT_` folder. `kt_fence.py` refuses a
source that serves both, and the checker refuses the wrong folder family. If you ever have to choose
between filling her queue and crossing that line, leave the queue empty and say so.

**Work alone, in this one session.** Never use the Agent or Task tool, never start subagents or background
tasks: read and write every plan yourself, one episode at a time. (6 Oct 2026: a run fanned out 21 agents
on the second-chance backlog, hit the account's usage limit, and pushed nothing.) **Commit and push after
each plan passes `check_plan.py`**, to the same branch - the merge job takes each push - so a run that is
cut off still keeps the plans it finished.

## Procedure
1. `pip install -q opencv-python-headless pillow numpy 2>/dev/null`
2. `python factory/routine_prep.py --brand ar --max 4` - prints HER queue, downloads and decrypts the
   next unplanned episodes from her list, and writes 30-second reading blocks.
   - Queue over 50 clips: plan nothing, report, stop. 30-50: plan 2. Under 30: plan 4.
2b. If the prep printed **TAKEN DOWN BY TIKTOK**, plan a replacement for each from the same episode - same lesson, different moment, different hook - and say so in your report.
2c. **NEW EPISODES COME FIRST (2 Nov 2026; Kamay's account has run this way since 16 Oct).** Plan the episodes the prep offers under READY TO PLAN before any re-cut: when her queue is under 30, at least 2 new episodes with 6-9 clips each. Until 2 Nov this step said re-cuts first: her planner re-cut the same refusals day after day (one episode on its 7th try) while 6 HD, transcribed episodes on her list sat unplanned and her queue fell to 0. Then, if the prep printed **SECOND CHANCES**, re-cut those clips - after the new episodes. The teaching was already judged worth posting and the episode is transcribed; only a gate stopped it. For each episode listed:
   - Write `factory/plans/ar_<id>_r2.json` (`_r3` if `_r2` exists) with the same `source`, brand = the old brand + `R2` (e.g. `AR_CANVAS` -> `AR_CANVASR2`), and every clip carrying `"retry_of": "<the key printed, e.g. ar_v6v9urd/WALL-STREET-500-RIVALS>"`.
   - Fix what the **WHY** line says, in `work/<id>.srt`:
     - hook lint ("not a direct promise", "opens on a riddle", "no stakes") -> rewrite the hook; keep the cut.
     - "opens mid-sentence", "ends mid-thought", "ends off the planned words" -> re-find the edges: open on the first words of a complete sentence after a pause, close on the sentence end where the teaching lands; copy `start_words` / `end_words` exactly from the cues.
     - "word repeated", "phrase scrambled", "(laughing)", "[BLANK_AUDIO]" -> move an edge so the damaged words fall outside the clip; if they sit in the middle of the teaching, skip the clip.
     - "captions vs the sound", "UNCAPTIONED SPEECH", "too few to judge" -> move both edges to different sentence boundaries (a few seconds re-times every caption). If the gap named is someone else talking, cut so it falls outside.
     - "opens on B-roll, no face" -> open on a different sentence where Kevin is speaking on camera (not over a graphic or clip); "runs into" / "no passing ending" -> end on an earlier sentence that closes the thought.
     - "no clip came out of the render" (filed before 20 Oct 2026) is NOT "nothing to fix": it was the edge step dropping the clip without saying why - almost always one of the two lines above. Re-cut it: open on a different complete sentence with Kevin on camera, close on a clean sentence end.
   - `tries 2` means this is its last chance: skip it unless you can see the cause and fix it.
   - Second chances count toward this run's clips. Report how many you re-cut and how many you skipped, and why.
2d. If the prep printed **MONTH LIST RUNNING OUT**, append 6 episodes to `factory/ar_source_plan.json`
   (append only, never reorder or drop) - from the stocked list and the candidates it printed, her lane
   only. Do this EVERY time it prints, even when second chances fill the run: an empty list is how her
   queue hit zero on 12 Oct 2026 and stayed there. The factory stocks and transcribes them overnight,
   and the next run plans them. If READY TO PLAN is 0, the second chances are the only clips you can
   make today - say so in the report.
2e. If the prep printed **SECOND PASS**, those episodes are hers, already cut once, and most of their minutes were never used (2 Nov 2026: 24 of her HD episodes hold 21 hours no clip has touched). Plan them after the new episodes and the second chances, the same way, with these differences:
   - Write `factory/plans/ar_<id>_p2.json` (`_p3` if `_p2` exists), with the same `source` and a **new** brand (`AR_` + one word, unused by any plan).
   - In `work/<id>_blocks.txt` every stretch a clip already uses is one line, `=== USED by <SLUG> (in-out s) ===`. Never cut inside it: `check_plan.py` refuses a clip that re-uses more than 10 seconds of another clip's minutes.
   - New teachings only: read the USED slugs, and skip a moment that repeats the lesson of a clip already cut, even from different minutes.
   - Her lane and her bar, exactly as for a first pass. If the unused minutes hold only 2 clips worth posting, plan 2.
2f. **CUT BEFORE THE FACTORY** in the prep names list entries cut on the Mac in September: the stocker never fetches them, so they are not stock. They count as dead; the month list needs real episodes in their place.
3. Read `factory/HOOK_PATTERNS.md` for the story and caption craft - then **invert the hook rule**
   (see below). Read each episode's `work/<id>_blocks.txt` in full. Choose 6-9 clips.
4. Write `factory/plans/ar_<id>.json` (same shape as his, brand `AR_<ONEWORD>`).
5. `python factory/check_plan.py factory/plans/ar_<id>.json` and fix everything it reports.
   Lines starting `~` are warnings, not errors: a hook with **no stakes** (nothing the viewer gets, fears or
   recognises, e.g. "Ten strangers waited / in the basement") gets one. Rewrite it unless the stab lands without a stake.
6. Commit only your new `ar_*.json` files (plus `factory/ar_source_plan.json` if you extended it -
   append only) and push to a branch `claude/ar-plans-<YYYY-MM-DD>`. The merge job checks them again
   and starts the factory. Never push to main.
7. Report: her queue depth, the episodes planned, each clip's hook and length, anything skipped.

## Her lane
The hidden and the inner: the Brotherhood and secret societies, ancient rituals and the prayer
formula, manifesting and the missing pieces of it, the subconscious, what the world programs into
you, luck as a science, disclosure. **Not** money mechanics, taxes, credit, business or real estate -
that is the other account.
- Depth over news. A clip should feel like being let in on something.
- Still refuse: medical and diet advice, party politics, attacks on named private people, and any
  pitch for a paid program.

## Her hooks - the INVERSE of his rule
His account opens with a direct promise (Why / How / What). **Hers does not, and this is deliberate**
(8 Sept 2026: 96% of her hooks opened Why/How/What and the lint now enforces the opposite for AR).
- Open with a **stab**: a statement, a fragment, a line that lands before it explains itself.
  `They knew this 2,000 years ago` · `Your words are building a cage` · `Nobody is coming to save you`
- Never open with Why / How / What. Never a question as the first line.
- Six words total, two short lines, and the clip must pay what the line implies.
- **THE HOOK TEST (3 Nov 2026, Kamay: "the hooks should be perfect and so shocking and emotional
  impacting and also truth and call for attention and curiosity").** Write 5 stabs for every clip, keep
  the one that passes all 4: **STOP** (line 1 alone lands - a hidden hand named, an age, a forbidden
  fact), **GAP** (only this clip answers it), **FEEL** (one emotion hard: unease, awe, being lied to,
  longing), **TRUE** (Kevin says it). Weak ones from her own feed: `It's never / an accident.` and `Not
  invented. / Just like your mind.` (no picture, nothing to fear or want); `Mediums talk to / your dead
  ancestors.` (line 1 broken mid-phrase - `check_plan.py` refuses a line 1 ending on TO / THE / YOUR...).
  Strong: `Your religion / is just geography.` - a stab, a picture, a gap.
- **Same for her: the hook must carry the clip's STRONGEST fact, not an incidental one.** 24 Sept 2026: a clip that
  contains "he changed one word", "over a million dollars before he turned 18", "$180 million in 18
  months" and "a $250,000 first royalty cheque" went out hooked `What a stranger told him` - the one
  detail in it with no number, no stakes and no subject. List the concrete facts in the clip, then
  hook the biggest one that the clip actually pays: the mechanism or the number. "Him" is not a
  subject; a stranger is not a promise.

- `check_plan.py` runs her rule automatically - it reads the folder name, so `AR_` gets her lint.

## Her trial hooks: 7 on every clip (3 Nov 2026, Kamay: "go ahead for Yaren and me")
Every clip also gets `"trial_hooks"`: exactly 7 alternatives to its hook, each `["line one", "line two"]`,
six words in all, ALL in her stab rule (no Why / How / What, no question first), each a different lever,
all true to the clip: (1) the number or the age ("2,000 years ago"), (2) the hidden hand named ("the
Brotherhood", "your programming"), (3) a reversal ("Luck is not luck."), (4) what the viewer loses by not
knowing it, (5) a named person or text + what they knew, (6) a command ("Stop praying for it."), (7) the
wildest true line in the clip. The factory renders all 7 (only the hook card changes) and posts them on
HER Instagram as Trial Reels (non-followers only, never on her grid) once the clip has posted; 48 h later
`state/variants.json` names the winning words. Read her last winners there first. Until one experiment
has posted all 7 arms, `check_plan.py` allows trial hooks on ONE clip a plan (the strongest).

## Her captions
- Same craft as his (first line stands alone, one idea per paragraph, one call to action), in her
  voice: quieter, second person, unhurried. She is not selling; she is letting someone in.
- Her call to action is the word **RISE** ("Comment RISE and I'll send you..."). Never his keywords.
- 400-600 characters, 6 hashtags, and do not write "Kevin Trudeau" as a brand name in every caption -
  her account is about the teaching, not the man.

## Her plan format
```json
{"source": "<id>.mp4", "brand": "AR_<ONEWORD>", "test": false,
 "note": "<date> - '<episode title>' (Rumble <id>). Awakened Rise weekly agent.",
 "clips": [{"slug": "UPPER-DASHED-NAME", "in": 211.6, "out": 291.0,
            "start_words": "exact first words", "end_words": "exact last words of the payoff",
            "hook": ["They knew this", "two thousand years ago"],
            "caption": "...\n\n#awakening #..."}]}
```
Every episode gets its own `AR_` folder, not used by any other plan. The scheduler allows two posts
per folder a day, so separate folders keep her slots full.

## Openings
- **Start where the speaker is on camera.** The first second must show the speaker's face (Kamay's first-3-seconds rule, 2 Oct 2026). Episodes often cut to B-roll mid-story. If your opening sentence plays over a cutaway, start on the next sentence where Kevin is on screen. The build checks the first 1.0s with face detection: it moves the start to the nearest sentence on camera, or drops the clip with "opens on B-roll, no face".
