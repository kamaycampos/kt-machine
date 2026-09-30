# SYNC LOG

Every propagation between projects. Newest first. Format:
date · from → to · what · verified how.

## 30 Sept 2026

**VSC → shared → KT + Awakened Rise · quality gate false positives**
`vsc-factory/pipeline/kt_qc.py` had a fix `kt-machine/shared/kt_qc.py` did not: two
clips that were RIGHT were failing ("that firing that he started NeXT", "They attack.
They get pissed off"). Function words recurring and a full stop between repeats are
now correctly passed. The fix lived only in VSC, because VSC copies its own
`pipeline/*.py` over the shared engine at setup — so the shared copy had silently
forked.
- Ported to `shared/kt_qc.py`, `MANIFEST.json` hash updated, zero drift after.
- Verified: both false positives now pass; real damage ("Without Without",
  "said He it said", "It's not It's not") still fails.
- Still to do: delete `vsc-factory/pipeline/kt_qc.py` so VSC uses the shared copy
  (needs push access to vsc-factory — the VSC chat or Kamay).

**Docs · shared/README named the wrong VSC repo**
It said vsc-machine (private) pulls the engine; the active one is vsc-factory (public).
Corrected.
