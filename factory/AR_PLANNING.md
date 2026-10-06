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
2c. If the prep printed **SECOND CHANCES**, re-cut those clips FIRST - before any new episode. The teaching was already judged worth posting and the episode is transcribed; only a gate stopped it. For each episode listed:
   - Write `factory/plans/ar_<id>_r2.json` (`_r3` if `_r2` exists) with the same `source`, brand = the old brand + `R2` (e.g. `AR_CANVAS` -> `AR_CANVASR2`), and every clip carrying `"retry_of": "<the key printed, e.g. ar_v6v9urd/WALL-STREET-500-RIVALS>"`.
   - Fix what the **WHY** line says, in `work/<id>.srt`:
     - hook lint ("not a direct promise", "opens on a riddle", "no stakes") -> rewrite the hook; keep the cut.
     - "opens mid-sentence", "ends mid-thought", "ends off the planned words" -> re-find the edges: open on the first words of a complete sentence after a pause, close on the sentence end where the teaching lands; copy `start_words` / `end_words` exactly from the cues.
     - "word repeated", "phrase scrambled", "(laughing)", "[BLANK_AUDIO]" -> move an edge so the damaged words fall outside the clip; if they sit in the middle of the teaching, skip the clip.
     - "captions vs the sound", "UNCAPTIONED SPEECH", "too few to judge" -> move both edges to different sentence boundaries (a few seconds re-times every caption). If the gap named is someone else talking, cut so it falls outside.
   - `tries 2` means this is its last chance: skip it unless you can see the cause and fix it.
   - Second chances count toward this run's clips. Report how many you re-cut and how many you skipped, and why.
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
- **Same for her: the hook must carry the clip's STRONGEST fact, not an incidental one.** 24 Sept 2026: a clip that
  contains "he changed one word", "over a million dollars before he turned 18", "$180 million in 18
  months" and "a $250,000 first royalty cheque" went out hooked `What a stranger told him` - the one
  detail in it with no number, no stakes and no subject. List the concrete facts in the clip, then
  hook the biggest one that the clip actually pays: the mechanism or the number. "Him" is not a
  subject; a stranger is not a promise.

- `check_plan.py` runs her rule automatically - it reads the folder name, so `AR_` gets her lint.

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
