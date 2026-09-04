# Rust Safety: Server / Backend / Long-running Service

サーバではmemory safetyに加えて、**availability、resource exhaustion、cancellation、情報漏洩**を重視する。

## 1. Request boundary

外部入力は境界で検証する。

- body size
- header/count/field length
- parse range
- decompression expansion
- uploaded file size
- pagination / query cost
- concurrency / queue size

入力不正をpanicに変換せず、protocol上の適切なerrorへ変換する。

## 2. Panic

request taskのpanicが必ずprocess全体を停止するとは限らないため、「panic = 即DoS」と単純化しない。

ただし外部入力でpanicを再現できる状態は：
- request loss
- repeated task failure
- resource churn
- `panic = abort` 構成でprocess termination

につながり得るため修正対象とする。

`unwrap` / `expect` を本番サーバで一律禁止しないが、外部要因・I/O・DB・network・user inputには原則使わない。

## 3. Error response

- internal error detailをclientへ返さない。
- SQL、filesystem path、internal URL、credential、stack traceをresponseへ含めない。
- server logには診断情報を残すがsecretはredactする。
- client-visible error codeとinternal source errorを分離する。

## 4. Async blocking

async runtime固有の詳細は `references/async-concurrency.md`。

- blocking file/network APIをrequest worker上で長時間実行しない。
- CPU-heavy workは専用pool、runtimeのblocking facility、別service等へ分離する。
- `std::sync::Mutex` は短いdata lockで `.await` を跨がないなら適切な場合がある。
- async mutexはlock保持中に `.await` が必要なshared I/O resource等で使う。

## 5. Timeout / cancellation

外部I/Oには適切なtimeout/deadlineを設定する。

確認対象：
- client request timeout
- upstream connect/read/write timeout
- DB query timeout
- shutdown deadline
- retry budget

Futureがdropされたときのcancellation safetyを確認し、partial write・transaction・state machineが壊れないようにする。

## 6. Bounded resource

- connection pool、channel、queue、task spawnを必要に応じてboundedにする。
- requestごとに無制限taskをspawnしない。
- retryには上限・backoff・jitterを設ける。
- allocation sizeはexternal lengthから直接信用せず上限を置く。

## 7. Graceful shutdown

- 新規受付停止
- in-flight workのdrain
- deadline超過後の終了方針
- DB/message queue等のflush/close

を設計する。framework/runtime固有APIに従う。

## 8. Secret / logging

- Authorization、Cookie、session、API key、password、request bodyを無条件にtrace/debugしない。
- `#[instrument]` 等の自動引数記録ではsecret引数をskipする。
- secret wrapper crateを使う場合は、現在のproject version/APIを確認し、古い型名を決め打ちしない。

## 9. Authentication / authorization

- authenticationとauthorizationを混同しない。
- resource accessごとにauthorizationを確認する。
- user-provided identity headerをtrustする場合は、trusted proxy境界を明確にする。

## 10. Database

- transaction boundaryを明示する。
- cancellation時にtransactionがどうなるか確認する。
- dynamic SQLで値を文字列連結せずparameter bindingを使う。
- connection pool exhaustionを考慮する。

## 11. Observability

- request/correlation IDはsecretでない値を使う。
- high-cardinality fieldを無制限にmetric labelへしない。
- user-controlled stringをlogに出す場合、log injectionや容量増大を考慮する。
