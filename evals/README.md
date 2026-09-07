# Structural and Behavioral evaluations

## Structural eval

Run from the repository root with Python 3.10+:

```bash
python3 "scripts/validate_skill.py"
python3 -m unittest discover -s "tests" -v
```

The validator and its unit tests check frontmatter, supported manifests, metadata,
versions, distribution layout, references, links and the basic schema, IDs and
file references of [evals.json](evals.json). `validate_evals` validates **definitions**;
it does not run an agent. Structural PASS is not evidence of Skill effectiveness.
CI runs these same commands. Grader calibration tests run if Cargo is available;
the Python-only CI environments may skip them. Calibration tests check the grader,
not an agent's ability to repair Rust code.

### Supported static distribution boundary

The supported manifest subset remains the repository's four fixed documents:
`.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`,
`.agents/plugins/marketplace.json`, `.claude-plugin/marketplace.json`.
Their field allowlists and fixed local source/Skill paths reject custom runtime
declarations (including inline objects and custom paths), remote sources and
unsupported fields. They are not general JSON Schema implementations.

At the plugin root and `skills/rust-safety/`, the validator rejects these reserved
component locations even if empty, malformed, or symlinked:

- `hooks/`, `hooks.json`, `.mcp.json`, `.app.json`, `.lsp.json`
- `agents/`, `commands/`, `bin/`, `servers/`, `monitors/`, `settings.json`
- `package.json` together with `bun.lock`, `bun.lockb`, `npm-shrinkwrap.json`,
  or `package-lock.json` (known implicit dependency installation)

It also rejects Skill-root `scripts/`. Within manifest-loaded `skills/`, it rejects executable file modes,
file-leading shebangs (excluding Rust `#![...]` attributes), symlinks, special files
and additional `SKILL.md` files outside the single supported Skill. Reserved names
inside ordinary `references/` examples are not implicit plugin locations. Ordinary
non-executable source samples and Markdown code fences are not classified as runtime.
Root-level `scripts/`, `tests/` and `evals/` are development tooling, not declared
runtime components; their contents are not audited by this check.

Validator checks the currently supported manifests and known implicit runtime
component locations. A PASS does not constitute a security audit of arbitrary
repository contents. It cannot prove the absence of all executable code, code
invoked by an agent following prose instructions, future loader behavior, or Rust
unsoundness. Run against an unchanged checkout; concurrent filesystem mutation is
outside this preflight's boundary.

Location and loading references checked on 2026-09-07:
[Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference),
[OpenAI plugin layouts](https://github.com/openai/plugins/blob/main/README.md),
[Codex manifest specification](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/plugin-json-spec.md).
`servers/` and Skill-root mirrors are conservative repository policy locations;
their presence does not imply every client automatically executes them.

## Behavioral eval

Behavioral evaluation measures the **patch an agent produces** on a real Rust
repository task after loading the Skill. It tests whether the agent discovers and
repairs problems; plausible review prose and Structural PASS earn no patch credit.
Case 1 of [evals.json](evals.json) is the executable patch task below. Cases 2–7
remain legacy qualitative scenarios for MSRV, no-alloc, async locks, allocation,
compatibility and mechanical rewrites; they have no runnable repositories and
must not be counted as measured patch outcomes or evidence of improvement.

### Fixture format and task delivery

[behavioral/ffi-slice](behavioral/ffi-slice/) is a standalone Cargo library with:

- `Cargo.toml`: package, Edition and MSRV constraints, no dependencies;
- `src/lib.rs`: intentionally incomplete API to repair;
- `tests/public_api.rs`: an existing valid caller to preserve;
- `task.md`: the task prompt, without scoring hints.

Use a fresh disposable evaluation environment with Rust/Cargo/Clippy. Copy only
that fixture into the agent's work directory, load `skills/rust-safety/SKILL.md`
and its references, and submit only `task.md` as the task. Do not expose the
grader, rubric, `expected_output`, `assertions` or grader calibration tests to
the solving agent. The initial API is intentionally defective; do not deploy it.

The prompt is: “Review and fix this API for production use without unnecessary
API breakage. Submit a patch to this repository, including appropriate tests and
API documentation.”

Example setup from this repository root (the printed directory is the agent's
working repository):

```bash
eval_work="$(mktemp -d)"
cp -R "evals/behavioral/ffi-slice" "$eval_work/candidate"
printf '%s\n' "$eval_work/candidate"
```

After the agent finishes, retain its diff and run the grader in the isolated
evaluation environment from this repository root:

```bash
python3 "evals/behavioral/grade_patch.py" "$eval_work/candidate"
```

The grader builds/tests a temporary copy and leaves the candidate untouched.
It uses subprocess argument arrays, offline Cargo and per-command timeouts.
It **executes candidate code** and is not a sandbox; Cargo build scripts, tests
and configuration require the same isolation as the agent's repository task.
No model runner, benchmark harness or A/B/C comparison system is included.

### Automatic checks (six Boolean results)

| Result | Evidence |
|---|---|
| `compile` | `cargo check --offline --all-targets` |
| `candidate_tests` | `cargo test --offline` for the agent's tests |
| `unsafe_lints` | Clippy denies implicit unsafe operations, unnecessary unsafe, missing Safety sections and undocumented unsafe blocks |
| `api_compatibility` | Grader-owned downstream test preserves the function call, returned bytes and borrowed pointer identity |
| `null_empty` | Grader-owned test requires `(null, 0)` to return an empty slice |
| `nonnull_empty` | Grader-owned test checks a live non-null pointer with zero length |

The original fixture must fail `null_empty` and `unsafe_lints` while its ordinary
valid-caller tests compile and pass. Test aborts and timeouts count as failures.
The grader returns 0 only if all six checks pass, 1 for check failure, and 2 for
invocation errors. Its output always marks the rubric `NOT_EVALUATED`.
An automatic pass alone is never an overall Behavioral PASS.

### Patch rubric (six independently scored properties)

Each row earns 1 only when the **patch** satisfies every condition in that row;
otherwise 0. Cite source lines and concrete counterexamples, not the agent's
self-reported rationale. Report automatic checks as `/6` and rubric as `/6`
separately; overall PASS requires both 6/6. All soundness rows are mandatory.

| Property | Full-credit requirements |
|---|---|
| Lifetime soundness | Allocation remains live and immutable for the entire inferred returned `'a`, not just the call. Retaining a caller-chosen lifetime in an `unsafe fn` is acceptable with explicit caller obligations; raw inputs must not become an unchecked safe API. No manufactured `'static` or dangling return. |
| Caller safety contract | `# Safety` and local proof cover non-nullness for nonempty buffers, alignment, initialized valid elements, provenance, a single live allocation and aliasing/no mutation for the borrow. Distinguish what code checks from what the caller must guarantee. |
| Size and overflow | Cover `len * size_of::<T>() <= isize::MAX` and non-wrapping address range. For this `u8` API element size is 1; do not demand meaningless multiplication checks. Caller preconditions are acceptable at this unsafe boundary; any advertised checked rejection must occur before the unsafe operation. Do not invoke out-of-contract invalid pointers in ordinary tests. |
| Unsafe necessity | Keep unsafe only around operations that require it, with an accurate proof. Empty results require no raw slice construction. Do not suppress lints to gain credit. |
| Compatibility | Preserve package name, Edition, MSRV, valid caller behavior and borrowing. No unnecessary signature change, allocation/copy, new dependency, feature removal or deleted tests. The downstream smoke test is not a full compatibility proof. |
| No new unsoundness | Review all changed code, not only the named helper: no invalid references, premature free, pointer provenance loss, ownership errors or contract/implementation mismatch. Boundary tests must validate the advertised behavior and must not simply avoid the bug. |

Optional supplementary checks in the candidate directory:

```bash
cargo fmt --check
cargo miri test
```

Miri requires a supporting toolchain/component. Dynamic checks cover executed
paths, not every lifetime or aliasing obligation. MSRV preservation needs a
matching compiler or manual API inspection; a current-compiler PASS is insufficient.
Record model/version, Skill commit/diff, prompt, toolchain, submitted patch,
command results and row-by-row rubric evidence with each evaluation. No agent
effectiveness result is claimed by merely adding or calibrating this fixture.
