# rust-safety

[日本語](README.md)

`rust-safety` is an **Agent Skill** for generating, modifying, reviewing, refactoring, and auditing Rust code while preserving safety and correctness.

It is intentionally project-agnostic and supports libraries, binaries, servers, embedded / `no_std`, WebAssembly, procedural macros, FFI, async/concurrent code, and unsafe systems code through one composable skill. Codex and Claude Code plugins load the same canonical `skills/rust-safety/` directory.

## Highlights

- Common rules for every Rust project plus focused, composable references
- Preserves the repository's Edition, MSRV, targets, features, `std` / `alloc` / `no_std` model, public API, dependency policy, and CI constraints
- Safe Rust by default without mechanically banning justified `unsafe`
- Treats unsafe code as a proof obligation with explicit safety contracts and narrow boundaries
- Avoids universal mandates such as "all arithmetic must use `checked_*`", "one error crate is mandatory", or fixed source-file length limits
- Covers input validation, panic behavior, conversions, ownership, secrets, concurrency, ABI boundaries, and unsafe invariants
- Uses progressive disclosure: detailed rules live under `skills/rust-safety/references/` and are loaded only when relevant
- Includes Marketplace metadata for Codex and Claude Code

## Coverage

This skill supports Rust projects in the following areas.

| Area | Reference |
|---|---|
| library / shared API | `skills/rust-safety/references/library.md` |
| CLI / desktop / batch / daemon | `skills/rust-safety/references/binary.md` |
| HTTP / gRPC / RPC / long-running service | `skills/rust-safety/references/server.md` |
| embedded / firmware / `no_std` / HAL / PAC | `skills/rust-safety/references/embedded.md` |
| WebAssembly / WASI | `skills/rust-safety/references/wasm.md` |
| proc macro / `build.rs` | `skills/rust-safety/references/proc-macro.md` |
| C/C++ / OS API / external ABI / FFI | `skills/rust-safety/references/ffi.md` |
| raw pointer / allocator / `MaybeUninit` / `Pin` / unsafe trait | `skills/rust-safety/references/unsafe-systems.md` |
| async / thread / channel / lock / atomic | `skills/rust-safety/references/async-concurrency.md` |

References are composable rather than mutually exclusive.

## Directory layout

```text
rust-safety/
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── .codex-plugin/
│   └── plugin.json
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── skills/
│   └── rust-safety/
│       ├── SKILL.md
│       └── references/
│           ├── async-concurrency.md
│           ├── binary.md
│           ├── embedded.md
│           ├── ffi.md
│           ├── library.md
│           ├── proc-macro.md
│           ├── server.md
│           ├── unsafe-systems.md
│           └── wasm.md
├── evals/
├── scripts/
└── tests/
```

`skills/rust-safety/SKILL.md` and its adjacent `references/` directory are the canonical skill source. There are no separate copies for Codex, Claude Code, or standalone clients.

## Install in Codex

Add the repository Marketplace, then install the plugin:

```bash
codex plugin marketplace add Neuron-Grid/rust-safety --ref main
codex plugin add rust-safety@rust-safety
```

For interactive installation:

```text
codex
/plugins
Select rust-safety and install it
/new or start a new Codex session
```

Use `$rust-safety` to invoke the skill explicitly.

### Update in Codex

Refresh the Marketplace catalog, then reinstall the plugin from the refreshed catalog:

```bash
codex plugin marketplace upgrade rust-safety
codex plugin add rust-safety@rust-safety
```

`marketplace upgrade` only refreshes the catalog snapshot; it does not replace the loaded plugin. After `plugin add`, start a new session because the current session continues to use its loaded version. Continuous automatic updates of third-party plugins are not guaranteed for personal Codex CLI installations.

For a ChatGPT workspace, an administrator can import `https://github.com/Neuron-Grid/rust-safety` as a Marketplace. Selecting the `main` branch tracks future commits, and daily sync is the default for a newly imported Marketplace. Use `Admin > Plugins > Marketplaces > Sync now` for an immediate sync. An import pinned to a tag or commit SHA remains on that revision and does not automatically follow later releases. See [OpenAI Plugin management](https://learn.chatgpt.com/docs/enterprise/plugin-management).

## Install in Claude Code

Add the repository Marketplace, then install the plugin:

```bash
claude plugin marketplace add Neuron-Grid/rust-safety
claude plugin install rust-safety@rust-safety
```

Use `/rust-safety:rust-safety` to invoke the skill explicitly.

### Update in Claude Code

Update the Marketplace catalog and the installed plugin in order:

```bash
claude plugin marketplace update rust-safety
claude plugin update rust-safety@rust-safety
```

After the update notification, load the new version into the current session with:

```text
/reload-plugins
```

Automatic updates are disabled by default for third-party Marketplaces. Open `/plugin`, select `Marketplaces`, select `rust-safety`, then select `Enable auto-update`. After a session starts, auto-update refreshes the Marketplace and installed plugin on disk with a randomized delay of up to ten minutes. The current session continues using its loaded version, so run `/reload-plugins` or start a new session. See [Claude Code plugin discovery](https://code.claude.com/docs/en/discover-plugins).

## Standalone Agent Skills clients

Clone the repository, then configure the client to use `skills/rust-safety/` as the skill directory:

```bash
git clone "https://github.com/Neuron-Grid/rust-safety.git" "rust-safety"
```

An Agent Skills-compatible client must treat `rust-safety/skills/rust-safety/SKILL.md` and its referenced `rust-safety/skills/rust-safety/references/` directory as one skill directory. Installation paths and discovery mechanisms are client-specific.

## Versions and update tracking

- The canonical release version is `metadata.version` in `skills/rust-safety/SKILL.md`.
- `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` carry the same version, and the repository validator rejects mismatches.
- Release tags use `v<SemVer>`. The initial Marketplace release is `v0.1.0`.
- A Marketplace registration that follows the default branch receives future commits from the current default branch, `main`.
- To pin a release, use `--ref v0.1.0` with Codex or a source such as `Neuron-Grid/rust-safety@v0.1.0` with Claude Code.
- A Marketplace registration pinned to a tag does not automatically move to later tags. Commit-SHA pinning is available through paths that accept a SHA, such as ChatGPT workspace imports.
- Published version contents are not replaced. Changes require updating all three version fields and creating a new tag.

Registering this GitHub repository as a Marketplace does not automatically publish it in a central directory operated by OpenAI or Anthropic. Central-directory publication requires each provider's separate submission process.

## Skill behavior

`SKILL.md` first inspects the target repository's constraints and loads only the references relevant to the requested change.

1. **Preserve existing constraints** — Do not change the MSRV, Edition, targets, features, APIs, or CI merely in the name of safety.
2. **Treat unsafe code as a proof obligation** — Require a safety contract, proof, narrow boundary, and validation instead of banning it universally.
3. **Validate untrusted input at the boundary** — Check sizes, offsets, encodings, numeric ranges, and pointer validity where data enters the trust boundary.
4. **Separate security, soundness, reliability, and maintainability** — Do not present maintainability preferences as memory-safety requirements.
5. **Validate for the target environment** — Do not mechanically apply host tests, cross-target builds, Miri, sanitizers, or fuzzing to every project.

## Structural validation

The dependency-free **repository-local preflight validator** checks Agent Skills frontmatter and this repository's Plugin and Marketplace distribution invariants.

```bash
python3 "scripts/validate_skill.py"
python3 -m unittest discover -s "tests" -v
```

It validates:

- Allowed `SKILL.md` frontmatter fields and types, duplicate keys, and metadata string mappings
- Skill directory/name consistency, naming rules, and `description` / `compatibility` lengths
- SemVer consistency between the skill and plugin manifests
- Codex and Claude Code manifests and Marketplace source paths
- Rejection of runtime declarations and remote sources in supported manifests, and known implicit runtime locations
- Hooks, MCP/app/LSP configuration, agents, commands, bin, servers, monitors and settings at the plugin/Skill roots, plus implicit dependency installation through a package manifest and lockfile
- Rejection of scripts locations, executable modes, shebangs, symlinks and additional Skills within distributed `skills/`
- The repository's MIT-only license policy
- The recommended 500-line `SKILL.md` limit
- Existing `references/*.md` files and canonical `references/...` paths in `SKILL.md`
- The basic `evals/evals.json` schema, unique IDs, and file references
- Relative Markdown links throughout the repository
- Final newlines and common `__MACOSX` / AppleDouble archive metadata
- Agreement between a `v<SemVer>` CI tag and the canonical version

Validator checks the currently supported manifests and known implicit runtime component locations. A PASS does not constitute a security audit of arbitrary repository contents or prove the absence of all executable code. Ordinary references and non-executable source samples are not classified as runtime components. See [evals/README.md](evals/README.md#supported-static-distribution-boundary) for exact paths, the development-tooling boundary and supported specifications.

These are Structural evals. Passing an eval definition's schema does not demonstrate improved agent behavior or the soundness of a Rust patch.

If the official Agent Skills reference validator is available, also run:

```bash
skills-ref validate "skills/rust-safety"
```

Specification: <https://agentskills.io/specification>

## Behavioral evals

Case 1 in [evals/evals.json](evals/evals.json) is an [FFI fixture](evals/behavioral/ffi-slice/) that grades an agent's patch to a real Rust repository. Its task prompt omits scoring hints. Automatic compile, test, compatibility, empty-buffer and unsafe-lint checks are separate from the rubric for lifetimes, caller contracts, size conditions and newly introduced unsoundness. Existing cases 2–7 remain qualitative supporting scenarios and are not counted as measured patch outcomes.

See [evals/README.md](evals/README.md#behavioral-eval) for execution and scoring. Grader calibration is not evidence of Skill effectiveness. No agent improvement or comparative experiment result is claimed yet.

## CI

The same validation runs in:

- GitHub Actions: `.github/workflows/validate.yml`
- GitLab CI: `.gitlab-ci.yml`

Branches, pull/merge requests, and `v<SemVer>` tags run the unit tests and validator. The skill has no runtime dependencies; the validator and Python tests use only the standard library. Executing the Behavioral grader requires Rust/Cargo/Clippy; grader execution calibration tests are skipped when Cargo is unavailable. CI does not run an agent on Behavioral tasks.

## Distribution security

The supported plugin manifests declare static skill documents and metadata. The validator also rejects known implicit runtime locations. No declaration invokes the development validator, tests or evals during installation or plugin loading. PASS is limited to the static checks above; it does not guarantee the safety of arbitrary repository contents or code an agent runs by following document instructions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes that make safety claims or introduce crate/API-specific guidance should be grounded in current specifications or official documentation, and code examples should be compile-valid for their stated environment.

## Security

For vulnerability or soundness reports, see [SECURITY.md](SECURITY.md) before publishing exploit details in a public issue.

## License

Licensed under the [MIT License](LICENSE).
