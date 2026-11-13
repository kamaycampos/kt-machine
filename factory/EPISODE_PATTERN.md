# The Episode pattern (measured from kevins_apprentice "Episode 5", 12 Nov 2026)

Kamay, 12 Nov: "PROVE ME you can literally duplicate his last clip ... learn the patterns and
ways, engrave it in your blood, and second make with the same essence our own."
This file is the pattern, measured frame by frame (3 frames a second, all 45 seconds).
Their reel: instagram.com/kevins_apprentice/reel/DfnKhG_N-S1 - 44,700 views and 3,520 likes in
a day; their everyday reels get 150-1,300.

**A study remake is for learning and is never posted.** The Kevin footage is his own show (ours
to clip); their generated scenes and their edit are theirs. What we post is our own story in
this pattern.

## 1. The source (it is in OUR library)
Kevin says this in **v66j311**, 1080p, "Your Wish Is Your Command: How To Manifest Your Desires |
Ep. 80", from **2:59** (179.8 s). Their clip is three pieces of it, jump-cut:

| Keep | Source (about) | Words |
|---|---|---|
| K1 | 181-203 s | "I was in the Brotherhood, as you know, a secret society. I learned how to use your mind to manipulate energy and matter and manifest goals, dreams and desires. That's what I learned. I learned it from people that were worth hundreds of millions of dollars and ... billions of dollars. I learned it by members of royal families." |
| cut | | "These were members of the Brotherhood. Billionaires," |
| K2 | 206-212 s | "the biggest, most powerful movers and shakers in the world." |
| cut | 212-238 s | Skull and Bones, Bohemian Grove, "inducted ... in the late '60s", "lots of things ... a future episode" |
| K3 | 239-266 s | "But I used those techniques to generate companies that generated billions of dollars in sales in Australia, in the U.S., in Canada, South Africa, the U.K., and some parts of Europe. I applied what I learned showing and proving that it works. I manifested my dreams." |
| end | | cut BEFORE "I manifested money" - it ends on "my dreams" |

Find any line again: workflow `transcript-find` (phrases, or `@v66j311@150@760` to print a stretch).

## 2. The file
- 16:9 landscape, 1916x1078, 45.2 s. Instagram shows it as a wide picture in the feed.
  (Their two August hits are the same picture inside a 9:16 file with black above and below.)
- No headline on screen, no logo, no watermark, no progress bar. Hard cuts only.
- Last 1.1 s: the Your Wish Is Your Command book standing on plain white. No words.

## 3. The shots (14 in 45 s; a new picture every 1.5-3.5 s for the first 30 s)
| Time | What | Kind |
|---|---|---|
| 0.0-3.2 | Ballroom: a young man (navy suit, red tie) seated with a huge old book, old men in tuxedos behind, an elder's hand over the book | generated |
| 3.3-6.8 | A brain of orange light forming on black | generated |
| 6.9-8.0 | Kevin, studio (his own wide shot, not cropped) | Kevin |
| 8.1-9.5 | The young man and a bearded elder pointing at the book | generated |
| 9.6-11.3 | Close-up of the old page, a finger on it | generated |
| 11.4-13.1 | Kevin | Kevin |
| 13.2-16.7 | Office in a tower: an old man signing in the foreground, the young man waiting in the background | generated |
| 16.8-20.5 | Palace garden, tall hedges: the young man walking with an older man | generated |
| 20.6-24.2 | Kevin | Kevin |
| 24.3-25.6 | The young man in a tower office, city behind | generated |
| 25.7-27.8 | Kevin | Kevin |
| 27.9-28.6 | Boardroom, older men along a table | generated |
| 28.7-30.2 | A blonde woman in profile in a boardroom | generated |
| 30.3-44.0 | Kevin, 14 seconds straight, for the payoff | Kevin |
| 44.1-45.2 | The book on white | still |

Rules it follows:
- **The first frame is never Kevin.** It is the most cinematic picture of the story.
- **One stand-in plays "young Kevin"** in every scene: same suit, same red tie. That is what makes
  nine separate pictures read as one story.
- Each scene shows exactly what he is saying that second (old book = "I learned", office =
  "hundreds of millions of dollars", palace garden = "royal families").
- Scenes are dense at the start and thin out; the last third is only Kevin.
- 20 of the first 30 seconds are scenes; in all, 46% of the clip.

## 4. The captions (five voices, all white unless said)
Position: the centre of the picture. One to three words at a time, each from its own sound.
| Voice | Looks like | Used for | Size on a 1920-wide frame |
|---|---|---|---|
| Plain | bold geometric sans, as spoken | joining words: "as you know", "I learned", "that were worth" | ~80 px |
| Formal script | copperplate handwriting, soft glow | the mysterious nouns: Brotherhood, secret society, desires, Royal Families | ~95 px |
| Brush script | fast pen script | the verbs of power: manipulate, manifest, people, millions, sales | ~95 px |
| Bold italic | heavy italic sans | the turn of a phrase: Billions, the *biggest*, most *POWERFUL*, *movers* and *shakers*, *in the world* | ~110-150 px |
| BIG | heavy capitals | the payoff, one word at a time: BILLIONS, COMPANIES, APPLIED, WHAT I LEARNED, SHOWING, AND, PROVING, THAT, IT WORKS, I, MANIFESTED, MY, DREAMS | ~150-160 px |

Special marks:
- **Country names are filled with their flag**: Australia, US, CANADA, South Africa, UK; EUROPE solid blue.
- "techniques" in a teal gradient.
- Around the brain the words take places: HOW (left), TO (right), "use your *MIND*" (below),
  then "manipulate" (left, script) and "energy" (right).
- Words can stack: "and" above "matter".
- The last 10 seconds are ONLY BIG capitals, one word per beat: the clip gets louder as it ends.

## 5. The post
- Caption text: "Episode 5 (Manifesting Secrets)" / a 4-sentence story about Kevin in the third
  person / 'Comment "Manifest" to access Success Training that Kevin was taught.'
- No hashtags. Cover = the first frame (the ballroom).
- Series: "Episode N (two-word title)". Episode 2 "Private Jet" has 232K views.

## 6. Where the build stands (12 Nov, 19:20 DC) - BUILT
- **The builder:** `factory/episode_build.py` + workflow `episode-build`. One `spec.json` per
  Episode in `factory/episodes/<slug>/`: the kept pieces, the scenes and the caption voices, all
  by WORD INDEX from a `list` run (never a guessed second). Output: the 16:9 film, the same film
  upright for TikTok and Shorts, the cover (first frame), in the `previews` release.
- **Two finished clips** in `~/Kamay/work/episodes/`:
  1. `1_REMAKE_of_their_Episode_5_study_only.mp4` (47 s) - their Episode 5 from OUR source with
     OUR scenes; `0_PROOF_theirs_vs_remake.jpg` puts 16 moments side by side. STUDY ONLY.
  2. `2_OURS_Episode_1_wide.mp4` (55 s) + upright + cover + post text - "Episode 1 (The Secret
     Behind The Secret)", v6z25lm (the YWIYC interview) 58-215 s in five pieces.
- **Scenes without spending:** five pictures generated in Canva before its credits ran out
  (ballroom, brain, mentor, old page, office - exported at full size through a scratch design)
  and seven stock clips picked BY EYE from Pixabay contact sheets (never the first search hit;
  licences in each folder's `stock_licences.json`). Stills get a slow push or slide; they do
  not have people moving. That is the one place a trained eye can tell ours from theirs.
- **Source hygiene:** the interview has a web address burned along the bottom and a name bar;
  `"kevin_crop": [0.78, 0.78, 0.11, 0.0]` crops Kevin's picture clear of both.
- **The stock site refuses the cloud runner** (429) - stock clips are trimmed here and kept
  beside the spec.
- NOT DONE: moving generated scenes (needs a video generator); a clean official book cover for
  the end card (ours is flattened from Kamay's own photo); the Episode pattern is not in the
  daily posting machine - each Episode is a hand-made spec.

## 6b. Second pass (12 Nov, ~20:00 DC) - Kamay: "not the same ... their captions have even more effects ... more quality moving scenes"
Re-measured their clip at SINGLE-FRAME steps. What the first pass had wrong, now in the builder:
- **Typefaces.** Big words = a Futura-style heavy face (we use Jost 900, italic for APPLIED / IT);
  "Billions" = heavy italic (Jost 800 italic); "of $dollars" = a LIGHT face (Jost 300), with the
  dollar sign; small joining words = round bold sans (Poppins 700 / 800 italic / 900 caps);
  flag words = a chunky display face in their own case - Australia, US, CANADA, South Africa, UK,
  EUROPE (Titan One, flag-filled).
- **Every word is shown**, also "IN" ("I WAS" / "IN" / "the Brotherhood").
- **A new line fades in over 2-3 frames**; a line that stays (HOW while TO arrives) does not blink.
- **Pace.** They cut his pauses: 44 s against our 46. `"tighten": 1.0` cuts only pauses longer than a
  second down to about a third of one (0.5 was tried: 38 s, too choppy).
- **Scenes.** Theirs are generated VIDEO (hands move, people walk). Ours, free: `factory/episodes/_tools/scenes.py`
  (run on the Mac, with `cutout.swift`) cuts the subject out with macOS Vision, fills the
  room behind it, and moves room and subject at different speeds (depth), with breathing light,
  drifting dust, a hand-held sway and a vignette. The brain FORMS out of points of light in the
  first second, then pulses. Rendered here to `m_*.mp4` and kept beside the spec ("raw": true).
- **Export.** x264 slow, CRF 14 (upright copy CRF 15) - master quality, about 3x the first files.
- Still not theirs: people do not walk or gesture inside our scenes; four scenes are stock.

## HOW TO RESUME THIS WORK IN A NEW CHAT
Say: "Read ~/Kamay/MASTER.md (top entries of 12 Nov) and kt-machine/factory/EPISODE_PATTERN.md,
then continue the Episode work." Everything needed is in the repo: the builder
(`factory/episode_build.py`), the workflow (`episode-build`), both edit sheets
(`factory/episodes/ep5_study/spec.json`, `ours_ep1/spec.json`) with every scene file beside them,
and `transcript-find` to locate any line Kevin says. Finished files: `~/Kamay/work/episodes/` and
the Desktop folder "KT Episodes HD".

## 7. Next Episodes
- **The $1,500 Firebird** (v66j311, 351-523 s) - the best story found, but stock has no 1967
  Firebird convertible and the wrong car is worse than none. It waits for generated scenes.
- The pool of five pictures fits any "Brotherhood / taught by the wealthy / the old book" story.
