# Rust Safety: Async / Concurrency

async/threaded codeではmemory safetyに加えて、deadlock、starvation、cancellation、resource lifetimeを確認する。

## 1. Runtimeを特定する

Tokio、async-std、smol、Embassy、custom executor等を混同しない。既存runtimeを尊重し、別runtimeを新規導入しない。

## 2. Blocking work

async executor thread上では、長時間blockingする処理を避ける。

例：
- synchronous filesystem/network
- `thread::sleep`
- long CPU-bound loop
- blocking foreign call

対処はruntime・platformに従い、blocking pool、dedicated thread/pool、chunking/yield等を使う。

## 3. Mutex selection

async mutexを常に選ばない。

- guardを `.await` を跨いで保持しない短いin-memory data lock：`std::sync::Mutex` や既存blocking mutexが適切な場合がある。
- lock中に `.await` が必要なshared I/O resource：async mutexを検討する。
- 最良の設計がmessage passing / owner taskである場合もある。

blocking mutex guardを `.await` を跨いで保持する設計はdeadlockやexecutor starvationを招きやすいため避ける。

## 4. Lock scope / order

- lock保持時間を短くする。
- 複数lockの取得順序を固定する。
- callback/user codeをlock保持中に呼ばない。
- blocking operationをlock保持中に行わない。

## 5. Cancellation safety

Futureは任意の`.await`でdropされ得ることを考える。

確認：
- partial write
- protocol framing
- transaction
- semaphore permit
- temporary state
- child task

途中キャンセルで不整合になる操作は、commit pointを設けるか、cancellation-safe primitiveへ分割する。

## 6. Spawned task lifecycle

- detached taskがresourceを永続保持しないか。
- shutdown時にjoin/cancelする必要があるか。
- task panic/errorが観測されるか。
- requestごとのunbounded spawnを避ける。

## 7. Channels / queues

- unbounded channelはproducerがconsumerを上回るとmemory exhaustionになり得る。
- bounded capacityとbackpressureを検討する。
- channel closeを通常状態として扱う。

## 8. CPU parallelism

blocking poolへ大量CPU taskを無制限に投げない。CPU-bound専用poolや並列数制限を検討する。

## 9. Atomics

lock-free/atomic codeは `references/unsafe-systems.md` も適用する。orderingはproofを伴って選ぶ。

## 10. Testing

race/deadlockは通常testだけでは見つからないことがある。projectが利用している場合はmodel checking、Miri、sanitizer等を併用する。
