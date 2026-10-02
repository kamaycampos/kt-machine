# kit/: THE AFFILIATE FACTORY (Project 5)

This turns this live machine into a product: a template that any KT affiliate member can run with Claude Pro.

| Path | What it is |
|---|---|
| `build_kit.py` | Generates the member template from this repo, then re-hashes `shared/MANIFEST.json` so `setup.sh` accepts it. It strips Kamay's state, plans and secrets and Yaren's AR lane, and switches posting to Studio mode by default. Run `python3 kit/build_kit.py OUT --check`, which fails if anything private leaks or a module stops compiling. |
| `member/` | The files laid over the top of the member's copy: `CLAUDE.md` (the member's Claude: `start` / `plan` / `clips` / `post` / `report`), `START_HERE.md` (which becomes their README), `SETUP_POSTING.md`, `playbook/COMPLIANCE.md`, `my_brand/`, and `personalize.py` |
| `dustin/` | The proposal for the affiliate program. Kept out of git on purpose (this repo is public), on disk only. |

## Why it is generated and not copied
Connector law 5 says there is one copy of everything. Every fix made here reaches every member on the next build.

## What is not done yet
| | State |
|---|---|
| Its own public template repo (`affiliate-factory`, marked "Template repository") | Needs creating from a session with that repo in scope, or by Kamay with one click |
| First end-to-end run on a fresh member repo (stock → transcribe → plan → render → board) | Run it on the first pilot repo before members get it |
| Studio mode: how the board shows a due clip that was posted by hand | Verify on the pilot |
| Rights: which footage affiliates may clip | Waiting on the affiliate program (decision 1 in the brief) |
| Style Studio (frame-drawn colour, push-in, sound sting) | See `shared/FIRST_3_SECONDS.md`: the next build, shown to Kamay before it ships |
