# rust-safety

[English](README_EN.md)

`rust-safety` は、Rustコードの生成・修正・レビュー・リファクタリング・監査で、安全性と正しさを維持するための **Agent Skill** です。

特定のフレームワークやアプリ種別に固定せず、library、CLI、server、embedded / `no_std`、WebAssembly、proc macro、FFI、async/concurrency、unsafe systems code を同じSkillから扱えるように設計しています。Codex PluginとClaude Code Pluginの両方から、同じ `skills/rust-safety/` を読み込みます。

## 特徴

- **全Rustプロジェクト共通のコアルール**と、用途別referenceを分離
- repositoryの **Edition / MSRV / target / feature / `std`・`alloc`・`no_std` / public API / CI** を優先
- safe Rustを既定値にしつつ、FFI・allocator・HAL・kernel等で必要な `unsafe` は証明責務付きで許容
- `checked_*`、特定crate、固定行数上限などを普遍的な安全要件として強制しない
- input validation、panic、integer conversion、ownership、secret、concurrency、ABI、unsafe invariantを横断的に扱う
- Agent Skillsのprogressive disclosureを前提に、詳細を `skills/rust-safety/references/` へ分割
- CodexとClaude Code向けのMarketplace metadataを同梱

## 対象

このSkillは、以下を含むRustプロジェクトで利用できます。

| 領域 | Reference |
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

複数領域に該当するプロジェクトでは、referenceを排他的に選ぶのではなく重ねて適用します。

## ディレクトリ構成

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

`skills/rust-safety/SKILL.md` と同directoryの `references/` がSkillの正本です。Codex用、Claude Code用、standalone client用のコピーは作成しません。

## Codexへのインストール

repository Marketplaceを登録し、Pluginをインストールします。

```bash
codex plugin marketplace add Neuron-Grid/rust-safety --ref main
codex plugin add rust-safety@rust-safety
```

対話型UIでは次の順序で操作します。

```text
codex
/plugins
rust-safety を選択して install
/new または新しい Codex session を開始
```

明示的にSkillを指定する場合は `$rust-safety` を使用します。

### Codexでの更新

Marketplace catalogを更新した後、更新済みcatalogからPluginを再インストールします。

```bash
codex plugin marketplace upgrade rust-safety
codex plugin add rust-safety@rust-safety
```

`marketplace upgrade` はcatalog snapshotだけを更新し、読み込み済みPluginは置き換えません。`plugin add` 後も実行中sessionには旧版が読み込まれているため、新しいsessionを開始します。個人用Codex CLIでthird-party Pluginの継続的な自動更新は保証されません。

ChatGPT workspaceでは、管理者がGitHub repository URL `https://github.com/Neuron-Grid/rust-safety` をMarketplaceとしてimportできます。branchを `main` にすると将来のcommitを追跡し、新規Marketplaceではdaily syncが既定です。即時反映は `Admin > Plugins > Marketplaces > Sync now` を使用します。tagまたはcommit SHAを指定したimportは固定revisionとなり、後続releaseを自動追跡しません。詳細は [OpenAI Plugin management](https://learn.chatgpt.com/docs/enterprise/plugin-management) を参照してください。

## Claude Codeへのインストール

repository Marketplaceを登録し、Pluginをインストールします。

```bash
claude plugin marketplace add Neuron-Grid/rust-safety
claude plugin install rust-safety@rust-safety
```

明示的にSkillを指定する場合は `/rust-safety:rust-safety` を使用します。

### Claude Codeでの更新

Marketplace catalogとインストール済みPluginを順番に更新します。

```bash
claude plugin marketplace update rust-safety
claude plugin update rust-safety@rust-safety
```

実行中sessionへ反映するには、更新通知後に次を実行します。

```text
/reload-plugins
```

third-party Marketplaceのauto-updateは既定で無効です。`/plugin` を開き、`Marketplaces`、`rust-safety`、`Enable auto-update` の順で有効化します。auto-updateはsession開始後、最大10分のランダムな遅延を伴ってMarketplaceとインストール済みPluginをディスク上で更新します。現在のsessionは読み込み済みの版を使い続けるため、`/reload-plugins` または新しいsessionが必要です。詳細は [Claude Code plugin discovery](https://code.claude.com/docs/en/discover-plugins) を参照してください。

## standalone Agent Skills client

repositoryをcloneし、clientのSkill directoryまたは設定に `skills/rust-safety/` を指定します。

```bash
git clone "https://github.com/Neuron-Grid/rust-safety.git" "rust-safety"
```

Agent Skills互換clientでは、`rust-safety/skills/rust-safety/SKILL.md` とそこから参照される `rust-safety/skills/rust-safety/references/` を同じSkill directoryとして扱う必要があります。配置先とdiscovery mechanismは各clientの仕様に従ってください。

## Versionと更新追跡

- release versionの正本は `skills/rust-safety/SKILL.md` の `metadata.version` です。
- `.codex-plugin/plugin.json` と `.claude-plugin/plugin.json` は同じversionを持ち、repository validatorが不一致を拒否します。
- release tagは `v<SemVer>` 形式です。初回Marketplace releaseは `v0.1.0` です。
- default branchを追跡するMarketplace登録は、現在のdefault branch `main` の将来のcommitを取得できます。
- 固定版が必要な場合、Codexでは `--ref v0.1.0`、Claude Codeでは `Neuron-Grid/rust-safety@v0.1.0` のようにtagを指定します。
- tagで固定したMarketplace登録は、後続tagへ自動移行しません。commit SHA固定はChatGPT workspace importなど、clientがSHA指定を提供する経路で利用します。
- release済みversionの内容は差し替えず、変更時は三つのversionを更新して新しいtagを作成します。

GitHub repositoryをMarketplaceとして登録しても、OpenAIまたはAnthropicが運営する中央公開directoryへ自動掲載されるわけではありません。中央directoryへの掲載には、各providerの別途submission processが必要です。

## Skillの適用方針

`SKILL.md` は最初に既存repositoryの制約を確認し、変更対象に応じて必要なreferenceだけを追加で読む構成です。

1. **既存制約を保持する** — MSRV、Edition、target、feature、API、CI等を安全性の名目で勝手に変更しない。
2. **unsafeを証明責務として扱う** — 一律禁止ではなく、Safety contract、proof、boundary、validationを要求する。
3. **非信頼入力を境界で検証する** — size、offset、encoding、numeric range、pointer validity等を入力境界で検査する。
4. **security / soundness / reliability / maintainabilityを区別する** — 保守性上の好みをmemory-safety要件として扱わない。
5. **対象環境に応じて検証する** — host test、cross target、Miri、sanitizer、fuzzing等を機械的に全適用しない。
6. **resource exhaustionを防ぎ、性能目的の複雑化は実測で判断する** — 入力規模に応じたresource制御と不要なallocation/copyを確認し、複雑な最適化はrelease相当の条件で必要性を確認する。妥当なclone/collectや単純な冗長処理の除去を妨げず、性能保証や全変更へのbenchmark義務化はしない。

## Structural validation

repository付属のvalidatorは外部Python packageを必要としない **repository-local preflight validator** です。Agent Skills frontmatterと、このrepository固有のPlugin・Marketplace配布整合性を検査します。

```bash
python3 "scripts/validate_skill.py"
python3 -m unittest discover -s "tests" -v
```

以下を確認します。

- `SKILL.md` frontmatterの許可フィールド、型、重複key、`metadata` string→string制約
- Skill directory名と `name` の一致、命名規則、`description` / `compatibility` 長
- SkillとPlugin manifestのSemVer一致
- Codex / Claude Code manifestとMarketplace source pathの整合性
- サポート対象manifest内のruntime宣言・remote sourceと、既知の暗黙runtime配置の拒否
- Plugin root / Skill rootのhooks、MCP・app・LSP設定、agents、commands、bin、servers、monitors、settings、およびpackage manifest＋lockfileによる暗黙の依存インストール
- 配布対象 `skills/` 内のscripts配置・実行権限・shebang・symlink・追加Skillの拒否
- repository方針としてのMIT-only license整合性
- `SKILL.md` の推奨500行上限
- `references/*.md` の存在と、`SKILL.md` 内reference pathの `references/...` 統一
- `evals/evals.json` の基本schema・ID重複・file reference
- repository内Markdownの相対link切れ
- text fileの末尾改行と `__MACOSX` / AppleDouble混入
- tag pipelineで `v<SemVer>` とcanonical versionが一致すること

validatorは現在サポートする4種類のmanifestと、既知の暗黙runtime component配置を静的に検査します。PASSは任意のrepository contentsに対するsecurity auditではなく、あらゆる実行可能コードの不在を証明しません。通常のreference・非実行sample codeはruntime扱いしません。検査対象path、開発用toolingとの境界、サポート対象仕様は [evals/README.md](evals/README.md#supported-static-distribution-boundary) に記載しています。

これらはStructural evalです。eval定義のschemaがPASSしても、Agentの行動改善やRust patchのsoundnessを保証しません。

Agent Skills公式reference validatorが利用可能な環境では、追加で次も実行できます。

```bash
skills-ref validate "skills/rust-safety"
```

仕様: <https://agentskills.io/specification>

## Behavioral evals

[evals/evals.json](evals/evals.json) のcase 1は、実際のRust repositoryにAgentが提出したpatchを採点する [FFI fixture](evals/behavioral/ffi-slice/) です。問題文から採点のヒントを除き、compile・test・互換性・空buffer・unsafe lintの自動チェックと、lifetime・caller contract・サイズ条件・新たなunsoundnessのrubricを分離しています。case 2–7の既存シナリオは定性的な補助素材として維持し、測定済みpatch評価には数えません。

実行手順と採点基準は [evals/README.md](evals/README.md#behavioral-eval) を参照してください。graderの校正はSkillの有効性評価ではありません。Agentによる改善実績や比較実験の結果はまだ主張しません。

case 8–10は、不要なcopyと必要な所有権・materializationの区別、複雑な最適化前の実測、batch処理のresource増大を扱う定性レビューです。case 5・8・9の変更前後比較とcase 10のhold-out評価の手順を定義していますが、実行可能なRust patch fixtureや性能測定ではありません。

## CI

同じvalidatorを以下で実行します。

- GitHub Actions: `.github/workflows/validate.yml`
- GitLab CI: `.gitlab-ci.yml`

branch、pull/merge request、`v<SemVer>` tagでunit testとvalidatorを実行します。Skill自体はruntime dependencyを持たず、validatorとPython testは標準ライブラリのみを使用します。Behavioral graderの実行にはRust/Cargo/Clippyが必要で、Cargoがない環境ではgrader実行の校正testをskipします。CIはAgentによるBehavioral taskを実行しません。

## 配布物の安全性

サポート対象Plugin manifestは静的なSkill文書とmetadataを宣言します。既知の暗黙runtime配置もvalidatorで拒否します。開発用validator、tests、evalsをinstall時・Pluginロード時に呼び出す宣言はありません。PASSの保証は上記の静的検査範囲に限定され、Agentが文書の指示に従って実行するコードや任意のrepository contentsの安全性までは保証しません。

## Contributing

変更方針とreview基準は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

特に、安全性に関する断定やcrate/API固有の記述を追加する場合は、現行仕様・公式documentation・実際にcompile可能なexampleを優先してください。

## Security

脆弱性やsoundness上の問題を発見した場合は、公開issueへexploit詳細を投稿する前に [SECURITY.md](SECURITY.md) を確認してください。

## License

[MIT License](LICENSE) で提供します。
