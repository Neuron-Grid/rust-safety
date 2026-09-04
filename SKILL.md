---
name: rust-safety
description: >-
  Safety and correctness rules for any Rust project. Apply when generating,
  modifying, reviewing, refactoring, or auditing Rust code, Cargo manifests,
  build scripts, proc macros, FFI, async/concurrent code, no_std/embedded code,
  WebAssembly, libraries, binaries, servers, or unsafe systems code. Preserve
  the repository's edition, MSRV/rust-version, target support, std/alloc/no_std
  model, features, public API, dependency policy, and CI constraints. Use safe
  Rust by default, but permit justified unsafe Rust behind explicit proof
  obligations and minimal boundaries.
license: MIT
metadata:
  version: "0.1.0"
---

# Rust Safety Skill

このSkillは、Rustを使う**すべてのプロジェクト**で、安全性・正しさ・可用性・移植性を損なわずにコードを生成・修正・レビューするための共通ルールを定義する。

重要な原則は次の3点。

1. **リポジトリの既存制約を最優先する。** Edition、MSRV、ターゲット、`std` / `alloc` / `no_std`、feature、公開API、依存方針、CIを勝手に変更しない。
2. **safe Rustを既定値にするが、`unsafe` を機械的に禁止しない。** FFI、HAL、allocator、kernel、SIMD、低レベルデータ構造などで必要な場合は、証明責務を明示して最小境界に閉じ込める。
3. **安全性ルールと保守性ルールを混同しない。** 行数、モジュール分割、エラーcrateの選択などは設計判断であり、普遍的なmemory-safety要件として強制しない。

---

## 1. 最初に確認すること

コードを書き換える前に、利用可能な範囲で以下を確認する。

- `Cargo.toml` / workspace `Cargo.toml`
- `Cargo.lock` の有無と、library/applicationの性質
- `rust-version`、`edition`、`rust-toolchain.toml`
- `.cargo/config.toml`、target、cross compilation設定
- `#![no_std]`、`extern crate alloc`、feature gates
- `clippy.toml`、`rustfmt.toml`、crate-level lint
- CIで実行される `cargo check/test/clippy`、target、feature組合せ
- 既存のエラー型、async runtime、serialization、logging、secret管理、FFI方式
- `CONTRIBUTING.md`、`README`、ADR等のプロジェクト固有規則
- generated / vendored codeか、生成元を修正すべきファイルか

### 1.1 既存制約の保持

- MSRVを上げない。
- Editionを変更しない。
- target supportを狭めない。
- `std` を使えないcrateへ `std` 依存を持ち込まない。
- featureのdefault値やpublic feature名を理由なく変更しない。
- 新規依存を追加する前に、標準ライブラリ・既存依存・小さな自前実装で満たせないか確認する。
- ユーザーが依存追加を許可していない場合、必要性を説明せずに本番依存を追加しない。
- generated / vendored fileは原則として直接編集せず、generator・source・patch mechanismを修正する。明示的に直接編集する方針のprojectではその方針に従う。

---

## 2. 適用する参照ファイル

このSkillは**排他的な「プロジェクトタイプ」ではなく、該当する能力・境界を重ねて適用する**。

| 条件 | 追加で読むファイル |
|---|---|
| 公開または共有ライブラリAPIがある | `references/library.md` |
| `main.rs`、CLI、desktop、batch、daemon等の実行形式 | `references/binary.md` |
| HTTP/gRPC/RPC/長時間稼働サービス | `references/server.md` |
| `#![no_std]`、firmware、HAL/PAC、RTOS、kernel寄りコード | `references/embedded.md` |
| WebAssembly / WASI | `references/wasm.md` |
| proc macro または `build.rs` | `references/proc-macro.md` |
| C/C++/OS API/外部ABIとの境界、`extern`、`repr(C)` | `references/ffi.md` |
| raw pointer、allocator、`MaybeUninit`、union、Pin、unsafe trait等 | `references/unsafe-systems.md` |
| async、thread、channel、lock、atomic等の並行処理 | `references/async-concurrency.md` |

workspaceでは**変更対象crateごと**に判定する。複数条件に該当する場合はすべて適用し、矛盾する場合は対象環境により具体的な参照ルールを優先する。

---

## 3. 全Rustコード共通の必須ルール

### 3.1 `unsafe` は証明責務として扱う

新しい `unsafe` を導入する前にsafeな代替を検討する。必要な場合は以下を満たす。

- `unsafe` が必要な操作だけを最小のblockへ入れる。
- block直前に `// SAFETY:` を置き、**何が安全条件で、なぜ現在満たされるか**を書く。
- `unsafe fn` では、関数全体を暗黙にunsafe操作可能領域として扱わず、unsafe操作を明示的な `unsafe {}` に限定する。
- 公開 `unsafe fn` / `unsafe trait` はrustdocに `# Safety` を設け、呼び出し側・実装側の義務を具体的に書く。
- safe wrapperは、wrapper自身が前提条件を検査または型で保証できる場合だけ提供する。保証できないunsafe操作をsafe APIで隠さない。
- 既存unsafeコードを変更する場合、元の不変条件・aliasing・lifetime・initialization・thread-safety条件を先に確認する。

`transmute`、raw pointer dereference、`from_raw_parts`、`from_raw`、`MaybeUninit::assume_init` 等は「名前で禁止」するのではなく、**その操作の前提条件を証明できるか**で判断する。詳細は `references/unsafe-systems.md`。依存crate内部のunsafeは `forbid(unsafe_code)` では排除できないため、依存選定と監査は別途扱う。

### 3.2 外部・非信頼入力を境界で検証する

次の値は原則として非信頼入力として扱う。

- CLI引数、stdin、ファイル、network、DB、environment
- FFIから来るpointer/length/string/tag
- JS/WASM hostから来る値
- serialized data、plugin入力、proc-macro入力

境界で検証する項目：

- index / length / offset / allocation size
- enum/tag/discriminant
- UTF-8、NUL終端、path、URL、identifier
- numeric range、overflow、resource上限
- pointerのnull、alignment、validity、lifetime（FFI/unsafe時）

検証済みの値はnewtype・enum・validated struct等へ変換し、内部で同じ検証を繰り返さない。

### 3.3 indexing とslice操作

- 非信頼値で `slice[index]` を行わない。`get`、iterator、`chunks`、`windows` 等を使う。
- 固定長配列の既知indexや、型・直前の検証で範囲が保証される場合は直接indexingを許容する。
- 性能理由でunchecked accessが必要なら、benchmarkで必要性を確認し `references/unsafe-systems.md` の手続きを適用する。

### 3.4 UTF-8と文字列

- 外部byte列には `str::from_utf8` / `String::from_utf8` 等の検証APIを使う。
- `from_utf8_unchecked` は、同じ関数または型不変条件でUTF-8 validityを証明できる低レベル実装に限定する。
- 「ASCIIだから安全」等の前提は、入力生成元が保証するか明示的に検証する。

### 3.5 数値変換

`as` を一律禁止しない。変換の意味で判断する。

- 値域を失う可能性があり、その損失が仕様でない場合：`TryFrom` / checked conversionを使う。
- widening conversion、bit-level protocol、明示的truncate等、仕様上の意味が明確な場合：`as` を許容する。
- pointer/int変換やprovenanceに関わる変換は `references/unsafe-systems.md` を適用する。
- 浮動小数点→整数変換はNaN、無限大、範囲外の意味を確認する。

### 3.6 整数overflow

`checked_*` をすべての算術へ機械的に適用しない。意味に応じて選択する。

- allocation size、offset、length、external count、security boundary：overflowを検出し `checked_*` / `TryFrom` 等で失敗させる。
- wrappingがアルゴリズム仕様：`wrapping_*` を使う。
- saturatingが仕様：`saturating_*` を使う。
- 通常の `+ - *` で数学的に範囲内が保証される場合：そのまま使用してよい。

「debugではpanic、releaseではwrapするはず」といったprofile依存の暗黙挙動をアルゴリズム仕様にしない。

### 3.7 panic / `unwrap` / `expect`

panicはmemory unsafetyではない。用途に応じて扱う。

避ける：
- 非信頼入力や通常発生し得るI/O失敗をpanicへ変換する。
- server requestやlibrary public APIで、回復可能な条件をpanicにする。
- `todo!` / `unimplemented!` をrelease pathへ残す。

許容し得る：
- test、example、benchmark、prototype。testでは意図したpanicの検証も許容する。
- 到達すればprogrammer bugである内部不変条件。
- 起動直後に検証する構成不変条件で、プロセス継続が意味を持たない場合。

`expect` を使う場合は、失敗した**操作**ではなく「なぜ成功が保証されるはずか」をメッセージに書く。

### 3.8 ownership・resource lifetime

- RAIIでresourceを閉じる。
- `mem::forget`、`ManuallyDrop`、`Box::leak` は一律禁止しない。FFI ownership transfer、process-lifetime allocation等で正当な用途がある。
- ただし、外部入力やloop回数に比例して永続leakする設計は避ける。
- raw ownership変換（`Box::into_raw` / `from_raw`、`Vec::from_raw_parts` 等）はallocation元・layout・所有権の一意性を証明する。

### 3.9 concurrency / async

並行処理を使う場合は `references/async-concurrency.md` を読む。

共通原則：
- lock order、deadlock、starvation、cancellation、task/thread lifetimeを考慮する。
- blocking I/Oや長時間CPU処理をasync executorのworker上で無条件に実行しない。
- `std::sync::Mutex` をasync codeで一律禁止しない。guardを `.await` を跨いで保持しない短いdata lockなら適切な場合がある。
- async mutexは `.await` を跨ぐ共有I/O state等、必要な場合に使う。
- `unsafe impl Send/Sync` は `references/unsafe-systems.md` の証明対象。

### 3.10 secret・credential・PII

該当する場合のみ適用する。

- secretをlog、panic message、error response、`Debug` / `Display` に含めない。
- secretを含む型の自動 `Debug` deriveを確認する。
- secretをsource codeやWASM配布物へ埋め込まない。
- zeroizationは脅威モデルと型・allocator・copy挙動を踏まえて採用し、「zeroizeしたので完全消去」と断定しない。
- secret用crateを新規導入するかは既存依存・MSRV・`no_std`制約に従う。

### 3.11 path・environment・platform

- ユーザー環境固有の絶対pathを埋め込まない。
- `Path` / `PathBuf` を使い、pathをUTF-8文字列だと仮定しない。
- platform固有APIには `cfg` を付け、support targetを保つ。
- process environmentはglobal mutable stateであることを意識し、並行実行中の変更を避ける。Edition/APIに応じてunsafe要件も確認する。

### 3.12 public APIと型不変条件を壊さない

- safety修正を理由に無関係なpublic API breaking changeを起こさない。
- `Send` / `Sync` / `Unpin` / variance / layout / `repr` の変化は公開型ではbreakingまたはsoundness影響になり得るため確認する。
- serialization format、CLI output、exit code、FFI ABIも外部契約として扱う。

### 3.13 dependency safety

- 新しいcrateを「推奨crateだから」という理由だけで追加しない。
- 既存lockfile、MSRV、license、feature、target、`no_std` compatibilityを確認する。
- default featuresを切る場合は既存機能を壊さないか確認する。
- security audit toolは利用可能な場合に使うが、未導入ツールを必須前提にしない。

### 3.14 保守性

ソースファイルの**固定行数上限は設けない**。

分割する基準：
- 複数の責務が混在している。
- unsafe invariantが広範囲へ漏れている。
- public APIとimplementation detailが混ざっている。
- testability・reviewabilityが低下している。

生成コード、large table、protocol definition等は長くても分割しない方が安全な場合がある。行数ではなく責務と変更境界で判断する。

---

## 4. lint方針

既存crate-level lintを尊重し、Skillが勝手にlint policyを全面置換しない。

unsafeを含むcrateでは、toolchain/MSRVが対応する場合に次を検討する。

```rust
#![deny(unsafe_op_in_unsafe_fn)]
```

ClippyをCIで使用している場合は `clippy::undocumented_unsafe_blocks` も候補だが、既存CI policyに合わせる。

`#![forbid(unsafe_code)]` は、**そのcrateが今後もunsafeを必要としないと設計上判断できる場合だけ**採用する。FFI、embedded HAL、allocator、kernel、SIMD等に一律適用しない。

`clippy::pedantic` / `clippy::nursery` をSkill側から一律denyしない。

---

## 5. unsafe変更時の必須手続き

unsafeを追加・変更・削除する場合、レビューでは最低限以下を確認する。

1. **必要性** — safe APIでは満たせないか。
2. **Safety contract** — pointer validity、alignment、initialization、aliasing、lifetime、threading、layout等の必要条件は何か。
3. **Proof** — その条件を誰が、どのコードで保証するか。
4. **Boundary** — unsafe範囲を狭められるか。
5. **API** — safe wrapperが本当に全前提を保証できるか。できなければunsafe APIのままにする。
6. **Mutation resistance** — 将来の変更で不変条件が破れにくい型・module visibilityになっているか。
7. **Validation** — 対象に応じてtest、Miri、sanitizer、fuzzing等を実行する。

`SAFETY:` コメント例：

```rust
// `slice: &[u32]` is known to be non-empty here.
let ptr = slice.as_ptr();
// SAFETY: `ptr` comes from this live non-empty slice, is aligned for `u32`,
// and points to at least one initialized `u32`. Reading a `u32` does not move
// ownership out of the slice because `u32: Copy`.
let value = unsafe { ptr.read() };
```

コメントは「unsafeだから安全」のような循環説明にしない。

---

## 6. 検証

変更後は、リポジトリで既に採用されている方法を優先して検証する。

一般的な候補：

```text
cargo fmt --check
cargo check
cargo test
cargo clippy --all-targets
```

ただし以下を守る。

- workspace、feature matrix、cross targetではCIと同じコマンドを優先する。
- `--all-features` が相互排他的featureやtarget-specific featureを壊すprojectでは使用しない。
- `no_std` / embedded / WASMではhost `cargo test` が意味を持たない場合がある。
- networkやhardwareが必要なtestを勝手に実行しない。
- Miri/sanitizer/fuzzerは、対象コードとtoolchainが対応し利用可能な場合のみ使う。

unsafe関連の変更では、可能ならMiri等の動的検証を追加するが、**動的検証の成功をsoundness証明の代替にしない**。

---

## 7. レビューチェックリスト

- [ ] repositoryのEdition / MSRV / target / `std`・`alloc`・`no_std` / featureを保持したか
- [ ] 非信頼入力を境界で検証したか
- [ ] narrowing、overflow、allocation sizeの意味が明示されているか
- [ ] recoverable errorを不要にpanicへ変換していないか
- [ ] 新規unsafeが本当に必要か
- [ ] 各unsafe操作のSafety contractとproofが追跡可能か
- [ ] raw ownership、lifetime、aliasing、initializationを破っていないか
- [ ] async/thread codeでblocking、deadlock、cancellation問題を増やしていないか
- [ ] secretや内部情報をlog/errorへ漏らしていないか
- [ ] public API / ABI / serialization / CLI contractを意図せず壊していないか
- [ ] 新規依存がMSRV・target・feature・license方針に適合するか
- [ ] 変更範囲に適したtest/checkを実行したか

