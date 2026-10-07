# Gate ledger — shadow-mode streak

_Rebuilt 2026-10-07T13:22:22Z by .github/scripts/gate_ledger.py from `ledger/gate-ledger.jsonl` (1 live decisions, 17 backfilled)._

**Switch-off bar** (Agency Hub — Full Automation Plan, 2 Oct 2026): the gates must match a person's call on **15 posts in a row, with zero "too loose"** (a post the gates passed that a person then stopped or changed). Only then does `HOLD_NEW_POSTS` turn off for that folder — vendors/ first, then parents/, then edits. A miss resets the count; the fix is a new gate.

| Folder | Current streak | Bar | Too loose in the streak | Too loose ever | Too strict ever | Person decisions counted | Status |
|---|---|---|---|---|---|---|---|
| vendors/ — new posts | 0 | 0/15 | 0 | 0 | 0 | 0 | not yet |
| parents/ — new posts | 1 | 1/15 | 0 | 0 | 0 | 1 | not yet |
| edits to live posts (text or images) | 0 | 0/15 | 0 | 0 | 0 | 0 | not yet |

## Last live decisions

| PR | Folder | Gates | Person | Edited first | Result |
|---|---|---|---|---|---|
| #32 | parents | fail | merged by oryn-quest | yes | agree |

## Backfill (pull requests before shadow mode — NOT counted)

Verdicts recomputed with the rules on main on the day of the backfill (`.github/scripts/check-post.sh` + the contract), run on the Hub's own last version of each pull request. They show how today's gates would have judged the past; they never count toward the bar.

Of 9 person decisions: 9 agree, 0 too loose, 0 too strict.

| PR | Folder | Gates (today's rules) | Person | Edited first | Result |
|---|---|---|---|---|---|
| #2 | parents | fail | merged by github-actions[bot] | no | not counted: decided by github-actions[bot] |
| #1 | parents | fail | merged by github-actions[bot] | no | not counted: decided by github-actions[bot] |
| #3 | edits | fail | merged by github-actions[bot] | no | not counted: decided by github-actions[bot] |
| #4 | edits | fail | merged by github-actions[bot] | no | not counted: decided by github-actions[bot] |
| #6 | edits | fail | closed by oryn-quest | no | agree |
| #7 | edits | fail | closed by oryn-quest | no | agree |
| #8 | parents | fail | merged by github-actions[bot] | yes | not counted: decided by github-actions[bot] |
| #9 | edits | pass | merged by github-actions[bot] | no | not counted: decided by github-actions[bot] |
| #11 | parents | fail | closed by oryn-quest | no | agree |
| #13 | parents | fail | closed by oryn-quest | no | agree |
| #14 | parents | fail | closed by oryn-quest | no | agree |
| #10 | parents | fail | closed by AceWattGit | no | not counted: decided by AceWattGit |
| #12 | vendors | fail | closed by AceWattGit | no | not counted: decided by AceWattGit |
| #15 | parents | fail | merged by oryn-quest | yes | agree |
| #16 | parents | fail | merged by oryn-quest | yes | agree |
| #29 | vendors | fail | merged by oryn-quest | yes | agree |
| #30 | parents | fail | merged by oryn-quest | yes | agree |
