# Changelog

All notable changes to this project will be documented in this file.

The project follows Semantic Versioning for published releases where practical.

## [Unreleased]

## [0.1.0] - 2026-09-05

### Added

- Universal Rust safety and correctness core rules.
- Composable references for libraries, binaries, servers, embedded/`no_std`, WebAssembly, proc macros/build scripts, FFI, unsafe systems code, and async/concurrency.
- Codex and Claude Code Plugin manifests and repository Marketplace catalogs.
- Public repository documentation for GitHub and GitLab.
- Dependency-free Skill validation script.
- Unit tests for the repository-local Skill validator.
- Behavioral evaluations in `evals/evals.json` covering FFI, MSRV, `no_std`, async locking, untrusted allocation sizes, SemVer compatibility, and blanket arithmetic/error rewrites.
- GitHub Actions and GitLab CI validation.
- Contribution, security, code-of-conduct, issue, and pull/merge-request templates.

### Changed

- Reworked project-specific hard rules into environment-aware guidance.
- Replaced blanket `unsafe`, integer arithmetic, source length, and dependency mandates with proof- and context-based rules.
- Moved the canonical Skill and references under `skills/rust-safety/` for Codex and Claude Code Plugin compatibility.
- Standardized Skill and reference cross-links on skill-root-relative `references/...` paths, with traversal/missing-target validation.
- Strengthened frontmatter, eval, license, reference-path, archive-hygiene, Marketplace, version, repository-policy, and metadata validation, and expanded validator regression tests.
- Expanded GitHub/GitLab security disclosure guidance, pull/merge-request security routing, and Code of Conduct reporting/enforcement procedures.
- Added security-routing warnings to GitHub and GitLab safety-correction templates.
- Corrected `transmute` alignment guidance to distinguish by-value alignment from pointed-to alignment requirements.
- Changed the project license from dual MIT/Apache-2.0 to MIT-only.
