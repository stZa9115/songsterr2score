# songsterr2score

把瀏覽器另存的 Songsterr 譜頁 (.html) 轉成五線譜 / TAB 的 PDF 與 MusicXML。
本機工具：使用者 clone 後在自己電腦上跑，不部署。

- 規格與驗收條件：[docs/SPEC.md](docs/SPEC.md)
- 待辦清單（loop 的工作來源）：[docs/BACKLOG.md](docs/BACKLOG.md)

## 指令

```
uv sync                                   # 安裝依賴
uv run pytest -q                          # 全部測試（約 30 秒，多數時間在 LilyPond 編譯）
uv run python -m songsterr2score 譜.html  # CLI 轉換
git config core.hooksPath .githooks       # clone 後執行一次，啟用禁止直推 main 的 hook
```

PDF 需要系統已安裝 LilyPond 2.24+；找不到時只輸出 .ly 與 .musicxml。

## 結構

- `songsterr2score/core.py` — 全部轉換邏輯：解析 HTML 內的 SVG 譜面 → 節奏推算 → 產生 LilyPond / MusicXML。
- `songsterr2score/server.py` — FastAPI 後端（`/api/inspect`、`/api/convert`、`/files/`），`uv run python -m songsterr2score.server`（或 `start.bat`）啟動並開啟瀏覽器；`static/index.html` 是單頁 UI。
- `tests/test_core.py` — 純函式單元測試，不需要樣本。
- `tests/test_golden.py` — 對 `samples/*.html` 做 golden 比對，並確認 LilyPond 編譯成功。
- `tools/collect-songsterr.js` — 使用者在 Songsterr 譜頁 F12 Console 執行，逐行捲動收集完整譜面並下載成一個 .html。
  Ctrl+S 或複製 DOM 都只拿得到畫面附近約 10 行。
- `samples/` — **gitignore**。真實 Songsterr 頁面與 `samples/golden/` 基準輸出，只存在本機。

## 規則

- **版權**：Songsterr 頁面及其衍生物（.ly / .musicxml / PDF、golden）不可提交、不可貼進 PR 或 issue。新增測試樣本一律放 `samples/`。
- **Golden**：`samples/golden/` 是防止退步的基準。目前只有プロポーズ有基準：第 1–73 小節使用者看過「大致正確」，
  第 74–162 小節未經人工核對（但零警告）。
  還沒有 golden 的樣本會被跳過（輸出尚未可信）。
  只有待辦項目明確要改變輸出時才能用 `UPDATE_GOLDEN=<樣本名稱片段> uv run pytest` 重新產生單一樣本（`=1` 為全部），
  而且要先看 diff 確認每個差異都是預期的，並在 PR 說明改了什麼、為什麼。不可為了讓測試變綠而更新 golden。
- **語言**：UI 文字、警告訊息、README、docs 用繁體中文；識別字、commit 訊息、PR 標題用英文。
- **依賴**：能用標準庫或既有依賴就不要加新的。不要預先做抽象層。
- 在 Windows 終端機印出日文 / 中文時要設 `PYTHONIOENCODING=utf-8`，否則會因 cp950 編碼錯誤中斷。

## Loop 工作流程

每一輪做 BACKLOG 的一個項目：

1. 取 [docs/BACKLOG.md](docs/BACKLOG.md) 中第一個未勾選、且沒有標示「阻擋」的項目。
2. 從最新的 `main` 開分支 `feat/<slug>`。若此項目依賴尚未合併的 PR，就從那個分支開，PR 的 base 也設成那個分支，並在 PR 內註明。
3. 實作並補測試，直到該項目的驗收條件全部滿足、`uv run pytest -q` 全綠。
4. 在同一個分支把 BACKLOG 該項目打勾，commit。
5. **獨立審查**：寫程式的 agent 也寫了測試，兩者可能基於同一個誤解。開 PR 前用 Agent 工具啟動一個全新的
   general-purpose subagent 審查，提示中只給：
   - 該項目在 BACKLOG 的驗收條件原文，以及 SPEC 相關段落的路徑；
   - 要它自己跑 `git diff <base>...HEAD`（base 為 PR 的目標分支）與 `uv run pytest -q`。

   不要給它你的實作說明、理由或自評。要求它逐條驗收條件回報：是否滿足（是 / 否 / 不確定）、
   證據（`檔案:行號` 或測試名稱）、以及「若功能壞掉，對應的測試是否真的會失敗」。
   有任何「否」或「不確定」就修正並 commit，再用新的 subagent 重審；三輪仍未全部通過就停下回報。
6. `git push -u origin <branch>`；push 與 `gh pr create` 分成兩個指令執行。PR 內容用繁中寫：
   做了什麼、如何驗證、golden 是否變動、獨立審查結果摘要（每條驗收條件一行）。
7. 接著做下一個項目。

停下並回報的情況：測試修不好、驗收條件不清楚或互相矛盾、獨立審查三輪未通過、需要使用者提供樣本或做決定、沒有可做的項目。

不可做：直接 push 到 `main`、force push、合併 PR（由使用者審閱後合併）、跳過 hook。
