#!/usr/bin/env bash
# PUSH THE FACTORY'S COMMIT, OR FAIL OUT LOUD (17 Oct 2026).
# WB's "real vitamin E" clip passed every gate and was uploaded, then two overlapping
# factory runs both rewrote factory/reports/latest.md, the rebase stopped on that
# conflict, the old 3-try loop gave up - and the run still showed SUCCESS. The clip
# never reached the queue and Kamay's inbox stayed empty.
# A conflict in a GENERATED file (reports, the board) takes this run's version and the
# save continues. A conflict anywhere else aborts that try. Five tries, then exit 1.
set -u
for i in 1 2 3 4 5; do
  if git pull -q --rebase --autostash; then
    git push -q && { echo "saved to main"; exit 0; }
  else
    bad=$(git diff --name-only --diff-filter=U)
    if [ -n "$bad" ] && ! echo "$bad" | grep -qvE '^(factory/reports/|docs/)'; then
      echo "generated files collided ($bad) - keeping this run's version"
      # in a rebase, --theirs is the commit being replayed: this run's
      git checkout --theirs -- $bad && git add -- $bad \
        && GIT_EDITOR=true git rebase --continue && git push -q && { echo "saved to main"; exit 0; }
    fi
    git rebase --abort 2>/dev/null
  fi
  sleep $((i * 5))
done
echo "SAVE FAILED: this run's commit did not reach main"
exit 1
