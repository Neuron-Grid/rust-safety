from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "evals/behavioral/grade_patch.py"
spec = importlib.util.spec_from_file_location("grade_patch", MODULE_PATH)
assert spec is not None and spec.loader is not None
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)

# Grader calibration only: never include this repair or the rubric in agent input.
REPAIRED = """/// Borrows a foreign byte buffer; absent empty buffers are accepted.
///
/// # Safety
/// For nonzero len, ptr must be non-null and aligned, with provenance allowing
/// reads of len initialized u8 values within one live allocation. The total byte
/// size must not exceed isize::MAX and the address range must not wrap.
/// The caller must keep that allocation live and immutable for the entire
/// inferred return lifetime 'a, not merely until this function returns.
pub unsafe fn slice_from_raw<'a>(ptr: *const u8, len: usize) -> &'a [u8] {
    if len == 0 {
        return &[];
    }
    // SAFETY: The caller guarantees the readable, initialized, single-allocation
    // range, non-nullness, alignment, provenance, size and no wrap. They also
    // guarantee that the storage remains live and immutable throughout 'a.
    unsafe { std::slice::from_raw_parts(ptr, len) }
}
"""


class BehavioralDefinitionTests(unittest.TestCase):
    def test_fixture_is_complete_and_prompt_is_separate(self) -> None:
        for relative in ("Cargo.toml", "src/lib.rs", "tests/public_api.rs", "task.md"):
            self.assertTrue((grader.FIXTURE / relative).is_file())
        prompt = (grader.FIXTURE / "task.md").read_text(encoding="utf-8").lower()
        for answer in ("null", "lifetime", "overflow", "from_raw_parts", "isize"):
            self.assertNotIn(answer, prompt)

    def test_missing_candidate_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "Cargo.toml"):
            grader.grade_patch(Path(tmp))


@unittest.skipUnless(shutil.which("cargo"), "Rust toolchain unavailable; grader execution requires cargo/clippy")
class BehavioralGraderTests(unittest.TestCase):
    def test_unrepaired_fixture_fails_behavioral_checks(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            scores = grader.grade_patch(grader.FIXTURE)
        self.assertTrue(scores["compile"])
        self.assertTrue(scores["candidate_tests"])
        self.assertTrue(scores["api_compatibility"])
        self.assertTrue(scores["nonnull_empty"])
        self.assertFalse(scores["null_empty"])
        self.assertFalse(scores["unsafe_lints"])

    def test_repaired_patch_passes_without_modifying_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="candidate with spaces ") as tmp:
            candidate = Path(tmp) / "ffi-slice"
            shutil.copytree(grader.FIXTURE, candidate)
            source = candidate / "src/lib.rs"
            source.write_text(REPAIRED, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                scores = grader.grade_patch(candidate)
            self.assertTrue(all(scores.values()), scores)
            self.assertEqual(source.read_text(encoding="utf-8"), REPAIRED)
            self.assertFalse((candidate / "target").exists())
            self.assertFalse((candidate / "tests/grader_boundaries.rs").exists())


if __name__ == "__main__":
    unittest.main()
