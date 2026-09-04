# Rust Safety: Unsafe / Systems Programming

allocator、kernel、HAL、FFI、intrusive collection、SIMD等ではunsafe Rustが本質的な場合がある。この参照はunsafeを禁止するのではなく、**soundness proofを局所化する**。

## 1. Unsafe inventory

変更対象で以下を検索・確認する：
- `unsafe {}` / `unsafe fn` / `unsafe trait` / `unsafe impl`
- raw pointer dereference
- `NonNull`
- `MaybeUninit`
- `from_raw_parts` / `from_raw_parts_mut`
- `Box::from_raw`, `Vec::from_raw_parts`
- `ptr::read`, `write`, `copy`, `copy_nonoverlapping`
- union field access
- `static mut`
- `transmute`
- unsafe attributes / extern declarations
- architecture intrinsics / target features

既存のSafety comment・module docs・testsも同時に読む。

## 2. Raw pointers

各dereferenceで確認する：
- non-null requirement
- alignment
- dereferenceable byte range
- initialization
- pointee validity
- aliasing
- lifetime
- provenance / address manipulation

integer→pointer変換を通常のreference代替として使わない。

## 3. `MaybeUninit`

`assume_init` 前に**全byteではなく型として必要なinitialization invariant**が成立していることを確認する。

- partial init countを追跡する。
- error pathでinitialized elementsだけdropする。
- uninitialized referenceを作らない。
- invalid bit patternを持つ型をzero-initできると仮定しない。

## 4. Raw slice construction

`slice::from_raw_parts{,_mut}` では：
- pointer validity/alignment
- 1 allocation内で連続していること
- length arithmetic
- `isize::MAX` 等、APIが要求するsize条件
- mutable aliasing

を使用toolchainのAPI docsに照らして確認する。

## 5. Ownership reconstruction

`Box::from_raw` / `Vec::from_raw_parts` 等はallocation provenance、layout、capacity、exactly-once ownershipを一致させる。

他allocator・foreign allocatorで作ったmemoryをRust allocator ownership型として回収しない。

## 6. `transmute`

代替が明確なら代替する。

使用する場合は：
- `Src` と `Dst` のsizeが等しいこと
- source値と変換後の値が、それぞれの型でvalidなbit patternであること
- lifetime
- provenance
- repr/layout
- pointer/reference/`Box` 等を変換する場合、変換後に指す先が要求alignmentを満たすこと

を確認する。`transmute` 自体はby-value operationなので、`Src` / `Dst` 値そのもののalignmentはcompilerが保証する。lifetime extension目的のtransmuteは特に危険で、所有権設計の見直しを優先する。

## 7. `ManuallyDrop` / `mem::forget`

destructor suppression自体はRustの安全モデル上許容されるが、resource leak・double drop・use-after-freeを設計で防ぐ。

`ManuallyDrop<T>` のfieldをpublicに露出させる場合、downstream move/drop interactionを確認する。

## 8. Pin

unsafe Pin projection / `Pin::new_unchecked` では：
- pinned valueをmoveしない
- structural pinning対象fieldを明確にする
- Dropでmove-outしない
- projection APIがpin invariantを保持する

を証明する。

## 9. Unsafe traits / Send / Sync

`unsafe impl` は型の全reachable stateについてtrait contractを満たす必要がある。

`Send` / `Sync` では特に：
- interior mutability
- foreign handle thread affinity
- aliasing
- destructor thread
- raw pointer pointee lifetime

を確認する。

## 10. Atomics

atomic codeはdata-race freeでもlogical correctnessを失い得る。

- orderingの理由を説明する。
- relaxed orderingを「速いから」で選ばない。
- publication / synchronization relationを確認する。
- ABA、overflow、tearing assumptionsを確認する。

## 11. Validation

unsafe変更では可能な範囲で：
- focused unit/property tests
- Miri
- sanitizer
- fuzzing
- concurrency model checking

を検討する。ただしtool実行結果だけでsoundnessを証明したことにはしない。
