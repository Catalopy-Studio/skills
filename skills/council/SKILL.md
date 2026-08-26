---
name: council
description: Run a five-advisor, anonymous-peer-review council with a separate chairman for architecture, implementation phases, code changes, debugging hypotheses, release decisions, and risk reviews. Return evidence-backed GO, GO_WITH_FIXES, or HOLD verdicts with preserved dissent.
---

# Council

Use this skill as a decision-quality gate, not as theatrical debate. A full council has five independent advisor seats, five fresh anonymous peer reviewers, and one separate chairman. The five lenses intentionally create tension: Contrarian, First Principles, Expansionist, Outsider, and Executor. Phase-specific engineering profiles are overlays, not substitutes for the five seats.

## When to Run

Run after every implementation phase, before high-impact architecture, data, security, integration, or release decisions, and after every P0/P1 or acceptance-evidence fix. Also run when explicitly triggered by `council this`, `run the council`, `war room this`, `pressure-test this`, `stress-test this`, or `debate this`, and for a genuine high-stakes decision with competing options such as “which option,” “what would you do,” “is this the right move,” “validate this,” or “I can't decide.” Do not run for trivial formatting, factual lookups, or routine edits outside the reviewed boundary.

Read only the references needed for the current review:

- `references/profiles.yaml` for the five advisor seats, domain overlays, and phase selection.
- `references/council-roles.md` for the complete roster and chairman responsibilities.
- `references/protocol.md` for packet schema, prompts, orchestration, and artifact requirements.
- `references/verdict-template.md` for the final record.
- `scripts/manifest.py` for the deterministic reviewed-state manifest.
- `scripts/validate_session.py` for reject-by-default 5/5/1 artifact and gate validation.

## Step 1 — Enrich and frame the question

Scan the workspace for the explicit attachment, project instructions, relevant architecture/schema/API files, recent phase records, and relevant prior council transcripts. Spend only enough time to find the two or three sources that materially ground the question. Distinguish source-backed facts from implementer assertions. Frame a neutral prompt containing the decision or phase objective, context, constraints, stakes, acceptance criteria, and explicit in/out-of-scope boundaries. If the question is genuinely too vague, ask one clarifying question before convening.

## Required Review Packet

Every packet must use the canonical fields in `references/protocol.md`: review id, phase name or decision topic, objective, risk class, original requirement, scope contract, repository root, reviewed-state manifest path and digest, changed-file manifest, raw source-backed facts, architecture/API/schema references, verification commands with exact exit codes and raw results, environment constraints, explicit unknowns, advisor-to-overlay mapping, waiver object or `none`, and implementer assertions separated from facts. Use `none` or `not applicable` only when the field truly does not apply; an omitted mandatory field is a packet failure and produces `HOLD`.

Compute the state with `scripts/manifest.py fingerprint --root <review-root>`. The manifest recursively covers every in-scope file, including untracked files, while excluding only its documented transient directories. The sorted per-file SHA-256 manifest and aggregate digest are the reviewed-state fingerprint. Save a manifest outside the reviewed root; the helper rejects an output path inside the root and rejects symlinked files. Freeze the reviewed state until all advisors in a round finish. Every result must echo the digest, seat id, and round; a mismatch, duplicate seat, missing seat, or malformed result invalidates the round and produces `HOLD`.

## The five advisor seats

Always convene all five seats in parallel for a full council. Apply the named phase domain profiles as additional questions to every advisor, and record the mapping in the packet.

1. **The Contrarian** — actively search for fatal flaws, unsafe assumptions, false positives, security failures, and what will fail under pressure.
2. **The First Principles Thinker** — reconstruct the actual problem, invariants, success criteria, and simplest solution; challenge whether the question is framed correctly.
3. **The Expansionist** — identify durable upside, leverage, adjacent value, and opportunities the narrow proposal undervalues; label speculation as such.
4. **The Outsider** — use only observable context to expose confusing language, hidden assumptions, accessibility gaps, and curse-of-knowledge friction.
5. **The Executor** — focus on whether the proposal can be built, operated, verified, recovered, and advanced through a concrete next action.

Each advisor responds independently in a bounded 150–300 words, returns the exact fingerprint, strengths, failure modes, evidence-backed findings with severity and exact evidence, recommendation, confidence from 1–10, uncertainty/ways it may be wrong, and a pre-exposure stance. No advisor may edit files, stage, commit, spawn recursive reviewers, or see another advisor's result.

## Step 3 — Five anonymous peer reviewers

After all five advisor artifacts are durably recorded, randomize the seat-to-letter mapping and expose only `Response A` through `Response E` to five new fresh peer-review agents in parallel. Each peer reviewer sees the framed question and all five anonymized responses and answers:

1. Which response is strongest and why?
2. Which response has the biggest blind spot and what is missing?
3. What did all five responses miss that the council must consider?

Each peer result must identify its unique peer seat, echo the packet fingerprint, remain under 200 words where practical, and preserve dissent. Missing or duplicate peer outputs, incomplete response coverage, or a fingerprint mismatch is `HOLD`.

## Step 4 — Separate chairman synthesis

The chairman is not one of the five advisors or peer reviewers. Give the chairman the framed question, de-anonymized advisor responses, all five peer reviews, raw verification evidence, and the verdict template only after both prior rounds are complete. The chairman must produce:

- `## Where the Council Agrees`
- `## Where the Council Clashes`
- `## Blind Spots the Council Caught`
- `## The Recommendation`
- `## The One Thing to Do First`
- the engineering gate: `GO`, `GO_WITH_FIXES`, or `HOLD`

The chairman must preserve minority views, cite evidence, distinguish blockers from follow-ups, and never invent test results. For a phase gate, save the verdict record. For an ad hoc decision, present the verdict in the response unless the user asks for a transcript. A missing separate chairman context is a non-independent fallback and caps confidence at 5/10.

## Gate outcomes

- `GO`: no blocking findings; proceed.
- `GO_WITH_FIXES`: proceed only with named, non-blocking follow-ups, each with owner, due point, acceptance evidence, non-blocking rationale, and re-review trigger.
- `HOLD`: a blocker must be fixed and re-reviewed before progression.

Any data loss, auth bypass, cross-tenant access, incorrect approval state, unrecoverable migration, unmet acceptance criterion, failed/missing mandatory verification, duplicate/missing council seat, or incomplete peer-review set is a blocker. A waiver can avoid a verification blocker only if it is explicit, time-bounded, names an owner and approving authority, gives a rationale, expiry, and acceptance evidence. `scripts/validate_session.py` is the required machine check for the waiver and artifact contract.

## Fallback

Detect host capability before orchestration. Prefer `multi_agent_v1__spawn_agent` (or the host equivalent) with fresh contexts: five advisors, then five peer reviewers, then one chairman. If fresh contexts are unavailable, execute the same prompts as separate saved reviewer artifacts in the current context, label the result `non-independent fallback`, cap confidence at 5/10, and do not claim independent confidence. A non-independent fallback cannot advance an implementation phase or high-risk decision; it is `HOLD` until a fresh-context council runs. Missing fallback artifacts are also `HOLD`.

## Phase-Gate Discipline

1. Run phase tests and collect raw evidence.
2. Enrich and frame the packet; compute the repository manifest.
3. Freeze the state and convene five independent advisors.
4. Anonymize and peer-review with five fresh reviewers.
5. Synthesize with a separate chairman.
6. Run `scripts/validate_session.py --session <sealed-session-directory> --manifest <external-manifest> --barrier final` and record its raw result; run the same validator at the Round 1 and Round 2 barriers before disclosure.
7. Write the verdict using `references/verdict-template.md`.
8. Fix blockers without unrelated scope changes, compute a new manifest, and run a fresh full council after every P0/P1 or acceptance-evidence fix. A re-review is not required only when a change is demonstrably outside the reviewed boundary and the verdict records that boundary.
9. Update the implementation roadmap only after `GO` or an explicitly tracked `GO_WITH_FIXES`.

The implementer owns fixes and final verification. Reviewers are read-only and must not edit, stage, commit, spawn recursive reviewers, or run broad suites merely to repeat existing evidence.
