# Council Roster and Decision Flow

## Executive answer

A full council session uses **11 role instances**:

| Group | Count | Fresh contexts | Purpose |
|---|---:|---:|---|
| Primary advisors (“councilmen”) | 5 | 5 | Independently analyze the question from different thinking lenses. |
| Anonymous peer reviewers | 5 | 5 | Review all five anonymized advisor responses and expose blind spots. |
| Chairman | 1 | 1 | Synthesize the complete record and issue the final gate verdict. |
| **Total** | **11** | **11** | One complete council session. |

The five primary advisors are the councilmen. The five peer reviewers are a second, fresh review panel; they are not allowed to see advisor identities. The chairman is a separate final role and is not counted among the five advisors or five peer reviewers.

## Primary advisor seats

All five seats run in parallel and independently. Every seat receives the same framed question, frozen state manifest, evidence packet, phase-domain overlays, and constraints, but each seat has a different thinking lens.

| Seat | Core responsibility | Main tension it adds |
|---|---|---|
| **The Contrarian** | Search for fatal flaws, unsafe assumptions, false positives, security failures, and failure under pressure. | Downside and risk. |
| **The First Principles Thinker** | Reconstruct the real problem, invariants, success criteria, and simplest valid solution. | Problem framing and conceptual simplicity. |
| **The Expansionist** | Find durable upside, leverage, adjacent value, and opportunities the narrow plan undervalues. | Upside and strategic leverage. |
| **The Outsider** | Detect confusing language, hidden context, accessibility gaps, adoption friction, and curse-of-knowledge assumptions. | Fresh eyes and clarity. |
| **The Executor** | Test whether the proposal can be built, operated, verified, recovered, and advanced through a concrete next action. | Delivery and operational reality. |

Each advisor must return the packet fingerprint, strengths, failure modes, evidence-backed findings with severity and exact evidence, a recommendation, confidence from 1–10, uncertainty/ways it may be wrong, and a pre-exposure stance. Advisors are read-only.

## Phase-specific domain overlays

The five thinking lenses are always present. Named engineering domains are overlays that focus the advisors on the current phase; they do not replace any seat.

| Domain overlay | What it checks |
|---|---|
| Architecture | Boundaries, ownership, API contracts, invariants, maintainability, migrations. |
| Product/operator | User value, workflow clarity, accessibility, adoption, and operational fit. |
| Security/governance | Authentication, authorization, privacy, provenance, secrets, integrity, and auditability. |
| Reliability/testing | Failure modes, retries, concurrency, observability, rollback, recovery, and test evidence. |
| Data/AI contrarian | Data quality, model evidence, false positives, evaluation gaps, provenance, and simpler alternatives. |

The active phase selects its overlays in `references/profiles.yaml`. The packet records the selected overlays and how they were applied to the five seats.

## Anonymous peer-review panel

After all five advisor outputs are recorded, their identities are randomized to `Response A` through `Response E`. Five new peer reviewers run in parallel. They see the framed question and all five anonymized responses, but not advisor seat names, host ids, or reviewer-identifying metadata.

Each peer reviewer answers:

1. Which response is strongest and why?
2. Which response has the biggest blind spot and what is missing?
3. What did all five responses miss that the council must consider?

The host requires exactly five unique peer outputs and complete coverage of Responses A–E before the chairman can synthesize. A duplicate, missing, malformed, or fingerprint-mismatched peer result is a gate failure.

## Chairman

The chairman is **a separate sixth context** from the advisor panel and a separate context from the peer-review panel. The chairman receives only after both prior rounds finish:

- the original framed question and packet;
- all five advisor responses with identities restored;
- all five anonymous peer reviews;
- raw verification commands and results;
- the manifest fingerprint, reviewer counts, dissent, and uncertainty.

The chairman must not invent evidence or silently erase disagreement. The required narrative is:

1. `Where the Council Agrees`
2. `Where the Council Clashes`
3. `Blind Spots the Council Caught`
4. `The Recommendation`
5. `The One Thing to Do First`

For an implementation phase, the chairman additionally issues exactly one engineering gate:

- `GO` — no blocking findings; proceed.
- `GO_WITH_FIXES` — only named non-blocking follow-ups with an owner, due point, acceptance evidence, non-blocking rationale, and re-review trigger.
- `HOLD` — a blocker must be fixed and reviewed again before progression.

## Full sequence

```text
Context enrichment and neutral framing
              |
       5 advisors in parallel
              |
   freeze and validate five outputs
              |
 randomize identities to A/B/C/D/E
              |
    5 peer reviewers in parallel
              |
   validate five peer outputs and coverage
              |
          1 chairman
              |
       narrative + gate verdict
```

## Integrity rules

- Every role echoes the same reviewed-state fingerprint.
- Missing or duplicate role output is not silently substituted.
- Advisor independence is preserved before peer review material is disclosed.
- Peer review is anonymous to reduce deference to named roles.
- Dissent, uncertainty, and the pre-exposure stance are preserved.
- P0/P1 findings, unmet acceptance criteria, failed mandatory verification, auth bypass, cross-tenant access, data loss, incorrect approval state, or unrecoverable migration produce `HOLD`.
- If fresh contexts are unavailable, the result is labeled `non-independent fallback` and confidence is capped at 5/10.
