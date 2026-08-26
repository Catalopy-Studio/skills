#!/usr/bin/env python3
"""Create and verify deterministic SHA-256 manifests for council review packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


EXCLUDED_DIRECTORIES = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    ".mypy_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"symlinked paths are not allowed in a council manifest: {path}")
        if not path.is_file():
            continue
        try:
            path.resolve(strict=True).relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"file resolves outside the reviewed root: {path}") from exc
        relative_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRECTORIES for part in relative_parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        yield path


def build_manifest(root: Path) -> dict:
    root = root.resolve()
    files = []
    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    canonical = "".join(
        f"{item['path']}\0{item['bytes']}\0{item['sha256']}\n" for item in files
    ).encode("utf-8")
    return {
        "schema": "council-manifest/v1",
        "root": str(root),
        "file_count": len(files),
        "files": files,
        "digest": hashlib.sha256(canonical).hexdigest(),
    }


def verify(root: Path, expected: dict) -> tuple[bool, dict]:
    actual = build_manifest(root)
    expected_files = expected.get("files")
    expected_root = expected.get("root")
    expected_count = expected.get("file_count")
    schema_match = expected.get("schema") == "council-manifest/v1"
    root_match = expected_root == str(root.resolve())
    count_match = isinstance(expected_count, int) and expected_count == actual["file_count"]
    files_match = isinstance(expected_files, list) and expected_files == actual["files"]
    digest_match = isinstance(expected.get("digest"), str) and expected.get("digest") == actual["digest"]
    result = {
        "valid": schema_match and root_match and count_match and digest_match and files_match,
        "schema_match": schema_match,
        "root_match": root_match,
        "count_match": count_match,
        "expected_digest": expected.get("digest"),
        "actual_digest": actual["digest"],
        "expected_file_count": expected_count,
        "actual_file_count": actual["file_count"],
        "files_match": files_match,
    }
    return result["valid"], result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fingerprint = subparsers.add_parser("fingerprint", help="print a JSON manifest")
    fingerprint.add_argument("--root", required=True, type=Path)
    fingerprint.add_argument("--output", type=Path, help="also save the JSON manifest")

    verify_parser = subparsers.add_parser("verify", help="verify a saved JSON manifest")
    verify_parser.add_argument("--root", required=True, type=Path)
    verify_parser.add_argument("--manifest", required=True, type=Path)

    args = parser.parse_args()
    if not args.root.exists() or not args.root.is_dir():
        parser.error(f"root is not a directory: {args.root}")

    try:
        if args.command == "fingerprint":
            result = build_manifest(args.root)
        else:
            expected = json.loads(args.manifest.read_text(encoding="utf-8"))
            valid, result = verify(args.root, expected)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        sys.stderr.write(f"manifest validation failed: {exc}\n")
        return 1

    if args.command == "fingerprint":
        serialized = json.dumps(result, indent=2) + "\n"
        if args.output:
            output_path = args.output.resolve()
            root_path = args.root.resolve()
            if output_path == root_path or root_path in output_path.parents:
                parser.error("--output must be outside --root so the manifest cannot change its own fingerprint")
            output_path.write_text(serialized, encoding="utf-8")
        sys.stdout.write(serialized)
        return 0

    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
