#!/usr/bin/env python3
"""Repository-local preflight validation for the rust-safety Agent Skill.

This intentionally validates the Agent Skills frontmatter subset used by this
repository and the official plugin-manifest subset selected by this repository.
It is not a general-purpose YAML, JSON Schema, or marketplace validator.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import unquote

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = Path("skills/rust-safety")
CODEX_PLUGIN_PATH = Path(".codex-plugin/plugin.json")
CLAUDE_PLUGIN_PATH = Path(".claude-plugin/plugin.json")
CODEX_MARKETPLACE_PATH = Path(".agents/plugins/marketplace.json")
CLAUDE_MARKETPLACE_PATH = Path(".claude-plugin/marketplace.json")
PLUGIN_NAME = "rust-safety"
PLUGIN_DESCRIPTION = (
    "Rust development safety skill for secure coding, unsafe code, FFI, "
    "concurrency, panic handling, secret handling, and platform-specific Rust development."
)
PLUGIN_AUTHOR = {"name": "Neuron-Grid", "url": "https://github.com/Neuron-Grid"}
PLUGIN_REPOSITORY = "https://github.com/Neuron-Grid/rust-safety"
PLUGIN_KEYWORDS = ["rust", "safety", "security", "ffi", "concurrency"]
PLUGIN_COMMON_VALUES: dict[str, object] = {
    "name": PLUGIN_NAME,
    "description": PLUGIN_DESCRIPTION,
    "author": PLUGIN_AUTHOR,
    "homepage": PLUGIN_REPOSITORY,
    "repository": PLUGIN_REPOSITORY,
    "license": "MIT",
    "keywords": PLUGIN_KEYWORDS,
}
CODEX_INTERFACE = {
    "displayName": "Rust Safety",
    "shortDescription": "Secure and correct Rust development guidance.",
    "longDescription": PLUGIN_DESCRIPTION,
    "developerName": "Neuron-Grid",
    "category": "Productivity",
    "capabilities": ["Read", "Write"],
    "websiteURL": PLUGIN_REPOSITORY,
    "defaultPrompt": ["Review this Rust code for safety, security, and correctness."],
}
CLAUDE_PLUGIN_SCHEMA = "https://json.schemastore.org/claude-code-plugin-manifest.json"
CLAUDE_MARKETPLACE_SCHEMA = "https://json.schemastore.org/claude-code-marketplace.json"
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
FORBIDDEN_MANIFEST_FIELDS = {
    "lspServers",
    "monitors",
    "experimental",
    "settings",
    "channels",
    "agent",
    "agents",
    "app",
    "apps",
    "bin",
    "command",
    "commands",
    "dependencies",
    "dependency",
    "hooks",
    "install",
    "mcp",
    "mcpServers",
    "mcp_servers",
    "postinstall",
    "scripts",
}
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
# Reserved component locations, relative to a plugin or standalone Skill root.
# See evals/README.md for the supported specification boundary and sources.
RUNTIME_LOCATIONS = (
    "hooks",
    "hooks.json",
    ".mcp.json",
    ".app.json",
    ".lsp.json",
    "agents",
    "commands",
    "bin",
    "servers",
    "monitors",
    "settings.json",
)


def validate_runtime_components(root: Path, errors: list[str]) -> None:
    """Reject known runtime surfaces without classifying arbitrary source code."""
    root = root.resolve()
    skill_root = root / SKILL_PATH
    for base in (root, skill_root):
        locations = RUNTIME_LOCATIONS + (("scripts",) if base == skill_root else ())
        for location in locations:
            path = base / location
            if path.exists() or path.is_symlink():
                _add(errors, f"{path.relative_to(root)}: forbidden runtime component location")
        # A package manifest plus a supported lockfile triggers dependency install.
        if (base / "package.json").exists() and any(
            (base / name).exists() for name in ("bun.lock", "bun.lockb", "npm-shrinkwrap.json", "package-lock.json")
        ):
            _add(errors, f"{base.relative_to(root)}: implicit package dependency installation")

    # skills/ is manifest-loaded. Do not follow links or silently admit another
    # Skill whose frontmatter is outside our supported single-Skill schema.
    skills = root / "skills"
    if skills.is_symlink():
        _add(errors, "skills: symlinks are unsupported in the Skill distribution")
        return

    def walk_error(exc: OSError) -> None:
        _add(errors, f"skills: cannot inspect distribution: {exc}")

    for directory, dirs, files in os.walk(skills, followlinks=False, onerror=walk_error):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            rel = path.relative_to(root)
            try:
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode):
                    _add(errors, f"{rel}: symlinks are unsupported in the Skill distribution")
                elif stat.S_ISREG(mode):
                    if name == "SKILL.md" and rel != SKILL_PATH / "SKILL.md":
                        _add(errors, f"{rel}: unsupported additional Skill")
                    with path.open("rb") as stream:
                        prefix = stream.read(3)
                        shebang = prefix.startswith(b"#!") and prefix != b"#!["
                    if mode & 0o111 or shebang:
                        _add(errors, f"{rel}: executable file or shebang in Skill distribution")
                elif not stat.S_ISDIR(mode):
                    _add(errors, f"{rel}: unsupported special file in Skill distribution")
            except OSError as exc:
                _add(errors, f"{rel}: cannot inspect distribution: {exc}")


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

    metadata = fields.get("metadata")
    if not isinstance(metadata, dict):
        _add(errors, "SKILL.md: required 'metadata' must be a mapping from string keys to string values")
    else:
        for key, value in metadata.items():
            if not isinstance(key, str) or not key:
                _add(errors, "SKILL.md: metadata keys must be non-empty strings")
            if not isinstance(value, str):
                _add(errors, f"SKILL.md: metadata value for '{key}' must be a string")
        version = metadata.get("version")
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            _add(errors, "SKILL.md: metadata.version must be a SemVer 2.0.0 string")

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


def _read_json_object(root: Path, relative: Path, errors: list[str]) -> dict[str, object] | None:
    path = root / relative
    if not path.is_file():
        _add(errors, f"{relative}: required plugin metadata file is missing")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(errors, f"{relative}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        _add(errors, f"{relative}: root must be an object")
        return None
    return value


def _validate_static_manifest(value: object, label: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_MANIFEST_FIELDS:
                _add(errors, f"{label}: forbidden executable field '{key}'")
            _validate_static_manifest(child, label, errors)
    elif isinstance(value, list):
        for child in value:
            _validate_static_manifest(child, label, errors)


def _validate_fields(
    value: dict[str, object], allowed: set[str], label: str, errors: list[str]
) -> None:
    for key in sorted(set(value) - allowed):
        if key not in FORBIDDEN_MANIFEST_FIELDS:
            _add(errors, f"{label}: unsupported field '{key}'")


def _validate_required_values(
    value: dict[str, object], expected: Mapping[str, object], label: str, errors: list[str]
) -> None:
    for key, expected_value in expected.items():
        if key not in value:
            _add(errors, f"{label}: required field '{key}' is missing")
        elif value[key] != expected_value:
            _add(errors, f"{label}: field '{key}' must equal {expected_value!r}")


def _validate_manifest_version(
    value: dict[str, object], canonical_version: str | None, label: str, errors: list[str]
) -> None:
    version = value.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        _add(errors, f"{label}: 'version' must be a SemVer 2.0.0 string")
    elif canonical_version is not None and version != canonical_version:
        _add(errors, f"{label}: version '{version}' must match SKILL.md metadata.version '{canonical_version}'")


def _validate_local_directory(
    root: Path,
    raw_path: object,
    label: str,
    required_files: tuple[Path, ...],
    errors: list[str],
) -> None:
    if not isinstance(raw_path, str) or not raw_path.startswith("./"):
        _add(errors, f"{label}: path must be a './'-relative string")
        return
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        _add(errors, f"{label}: path escapes repository root: {raw_path}")
        return
    if not candidate.is_dir():
        _add(errors, f"{label}: directory does not exist: {raw_path}")
        return
    for required in required_files:
        if not (candidate / required).is_file():
            _add(errors, f"{label}: source is missing required file: {required}")


def _single_plugin(value: object, label: str, errors: list[str]) -> dict[str, object] | None:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        _add(errors, f"{label}: 'plugins' must contain exactly one object")
        return None
    return value[0]


def _validate_codex_plugin(
    root: Path, value: dict[str, object], canonical_version: str | None, errors: list[str]
) -> None:
    label = str(CODEX_PLUGIN_PATH)
    allowed = set(PLUGIN_COMMON_VALUES) | {"version", "skills", "interface"}
    _validate_fields(value, allowed, label, errors)
    _validate_required_values(value, PLUGIN_COMMON_VALUES, label, errors)
    _validate_manifest_version(value, canonical_version, label, errors)
    _validate_required_values(value, {"skills": "./skills/"}, label, errors)
    _validate_local_directory(
        root, value.get("skills"), f"{label}: skills", (Path(PLUGIN_NAME) / "SKILL.md",), errors
    )

    interface = value.get("interface")
    if not isinstance(interface, dict):
        _add(errors, f"{label}: required 'interface' must be an object")
    else:
        _validate_fields(interface, set(CODEX_INTERFACE), f"{label}: interface", errors)
        _validate_required_values(interface, CODEX_INTERFACE, f"{label}: interface", errors)


def _validate_claude_plugin(
    root: Path, value: dict[str, object], canonical_version: str | None, errors: list[str]
) -> None:
    label = str(CLAUDE_PLUGIN_PATH)
    expected = {
        **PLUGIN_COMMON_VALUES,
        "$schema": CLAUDE_PLUGIN_SCHEMA,
        "displayName": "Rust Safety",
        "skills": "./skills/",
    }
    _validate_fields(value, set(expected) | {"version"}, label, errors)
    _validate_required_values(value, expected, label, errors)
    _validate_manifest_version(value, canonical_version, label, errors)
    _validate_local_directory(
        root, value.get("skills"), f"{label}: skills", (Path(PLUGIN_NAME) / "SKILL.md",), errors
    )


def _validate_codex_marketplace(root: Path, value: dict[str, object], errors: list[str]) -> None:
    label = str(CODEX_MARKETPLACE_PATH)
    _validate_fields(value, {"name", "interface", "plugins"}, label, errors)
    _validate_required_values(value, {"name": PLUGIN_NAME}, label, errors)

    interface = value.get("interface")
    if not isinstance(interface, dict):
        _add(errors, f"{label}: required 'interface' must be an object")
    else:
        _validate_fields(interface, {"displayName"}, f"{label}: interface", errors)
        _validate_required_values(interface, {"displayName": "Rust Safety"}, f"{label}: interface", errors)

    plugin = _single_plugin(value.get("plugins"), label, errors)
    if plugin is None:
        return
    plugin_label = f"{label}: plugin"
    _validate_fields(plugin, {"name", "source", "policy", "category"}, plugin_label, errors)
    _validate_required_values(plugin, {"name": PLUGIN_NAME, "category": "Productivity"}, plugin_label, errors)

    source = plugin.get("source")
    if not isinstance(source, dict):
        _add(errors, f"{plugin_label}: required 'source' must be an object")
    else:
        _validate_fields(source, {"source", "path"}, f"{plugin_label}: source", errors)
        _validate_required_values(source, {"source": "local", "path": "./"}, f"{plugin_label}: source", errors)
        _validate_local_directory(
            root,
            source.get("path"),
            f"{plugin_label}: source.path",
            (CODEX_PLUGIN_PATH, SKILL_PATH / "SKILL.md"),
            errors,
        )

    policy = plugin.get("policy")
    if not isinstance(policy, dict):
        _add(errors, f"{plugin_label}: required 'policy' must be an object")
    else:
        expected_policy = {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
        _validate_fields(policy, set(expected_policy), f"{plugin_label}: policy", errors)
        _validate_required_values(policy, expected_policy, f"{plugin_label}: policy", errors)


def _validate_claude_marketplace(root: Path, value: dict[str, object], errors: list[str]) -> None:
    label = str(CLAUDE_MARKETPLACE_PATH)
    expected = {
        "$schema": CLAUDE_MARKETPLACE_SCHEMA,
        "name": PLUGIN_NAME,
        "description": PLUGIN_DESCRIPTION,
        "owner": PLUGIN_AUTHOR,
    }
    _validate_fields(value, set(expected) | {"plugins"}, label, errors)
    _validate_required_values(value, expected, label, errors)

    plugin = _single_plugin(value.get("plugins"), label, errors)
    if plugin is None:
        return
    plugin_label = f"{label}: plugin"
    _validate_fields(plugin, {"name", "source"}, plugin_label, errors)
    _validate_required_values(plugin, {"name": PLUGIN_NAME, "source": "./"}, plugin_label, errors)
    _validate_local_directory(
        root,
        plugin.get("source"),
        f"{plugin_label}: source",
        (CLAUDE_PLUGIN_PATH, SKILL_PATH / "SKILL.md"),
        errors,
    )


def validate_release_tag(
    version: str | None, errors: list[str], environ: Mapping[str, str] | None = None
) -> None:
    if version is None:
        return
    environment = os.environ if environ is None else environ
    expected = f"v{version}"
    if environment.get("GITHUB_REF_TYPE") == "tag" and environment.get("GITHUB_REF_NAME") != expected:
        actual = environment.get("GITHUB_REF_NAME", "")
        _add(errors, f"GitHub release tag '{actual}' must match canonical version tag '{expected}'")
    gitlab_tag = environment.get("CI_COMMIT_TAG")
    if gitlab_tag and gitlab_tag != expected:
        _add(errors, f"GitLab release tag '{gitlab_tag}' must match canonical version tag '{expected}'")


def validate_plugin_metadata(
    root: Path, skill_fields: dict[str, object], errors: list[str], environ: Mapping[str, str] | None = None
) -> None:
    root = root.resolve()
    metadata = skill_fields.get("metadata")
    version_value = metadata.get("version") if isinstance(metadata, dict) else None
    canonical_version = version_value if isinstance(version_value, str) and SEMVER_RE.fullmatch(version_value) else None

    documents = {
        CODEX_PLUGIN_PATH: _read_json_object(root, CODEX_PLUGIN_PATH, errors),
        CLAUDE_PLUGIN_PATH: _read_json_object(root, CLAUDE_PLUGIN_PATH, errors),
        CODEX_MARKETPLACE_PATH: _read_json_object(root, CODEX_MARKETPLACE_PATH, errors),
        CLAUDE_MARKETPLACE_PATH: _read_json_object(root, CLAUDE_MARKETPLACE_PATH, errors),
    }
    for path, value in documents.items():
        if value is not None:
            _validate_static_manifest(value, str(path), errors)

    codex_plugin = documents[CODEX_PLUGIN_PATH]
    if codex_plugin is not None:
        _validate_codex_plugin(root, codex_plugin, canonical_version, errors)
    claude_plugin = documents[CLAUDE_PLUGIN_PATH]
    if claude_plugin is not None:
        _validate_claude_plugin(root, claude_plugin, canonical_version, errors)
    codex_marketplace = documents[CODEX_MARKETPLACE_PATH]
    if codex_marketplace is not None:
        _validate_codex_marketplace(root, codex_marketplace, errors)
    claude_marketplace = documents[CLAUDE_MARKETPLACE_PATH]
    if claude_marketplace is not None:
        _validate_claude_marketplace(root, claude_marketplace, errors)
    validate_release_tag(canonical_version, errors, environ)


def validate_markdown_links(root: Path, errors: list[str]) -> None:
    root = root.resolve()
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
    root = root.resolve()
    path = root / "evals" / "evals.json"
    if not path.is_file():
        _add(errors, "evals/evals.json: eval definition file is required by repository policy")
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
    skill_root = (root / SKILL_PATH).resolve()
    skill = skill_root / "SKILL.md"
    fields: dict[str, object] = {}
    text = _read_utf8(skill_root, skill, errors) if skill.is_file() else None
    if text is None:
        if not skill.is_file():
            _add(errors, f"{SKILL_PATH}/SKILL.md: missing")
    else:
        fields = validate_frontmatter(skill_root, text, errors)
        validate_skill_size(text, errors)
        validate_all_reference_paths(skill_root, text, errors)

    validate_plugin_metadata(root, fields, errors)
    validate_runtime_components(root, errors)
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
