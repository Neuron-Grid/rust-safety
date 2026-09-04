# rust-safety

[日本語](README.md)

`rust-safety` is an **Agent Skill** for generating, modifying, reviewing, refactoring, and auditing Rust code while preserving safety and correctness.

It is intentionally project-agnostic and supports libraries, binaries, servers, embedded / `no_std`, WebAssembly, procedural macros, FFI, async/concurrent code, and unsafe systems code through one composable skill.

## Highlights

- Common rules for every Rust project plus focused, composable references
- Preserves the repository's Edition, MSRV, targets, features, `std` / `alloc` / `no_std` model, public API, dependency policy, and CI constraints
- Safe Rust by default without mechanically banning justified `unsafe`
- Treats unsafe code as a proof obligation with explicit safety contracts and narrow boundaries
- Avoids universal mandates such as "all arithmetic must use `checked_*`", "one error crate is mandatory", or fixed source-file length limits
- Covers input validation, panic behavior, conversions, ownership, secrets, concurrency, ABI boundaries, and unsafe invariants
- Uses progressive disclosure: detailed rules live under `references/` and are loaded only when relevant

## Coverage

| Area | Reference |
|---|---|
| library / shared API | `references/library.md` |
| CLI / desktop / batch / daemon | `references/binary.md` |
| HTTP / gRPC / RPC / long-running service | `references/server.md` |
| embedded / firmware / `no_std` / HAL / PAC | `references/embedded.md` |
| WebAssembly / WASI | `references/wasm.md` |
| proc macro / `build.rs` | `references/proc-macro.md` |
| C/C++ / OS API / external ABI / FFI | `references/ffi.md` |
| raw pointer / allocator / `MaybeUninit` / `Pin` / unsafe trait | `references/unsafe-systems.md` |
| async / thread / channel / lock / atomic | `references/async-concurrency.md` |

References are composable rather than mutually exclusive.

## Installation

The repository root is itself the skill directory:

```bash
git clone <repository-url> rust-safety
```

Place the cloned directory in the skill location used by your Agent/CLI. Installation paths and discovery mechanisms are client-specific.

For Agent Skills-compatible clients, keep `SKILL.md` and its referenced `references/` directory together.

## Validation

Run the dependency-free **repository-local preflight validator** and its unit tests:

```bash
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests -v
```

It validates the allowed Agent Skills frontmatter fields and value types, duplicate keys, metadata string mappings, directory/name consistency, length constraints, the repository MIT-only license policy, the recommended 500-line limit, canonical `references/...` paths, behavioral-eval structure, relative Markdown links, final newlines, and common macOS archive metadata.

If the official Agent Skills reference validator is available in your environment, you can additionally run:

```bash
skills-ref validate .
```

Specification: <https://agentskills.io/specification>

## Behavioral evals

Behavioral cases are defined in [evals/evals.json](evals/evals.json). They cover FFI contracts, MSRV and `no_std` preservation, async mutex overgeneralization, untrusted allocation sizes, public API compatibility, and blanket `checked_*` / `unwrap` rewrites. See [evals/README.md](evals/README.md) for the with-skill/baseline workflow.

## CI

The same local validation is run by:

- GitHub Actions: `.github/workflows/validate.yml`
- GitLab CI: `.gitlab-ci.yml`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes that make safety claims or introduce crate/API-specific guidance should be grounded in current specifications or official documentation, and code examples should be compile-valid for their stated environment.

## Security

For vulnerability or soundness reports, see [SECURITY.md](SECURITY.md) before publishing exploit details in a public issue.

## License

Licensed under the [MIT License](LICENSE).
