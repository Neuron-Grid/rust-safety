# Rust Safety: Binary / CLI / Desktop / Batch

実行形式では、panicを完全排除するより**ユーザー入力・I/O失敗を適切な終了状態へ変換すること**を重視する。

## 1. `main` 境界

内部処理は `Result` を返し、`main` で表示・exit codeへ変換する構造を推奨する。

```rust
fn main() {
    if let Err(error) = run() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}
```

error crateは既存project方針に従い、特定crateを必須にしない。

## 2. `unwrap` / `expect`

避ける：
- CLI引数、stdin、config、filesystem、network、subprocessの通常失敗
- user-controlled parse

許容し得る：
- compile-time/static invariant
- 起動時に満たされなければ継続不能な内部条件
- test/example

`Mutex` poisoning等も「CLIだから常にunwrap可」とは扱わず、アプリの一貫性要件で判断する。

## 3. Exit code / stdout / stderr

- machine-readable outputはstdoutへ出し、diagnosticはstderrへ出す。
- 成功時は0、失敗は非0。既存CLI contractがあれば保持する。
- library code内から `process::exit` しない。top-level boundaryへ返す。

## 4. File更新

重要ファイルを更新する場合：
- 一時ファイルへ完全に書く
- 必要ならflush/sync policyを確認
- rename/replaceで切り替える
- platform semanticsを確認する

「atomic rename」はfilesystem/platform条件に依存するため、無条件に完全atomicと断定しない。

## 5. Path

- `Path` / `PathBuf` を使う。
- pathがUTF-8とは限らない。
- `to_string_lossy()` を識別・再入力用のcanonical representationに使わない。
- home/config/cache directoryはproject既存方法またはplatform APIを使う。

## 6. Subprocess

- shellを経由する必要がなければ `Command` へ引数を個別に渡す。
- user inputをshell command文字列へ連結しない。
- exit status、stderr、timeout、child cleanupを扱う。
- secretをcommand lineへ載せるとprocess listing等から見える可能性を考慮する。

## 7. Signal / cancellation

長時間動くCLI・daemonでは：
- partial outputの扱いを決める。
- child process、temporary files、lock file等をcleanupする。
- signal handlerでasync-signal-safeでない処理を直接行う設計を避ける。

server性が高いdaemonは `references/server.md` も読む。

## 8. Desktop GUI

- UI threadを長時間blockしない。
- background taskのpanic/errorをUIへ適切に戻す。
- file picker等から得たpathをUTF-8前提にしない。
- native FFIを使う場合 `references/ffi.md` を読む。
