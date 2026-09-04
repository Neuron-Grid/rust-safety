## Summary

> **Security-sensitive disclosure:** Do not include undisclosed exploit details, secrets, private infrastructure information, or other material that should be reported privately. Follow `SECURITY.md` and use the repository host's private reporting channel instead.

Describe the rule, reference, documentation, or validation change.

## Safety and compatibility checklist

- [ ] Soundness/security requirements are distinguished from style/maintainability preferences.
- [ ] No unnecessary crate/runtime/MSRV/Edition/target/feature mandate was introduced.
- [ ] Rust examples are valid for their stated context.
- [ ] Version-sensitive claims are supported by current official documentation or an explicit version.
- [ ] `python3 scripts/validate_skill.py` passes.
- [ ] `python3 -m unittest discover -s tests -v` passes.
- [ ] Behavioral evals are updated when observable Skill behavior changes.
- [ ] `CHANGELOG.md` is updated for notable semantic changes.
