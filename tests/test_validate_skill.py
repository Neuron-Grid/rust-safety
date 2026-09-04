from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_skill.py"
spec = importlib.util.spec_from_file_location("validate_skill", MODULE_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

VALID_FRONTMATTER = '''---
name: rust-safety
description: >-
  Safety rules for Rust. Use when generating or reviewing Rust code.
license: MIT
metadata:
  version: "0.1.0"
---
# Skill
'''


def root_dir(tmp: str) -> Path:
    root = Path(tmp) / "rust-safety"
    root.mkdir()
    return root


class FrontmatterTests(unittest.TestCase):
    def test_valid_frontmatter(self) -> None:
        fields = validator.parse_frontmatter(VALID_FRONTMATTER)
        self.assertEqual(fields["name"], "rust-safety")
        self.assertEqual(fields["license"], "MIT")
        self.assertEqual(fields["metadata"], {"version": "0.1.0"})

    def test_missing_opening_frontmatter_is_rejected(self) -> None:
        with self.assertRaises(validator.FrontmatterParseError):
            validator.parse_frontmatter("name: rust-safety\n")

    def test_unclosed_frontmatter_is_rejected(self) -> None:
        with self.assertRaises(validator.FrontmatterParseError):
            validator.parse_frontmatter("---\nname: rust-safety\n")

    def test_duplicate_top_level_key_is_rejected(self) -> None:
        text = VALID_FRONTMATTER.replace("license: MIT\n", "license: MIT\nlicense: MIT\n")
        with self.assertRaises(validator.FrontmatterParseError):
            validator.parse_frontmatter(text)

    def test_duplicate_metadata_key_is_rejected(self) -> None:
        text = VALID_FRONTMATTER.replace('version: "0.1.0"', 'version: "0.1.0"\n  version: "0.1.1"')
        with self.assertRaises(validator.FrontmatterParseError):
            validator.parse_frontmatter(text)

    def test_invalid_plain_scalar_colon_is_rejected(self) -> None:
        text = '''---\nname: rust-safety\ndescription: Use this skill when: Rust safety matters\nlicense: MIT\n---\n'''
        with self.assertRaises(validator.FrontmatterParseError):
            validator.parse_frontmatter(text)

    def test_tabs_are_rejected(self) -> None:
        text = VALID_FRONTMATTER.replace("name: rust-safety", "\tname: rust-safety")
        with self.assertRaises(validator.FrontmatterParseError):
            validator.parse_frontmatter(text)

    def test_unknown_frontmatter_field_is_rejected(self) -> None:
        text = VALID_FRONTMATTER.replace("license: MIT\n", "license: MIT\nowner: someone\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            errors: list[str] = []
            validator.validate_frontmatter(root, text, errors)
            self.assertIn("SKILL.md: unsupported frontmatter field 'owner'", errors)

    def test_invalid_name_and_directory_mismatch_are_rejected(self) -> None:
        text = VALID_FRONTMATTER.replace("name: rust-safety", "name: rust--safety")
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            errors: list[str] = []
            validator.validate_frontmatter(root, text, errors)
            self.assertTrue(any("single internal hyphens" in e for e in errors))
            self.assertTrue(any("must match directory name" in e for e in errors))

    def test_overlong_name_description_and_compatibility_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            text = VALID_FRONTMATTER.replace("name: rust-safety", "name: " + "a" * 65)
            text = text.replace("Safety rules for Rust. Use when generating or reviewing Rust code.", "d" * 1025)
            text = text.replace("license: MIT\n", "license: MIT\ncompatibility: \"" + ("x" * 501) + "\"\n")
            errors: list[str] = []
            validator.validate_frontmatter(root, text, errors)
            self.assertTrue(any("name' exceeds 64" in e for e in errors))
            self.assertTrue(any("description' exceeds 1024" in e for e in errors))
            self.assertTrue(any("compatibility" in e and "exceeds 500" in e for e in errors))

    def test_frontmatter_types_and_license_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            text = VALID_FRONTMATTER.replace('version: "0.1.0"', "version: 1")
            text = text.replace("license: MIT", "license: Apache-2.0")
            text = text.replace("metadata:\n", "allowed-tools: 1\nmetadata:\n")
            errors: list[str] = []
            validator.validate_frontmatter(root, text, errors)
            self.assertTrue(any("metadata value" in e for e in errors))
            self.assertTrue(any("allowed-tools" in e and "string" in e for e in errors))
            self.assertIn("SKILL.md: repository policy requires exactly 'license: MIT'", errors)


class ReferenceTests(unittest.TestCase):
    def make_refs(self, root: Path) -> None:
        (root / "references").mkdir()
        (root / "references" / "ffi.md").write_text("# FFI\n", encoding="utf-8")
        (root / "references" / "server.md").write_text("# Server\n", encoding="utf-8")

    def test_bare_reference_filename_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            self.make_refs(root)
            errors: list[str] = []
            validator.validate_skill_references(root, VALID_FRONTMATTER + "See `ffi.md`.\n", errors)
            self.assertTrue(any("references/..." in e for e in errors))

    def test_canonical_reference_path_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            self.make_refs(root)
            errors: list[str] = []
            validator.validate_skill_references(root, VALID_FRONTMATTER + "See `references/ffi.md`.\n", errors)
            self.assertEqual(errors, [])

    def test_reference_to_reference_bare_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            self.make_refs(root)
            source = root / "references" / "server.md"
            source.write_text("See `ffi.md`.\n", encoding="utf-8")
            errors: list[str] = []
            validator.validate_reference_paths(root, source, source.read_text(), errors)
            self.assertTrue(any("references/server.md" in e and "references/..." in e for e in errors))

    def test_reference_traversal_and_missing_file_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            self.make_refs(root)
            errors: list[str] = []
            text = VALID_FRONTMATTER + "`references/../SECURITY.md` `references/missing.md`\n"
            validator.validate_skill_references(root, text, errors)
            self.assertTrue(any("traversal" in e for e in errors))
            self.assertTrue(any("missing referenced file" in e for e in errors))


class ValidationComponentTests(unittest.TestCase):
    def test_skill_size_limit(self) -> None:
        errors: list[str] = []
        validator.validate_skill_size("\n".join(["x"] * 501), errors)
        self.assertTrue(any("501 lines" in e for e in errors))

    def test_markdown_broken_link_and_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            (root / "doc.md").write_text("[bad](missing.md) [escape](../outside.md)\n", encoding="utf-8")
            errors: list[str] = []
            validator.validate_markdown_links(root, errors)
            self.assertTrue(any("broken relative link" in e for e in errors))
            self.assertTrue(any("link escapes repository root" in e for e in errors))

    def test_license_missing_invalid_and_legacy_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            errors: list[str] = []
            validator.validate_license(root, errors)
            self.assertTrue(any("single LICENSE file" in e for e in errors))
            (root / "LICENSE").write_text("Apache License\n", encoding="utf-8")
            (root / "LICENSE-APACHE").write_text("legacy\n", encoding="utf-8")
            errors = []
            validator.validate_license(root, errors)
            self.assertTrue(any("expected MIT License text" in e for e in errors))
            self.assertTrue(any("LICENSE-APACHE" in e for e in errors))

    def test_final_newline_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            (root / "doc.md").write_bytes(b"no newline")
            errors: list[str] = []
            validator.validate_final_newlines(root, errors)
            self.assertEqual(errors, ["doc.md: missing final newline"])

    def test_archive_hygiene_rejects_macos_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            (root / "__MACOSX").mkdir()
            (root / "__MACOSX" / "._SKILL.md").write_text("x\n", encoding="utf-8")
            errors: list[str] = []
            validator.validate_archive_hygiene(root, errors)
            self.assertTrue(any("macOS archive metadata" in e for e in errors))


class EvalTests(unittest.TestCase):
    def write_eval(self, root: Path, payload: object) -> None:
        (root / "evals").mkdir()
        (root / "evals" / "evals.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_missing_eval_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            errors: list[str] = []
            validator.validate_evals(root, errors)
            self.assertTrue(any("behavioral eval file is required" in e for e in errors))

    def test_invalid_eval_shape_and_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            self.write_eval(root, {"skill_name": "wrong", "evals": [{"id": "", "prompt": "", "expected_output": 1, "assertions": []}]})
            errors: list[str] = []
            validator.validate_evals(root, errors)
            self.assertTrue(any("skill_name" in e for e in errors))
            self.assertTrue(any("requires a non-empty string or integer 'id'" in e for e in errors))
            self.assertTrue(any("expected_output" in e for e in errors))
            self.assertTrue(any("assertions" in e for e in errors))

    def test_duplicate_eval_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            payload = {"skill_name": "rust-safety", "evals": [
                {"id": 1, "prompt": "a", "expected_output": "b", "assertions": ["c"]},
                {"id": 1, "prompt": "d", "expected_output": "e", "assertions": ["f"]},
            ]}
            self.write_eval(root, payload)
            errors: list[str] = []
            validator.validate_evals(root, errors)
            self.assertTrue(any("duplicates id" in e for e in errors))

    def test_eval_file_escape_and_missing_file_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            payload = {"skill_name": "rust-safety", "evals": [
                {"id": 1, "prompt": "a", "expected_output": "b", "assertions": ["c"], "files": ["../outside.rs", "missing.rs"]}
            ]}
            self.write_eval(root, payload)
            errors: list[str] = []
            validator.validate_evals(root, errors)
            self.assertTrue(any("file escapes repository root" in e for e in errors))
            self.assertTrue(any("missing input file" in e for e in errors))


class PolicyTests(unittest.TestCase):
    def test_missing_policy_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            errors: list[str] = []
            validator.validate_repository_policy_files(root, errors)
            self.assertTrue(any("required repository policy file is missing" in e for e in errors))

    def test_repository_policy_routes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = root_dir(tmp)
            files = {
                "README.md": "[MIT](LICENSE)\n",
                "README_EN.md": "[MIT](LICENSE)\n",
                "CONTRIBUTING.md": "CODE_OF_CONDUCT.md SECURITY.md\n",
                "SECURITY.md": "Private Vulnerability Reporting GitLab Confidential\n",
                "CODE_OF_CONDUCT.md": "## Reporting conduct issues\n## Enforcement\nSECURITY.md\n",
                ".github/ISSUE_TEMPLATE/safety-correction.yml": "SECURITY.md\n",
                ".gitlab/issue_templates/Safety-correction.md": "SECURITY.md\n",
                ".github/PULL_REQUEST_TEMPLATE.md": "SECURITY.md\n",
                ".gitlab/merge_request_templates/Default.md": "SECURITY.md\n",
            }
            for rel, content in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            errors: list[str] = []
            validator.validate_repository_policy_files(root, errors)
            self.assertEqual(errors, [])


class RepositoryTests(unittest.TestCase):
    def test_repository_passes_its_own_validator(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(validator.validate_repository(root), [])


if __name__ == "__main__":
    unittest.main()
