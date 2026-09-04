# Rust Safety: FFI / External ABI

FFIではcompilerが相手側ABI・pointer validity・ownershipを検証できない。**binding declarationそのものがunsafe proofの一部**である。

## 1. ABI declaration

- 実際のC/C++/platform headerとsignatureを一致させる。
- integer width、signedness、calling convention、variadic、struct layoutを確認する。
- Rust 2024 Edition等、対象Editionで要求される `unsafe extern` / unsafe attribute syntaxに従う。
- `#[no_mangle]`、`#[export_name]`、`#[link_section]` 等はglobal symbol/linker invariantを持つため、対象Editionのunsafe attribute規則を確認する。

## 2. Layout

FFIに渡す型はABI contractを明示する。

- C structは通常 `#[repr(C)]`。
- Rust default layoutを外部ABIとして公開しない。
- `bool`、enum、trait object、Rust `String` / `Vec` 等をC ABIへそのまま出さない unless binding contractが明示的に保証する。
- opaque handleはpointer/newtype等で表現する。

## 3. Pointer + length

raw pointerからslice/stringを作る前に確認する：
- nullability
- alignment
- valid memory range
- element initialization
- `len * size_of::<T>()` overflow
- aliasing / mutability
- lifetime

zero-length pointerに関するAPI preconditionも使用するRust APIのcontractに従う。推測しない。

## 4. Ownership

FFI contractで明示する：
- 誰がallocateするか
- 誰がfreeするか
- どのallocator/deallocator pairを使うか
- transfer後に元ownerがaccessしてよいか
- callback終了後もpointerが保持されるか

`Box::into_raw` / `Box::from_raw` 等は、**同じallocationをexactly onceで回収する**ことを保証する。

## 5. Strings

C stringでは：
- NUL termination
- interior NUL
- encoding（UTF-8とは限らない）
- borrowed/owned lifetime

を確認する。

`CStr` / `CString` 等、対象環境で使える標準型を優先する。

## 6. Callback

callbackでは：
- userdata pointerの型・lifetime
- callback thread
- reentrancy
- unregister timing
- foreign codeがcallbackを保持する期間

を明示する。

Rust closureをraw pointerへ変換して渡す場合はdrop timingとdouble-freeを特に確認する。

## 7. Panic / unwind

Rust panicを、unwindを許可しないforeign ABI境界へ越境させない。

- ABIがunwindを契約している場合だけ、その契約に従う。
- C callback等でpanicを封じ込める必要がある場合はpanic strategyとunwind safetyを確認して境界で扱う。
- `panic = abort` では `catch_unwind` による回復を前提にしない。

## 8. Thread safety

foreign libraryのthread-safety contractを確認する。

raw handle wrapperへ `unsafe impl Send/Sync` を付ける場合は：
- foreign APIがcross-thread useを許可するか
- destruction thread制約
- concurrent call可否

をSafety commentに含める。

## 9. Safe wrapper

safe wrapperは、foreign APIの全unsafe preconditionをRust側で保証できるときだけsafeにする。

pointer validity等をcallerへ要求する必要が残るなら `unsafe fn` のまま公開する。
