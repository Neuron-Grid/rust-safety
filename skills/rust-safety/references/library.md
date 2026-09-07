# Rust Safety: Library / Public API

公開・共有ライブラリでは、memory safetyに加えて**API contractの安定性と互換性**もcorrectness / maintainability上の要件として扱う。ただしsoundness / securityとは区別する。

## 適用条件

- `src/lib.rs` を持つcrate
- workspace内で他crateから利用されるcrate
- crates.io等へ公開されるcrate
- `cdylib` / `staticlib` でRust外へ公開する場合は `references/ffi.md` も適用

## 1. 公開APIでpanicを契約にしない

- 通常発生し得る入力エラー、I/O、parse失敗は `Result` / `Option` 等で表現する。
- programmer errorを表すpanicは許容できるが、rustdocにpanic条件を記述する。
- index系APIは、panicking版とchecked版を意図的に設計する。標準ライブラリ同様、panic自体を全面禁止しない。

## 2. Error設計

- libraryのpublic errorに特定crateを必須としない。
- 既存のerror型・依存方針を尊重する。
- downstreamが分岐すべきエラーは型・variantで表現し、message parsingを要求しない。
- source errorを保持できる場合はerror chainを失わない。
- `anyhow::Error` 等のopaque errorをpublic contractに採用するかは、そのlibraryの設計方針に従う。

## 3. `unsafe` public API

公開 `unsafe fn` / `unsafe trait` が本質的に必要なlibraryは存在するため、一律禁止しない。

必須：
- rustdoc `# Safety`
- caller / implementorが守る条件を列挙
- 条件が型で表現できるならsafe APIへ寄せる
- safe wrapperが全条件を保証できないならunsafeのまま公開する

例：

```rust
/// Reads a value from `ptr`.
///
/// # Safety
///
/// `ptr` must:
/// - be non-null and properly aligned for `T`, even when `T` is zero-sized;
/// - permit reading at least `size_of::<T>()` bytes;
/// - point to a properly initialized value that is valid for `T`;
/// - for non-zero-sized reads, have provenance permitting access to the whole
///   range within one allocation that remains live for the entire read;
/// - satisfy Rust's aliasing rules and have no conflicting concurrent writes.
///
/// Because `T: Copy`, this read copies the value without transferring ownership
/// out of the pointed-to location; the original value remains usable.
pub unsafe fn read_one<T: Copy>(ptr: *const T) -> T {
    // SAFETY: The caller guarantees non-nullness, alignment, a readable range,
    // initialization and T-validity, plus allocation lifetime and provenance
    // for nonzero access, without aliasing or data-race violations during the
    // read. T: Copy permits retaining the source.
    unsafe { ptr.read() }
}
```

`initialized` と `valid for T` は別の条件。初期化は値を構成する部分が未初期化でないことを指し、
型のvalidityはその値が `T` の制約を満たすことを指す。初期化済みbyte `2` は有効な `bool` ではない。
enumも有効なdiscriminantやpayloadの制約を持つ。padding byteまで初期化を要求する意味ではない。
non-null・alignment・見かけ上のbyte列だけでは、解放済みallocation由来のpointerによるreadを正当化できない。
このwrapperではzero-sized typeでもnon-nullを要求する。これはRust 1.98.1の `ptr::read` が
zero-sized accessに許す例外より厳しいAPI contractであり、標準API一般の要件とは区別する。
zero-sized accessでもalignment・型のvalidityは必要だが、実際のallocationへのアクセスは発生しない。

根拠: [std::ptr::read](https://doc.rust-lang.org/std/ptr/fn.read.html)、
[pointer safety](https://doc.rust-lang.org/std/ptr/index.html#safety)、
[Rust value validity](https://doc.rust-lang.org/reference/behavior-considered-undefined.html#invalid-values)。

## 4. SemVer / compatibility

変更前に確認する：
- public itemの削除・rename
- trait method追加
- generic boundの追加
- auto trait (`Send` / `Sync` / `Unpin`) の変化
- enum variant追加がdownstream exhaustive matchへ与える影響
- `repr` / layout / FFI contract
- feature名・default featureの変更
- MSRV上昇

## 5. MSRV

- `Cargo.toml` の `rust-version` があれば必ず尊重する。
- `rust-version` がなくてもCIやREADMEにMSRVが定義されている可能性を確認する。
- 新しい標準APIを使う前にMSRVを確認する。
- MSRVを上げる修正は、単なるcleanupとして混ぜない。

## 6. Feature設計

- featureはadditiveを基本とする。
- `default-features = false` を勝手に導入して既存機能を落とさない。
- `std` featureを持つlibraryでは `core` / `alloc` / `std` の依存境界を保つ。
- mutually exclusive featureがあるprojectで `--all-features` を無条件に要求しない。

## 7. Public type invariant

constructorで検証できる不変条件は型に閉じ込める。

```rust
pub struct Port(u16);

impl Port {
    pub fn new(value: u16) -> Option<Self> {
        (value != 0).then_some(Self(value))
    }
}
```

unsafe内部実装がpublic safe APIを支える場合、public APIから不変条件を破れないvisibilityにする。

## 8. Documentation / examples

- public unsafe APIには `# Safety`。
- panic条件がAPI contractなら `# Panics`。
- error条件が重要なら `# Errors`。
- example内の `unwrap` は簡潔性のため許容できるが、本番向け例ではerror propagationも検討する。
- doctestがMSRV/feature/targetで実行可能か確認する。

## 9. Library validation

projectが対応する範囲で：

```text
cargo check
cargo test
cargo clippy --all-targets
cargo doc --no-deps
```

feature/MSRV/target matrixはCI定義を優先する。
