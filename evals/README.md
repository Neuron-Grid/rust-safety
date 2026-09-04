# Behavioral evaluations

`evals/evals.json` contains behavioral test cases for the `rust-safety` Skill using the format documented by Agent Skills.

The cases target failure modes that structural validation cannot detect: unsafe FFI contracts, MSRV preservation, `no_std` preservation, async-lock overgeneralization, attacker-controlled allocation, public API compatibility, and blanket `checked_*` / `unwrap` rewrites.

## Running an evaluation

For each case, run the same prompt in a clean context:

1. **with skill** — load this `rust-safety` Skill;
2. **baseline** — run without the Skill, or against the previous released Skill version;
3. grade every assertion using concrete evidence from the output;
4. compare pass rate and qualitative regressions between the two runs.

The repository validator checks the structure and file references of `evals/evals.json`; it does not claim to execute an LLM or prove behavioral quality by itself.

Agent Skills evaluation guidance: <https://agentskills.io/skill-creation/evaluating-skills>
