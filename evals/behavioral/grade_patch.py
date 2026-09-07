"""Run limited patch checks; soundness and overall scoring require the rubric.

Run only in an isolated evaluation environment: candidate Cargo builds and tests
execute candidate code. This script is not a sandbox or an agent runner.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "ffi-slice"
PROBE = """use ffi_slice::slice_from_raw;

#[test]
fn null_empty() {
    // SAFETY: The evaluation requires the repaired API to accept absent empty
    // buffers. No allocation is accessed and the returned empty slice is valid.
    let result = unsafe { slice_from_raw(std::ptr::null(), 0) };
    assert!(result.is_empty());
}

#[test]
fn nonnull_empty() {
    let byte = 42_u8;
    // SAFETY: The live u8 supplies an aligned non-null pointer; length is zero.
    let result = unsafe { slice_from_raw(&byte, 0) };
    assert!(result.is_empty());
}
"""


def grade_patch(candidate: Path) -> dict[str, bool]:
    """Grade a disposable copy, preserving the candidate and trusted probes."""
    candidate = candidate.resolve(strict=True)
    if not (candidate / "Cargo.toml").is_file():
        raise ValueError("candidate must be a Rust repository containing Cargo.toml")
    with tempfile.TemporaryDirectory(prefix="rust-safety-grade-") as tmp:
        work = Path(tmp) / "candidate"
        shutil.copytree(candidate, work, ignore=shutil.ignore_patterns("target", ".git"))

        def run(*args: str) -> bool:
            try:
                result = subprocess.run(
                    ["cargo", *args],
                    cwd=work,
                    timeout=120,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except subprocess.TimeoutExpired:
                return False
            if result.returncode:
                print(result.stdout)
            return result.returncode == 0

        scores = {
            "compile": run("check", "--offline", "--all-targets"),
            "candidate_tests": run("test", "--offline"),
            "unsafe_lints": run(
                "clippy",
                "--offline",
                "--all-targets",
                "--",
                "-D",
                "unsafe_op_in_unsafe_fn",
                "-D",
                "unused_unsafe",
                "-D",
                "clippy::missing_safety_doc",
                "-D",
                "clippy::undocumented_unsafe_blocks",
            ),
        }
        # Install grader-owned tests only after running the candidate's own suite.
        tests = work / "tests"
        tests.mkdir(exist_ok=True)
        (tests / "grader_compatibility.rs").write_text(
            (FIXTURE / "tests/public_api.rs").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (tests / "grader_boundaries.rs").write_text(PROBE, encoding="utf-8")
        scores["api_compatibility"] = run("test", "--offline", "--test", "grader_compatibility")
        for case in ("null_empty", "nonnull_empty"):
            scores[case] = run("test", "--offline", "--test", "grader_boundaries", case, "--", "--exact")
        return scores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="patched ffi-slice repository")
    args = parser.parse_args()
    try:
        scores = grade_patch(args.candidate)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot grade candidate: {exc}\n")
    print(json.dumps({"automatic_checks": scores, "rubric": "NOT_EVALUATED"}, indent=2))
    return 0 if all(scores.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
