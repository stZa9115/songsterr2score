# songsterr2score

把瀏覽器另存的 Songsterr 譜頁 (.html) 轉成五線譜 / TAB 的 PDF 與 MusicXML。

目前是命令列工具；Web 介面與六弦和弦支援開發中，見 [docs/BACKLOG.md](docs/BACKLOG.md)。

## 需求

- [uv](https://docs.astral.sh/uv/)
- [LilyPond](https://lilypond.org) 2.24 以上（產生 PDF 用；沒有時只輸出 .ly 與 .musicxml）

## 使用

```
uv sync
uv run python -m songsterr2score 譜.html
```

輸出在 html 所在資料夾下的 `output/`。Windows 也可以把 .html 拖到 `convert.bat` 上。

## 開發

```
git config core.hooksPath .githooks
uv run pytest -q
```

golden 測試需要自行在 `samples/` 放入另存的 Songsterr 頁面；沒有樣本時會自動跳過。

Songsterr 頁面與轉換結果含有版權內容，請勿提交到此 repo。
