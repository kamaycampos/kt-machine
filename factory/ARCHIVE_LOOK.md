# The frame look ("The Hidden Knowledge Archive") - DRAFT, not approved, not in the machine

11 Nov 2026. Kamay showed instagram.com/trudeau_files ("the way his clips are placed in the space
of the phone... comfortable to watch and very calling") and three creative briefs (clips,
thumbnails, hooks) under the brand name THE HIDDEN KNOWLEDGE ARCHIVE. This is the spec the
prototypes were built from. **Nothing posts in this look until Kamay picks one** (RULES #17).

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

## The two looks
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
5. The forced aligner did not load in the preview job ("aligner not installed"): captions are on
   anchored times only.

## Headline rules for this look (on top of HOOK_PATTERNS.md, which still decides the TOPIC)
- Only what Kevin says in the clip. Two lines, up to ~26 letters each; the last line is the turn.
- The headline is also the cover: it must read at grid size.

## Decided / open
- Open (Kamay): F1 or F2; whether the brand name appears on clips; whether it joins LOOK_TEST as
  a third arm (classic,cinema,frame) - the running test has no verdict yet.
- Thumbnails: three 16:9 mockups on the board (A dark luxury portrait = proposed standard, B red
  accent, C the number). The Kamay + Kevin version waits for Kamay's photos.
- Clips of other people ("The Masters"): see MASTER.md IDEA INBOX, 11 Nov.
