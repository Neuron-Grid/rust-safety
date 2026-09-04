#!/usr/bin/env python3
"""Repository-local preflight validation for the rust-safety Agent Skill.

This intentionally validates the Agent Skills frontmatter subset used by this
repository without requiring PyYAML. It is not a general-purpose YAML parser.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CODE_MD_PATH_RE = re.compile(r"`([^`\n]+\.md)`")
TEXT_NAMES = {".editorconfig", ".gitattributes", ".gitignore", "LICENSE"}
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json"}
BLOCK_MARKERS = {">", ">-", ">+", "|", "|-", "|+"}


class FrontmatterParseError(ValueError):
    pass


def _parse_scalar(raw: str, *, context: str) -> object:
    value = raw.strip()
    if not value:
        return ""

    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise FrontmatterParseError(f"{context}: invalid double-quoted scalar: {exc.msg}") from exc
        return parsed

    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise FrontmatterParseError(f"{context}: unterminated single-quoted scalar")
        return value[1:-1].replace("''", "'")

    # In YAML plain scalars, ': ' starts mapping syntax. Reject it rather than
    # silently accepting malformed frontmatter such as:
    # description: Use this skill when: Rust safety matters
    if ": " in value:
        raise FrontmatterParseError(
            f"{context}: unquoted ': ' is not accepted in a plain scalar; quote the value or use a block scalar"
        )

    if value.startswith(("[", "{", "&", "*", "!")):
        raise FrontmatterParseError(f"{context}: unsupported YAML construct")

    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", value):
        return float(value)
    return value


def _consume_block_scalar(lines: list[str], start: int, end: int, marker: str, *, context: str) -> tuple[str, int]:
    parts: list[str] = []
    i = start
    saw_indented = False
    while i < end:
        line = lines[i]
        if not line.strip():
            if saw_indented:
                parts.append("")
            i += 1
            continue
        if not line.startswith(" "):
            break
        saw_indented = True
        parts.append(line.lstrip())
        i += 1

    if not saw_indented:
        raise FrontmatterParseError(f"{context}: block scalar must contain an indented value")

    if marker.startswith(">"):
        value = " ".join(part for part in parts if part)
    else:
        value = "\n".join(parts)

    if marker.endswith("-"):
        value = value.rstrip("\n")
    elif marker.endswith("+"):
        value += "\n"
    return value, i


def parse_frontmatter(text: str) -> dict[str, object]:
    """Parse the restricted frontmatter shape accepted by this repository."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise FrontmatterParseError("YAML frontmatter must start with '---'")

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise FrontmatterParseError("YAML frontmatter is not closed with '---'") from exc

    fields: dict[str, object] = {}
    i = 1
    while i < end:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if "\t" in line:
            raise FrontmatterParseError(f"line {i + 1}: tabs are not accepted in frontmatter indentation")
        if line.startswith(" "):
            raise FrontmatterParseError(f"line {i + 1}: unexpected indentation")
        if ":" not in line:
            raise FrontmatterParseError(f"line {i + 1}: expected 'key: value'")

        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterParseError(f"line {i + 1}: empty key")
        if key in fields:
            raise FrontmatterParseError(f"line {i + 1}: duplicate top-level key '{key}'")

        value = raw_value.strip()
        if key == "metadata" and value == "":
            metadata: dict[str, object] = {}
            i += 1
            while i < end:
                child = lines[i]
                if not child.strip() or child.lstrip().startswith("#"):
                    i += 1
                    continue
                if not child.startswith(" "):
                    break
                if "\t" in child:
                    raise FrontmatterParseError(f"line {i + 1}: tabs are not accepted in metadata indentation")
                indent = len(child) - len(child.lstrip(" "))
                if indent != 2:
                    raise FrontmatterParseError(f"line {i + 1}: metadata entries must use exactly two spaces of indentation")
                entry = child.strip()
                if ":" not in entry:
                    raise FrontmatterParseError(f"line {i + 1}: expected metadata 'key: value'")
                meta_key, meta_raw = entry.split(":", 1)
                meta_key = meta_key.strip()
                if not meta_key:
                    raise FrontmatterParseError(f"line {i + 1}: empty metadata key")
                if meta_key in metadata:
                    raise FrontmatterParseError(f"line {i + 1}: duplicate metadata key '{meta_key}'")
                metadata[meta_key] = _parse_scalar(meta_raw, context=f"line {i + 1} metadata.{meta_key}")
                i += 1
            fields[key] = metadata
            continue

        if value in BLOCK_MARKERS:
            parsed, i = _consume_block_scalar(lines, i + 1, end, value, context=f"line {i + 1} {key}")
            fields[key] = parsed
            continue

        fields[key] = _parse_scalar(value, context=f"line {i + 1} {key}")
        i += 1

    return fields


def _add(errors: list[str], message: str) -> None:
    errors.append(message)


def _read_utf8(root: Path, path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _add(errors, f"{path.relative_to(root)}: cannot read as UTF-8: {exc}")
        return None


def validate_frontmatter(root: Path, text: str, errors: list[str]) -> dict[str, object]:
    try:
        fields = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        _add(errors, f"SKILL.md: invalid frontmatter: {exc}")
        return {}

    unknown = sorted(set(fields) - ALLOWED_FRONTMATTER_FIELDS)
    for key in unknown:
        _add(errors, f"SKILL.md: unsupported frontmatter field '{key}'")

    name = fields.get("name")
    if not isinstance(name, str) or not name:
        _add(errors, "SKILL.md: required 'name' must be a non-empty string")
    else:
        if len(name) > 64:
            _add(errors, "SKILL.md: 'name' exceeds 64 characters")
        if not NAME_RE.fullmatch(name):
            _add(errors, "SKILL.md: 'name' must use lowercase ASCII letters/digits with single internal hyphens only")
        if name != root.name:
            _add(errors, f"SKILL.md: name '{name}' must match directory name '{root.name}'")

    description = fields.get("description")
    if not isinstance(description, str) or not description:
        _add(errors, "SKILL.md: required 'description' must be a non-empty string")
    elif len(description) > 1024:
        _add(errors, f"SKILL.md: 'description' exceeds 1024 characters ({len(description)})")

    license_value = fields.get("license")
    if license_value != "MIT":
        _add(errors, "SKILL.md: repository policy requires exactly 'license: MIT'")

    if "compatibility" in fields:
        compatibility = fields["compatibility"]
        if not isinstance(compatibility, str) or not compatibility:
            _add(errors, "SKILL.md: 'compatibility' must be a non-empty string when provided")
        elif len(compatibility) > 500:
            _add(errors, f"SKILL.md: 'compatibility' exceeds 500 characters ({len(compatibility)})")

    if "allowed-tools" in fields:
        allowed_tools = fields["allowed-tools"]
        if not isinstance(allowed_tools, str) or not allowed_tools:
            _add(errors, "SKILL.md: 'allowed-tools' must be a non-empty space-separated string when provided")

    if "metadata" in fields:
        metadata = fields["metadata"]
        if not isinstance(metadata, dict):
            _add(errors, "SKILL.md: 'metadata' must be a mapping from string keys to string values")
        else:
            for key, value in metadata.items():
                if not isinstance(key, str) or not key:
                    _add(errors, "SKILL.md: metadata keys must be non-empty strings")
                if not isinstance(value, str):
                    _add(errors, f"SKILL.md: metadata value for '{key}' must be a string")

    return fields


def validate_skill_size(text: str, errors: list[str]) -> None:
    line_count = len(text.splitlines())
    if line_count > 500:
        _add(errors, f"SKILL.md: {line_count} lines; project policy keeps it at or below 500")


def validate_reference_paths(root: Path, source: Path, text: str, errors: list[str]) -> None:
    """Validate root-relative references/... code-span paths in Skill/reference docs."""
    reference_dir = (root / "references").resolve()
    known_reference_names = {p.name for p in reference_dir.glob("*.md")} if reference_dir.is_dir() else set()
    source_label = str(source.relative_to(root))

    for match in CODE_MD_PATH_RE.finditer(text):
        token = match.group(1).strip()
        token_path = Path(token)
        is_known_bare_reference = token_path.name in known_reference_names
        is_reference_path = token.startswith("references/")

        if is_known_bare_reference and not is_reference_path:
            _add(errors, f"{source_label}: reference path must be skill-root relative as 'references/...': {token}")
            continue
        if not is_reference_path:
            continue

        if token_path.is_absolute() or any(part in {".", ".."} for part in token_path.parts):
            _add(errors, f"{source_label}: reference path must not contain absolute or traversal components: {token}")
            continue

        resolved = (root / token_path).resolve()
        try:
            resolved.relative_to(reference_dir)
        except ValueError:
            _add(errors, f"{source_label}: reference must remain inside references/: {token}")
            continue
        if not resolved.is_file():
            _add(errors, f"{source_label}: missing referenced file: {token}")


def validate_skill_references(root: Path, text: str, errors: list[str]) -> None:
    """Backward-compatible wrapper for callers that validate SKILL.md only."""
    validate_reference_paths(root, root / "SKILL.md", text, errors)


def validate_all_reference_paths(root: Path, skill_text: str, errors: list[str]) -> None:
    validate_reference_paths(root, root / "SKILL.md", skill_text, errors)
    reference_dir = root / "references"
    if not reference_dir.is_dir():
        return
    for source in sorted(reference_dir.glob("*.md")):
        text = _read_utf8(root, source, errors)
        if text is not None:
            validate_reference_paths(root, source, text, errors)


def validate_markdown_links(root: Path, errors: list[str]) -> None:
    for source in sorted(root.rglob("*.md")):
        text = _read_utf8(root, source, errors)
        if text is None:
            continue
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                _add(errors, f"{source.relative_to(root)}: link escapes repository root: {raw_target}")
                continue
            if not resolved.exists():
                _add(errors, f"{source.relative_to(root)}: broken relative link: {raw_target}")


def validate_license(root: Path, errors: list[str]) -> None:
    license_path = root / "LICENSE"
    if not license_path.is_file():
        _add(errors, "LICENSE: MIT-only repository policy requires a single LICENSE file")
        return
    text = _read_utf8(root, license_path, errors)
    if text is not None and not text.startswith("MIT License\n"):
        _add(errors, "LICENSE: expected MIT License text")
    for forbidden in ("LICENSE-MIT", "LICENSE-APACHE", "LICENSE.txt"):
        if (root / forbidden).exists():
            _add(errors, f"{forbidden}: remove alternate/legacy license file; repository is MIT-only")


def validate_evals(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "evals.json"
    if not path.is_file():
        _add(errors, "evals/evals.json: behavioral eval file is required by repository policy")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(errors, f"evals/evals.json: invalid JSON: {exc}")
        return

    if not isinstance(data, dict):
        _add(errors, "evals/evals.json: root must be an object")
        return
    if data.get("skill_name") != "rust-safety":
        _add(errors, "evals/evals.json: skill_name must be 'rust-safety'")
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        _add(errors, "evals/evals.json: 'evals' must be a non-empty array")
        return

    seen_ids: set[object] = set()
    for index, item in enumerate(evals, start=1):
        prefix = f"evals/evals.json: eval #{index}"
        if not isinstance(item, dict):
            _add(errors, f"{prefix} must be an object")
            continue
        eval_id = item.get("id")
        if not isinstance(eval_id, (int, str)) or isinstance(eval_id, bool) or eval_id == "":
            _add(errors, f"{prefix} requires a non-empty string or integer 'id'")
        elif eval_id in seen_ids:
            _add(errors, f"{prefix} duplicates id {eval_id!r}")
        else:
            seen_ids.add(eval_id)

        for field in ("prompt", "expected_output"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                _add(errors, f"{prefix} requires non-empty string '{field}'")

        assertions = item.get("assertions")
        if not isinstance(assertions, list) or not assertions or not all(isinstance(v, str) and v.strip() for v in assertions):
            _add(errors, f"{prefix} requires a non-empty array of non-empty string 'assertions'")

        files = item.get("files", [])
        if not isinstance(files, list) or not all(isinstance(v, str) and v for v in files):
            _add(errors, f"{prefix} 'files' must be an array of non-empty strings when provided")
            continue
        for raw in files:
            resolved = (root / raw).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                _add(errors, f"{prefix} file escapes repository root: {raw}")
                continue
            if not resolved.is_file():
                _add(errors, f"{prefix} missing input file: {raw}")


def validate_final_newlines(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name not in TEXT_NAMES and path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            _add(errors, f"{path.relative_to(root)}: cannot read: {exc}")
            continue
        if data and not data.endswith(b"\n"):
            _add(errors, f"{path.relative_to(root)}: missing final newline")


def validate_archive_hygiene(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if "__MACOSX" in rel.parts or path.name.startswith("._"):
            _add(errors, f"{rel}: macOS archive metadata must not be committed or distributed")


def validate_repository_policy_files(root: Path, errors: list[str]) -> None:
    required = [
        "README.md",
        "README_EN.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/safety-correction.yml",
        ".gitlab/issue_templates/Safety-correction.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".gitlab/merge_request_templates/Default.md",
    ]
    texts: dict[str, str] = {}
    for rel in required:
        path = root / rel
        if not path.is_file():
            _add(errors, f"{rel}: required repository policy file is missing")
            continue
        text = _read_utf8(root, path, errors)
        if text is not None:
            texts[rel] = text

    for rel in ("README.md", "README_EN.md"):
        text = texts.get(rel, "")
        if "(LICENSE)" not in text:
            _add(errors, f"{rel}: MIT license section must link to LICENSE")
        for legacy in ("LICENSE-MIT", "LICENSE-APACHE", "MIT OR Apache-2.0"):
            if legacy in text:
                _add(errors, f"{rel}: legacy dual-license reference remains: {legacy}")

    security = texts.get("SECURITY.md", "")
    if "Private Vulnerability Reporting" not in security:
        _add(errors, "SECURITY.md: GitHub Private Vulnerability Reporting route is required")
    if "Confidential" not in security or "GitLab" not in security:
        _add(errors, "SECURITY.md: GitLab Confidential Issue route is required")

    for rel in (
        ".github/ISSUE_TEMPLATE/safety-correction.yml",
        ".gitlab/issue_templates/Safety-correction.md",
    ):
        if "SECURITY.md" not in texts.get(rel, ""):
            _add(errors, f"{rel}: safety-correction template must route sensitive reports to SECURITY.md")

    for rel in (
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".gitlab/merge_request_templates/Default.md",
    ):
        if "SECURITY.md" not in texts.get(rel, ""):
            _add(errors, f"{rel}: pull/merge-request template must route sensitive reports to SECURITY.md")

    contributing = texts.get("CONTRIBUTING.md", "")
    if "CODE_OF_CONDUCT.md" not in contributing:
        _add(errors, "CONTRIBUTING.md: must link to CODE_OF_CONDUCT.md")
    if "SECURITY.md" not in contributing:
        _add(errors, "CONTRIBUTING.md: must route security-sensitive reports to SECURITY.md")

    coc = texts.get("CODE_OF_CONDUCT.md", "")
    for heading in ("## Reporting conduct issues", "## Enforcement"):
        if heading not in coc:
            _add(errors, f"CODE_OF_CONDUCT.md: missing required section '{heading}'")
    if "SECURITY.md" not in coc:
        _add(errors, "CODE_OF_CONDUCT.md: security vulnerabilities must be routed to SECURITY.md")


def validate_repository(root: Path = DEFAULT_ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    skill = root / "SKILL.md"
    text = _read_utf8(root, skill, errors) if skill.is_file() else None
    if text is None:
        if not skill.is_file():
            _add(errors, "SKILL.md: missing")
    else:
        validate_frontmatter(root, text, errors)
        validate_skill_size(text, errors)
        validate_all_reference_paths(root, text, errors)

    validate_license(root, errors)
    validate_evals(root, errors)
    validate_markdown_links(root, errors)
    validate_final_newlines(root, errors)
    validate_archive_hygiene(root, errors)
    validate_repository_policy_files(root, errors)
    return errors


def main() -> int:
    errors = validate_repository(DEFAULT_ROOT)
    if errors:
        print("rust-safety validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("rust-safety validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
