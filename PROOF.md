# Proof, 2026-10-18

Same input every time: the made-up resume `examples/sample-resume.docx` (Morgan Ellis) and the real Fin
Customer Success Manager, Scale post saved in `examples/job-post.md`. Three separate Claude Code runs, each
reading only the skill folder and the two inputs. Full files for each run are in `proof/2026-10-18/`.

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Before | 2 of 10 | 2 of 10 | 2 of 10 |
| Checks that passed before | M4, J1 | M4, J1 | M4, J1 |
| After the rewrite, blanks still open | 7 of 10 | 8 of 10 | 8 of 10 |
| After the person answered the blanks | 10 of 10 | not run | not run |
| Anything invented | no | no | no |

- **The before score repeats exactly:** all three runs gave the same result on every one of the ten checks.
- **The after score depends on the rewrite.** Each run writes its own rewrite. Run 1 used four of the post's
  key terms truthfully and failed J6; runs 2 and 3 used five and passed it. Results (M3) and must-haves (J3)
  failed in all three until the person supplied real numbers and work authorization, as designed: a blank
  never earns a check.
- **10 of 10 came from the person's own answers** (`proof/2026-10-18/run1/USER-ANSWERS.md`, fictional,
  labeled as user input). Two of the checks passed with no margin: J6 at exactly five key terms, and J3 with
  AI tools still only partly shown (the rule allows one partial item).
