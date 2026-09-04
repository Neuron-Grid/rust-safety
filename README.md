# rust-safety

[English](README_EN.md)

`rust-safety` は、Rustコードの生成・修正・レビュー・リファクタリング・監査で、安全性と正しさを維持するための **Agent Skill** です。

特定のフレームワークやアプリ種別に固定せず、library、CLI、server、embedded / `no_std`、WebAssembly、proc macro、FFI、async/concurrency、unsafe systems code を同じSkillから扱えるように設計しています。

## 特徴

- **全Rustプロジェクト共通のコアルール**と、用途別referenceを分離
- repositoryの **Edition / MSRV / target / feature / `std`・`alloc`・`no_std` / public API / CI** を優先
- safe Rustを既定値にしつつ、FFI・allocator・HAL・kernel等で必要な `unsafe` は証明責務付きで許容
- `checked_*`、特定crate、固定行数上限などを普遍的な安全要件として強制しない
- input validation、panic、integer conversion、ownership、secret、concurrency、ABI、unsafe invariantを横断的に扱う
- Agent Skillsのprogressive disclosureを前提に、詳細を `references/` へ分割

## 対象

このSkillは、以下を含むRustプロジェクトで利用できます。

| 領域 | Reference |
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

複数領域に該当するプロジェクトでは、referenceを排他的に選ぶのではなく**重ねて適用**します。

## ディレクトリ構成

```text
rust-safety/
├── SKILL.md
├── references/
│   ├── async-concurrency.md
│   ├── binary.md
│   ├── embedded.md
│   ├── ffi.md
│   ├── library.md
│   ├── proc-macro.md
│   ├── server.md
│   ├── unsafe-systems.md
│   └── wasm.md
├── scripts/
│   └── validate_skill.py
├── tests/
│   └── test_validate_skill.py
├── evals/
│   ├── evals.json
│   └── README.md
├── README.md
├── README_EN.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
└── LICENSE
```

## インストール

このrepositoryは、cloneしたdirectory自体がSkill directoryになる構成です。

```bash
git clone <repository-url> rust-safety
```

その後、利用するAgent/CLIが読み込むSkill directoryへ配置してください。具体的な配置先やinstallation mechanismは各clientの仕様に従ってください。

Agent Skills互換clientでは、少なくとも `SKILL.md` とそこから参照される `references/` が同じSkill directory内に存在する必要があります。

## Skillの適用方針

`SKILL.md` は最初に既存repositoryの制約を確認し、変更対象に応じて必要なreferenceだけを追加で読む構成です。

中心となる考え方は次のとおりです。

1. **既存制約を保持する** — MSRV、Edition、target、feature、API、CI等を安全性の名目で勝手に変更しない。
2. **unsafeを証明責務として扱う** — 一律禁止ではなく、Safety contract、proof、boundary、validationを要求する。
3. **非信頼入力を境界で検証する** — size、offset、encoding、numeric range、pointer validity等を入力境界で検査する。
4. **security / soundness / reliability / maintainabilityを区別する** — 保守性上の好みをmemory-safety要件として扱わない。
5. **対象環境に応じて検証する** — host test、cross target、Miri、sanitizer、fuzzing等を機械的に全適用しない。

## Validation

repository付属のvalidatorは外部Python packageを必要としない **repository-local preflight validator** です。Agent Skills frontmatterの許可フィールド・型制約と、このrepository固有の配布整合性を検査します。

```bash
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests -v
```

以下を確認します。

- `SKILL.md` frontmatterの許可フィールド、型、重複key、`metadata` string→string制約
- Skill directory名と `name` の一致、命名規則、`description` / `compatibility` 長
- repository方針としてのMIT-only license整合性
- `SKILL.md` の推奨500行上限
- `references/*.md` の存在と、`SKILL.md` 内reference pathの `references/...` 統一
- `evals/evals.json` の基本schema・ID重複・file reference
- repository内Markdownの相対link切れ
- text fileの末尾改行と `__MACOSX` / AppleDouble混入

Agent Skills公式reference validatorが利用可能な環境では、追加で次も実行できます。

```bash
skills-ref validate .
```

仕様: <https://agentskills.io/specification>

## Behavioral evals

構造検証とは別に、[evals/evals.json](evals/evals.json) にSkillの実際の振る舞いを確認する評価ケースを収録しています。FFI、MSRV、`no_std`、async mutex、非信頼length、SemVer、過剰な `checked_*` 強制を対象に、Skillあり/なしまたは旧版との比較評価を行うためのものです。実行方法は [evals/README.md](evals/README.md) を参照してください。

## CI

同じvalidatorを以下で実行します。

- GitHub Actions: `.github/workflows/validate.yml`
- GitLab CI: `.gitlab-ci.yml`

Skill自体はruntime dependencyを持たず、CI用validatorとunit testもPython標準ライブラリのみを使用します。

## Contributing

変更方針とreview基準は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

特に、安全性に関する断定やcrate/API固有の記述を追加する場合は、現行仕様・公式documentation・実際にcompile可能なexampleを優先してください。

## Security

脆弱性やsoundness上の問題を発見した場合は、公開issueへexploit詳細を投稿する前に [SECURITY.md](SECURITY.md) を確認してください。

## License

[MIT License](LICENSE) で提供します。
