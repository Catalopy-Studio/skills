# Council Protocol

## Canonical packet

The packet is fail-closed and must contain every field below. The reviewed root is the scope boundary; the manifest covers all files beneath it except the helper's documented transient directories.

```yaml
review_id: council-<phase-or-topic>-<timestamp>
phase: <named phase or decision topic>
objective: <one sentence>
risk_class: low | normal | high | critical
original_requirement: <source text or reference>
scope_contract: {in_scope: [], out_of_scope: [], reviewed_root: <absolute path>}
repository_root: <absolute path>
state_manifest: {path: <external path>, digest: <sha256>, file_count: <integer>}
changed_files: [{path: <path>, change: added|modified|deleted|unchanged}]
raw_facts: []
implementer_assertions: []
references: []
verification: [{command: <exact command>, exit_code: <integer>, mandatory: true|false, raw_result: <text>}]
constraints: []
unknowns: []
phase_domains: []
phase_overlays_by_seat: {contrarian: [], first-principles: [], expansionist: [], outsider: [], executor: []}
advisor_seats: [contrarian, first-principles, expansionist, outsider, executor]
waiver: none | {owner: <name>, approving_authority: <name>, rationale: <text>, expiry: <ISO-8601>, acceptance_evidence: <artifact>}
```

`scripts/manifest.py fingerprint --root <review-root> --output <external-path>` must be used. It hashes all in-scope files, including untracked files, and emits a deterministic aggregate digest. Every advisor, peer reviewer, and chairman must echo the digest. Use `scripts/manifest.py verify --root <review-root> --manifest <saved-json>` before synthesis and after fixes. The verifier rejects missing schema, root, file list, file count, or digest matches and rejects symlinks. Unavailable values must be written as `none` or `not applicable`, never omitted. Raw facts must be supported by files or command output; interpretations belong in `implementer_assertions`.

For a named implementation phase, the phase must exist in `references/profiles.yaml` and its domain overlays must be mapped to all five seats. An unknown phase or incomplete overlay mapping is `HOLD`; an ad hoc decision must explicitly record `phase: not applicable` and its risk class.

## Context enrichment and framing

Before spawning advisors, scan the workspace for the explicit attachment, project instructions, relevant architecture/schema/API files, recent phase records, and relevant prior council transcripts. Keep this scan bounded and select only material sources. Reframe the raw question into a neutral prompt with context, stakes, constraints, acceptance criteria, and scope. Do not steer the advisors toward an implementer conclusion.

## Advisor prompt — run five in parallel

```text
You are one of five independent advisors on an engineering LLM Council.

Seat:
{seat_name}
Thinking lens:
{seat_description}
Phase domain overlays:
{phase_domains}

Framed question / phase objective:
{framed_question}

Review packet:
{packet}

Inspect the frozen repository state. Do not edit files, stage, commit, spawn reviewers, or rely on another advisor. Lean fully into your assigned lens; do not hedge or try to represent the other seats. Return 150-300 words with exactly: echoed fingerprint, strengths, failure modes, findings with severity and exact evidence, recommendation, confidence 1-10, uncertainty/ways you may be wrong, and pre-exposure stance. Use `none` where a category is not applicable.
```

Persist one write-once Round 1 artifact per unique seat at `<review-artifacts>/<review_id>/round-1/<seat>.json` outside the reviewed root. Create `session.json` only after all artifacts exist and include `schema: council-session/v1`, `barrier: round-1`, the externally verified manifest path/digest, canonical seat lists, fresh-context attestations, per-seat overlays, verification results, waiver, and the computed `artifact_digest` plus `session_digest`. Validate with `scripts/validate_session.py --barrier round-1 --manifest <manifest>` before disclosure; it rejects duplicates, missing roles, malformed fields, fingerprint mismatches, symlinks, invalid waivers, and failed mandatory verification.

## Peer-review prompt — run five new reviewers in parallel

Randomize the mapping of the five advisor seats to `Response A` through `Response E`. Do not expose seat names, host ids, or reviewer-identifying metadata.

```text
You are a fresh peer reviewer for an LLM Council.

Framed question:
{framed_question}

Anonymized advisor responses:

Response A:
{response_a}

Response B:
{response_b}

Response C:
{response_c}

Response D:
{response_d}

Response E:
{response_e}

Answer three questions directly, under 200 words where practical: (1) which response is strongest and why, (2) which response has the biggest blind spot and what it misses, and (3) what all five responses missed that the council must consider. Echo the packet fingerprint and your unique peer seat. Do not edit files.
```

Persist one write-once peer artifact per unique peer seat at `<review-artifacts>/<review_id>/round-2/peer-<seat>.json`. Persist `mapping.json` with the fingerprint and the one-to-one seat-to-A–E mapping, but disclose it to the chairman only after peer review. Update the sealed session to `barrier: round-2` and validate with `scripts/validate_session.py --barrier round-2 --manifest <manifest>`. Validate five unique outputs and complete A–E coverage before chairman synthesis. Preserve the pre-exposure stance from Round 1 beside the revised stance; do not overwrite it.

## Chairman prompt — separate final context

```text
You are the separate Chairman of an LLM Council. You did not write the five advisor responses or peer reviews.

Framed question / phase objective:
{framed_question}

De-anonymized advisor responses:
{deanonymized_responses}

Five peer reviews:
{peer_reviews}

Raw verification evidence and packet:
{packet}

Produce the verdict using exactly these sections:
## Where the Council Agrees
## Where the Council Clashes
## Blind Spots the Council Caught
## The Recommendation
## The One Thing to Do First

Then provide the engineering gate as exactly one of GO, GO_WITH_FIXES, or HOLD. Preserve dissent, cite evidence, distinguish blockers from follow-ups, include reviewer counts and confidence, and never invent test results. GO_WITH_FIXES requires an owner, due point, acceptance evidence, non-blocking rationale, and re-review trigger for every item.
```

## Orchestration and re-review

Prefer `multi_agent_v1__spawn_agent` once for each of five advisor seats, wait for all five, then spawn five new peer reviewers, wait for all five, then spawn one separate chairman. Do not allow communication during the advisor round. Record expected/received counts, unique seat ids, artifact paths, and fingerprints at each barrier. Run `scripts/validate_session.py --barrier round-1 --manifest <manifest>` before peer disclosure, `--barrier round-2` before chairman synthesis, and `--barrier final` after the chairman artifact. A duplicate, timeout, malformed artifact, or mismatch is `HOLD`. If no fresh-context host exists, a fallback is `HOLD` for phase progression or high-risk decisions.

The host adapter contract is: create a write-once external session directory, dispatch exactly five advisors, block until the five unique Round 1 artifacts validate, create and protect the anonymized mapping, dispatch exactly five fresh peer reviewers, block until A–E coverage validates, dispatch one separate chairman, validate exactly one gate, and persist the raw verdict. The adapter must stop on any validation error and include its commands/results in the packet.

After any P0/P1 or acceptance-evidence fix, compute a new external manifest and run a fresh five-advisor, five-peer, chairman council. Do not carry clean credit from a changed state unless the change is demonstrably outside the reviewed boundary and the verdict explicitly records that boundary.
