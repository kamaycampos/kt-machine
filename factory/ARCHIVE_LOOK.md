# The frame look ("The Hidden Knowledge Archive") - LOOK PICKED 11 Nov (F3), not in the machine yet

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

## Kamay's pick: F3 = Archive, captions on the tie
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
- Open (Kamay): whether the brand name appears on clips; where his own face goes.
- Next build: F3 into kt_render as a third LOOK_TEST arm (classic,cinema,archive) - the running
  test has no verdict yet, so the new look is measured against both, not switched on blind.
- Thumbnails with Kamay (`~/Kamay/work/frame_look/thumbnails/`): K1 him + the book, K2 Kevin + him
  (two separate pictures, a red line between), K3 pinned 9:16 cover. Built from his event photo
  holding YWIYC (the sharpest of his six; cut out on the Mac, nothing uploaded). Advice given:
  his face on the pinned post, the links page and Stories; NOT on every clip cover (a KT clip is
  Kevin; an unknown face on the cover costs the click). 16:9 thumbnails only matter on long
  YouTube videos - Reels, Shorts and TikTok show the clip's own frame.
- Clips of other people ("The Masters"): see MASTER.md IDEA INBOX, 11 Nov.
