# Rust Safety: WebAssembly / WASI

WASM sandboxはRust内部のundefined behaviorを無害化しない。host boundaryとlinear memoryの両方を安全に扱う。

## 1. Targetを特定する

repositoryが実際に使用するtargetを確認する。

例：
- browser向け `wasm32-unknown-unknown`
- WASI Preview 1系target
- WASI Preview 2 / Component Model系target
- Emscripten等

target名・runtime supportはtoolchainとhostに依存するため、Skill側で勝手にtarget migrationしない。

## 2. JS / host boundary

hostから来る値は非信頼入力として扱う。

- numeric range / NaN / infinity
- object shape
- buffer length
- string / serialization
- handle lifetime

`JsValue` 等から内部型へ変換する境界で検証する。

## 3. Panic

browser WASMのpanicはtrapとしてhostへ伝わり得る。user inputをpanicへ変換しない。

debug用panic hookは診断に有効だが、本番bundleへの採否はsize・情報漏洩を考慮する。

## 4. Long-running work

browser main thread上で長い同期計算を行うとUIをblockする。

- workを分割してyield
- Web Worker等へ退避
- parallel WASMを使う場合、hostのcross-origin isolation等の前提を確認

runtime固有asyncは `references/async-concurrency.md` も読む。

## 5. Secret

browserへ配布するWASM binaryへsecretを埋め込まない。binaryは利用者が取得・解析できる。

API credentialはserver側で保持するか、clientに公開してよいcredentialだけを渡す。

## 6. Memory and JS view

linear memory growthによりJS側viewが無効化・再取得必要になるAPIがあるため、binding libraryのcontractを確認する。

zero-copy view等でunsafeを使う場合：
- Rust側buffer lifetime
- reallocation prohibition
- JS側保持期間

をSafety contractに含める。

## 7. FFI-like boundary

WIT/component binding、raw exports/imports、`extern`、custom ABIを使う場合 `references/ffi.md` も適用する。

## 8. Size optimization

sizeは安全性の必須条件ではない。release profile、LTO、`wasm-opt`、allocator変更は**計測した上で**project要件に応じて行う。保守停止crateや特定allocatorをSkillから固定推奨しない。
