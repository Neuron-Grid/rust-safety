# Rust Safety: Proc Macro / build.rs

build-time codeは開発者環境・CIで実行されるため、runtime codeとは別のtrust boundaryを持つ。

## 1. Proc macro input

TokenStreamは非信頼入力として扱う。

- malformed inputでpanicしない。
- diagnosticには適切なSpanを付ける。
- parser libraryはrepository既存依存を優先し、特定version/crateを必須化しない。
- generated identifierは衝突・hygieneを考慮する。

## 2. Generated code

生成するRust codeにも本Skillを適用する。

- 不要なunsafeを生成しない。
- unsafe生成が必要なら、生成コード側でSafety contractを追跡可能にする。
- absolute path (`::core`, `::std`, target crate path等) の選択はmacro contractに合わせる。
- callerのimportsに偶然依存しない。

## 3. Macro errors

syntax/user input errorはcompiler diagnosticとして返す。単なるinvalid inputでproc-macro processをpanicさせない。

internal invariant破壊のpanicはbugとして許容され得るが、通常のparse failureと分離する。

## 4. Macro tests

必要に応じて：
- expansion unit test
- compile-pass
- compile-fail
- diagnostic test

を使う。特定testing crateを必須にしない。

## 5. build.rs side effects

build scriptは可能な限りdeterministicにする。

- source treeへ生成物を書かず、通常はCargoが提供するoutput directoryを使う。
- network access、package manager install、system-wide mutationを暗黙に行わない。
- environment secretを生成物・warning・logへ出さない。
- input file/envに応じたrerun条件を宣言する。

## 6. External command

- shellが不要なら `Command` へargumentを個別に渡す。
- user/environment値をshell文字列へ連結しない。
- exit statusを検証する。
- cross compile時はHOSTとTARGETを混同しない。

## 7. build helper分割

`build.rs` の補助moduleをsubdirectoryへ置く場合はRustのmodule探索規則を正しく扱う。

例：

```text
build.rs
build/build_helpers.rs
```

```rust
#[path = "build/build_helpers.rs"]
mod build_helpers;
```

または通常のmodule layoutに合わせる。単に `mod build_helpers;` と書いて別directoryを自動探索すると仮定しない。

## 8. Host/target distinction

build scriptとproc macroはhostで動き、生成対象crateはtarget向けにbuildされる。

- target executableをbuild時に実行しない。
- target-specific cfgをhost codeと混同しない。
- bindgen/codegen toolが必要な場合、cross environmentでのavailabilityを確認する。
