---
name: prreview
description: >-
  Review this branch with prreview, or finish work prreview is waiting on: a
  pull request review, a draft of a repository's review context, or applying
  fixes the author agreed to. Use when the user invokes /prreview, asks
  for the prreview code review, asks to review their changes before opening a
  pull request, or when prreview has written a handoff bundle.
---

# prreview handoff

prreview cannot drive a Claude Code login programmatically, so for a
contributor with no cloud credentials the model work happens here, in their own
session, at their own instruction. Everything around it is still prreview's
job, and you run those parts for them.

**This is the whole entry point.** A contributor should have to type one thing.
Do not finish by handing them a command you could have run yourself.

## 1. Get a bundle

Look for the most recently modified directory under
`.prreview/cache/handoff/`. Each bundle holds:

- `PROMPT.md` — the complete instructions for this piece of work
- `schema.json` — the shape your answer must take
- `meta.json` — which repository this is for, and a `stage` field

**If there is no bundle, make one.** The contributor asking for a review is
asking for the whole thing, not for a bundle to appear:

```bash
prreview check --no-wait
```

It writes the bundle and returns instead of blocking. If `prreview` is not on
PATH, say so and ask where it is installed rather than guessing — it is often
in a virtualenv belonging to the prreview checkout.

`meta.json` carries a `waiting` field, which decides step 5. Do not infer it
from whether the bundle was already there: `--no-wait` leaves one behind with
nobody waiting on it, and a bundle you find is as likely to be abandoned as
attended.

**Read `meta.json` next.** `stage` says which kind of work this is, and the
kinds are not interchangeable:

| `stage` | What it is | Section |
|---|---|---|
| `review`, `local_find`, `find` | Review a diff | §2 |
| `bootstrap` | Draft a repository's review context | §3 |
| `fix` | Apply fixes the author already agreed to | §4 |

Whichever it is: **read `PROMPT.md` in full and follow it**. It is the
authority, not this file. Do not substitute your own checklist for it.

`review` and `bootstrap` finish the same way: write `result.json` next to
`PROMPT.md`, one JSON object matching `schema.json` exactly, nothing else to
disk, and do not modify the repository. **`fix` is the exception** -- see §4.

**Answer only what `schema.json` asks for.** It is narrower on some runs than
on others on purpose: the pre-PR self review deliberately omits the fields that
classify a finding as systemic impact, because that is the question the
*reviewer* is there to answer and an author who resolves it away first leaves
them nothing. If a field is not in the schema, do not invent it.

Then go to §5.

## 2. Reviewing a diff

1. **Read the actual code.** The diff is not enough to judge whether a change
   breaks a caller. Open files with Read, trace usages with Grep and Glob. A
   claim you did not check is a `minor` at best.

2. **Verify the serious findings before reporting them.** `PROMPT.md` says how
   many verifiers to spawn. Use the Agent tool, one subagent per verifier, and
   give each one only the claim and the location — never your reasoning. A
   subagent shown an argument tends to agree with it, which defeats the point.
   Ask each to *refute* the finding, and tell it to answer "refuted" when
   uncertain. Record every verdict in that finding's `refuter_verdicts`.

3. **Do not modify the repository.** This is a review, not a fix.

### Things that are easy to get wrong

**Do not filter by severity.** It is tempting to report only what seems
important. Report everything you find, with a `confidence` and a `severity`
attached; a later stage does the filtering. Silently dropping a finding you
judged unimportant is the single most damaging thing you can do here, because
it looks identical to not having found it.

**Do not claim a severity you cannot evidence.** `block` and `major` require a
concrete failure scenario in `repro`: a specific input or state, the result
the code should produce, and the result it actually produces. No scenario
means `minor` or `nit`. Do not invent one to justify a severity — prreview
demotes unevidenced findings anyway, and an invented repro wastes a reviewer's
time in a way a demoted finding does not.

**Leave `suggested_patch` empty if you cannot write one that applies.** An
empty patch is a meaningful signal: it marks the finding as a question rather
than a conclusion, and it is presented that way to the human reviewer.

**Stay in scope.** Review the change in front of you. Do not redesign it, do
not propose refactors nobody asked for, and do not comment on pre-existing
code the diff does not touch.

## 3. Drafting review context (`stage: bootstrap`)

This one is not a review and has no diff. prreview is being set up on a
repository and needs the `[context]` block that makes every later review
specific to this codebase. A person will correct your draft, so being specific
and wrong is more useful than being vague and safe: a wrong sentence gets
fixed, a vague one gets kept.

1. **Read before you write.** README, CONTRIBUTING or CLAUDE.md, the top-level
   layout, the CI configuration, the test suite. Skim enough source to know
   what the thing does rather than what its README claims.

2. **Spend your effort on `priorities`.** "Correctness and logic errors"
   applies to every repository ever written and tells a reviewer nothing. Name
   the invariant that breaks and where: which data must not be trusted, which
   boundary must not be crossed, which two things must stay in sync. Dangerous
   areas first.

3. **Leave `conventions` empty rather than inventing plausible ones.** It is
   for rules someone would otherwise learn by being corrected — documentation
   that has to move with the code, changes that need a benchmark or migration,
   generated files that must not be hand-edited.

4. **List the files you actually opened in `evidence`**, and do not modify the
   repository. If you could not learn enough to say something specific, say so
   plainly in `project` instead of padding it.

## 4. Applying fixes (`stage: fix`)

The only stage that edits the repository. It exists because the author has
already marked these findings `Needs change` -- that is a decision they made,
not a question you are being asked to re-open. `PROMPT.md` contains one block
per finding.

1. **Do not re-litigate them.** If a fix looks wrong to you, apply what you can
   and say so plainly afterwards. Silently skipping one leaves the author
   believing it was handled.

2. **Apply `suggested_patch` when it applies cleanly**, and write the change
   yourself when it does not. The patch is a proposal from an earlier stage,
   not a verdict; the finding's `summary` and `reasoning` are what you are
   satisfying.

3. **Change nothing else.** No refactors, no drive-by cleanups, no
   reformatting of untouched lines. The author is about to read `git diff` and
   everything in it should be attributable to a finding.

4. **Do not commit and do not push.** The edits belong in the working tree
   where `git diff` shows them and `git checkout` undoes them.

5. **Report per finding**: what you changed, or why you could not.

6. **Then open the pull request**, unless some fix could not be applied:

   ```bash
   prreview open-pr --yes
   ```

   `--yes` takes the configured reviewers, the branch name as the title, and
   commits the tracked files you changed. It publishes the first round, which
   is where the impact review runs — on the fixed code.

   The consent for this was given when the author submitted the self review:
   that page says the pull request follows. Do not ask again, and do not stop
   at telling them the command. **But if any fix failed, stop and say so** —
   publishing would hand a reviewer a review asserting a finding was addressed
   over code that still contains it, and that is invisible to them.

## 5. Hand the result back

**If `meta.json` says `"waiting": true`**, a prreview command is blocked on
`result.json`. It picks the file up within seconds and carries on by itself.
Say so and stop — starting anything else would review the same diff twice.

**If it says `"waiting": false`**, nothing is blocked and the flow is yours to
finish:

```bash
prreview check
```

It reuses the answer you just wrote — matching on the commit, so it does not
re-ask — applies the evidence rules and the majority rule over your verifiers,
builds the page and opens it. The contributor marks each finding there. That
judgement is theirs; do not pre-empt it by telling them what to pick.

For a `bootstrap` bundle there is no command to run: the setup screen is
watching for the file and fills its fields in the moment it appears.

## After you finish

One caveat worth mentioning to them if it comes up: work produced this way runs
on whatever model their Claude Code session is set to, so it does not honour
the model and effort pinned in `.prreview/config.toml`. prreview stamps these
findings with `backend: claude_code` so the calibration data stays segmentable.
