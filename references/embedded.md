# Rust Safety: Embedded / no_std / Firmware / Kernel-adjacent

`no_std` では「標準ライブラリの代替を使う」だけでなく、**実際に利用可能な層が `core` / `alloc` / platform runtime のどこまでか**を先に確認する。

## 1. Environment matrix

確認する：
- `#![no_std]` のみか
- `alloc` が使えるか
- allocatorが存在するか
- single-core / multi-core
- interrupt / RTOS / async executor
- MMU / MPU / cache / DMA
- panic strategy
- target atomic support

`std` 向けcrateを候補として自動追加しない。

## 2. Hardware access

PAC/HALが提供するsafe abstractionを優先する。

raw MMIOが必要なら：
- addressの正当性
- register width/alignment
- volatile semantics
- read-modify-writeの副作用
- exclusive access

をSafety contractに含める。

単なるraw pointer read/writeをvolatile I/Oの代用にしない。

## 3. Global state

`static mut` を共有状態の通常手段にしない。

候補：
- critical-section abstraction
- interrupt-safe mutex
- atomics（targetが対応する場合）
- ownershipをperipheral singletonへ移す
- runtime/framework固有resource model

raw mutable staticがABIやlinker requirementで必要なら、参照生成・aliasing・interrupt concurrencyを明示してunsafe boundaryへ閉じ込める。

## 4. Interrupt safety

ISRで：
- blocking operationを避ける。
- allocationを避ける方針がある場合に従う。
- shared stateはcritical section / atomic / framework resourceで保護する。
- ISRとmain/task間のmemory orderingを確認する。

`volatile` はthread synchronizationの代替ではない。

## 5. DMA

DMAはRust borrow checkerの外でmemoryへアクセスするため、特に注意する。

確認する：
- buffer lifetime
- DMA中のCPU側access prohibition
- cache coherency
- alignment
- ownership return timing
- transfer completion / cancellation

safe HAL APIがこれらを型で保証する場合はそのAPIを使う。

## 6. Allocation / stack

- heap禁止を一律ルールにしない。実機resourceとproject policyで決める。
- bounded memoryが必要ならfixed-capacity collectionを検討する。
- large local array、recursion、large Futureによるstack usageを確認する。
- allocation failure handlingはallocator/runtimeの挙動に合わせる。

## 7. Panic

`#[panic_handler]` / runtime panic implementationの方針を確認する。

production firmwareではpanic後の動作（halt、reset、watchdog、diagnostic）を設計する。panicをerror recoveryの通常手段にしない。

## 8. no_std dependency

crate名で「no_std対応」と決め打ちしない。

確認する：
- `default-features`
- `alloc` requirement
- target-specific dependency
- MSRV
- feature graph

error型は手動 `core::fmt::Display` 実装でもderive crateでもよい。特定のerror crateを必須にしない。

## 9. Unsafe-heavy HAL / kernel code

HAL、allocator、kernel、driver等ではunsafeが本質的な場合がある。`#![forbid(unsafe_code)]` を一律に適用せず `references/unsafe-systems.md` を使う。
