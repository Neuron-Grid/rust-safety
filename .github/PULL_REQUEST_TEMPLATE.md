## Summary

> **Security-sensitive disclosure:** Do not include undisclosed exploit details, secrets, private infrastructure information, or other material that should be reported privately. Follow `SECURITY.md` and use the repository host's private reporting channel instead.

Describe the rule, reference, documentation, or validation change.

## Scope

- [ ] Core rule in `skills/rust-safety/SKILL.md`
- [ ] Domain-specific reference
- [ ] Documentation/repository metadata
- [ ] Validation/CI

## Safety and compatibility

- [ ] The change distinguishes soundness/security requirements from style or maintainability preferences.
- [ ] It does not unnecessarily require a specific crate, runtime, MSRV increase, Edition change, target change, or feature change.
- [ ] New or changed Rust examples are valid for their stated context.
- [ ] Version-sensitive claims are supported by current official documentation or an explicitly stated version.

## Validation

- [ ] `python3 scripts/validate_skill.py`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] Relevant Rust/toolchain/crate documentation reviewed, when applicable
- [ ] Behavioral evals updated when the change alters observable Skill behavior
- [ ] `CHANGELOG.md` updated for a notable semantic change
