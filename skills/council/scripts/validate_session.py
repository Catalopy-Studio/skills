#!/usr/bin/env python3
"""Validate a sealed five-advisor/five-peer/chairman council session."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from manifest import build_manifest


ADVISORS = ["contrarian", "first-principles", "expansionist", "outsider", "executor"]
PEERS = ["peer-1", "peer-2", "peer-3", "peer-4", "peer-5"]
LABELS = ["A", "B", "C", "D", "E"]
GATE_VALUES = {"GO", "GO_WITH_FIXES", "HOLD"}
SECTIONS = {
    "Where the Council Agrees",
    "Where the Council Clashes",
    "Blind Spots the Council Caught",
    "The Recommendation",
    "The One Thing to Do First",
}
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def read_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read JSON {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"JSON object required: {path}")
        return {}
    return value


def nonempty(value: object, label: str, errors: list[str]) -> None:
    if isinstance(value, str) and value.strip():
        return
    if isinstance(value, list) and value:
        return
    if isinstance(value, dict) and value:
        return
    errors.append(f"{label} must be non-empty")


def valid_confidence(value: object, label: str, errors: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10:
        errors.append(f"{label} must be an integer from 1 to 10")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def artifact_digest(root: Path) -> str:
    paths = []
    for directory in (root / "round-1", root / "round-2"):
        if directory.is_dir():
            paths.extend(path for path in directory.glob("*.json") if path.is_file())
    paths.extend(path for path in (root / "mapping.json", root / "chairman.json") if path.is_file())
    lines = []
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        lines.append(f"{relative}\0{path.stat().st_size}\0{hash_file(path)}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def supported_phase_domains(profiles_path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    text = profiles_path.read_text(encoding="utf-8")
    in_phase_profiles = False
    for line in text.splitlines():
        if line.strip() == "phase_profiles:":
            in_phase_profiles = True
            continue
        if in_phase_profiles and line and not line.startswith("  "):
            break
        if in_phase_profiles:
            match = re.match(r"^  ([A-Za-z0-9_-]+):\s*\[([^]]*)\]", line)
            if match:
                result[match.group(1)] = [item.strip() for item in match.group(2).split(",") if item.strip()]
    return result


def validate_manifest_binding(session: dict, manifest_path: Path, errors: list[str]) -> None:
    manifest = read_json(manifest_path, errors)
    if manifest.get("schema") != "council-manifest/v1":
        errors.append("external manifest has an invalid schema")
        return
    try:
        root = Path(manifest["root"]).resolve()
        actual = build_manifest(root)
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        errors.append(f"cannot recompute external manifest: {exc}")
        return
    if manifest.get("digest") != actual.get("digest") or manifest.get("files") != actual.get("files"):
        errors.append("external manifest is stale or tampered")
    digest = manifest.get("digest")
    if not isinstance(digest, str) or not HEX_DIGEST.fullmatch(digest):
        errors.append("external manifest digest is not a SHA-256 hex digest")
    if session.get("fingerprint") != digest:
        errors.append("session fingerprint does not match the verified external manifest")
    if session.get("manifest_digest") != digest:
        errors.append("session manifest_digest does not match the verified external manifest")
    try:
        if Path(session.get("manifest_path", "")).resolve() != manifest_path.resolve():
            errors.append("session manifest_path does not match the supplied manifest")
    except (OSError, TypeError):
        errors.append("session manifest_path is invalid")


def validate_waiver(session: dict, errors: list[str]) -> None:
    waiver = session.get("waiver")
    if waiver in (None, "none", "not applicable"):
        return
    if not isinstance(waiver, dict):
        errors.append("waiver must be none or an object")
        return
    required = {"owner", "approving_authority", "rationale", "expiry", "acceptance_evidence"}
    missing = sorted(required - set(waiver))
    if missing:
        errors.append(f"waiver missing fields: {', '.join(missing)}")
    for key in required - {"expiry"}:
        nonempty(waiver.get(key), f"waiver.{key}", errors)
    try:
        expiry = datetime.fromisoformat(str(waiver.get("expiry")).replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            errors.append("waiver.expiry must include a timezone")
        elif expiry <= datetime.now(timezone.utc):
            errors.append("waiver expiry must be in the future")
    except (TypeError, ValueError, OverflowError):
        errors.append("waiver expiry must be a timezone-aware ISO-8601 timestamp")


def validate_verification(session: dict, barrier: str, errors: list[str]) -> None:
    verification = session.get("verification")
    if not isinstance(verification, list) or not verification:
        errors.append("verification must contain command results")
        return
    markers = ["quick_validate.py", "manifest.py fingerprint", "manifest.py verify"]
    if barrier in {"round-2", "final"}:
        markers.append("validate_session.py")
    commands = []
    for index, item in enumerate(verification):
        if not isinstance(item, dict):
            errors.append(f"verification[{index}] must be an object")
            continue
        command = item.get("command")
        commands.append(command if isinstance(command, str) else "")
        if not isinstance(command, str) or not command.strip():
            errors.append(f"verification[{index}].command must be exact and non-empty")
        if isinstance(item.get("exit_code"), bool) or not isinstance(item.get("exit_code"), int):
            errors.append(f"verification[{index}].exit_code must be an integer")
        if not isinstance(item.get("mandatory"), bool):
            errors.append(f"verification[{index}].mandatory must be boolean")
        nonempty(item.get("raw_result"), f"verification[{index}].raw_result", errors)
        if item.get("mandatory") is True and item.get("exit_code") != 0:
            errors.append(f"mandatory verification failed: {command}")
    for marker in markers:
        if not any(marker in command for command in commands):
            errors.append(f"required verification command is missing: {marker}")


def validate_artifact(artifact: dict, role: str, expected_round: str, fingerprint: str, errors: list[str]) -> None:
    if artifact.get("role") != role:
        errors.append(f"{role}: role mismatch")
    if artifact.get("round") != expected_round:
        errors.append(f"{role}: round must be {expected_round}")
    if artifact.get("fingerprint") != fingerprint:
        errors.append(f"{role}: fingerprint mismatch")
    if artifact.get("independent") is not True or not isinstance(artifact.get("context_id"), str) or not artifact.get("context_id").strip():
        errors.append(f"{role}: fresh independent context attestation is required")


def validate_round(root: Path, directory_name: str, expected_roles: list[str], expected_round: str, fingerprint: str, errors: list[str]) -> set[str]:
    directory = root / directory_name
    if not directory.is_dir():
        errors.append(f"missing {directory_name} directory")
        return set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            errors.append(f"unexpected or symlinked artifact in {directory_name}: {path.name}")
    actual_files = sorted(path.stem for path in directory.glob("*.json") if path.is_file())
    if actual_files != sorted(expected_roles):
        errors.append(f"{directory_name} must contain exactly: {', '.join(expected_roles)}")
    contexts = set()
    for role in expected_roles:
        artifact = read_json(directory / f"{role}.json", errors)
        validate_artifact(artifact, role, expected_round, fingerprint, errors)
        context_id = artifact.get("context_id")
        if context_id in contexts:
            errors.append(f"duplicate context_id in {directory_name}: {context_id}")
        contexts.add(context_id)
        if expected_round == "advisor":
            for field in ("pre_exposure_stance", "recommendation", "uncertainty"):
                nonempty(artifact.get(field), f"{directory_name}/{role}.{field}", errors)
            for field in ("strengths", "failure_modes", "findings"):
                if not isinstance(artifact.get(field), list):
                    errors.append(f"{directory_name}/{role}.{field} must be a list")
            valid_confidence(artifact.get("confidence"), f"{directory_name}/{role}.confidence", errors)
        else:
            if artifact.get("coverage") != LABELS:
                errors.append(f"{directory_name}/{role}.coverage must be A-E")
            for field in ("pre_exposure_stance", "strongest_response", "biggest_blind_spot", "missing_scenario", "recommendation"):
                nonempty(artifact.get(field), f"{directory_name}/{role}.{field}", errors)
            valid_confidence(artifact.get("confidence"), f"{directory_name}/{role}.confidence", errors)
    return contexts


def validate_session(root: Path, manifest_path: Path, profiles_path: Path, barrier: str) -> tuple[bool, dict]:
    errors: list[str] = []
    root = root.absolute()
    if not root.is_dir() or root.is_symlink():
        return False, {"valid": False, "errors": [f"session root must be a real directory: {root}"]}
    if barrier not in {"round-1", "round-2", "final"}:
        return False, {"valid": False, "errors": [f"unsupported barrier: {barrier}"]}
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlinked session path is forbidden: {path}")

    session = read_json(root / "session.json", errors)
    if session.get("schema") != "council-session/v1":
        errors.append("session.schema must be council-session/v1")
    if session.get("barrier") != barrier:
        errors.append("session.barrier does not match the validator barrier")
    fingerprint = session.get("fingerprint")
    if not isinstance(fingerprint, str) or not HEX_DIGEST.fullmatch(fingerprint):
        errors.append("session.fingerprint must be a SHA-256 hex digest")
    validate_manifest_binding(session, manifest_path, errors)
    if session.get("phase_gate") is not True:
        errors.append("session.phase_gate must be true for a phase council")
    if session.get("review_mode") != "independent":
        errors.append("phase councils require independent review mode")
    if session.get("advisor_seats") != ADVISORS:
        errors.append("session.advisor_seats must contain the five canonical seats")
    if session.get("peer_seats") != PEERS:
        errors.append("session.peer_seats must contain peer-1 through peer-5")
    if session.get("response_labels") != LABELS:
        errors.append("session.response_labels must be A, B, C, D, E")

    phase = session.get("phase")
    phase_map = supported_phase_domains(profiles_path)
    phase_domains = session.get("phase_domains")
    if phase not in phase_map:
        errors.append(f"unsupported phase: {phase}")
    elif phase_domains != phase_map[phase]:
        errors.append("phase_domains do not match canonical profiles.yaml")
    overlays = session.get("phase_overlays_by_seat")
    if not isinstance(overlays, dict) or set(overlays) != set(ADVISORS):
        errors.append("phase_overlays_by_seat must map every advisor seat")
    elif phase in phase_map:
        valid_domains = set(phase_map[phase])
        for seat, values in overlays.items():
            if not isinstance(values, list) or not values or not set(values).issubset(valid_domains):
                errors.append(f"invalid phase overlay mapping for {seat}")

    validate_waiver(session, errors)
    validate_verification(session, barrier, errors)

    advisor_contexts = validate_round(root, "round-1", ADVISORS, "advisor", fingerprint, errors)
    if barrier in {"round-2", "final"}:
        peer_contexts = validate_round(root, "round-2", PEERS, "peer", fingerprint, errors)
        if advisor_contexts & peer_contexts:
            errors.append("advisor and peer contexts must be distinct")
        mapping = read_json(root / "mapping.json", errors)
        entries = mapping.get("mapping")
        if not isinstance(entries, list) or len(entries) != 5:
            errors.append("mapping.mapping must contain exactly five entries")
        else:
            seats = [entry.get("seat") for entry in entries if isinstance(entry, dict)]
            labels = [entry.get("label") for entry in entries if isinstance(entry, dict)]
            if sorted(seats) != sorted(ADVISORS) or sorted(labels) != sorted(LABELS):
                errors.append("mapping must be a one-to-one mapping of every seat to A-E")
            if mapping.get("fingerprint") != fingerprint:
                errors.append("mapping fingerprint mismatch")
    if barrier == "final":
        chairman = read_json(root / "chairman.json", errors)
        if chairman.get("role") != "chairman" or chairman.get("round") != "chairman" or chairman.get("fingerprint") != fingerprint:
            errors.append("chairman has an invalid role, round, or fingerprint")
        if chairman.get("independent") is not True or not isinstance(chairman.get("context_id"), str) or not chairman.get("context_id").strip():
            errors.append("chairman must have a distinct fresh context attestation")
        if chairman.get("context_id") in advisor_contexts:
            errors.append("chairman context must differ from advisor contexts")
        if chairman.get("gate") not in GATE_VALUES:
            errors.append("chairman.gate must be GO, GO_WITH_FIXES, or HOLD")
        if set(chairman.get("sections", [])) != SECTIONS:
            errors.append("chairman.sections must contain the five required sections")
        narrative = chairman.get("narrative")
        if not isinstance(narrative, dict) or set(narrative) != SECTIONS:
            errors.append("chairman.narrative must contain all five substantive sections")
        elif any(not isinstance(value, str) or not value.strip() for value in narrative.values()):
            errors.append("chairman.narrative sections must be non-empty")
        valid_confidence(chairman.get("confidence"), "chairman.confidence", errors)
        closure = chairman.get("closure_items", [])
        if chairman.get("gate") == "GO_WITH_FIXES":
            if not isinstance(closure, list) or not closure:
                errors.append("GO_WITH_FIXES requires closure_items")
            else:
                required = {"follow_up", "owner", "due_point", "acceptance_evidence", "non_blocking_rationale", "re_review_trigger"}
                for item in closure:
                    if not isinstance(item, dict) or required - set(item):
                        errors.append("every GO_WITH_FIXES item requires owner, due, evidence, rationale, and re-review trigger")
                    elif any(not isinstance(item[key], str) or not item[key].strip() for key in required):
                        errors.append("GO_WITH_FIXES closure fields must be non-empty")
        elif closure not in ([], None):
            errors.append("GO and HOLD must not contain GO_WITH_FIXES closure items")

    expected_digest = session.get("artifact_digest")
    actual_digest = artifact_digest(root)
    if expected_digest != actual_digest or not HEX_DIGEST.fullmatch(str(expected_digest)):
        errors.append("artifact_digest does not match the sealed artifacts")
    session_without_seal = dict(session)
    session_without_seal.pop("session_digest", None)
    expected_session_digest = session.get("session_digest")
    actual_session_digest = hashlib.sha256(canonical_json(session_without_seal).encode("utf-8")).hexdigest()
    if expected_session_digest != actual_session_digest:
        errors.append("session_digest does not seal session metadata")

    result = {
        "valid": not errors,
        "session_root": str(root),
        "barrier": barrier,
        "fingerprint": fingerprint,
        "artifact_digest": actual_digest,
        "session_digest": actual_session_digest,
        "advisor_count": 5,
        "peer_count": 5 if barrier in {"round-2", "final"} else 0,
        "chairman_count": 1 if barrier == "final" else 0,
        "errors": errors,
    }
    return not errors, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--profiles", type=Path, default=Path(__file__).resolve().parent.parent / "references" / "profiles.yaml")
    parser.add_argument("--barrier", choices=["round-1", "round-2", "final"], default="final")
    args = parser.parse_args()
    valid, result = validate_session(args.session, args.manifest, args.profiles, args.barrier)
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
