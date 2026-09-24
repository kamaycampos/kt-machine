# Weekly clip planning for AWAKENED RISE (Yaren's account)

This is a different person's account from the one `PLANNING.md` serves. Yaren's brand is
**Awakened Rise** (@theawakenedrise). Her lane, her voice, her hooks, her episodes. Nothing here is
shared with Kamay's account except the machinery.

**The fence, first.** A source episode is cut for ONE account, ever. Her list is
`factory/ar_source_plan.json`; his is `factory/source_plan.json`. Never plan an episode from his
list, never touch a file named `ep_*.json`, never write a `KT_` folder. `kt_fence.py` refuses a
source that serves both, and the checker refuses the wrong folder family. If you ever have to choose
between filling her queue and crossing that line, leave the queue empty and say so.

## Procedure
1. `pip install -q opencv-python-headless pillow numpy 2>/dev/null`
2. `python factory/routine_prep.py --brand ar --max 4` - prints HER queue, downloads and decrypts the
   next unplanned episodes from her list, and writes 30-second reading blocks.
   - Queue over 50 clips: plan nothing, report, stop. 30-50: plan 2. Under 30: plan 4.
2b. If the prep printed **TAKEN DOWN BY TIKTOK**, plan a replacement for each from the same episode - same lesson, different moment, different hook - and say so in your report.
3. Read `factory/HOOK_PATTERNS.md` for the story and caption craft - then **invert the hook rule**
   (see below). Read each episode's `work/<id>_blocks.txt` in full. Choose 6-9 clips.
4. Write `factory/plans/ar_<id>.json` (same shape as his, brand `AR_<ONEWORD>`).
5. `python factory/check_plan.py factory/plans/ar_<id>.json` and fix everything it reports.
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
