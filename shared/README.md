# shared - the engine every project runs

One canonical copy of the parts that are not about any one brand: word timings,
caption breaks, caption timing anchored to the sound, face framing, silence
detection, and the check that reads a finished clip back. A fix here reaches KT,
Yaren and VSC without anyone copying a file.

**Every factory pulls this folder at setup.** kt-machine copies it in directly;
vsc-factory (public) fetches it over https from this repo. So an improvement
lands once and is live everywhere on the next run - no Mac, no human step.

## What does NOT belong here
Anything a brand owns: hooks and their lint (Kamay states the benefit, Yaren's rule
is the inverse), styles and fonts, clip plans, captions, posting, fences. Those stay
in each project. The test is simple - if changing it for one project would be wrong
for another, it is not shared.

## The rule Kamay set, 27 Sept 2026
"EVERY SINGLE DETAIL IMPROVEMENT gets automatically shared between all projects,
without the individual details that are irrelevant to one another... make it
automatic, at all times, and vice versa."
