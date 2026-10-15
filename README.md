# songsterr2score

把瀏覽器另存的 Songsterr 譜頁 (.html) 轉成五線譜 / TAB 的 PDF 與 MusicXML。

目前是命令列工具；Web 介面與六弦和弦支援開發中，見 [docs/BACKLOG.md](docs/BACKLOG.md)。

## 需求

- [uv](https://docs.astral.sh/uv/)
- [LilyPond](https://lilypond.org) 2.24 以上（產生 PDF 用；沒有時只輸出 .ly 與 .musicxml）

## 取得譜頁

Songsterr 只會渲染畫面附近的譜行，直接 Ctrl+S 存到的譜不完整。請在譜頁按 F12 → Console，
貼上 [tools/collect-songsterr.js](tools/collect-songsterr.js) 的全部內容後按 Enter，
等它捲完整首後會自動下載一個 .html。

## 使用

```
uv sync
uv run python -m songsterr2score 譜.html            # 預設譜名「曲名 - 藝人」，可用 --name 指定
```

輸出在 html 所在資料夾下的 `output/`。Windows 也可以把 .html 拖到 `convert.bat` 上。

## 開發

```
git config core.hooksPath .githooks
uv run pytest -q
```

golden 測試需要自行在 `samples/` 放入另存的 Songsterr 頁面；沒有樣本時會自動跳過。

Songsterr 頁面與轉換結果含有版權內容，請勿提交到此 repo。
