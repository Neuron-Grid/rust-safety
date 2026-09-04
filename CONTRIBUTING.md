# Contributing

Contributions are welcome when they improve correctness, coverage, portability, or maintainability without turning project-specific preferences into universal Rust safety rules.

Before contributing, also review [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security-sensitive reports, undisclosed exploit details, and secrets must follow [SECURITY.md](SECURITY.md) rather than a normal public issue or pull/merge request.

## Scope

Changes should normally fit one of these categories:

- Correct an inaccurate or outdated Rust/API statement.
- Improve a safety contract, invariant, or review procedure.
- Add coverage for a Rust domain that is broadly reusable.
- Reduce ambiguity, duplication, or unnecessary context usage.
- Improve validation, documentation, or cross-client usability.

## Design rules

When changing the Skill:

1. Preserve the distinction between **soundness**, **security**, **reliability**, and **maintainability**.
2. Do not mandate a crate, runtime, error library, logging stack, or project layout unless the rule truly requires it.
3. Prefer language- and standard-library-level guidance over version-sensitive third-party APIs.
4. If third-party APIs are necessary, avoid unqualified claims such as "current" or "always" unless the statement is intentionally versioned.
5. Keep `skills/rust-safety/SKILL.md` focused on universally applicable behavior and move domain-specific detail into `skills/rust-safety/references/`.
6. Treat `unsafe` as a proof obligation rather than a keyword blacklist.
7. Preserve existing repository constraints such as MSRV, Edition, targets, features, `no_std`, public API, and CI policy.

## Code examples

Rust examples should be valid for their stated context. If an example intentionally omits surrounding code, make that clear.

For version-sensitive examples, include enough context to identify the relevant crate/toolchain assumptions. Avoid examples that require unnecessary dependencies.

## Validation

Before opening a pull/merge request, run:

```bash
python3 "scripts/validate_skill.py"
python3 -m unittest discover -s "tests" -v
```

If available, also run the official Agent Skills validator:

```bash
skills-ref validate "skills/rust-safety"
```

Review the changed guidance against the relevant Rust or crate documentation when the change depends on current behavior.

## Pull / merge requests

Keep each change focused. The description should state:

- what rule or reference changed;
- why the previous behavior was incomplete or incorrect;
- whether the change affects all Rust projects or only a specific reference;
- how the change was validated.

Breaking semantic changes to core rules should also update `CHANGELOG.md`.
