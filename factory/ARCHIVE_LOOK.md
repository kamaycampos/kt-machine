# The archive look (KT_LOOK=archive) - picked 11 Nov, built into kt_render 11 Nov

11 Nov 2026. Kamay showed instagram.com/trudeau_files ("the way his clips are placed in the space
of the phone... comfortable to watch and very calling") and three creative briefs (clips,
thumbnails, hooks) under the brand name THE HIDDEN KNOWLEDGE ARCHIVE. This is the spec the
prototypes were built from. **Kamay picked the Archive look with the captions on the tie (F3) on 11 Nov.** It still does not
post: it has to be built into kt_render first (gaps below).

Board (private): https://claude.ai/artifact/JsLMDGrstrc3UDxRsuz8Jd
Prototype tool: `factory/frame_preview.py` + workflow `frame-preview` (files land in the
`previews` release; copies in `~/Kamay/work/frame_look/`).

## What was measured on trudeau_files (5 reels, 1080x1920)
- Picture = a 1080x960 window in the middle (y 480-1440). From 16:9 that is 63% of the width,
  scaled x0.89. Ours fills 9:16: 32% of the width, scaled x1.78 on 1080p.
- Headline in the black band right above the picture, on screen the whole clip.
- Bottom ~25% plain black, so the platform's own name/caption/buttons cover nothing.
- Captions 1-2 words, small, dead centre of the picture (lands on his nose in close-ups).
- Instagram caption = the headline only. No hashtags, no link lines.
- Their numbers (32 reels, 11 Nov): usual reel 200-300 views, breakouts 14,000 / 1,991 / 1,537 /
  1,451; 1,966 followers. NOT evidence that the layout wins - our late-October median was
  207-979 with a full-bleed crop. The layout is a taste + sharpness choice until we test it.

## In the machine (kt_render, 11 Nov, kt `0e817473`)
`KT_LOOK=archive`, or a share of the plans through `LOOK_TEST=classic,cinema,archive`.
Kamay's second round, on seeing F3: "delete the hidden knowledge archive line, it's too much",
keep the small line under the picture ("I like the size, it's discreet") and use it for the book
("to program people ... through spaced repetition") or link lines.

- **No slug.** The brand name is not on the clips.
- **The line under the picture** = `ARCH_LINE`, default `KEVIN TRUDEAU  ·  YOUR WISH IS YOUR COMMAND`
  (Montserrat 600 19 px, ivory 51%, 58 px under the picture). Change it with repo variable
  `KT_ARCHIVE_LINE` or `"archive_line"` in a member's style.json.
  **RULE: the line is burned into ONE file that goes to every platform, so it may only say what
  is true on all of them.** "Link below" is not: TikTok gives no bio link under 1,000 followers
  and links in Instagram/Shorts captions do not click. Link lines stay in the caption text,
  per platform (`state/extra_links.json`). The book title is true everywhere.
- Window: one SIZE per clip (ffmpeg cannot resize a crop mid-stream) from the clip's usual face
  size; its x AND y follow every camera shot (`archive_plan`).
- Kevin's own on-screen words: `kt_textsafe` still finds the seconds the window would slice
  them; for those seconds the whole wide picture sits in the window (`archive_fit`).
- Headline: the plan's hook as written (sentence case), max 850 px wide (a tall phone crops ~10%
  off each side), last line italic gold. On screen the whole clip, so it is on any cover frame.
- Captions: `CAP_MAX` 26 in this look; y from the clip's usual shot, never nearer than 70 px to
  the chin of any shot of 2 s or more.
- YouTube cut (>59 s): same look, shots re-timed to the window's own clock. Story: cut from the
  finished clip, its tail card moved under the picture.
- Cover: frame scored on the window, no card pasted (the headline is already in the frame).
- NOT in this look yet: the stock opener (skipped, logged), the label card (WB), a hand-made
  `geo` layout is shown whole and upright inside the window.
- Test plans: `ep_v6z25lm_archivetest`, `ep_v4tz80x_archivetest` (test: true, never queued).

## Kamay's first pick: F3 = Archive, captions on the tie
11 Nov, on seeing F2: "Archive look but I do not want the CC under, I want them where the tie was."
- Everything from F2 (canvas, grade, headline, slug, hairlines), picture back in the middle (y 480-1440).
- Captions INSIDE the picture at tie height: y = chin + 0.45 x face height, never nearer than 70 px
  to his chin, never in the bottom 120 px of the picture. REGROUP y=1059, $87,500 y=989.
- Montserrat 600 50px, ivory, 3 px soft border + shadow, sentence pieces <= 26 letters.
- A soft shade behind the caption line (strongest 46%, fades over 130 px each way) so ivory reads
  on a white shirt. It shows as a faint band on a light wall: tune or drop it in kt_render.
- Credit line 58 px under the picture.
- Clips: `~/Kamay/work/frame_look/5_REGROUP_archive_tie.mp4`, `6_87500_archive_tie.mp4`.
- The caption height comes from the MEDIAN face of the clip. kt_render must do it per shot.

## The two earlier looks
| | F1 plain | F2 Archive |
|---|---|---|
| Canvas | #000000 | #0D0D0F + fine grain |
| Picture | y 480-1440 | y 440-1400, light film grade, gold hairlines |
| Headline | Josefin Sans SemiBold 62, white | Cormorant Garamond SemiBold 84, ivory #F3ECDD; last line italic, gold #B9975B |
| Slug | none | "THE HIDDEN KNOWLEDGE ARCHIVE", Montserrat 600 23px, tracked 7, gold, y~160 |
| Captions | 1-2 words, Josefin 46, in the picture under his chin | sentence pieces <=26 letters, Montserrat 600 48, ivory, own line at y 1454 |
| Credit | none | "KEVIN TRUDEAU - <real show/book>", Montserrat 19, ivory 40%, y 1512 |

Palette: charcoal #0D0D0F, aged gold #B9975B, ivory #F3ECDD, burgundy #7A1622 (thumbnails, one
mark), intelligence blue #3C5A73 (reserve). Fonts are open licence (fontsource static files).

Crop rule: the window is 9:8, centred on his face, his face about a third of the picture's
height, never scaled up more than x1.35 (a 1080p medium shot is scaled DOWN).

## Before it can go into kt_render (known gaps in the prototype)
1. Kevin's own on-screen name bar is sliced at the window's left edge (kt_textsafe is not wired).
2. Two-person shots / podcast side panels (speaker turns, `geo`) are not handled.
3. No opener, no sound design, no YouTube cut, no Story, no label card, no trial variants.
4. kt_qc, kt_verify_render and the cover picker all assume a full-bleed picture.
5. FIXED 11 Nov: the aligner never loaded in the preview job because `factory/queue.py` shadowed
   the standard library's `queue` and torch could not import. The script's folder now goes last
   on the path; F3 clips are force-aligned (123 and 175 words, onsets within 0.03 s).

## Headline rules for this look (on top of HOOK_PATTERNS.md, which still decides the TOPIC)
- Only what Kevin says in the clip. Two lines, up to ~26 letters each; the last line is the turn.
- The headline is also the cover: it must read at grid size.

## Decided / open
- DECIDED (Kamay, 11 Nov): Archive look, captions on the tie (F3). Thumbnails: the RED ACCENT
  style (B) if one must be chosen.
- DECIDED (Kamay, 11 Nov): no brand name on clips; the line under the picture carries the book.
- His face: `~/Kamay/FACE_PLAN.md` (he confirmed the affiliate program allows it beside Kevin's).
- Third LOOK_TEST arm (classic,cinema,archive): measured against both, not switched on blind.
- Thumbnails with Kamay (`~/Kamay/work/frame_look/thumbnails/`): K1 him + the book, K2 Kevin + him
  (two separate pictures, a red line between), K3 pinned 9:16 cover. Built from his event photo
  holding YWIYC (the sharpest of his six; cut out on the Mac, nothing uploaded). Advice given:
  his face on the pinned post, the links page and Stories; NOT on every clip cover (a KT clip is
  Kevin; an unknown face on the cover costs the click). 16:9 thumbnails only matter on long
  YouTube videos - Reels, Shorts and TikTok show the clip's own frame.
- Clips of other people ("The Masters"): see MASTER.md IDEA INBOX, 11 Nov.
