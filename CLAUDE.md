# songsterr2score

把瀏覽器另存的 Songsterr 譜頁 (.html) 轉成五線譜 / TAB 的 PDF 與 MusicXML。
本機工具：使用者 clone 後在自己電腦上跑，不部署。

- 規格與驗收條件：[docs/SPEC.md](docs/SPEC.md)
- 待辦清單（loop 的工作來源）：[docs/BACKLOG.md](docs/BACKLOG.md)

## 指令

```
uv sync                                   # 安裝依賴
uv run pytest -q                          # 全部測試（約 3 秒）
uv run python -m songsterr2score 譜.html  # CLI 轉換
git config core.hooksPath .githooks       # clone 後執行一次，啟用禁止直推 main 的 hook
```

PDF 需要系統已安裝 LilyPond 2.24+；找不到時只輸出 .ly 與 .musicxml。

## 結構

- `songsterr2score/core.py` — 全部轉換邏輯：解析 HTML 內的 SVG 譜面 → 節奏推算 → 產生 LilyPond / MusicXML。
- `tests/test_core.py` — 純函式單元測試，不需要樣本。
- `tests/test_golden.py` — 對 `samples/*.html` 做 golden 比對，並確認 LilyPond 編譯成功。
- `samples/` — **gitignore**。真實 Songsterr 頁面與 `samples/golden/` 基準輸出，只存在本機。

## 規則

- **版權**：Songsterr 頁面及其衍生物（.ly / .musicxml / PDF、golden）不可提交、不可貼進 PR 或 issue。新增測試樣本一律放 `samples/`。
- **Golden**：`samples/golden/` 是防止退步的基準，bass 樣本的基準「大致正確、未逐小節核對」。
  只有待辦項目明確要改變輸出時才能用 `UPDATE_GOLDEN=1 uv run pytest` 重新產生，
  而且要先看 diff 確認每個差異都是預期的，並在 PR 說明改了什麼、為什麼。不可為了讓測試變綠而更新 golden。
- **語言**：UI 文字、警告訊息、README、docs 用繁體中文；識別字、commit 訊息、PR 標題用英文。
- **依賴**：能用標準庫或既有依賴就不要加新的。不要預先做抽象層。
- 六弦 / 和弦相關的工作必須有 `samples/` 裡的吉他樣本才能做；沒有樣本就跳過該項並回報。

## Loop 工作流程

每一輪做 BACKLOG 的一個項目：

1. 取 [docs/BACKLOG.md](docs/BACKLOG.md) 中第一個未勾選、且沒有標示「阻擋」的項目。
2. 從最新的 `main` 開分支 `feat/<slug>`。若此項目依賴尚未合併的 PR，就從那個分支開，PR 的 base 也設成那個分支，並在 PR 內註明。
3. 實作並補測試，直到該項目的驗收條件全部滿足、`uv run pytest -q` 全綠。
4. 在同一個分支把 BACKLOG 該項目打勾，commit。
5. `git push -u origin <branch>`，`gh pr create`。PR 內容用繁中寫：做了什麼、如何驗證、golden 是否變動。
6. 接著做下一個項目。

停下並回報的情況：測試修不好、驗收條件不清楚或互相矛盾、需要使用者提供樣本或做決定、沒有可做的項目。

不可做：直接 push 到 `main`、force push、合併 PR（由使用者審閱後合併）、跳過 hook。
