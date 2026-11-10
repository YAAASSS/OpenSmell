# Autonomous maintenance runbook

This runbook implements the maintainer's standing mandate of 2026-11-04.
It supports bounded development sessions, not continuous background work.
Repository: https://github.com/YAAASSS/OpenSmell.

## Scope and limits

The maintainer authorizes routine implementation, tests, examples, documentation,
RFC changes, CI, firmware source changes, technical issues, branches, commits,
pushes, PRs and merges after verification and repository rules permit them.
Clean reverts of regressions introduced by this work are authorized. Do not
request approval again for covered routine decisions. New user instructions and
applicable platform/repository access controls take precedence.

- One main objective per session; up to 225 minutes of useful active work,
  subject to actual platform limits. Continue useful vertical slices after a small
  merge when budget permits; never manufacture work or wait to fill the budget.
  Reserve the final 20–30 available minutes for CI, publication and handoff.
- One daily task: **OpenSmell — développement autonome quotidien**, at
  **06:00 and 18:00 Europe/Brussels**, including daylight-saving transitions.
  This supersedes the single daily slot under the maintainer’s 2026-11-09 request.
  Start at the next future slot. No catch-up, additional automation or weekly task.
  A separate manual session is allowed only on an explicit maintainer request.
- Single agent by default; delegate only a bounded subtask with a clear total
  usage benefit. Do not repeat full audits or successful tests without cause.
- No force-push, destructive history rewrite, tags, releases, new paid services,
  subscriptions or purchases. Do not bypass approval or branch protections.
- No unattended physical commands, odor diffusion or device flashing. Use
  simulated devices, software tests and compilation. Prepare a manual procedure
  when physical evidence is needed, then continue independent software work.
- Preserve unknown data and the distinctions between representation, provenance,
  mapping, plan, command, acceptance, observed execution and measured olfactory
  outcome. LED activation is not odor reproduction. Acceptance is not completion.
- Keep stale-preview, duplicate-send, capability and duration protections.
  Preserve experimental status, accurate RFC maturity, English UI/docs and the
  existing official logos. Reports to the maintainer are in French.

## Durable sources and access

Read [development-status.md](development-status.md) and the current instructions
on the default branch. Inspect only changes since the last processed main SHA,
relevant open issues/PRs and CI. The README roadmap remains the broad roadmap;
the status page holds the short actionable backlog.

The **`automation/control` branch contains only `state.json`**. It is a separate
operational record, not a code branch. Never merge it into `main`. It carries
the lease, last processed SHA, last completed Brussels date/slot, pending work and a
bounded log (keep the most recent seven sessions). Its commit history preserves
older operational records without daily documentation-only commits on `main`.

Scratch checkouts are disposable. Re-clone the repository when necessary; never
assume a prior local directory, virtual environment or credential still exists.
Use the connected GitHub tools for publishing when shell Git has no credentials.
Do not invent credentials or change authentication controls.

Verify read, local execution and authenticated write capabilities at the start
of a run. A reminder is not a development run. If execution/publishing is missing,
record the exact limitation and avoid claiming unattended development succeeded.
Do not retry an unchanged access failure in a loop or repeat the same alert daily.

## Exclusive lease across isolated environments

All autonomous sessions, including manual continuations of this mandate, follow
this protocol before changing project files. Read-only inspection needs no lease.

1. Read the exact head SHA of `automation/control` and its `state.json`.
   If the branch/state cannot be read, fail closed for mutations; do not recreate
   an existing or uncertain lock. If a previous lease is still unexpired, stop.
   Identify scheduled slots as `YYYY-MM-DDT06:00` or `YYYY-MM-DDT18:00` in
   Europe/Brussels. If `last_completed_slot` or a recent session's `slot` matches,
   skip duplicate work. Keep `session_slot` while running. A legacy completed
   date represents the old 06:00 slot only; it must not block 18:00. Explicitly
   requested manual work uses `manual-<UTC timestamp>` and consumes no future slot.
   Preserve the existing history and `last_completed_brussels_date` for continuity.
2. Generate a unique run owner. Prepare a new state preserving previous fields,
   with that owner and an absolute UTC expiry **at most 240 minutes from acquisition**.
   Create a tree containing only `state.json`, then a commit whose parent is the
   observed control head. Move the branch with an **expected-head-SHA check** and
   `force=false`. The GitHub `update_ref` tool supports `expected_sha`.
3. A rejected lease means another session won: stop, rather than retrying with a
   newer SHA. Re-read state and verify ownership before making project changes.
4. Do not extend the lease. The initial 240-minute maximum supports the increased
   per-session budget authorized on 2026-11-09; there is no renewal. Before every publication,
   merge or final state update, verify the owner and that the lease has not
   expired. Stop writes at expiry or ownership loss. A later run can claim an
   expired lease; an old run must never resume writes on its former lease.
5. Keep pending branch/PR information in state as soon as it exists. Publish
   work on a normal task branch. Re-read the base branch before merging. A CAS
   lease does not replace review of changes by humans or other contributors.
6. On completion, update state with a new child commit and the same conditional
   non-forced ref update. Clear the lease; record outcome, checks, PR/commit,
   next action, last processed main SHA and completed Brussels date/slot. Record `slot` in
   each session (keep at most seven); update `last_completed_slot` only for a
   scheduled slot, and clear `session_slot`. Manual work does not overwrite the
   last scheduled slot. On a crash, the lease expires and pending work is recovered
   at the next authorized slot.

Lease acquisition/release commits are coordination records, not feature progress.
Never count them as a delivered improvement. This protocol coordinates cooperating
autonomous runs; it cannot lock out unrelated human edits, which must be preserved.

## One-session cycle

1. Acquire the lease; restore any pending work before starting a new objective.
2. Check the latest main SHA, applicable instructions, relevant diffs, open PRs
   and actual CI. Preserve any unrelated working-tree changes.
3. Choose the highest-value bounded task with an observable acceptance criterion.
   The 2026-11-10 maintainer direction prioritizes OpenSmell as a whole: installed
   SDK/CLI, data interoperability, reusable device integration, a reproducible
   hardware bench and adoption. Follow the milestone and exit criteria in
   development-status.md; Explorer is a demo client, not the default product.
   Handle demonstrated regressions/data loss/security first. Defer further
   Explorer history/diagnostic/UI refinements unless they unlock the active
   project milestone. Write down important trade-offs; do not substitute audits,
   test counts or roadmap edits for a usable new capability.
4. Implement and run targeted nominal/error/non-regression checks. Broaden checks
   only for a concrete risk or required gate. For visible UI changes, exercise the
   user flow if possible. Distinguish executed checks from inspection/history.
5. Review the diff and update affected docs/examples/RFC evidence. Introduce a
   new Draft RFC only for an architectural or interoperability contract decision.
   For incompatible behavior, state its scope and migration explicitly.
6. Publish a scoped branch/PR and verify the remote SHA and CI for that exact head.
   Merge when the checks and rules allow; otherwise leave a resumable PR. Never
   weaken checks to merge. Avoid polling loops: a pending CI run can be resumed
   in the next scheduled session. Correct or revert introduced regressions first.
7. Update the compact status/backlog only when substance changed, and release
   the lease with a short factual log. Do not manufacture commits for activity.

If blocked, make one reasonable resolution attempt, record the condition for
unblocking and choose an independent task if budget remains. Do not accumulate
half-finished features or ask the maintainer to choose routine reversible options.

## Communication and weekly review

Keep the normal result to a few French lines: delivered change, usefulness,
actual verification, commit/PR and next objective. Alert chiefly on a meaningful
milestone, confirmed critical regression/security issue or essential external
intervention. Respect notification controls; do not claim they suppress delivery
unless confirmed. Supply a downloadable Work handoff when a substantive task is
completed, using the established Markdown format.

On Mondays, include a slightly fuller review once (normally at 06:00) using the
bounded log: progress, current project state, blockers and next priorities.
Never create another schedule. Do not claim credit usage figures when unavailable.
