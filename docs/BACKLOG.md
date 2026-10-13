# 待辦清單

依序進行。每項的「驗收」全部滿足且 `uv run pytest -q` 全綠才算完成。規格見 [SPEC.md](SPEC.md)。

## 1. [ ] core 可被程式呼叫

現在的 `core.py` 只適合 CLI：找不到譜面時 `sys.exit`，檔名取自 HTML 檔名。

驗收：
- 解析失敗時丟出專用例外（CLI 在 `main()` 內接住並印出訊息後以非零碼結束），不可在函式庫程式碼內 `sys.exit`。
- 新增 `default_name(title)`，依 SPEC「譜名」規則回傳預設譜名；有單元測試涵蓋範例標題、不符合格式的標題。
- 新增檔名清理函式，依 SPEC 規則；有單元測試。
- `convert()` 可接受譜名，輸出檔名為 `{譜名}_staff/_tab/_both`，PDF 內標題為該譜名；回傳輸出檔路徑與警告清單。
- CLI 新增 `--name`；未指定時使用預設譜名。
- 現有 golden 測試不需更新即通過（.ly 內的 title 若因此改變，屬預期變動，於 PR 說明後更新 golden）。

## 2. [ ] FastAPI 後端

驗收：
- `POST /api/inspect`：上傳 .html，回傳 JSON（標題、預設譜名、弦數、調弦、小節範圍、警告）。
- `POST /api/convert`：上傳 .html 與譜名，轉換後回傳三個 PDF 的網址與警告；找不到 LilyPond 時回傳明確訊息。
- `GET /files/{檔名}`：提供 `output/` 內的檔案，不可讀到 `output/` 以外的路徑。
- 非 Songsterr 頁面、空譜名、非 .html、超過 20 MB 都回傳 4xx 與繁中訊息。
- 以 FastAPI `TestClient` 撰寫測試：錯誤情況不需樣本；成功情況使用 `samples/`，沒有樣本時跳過。
- 只聽 `127.0.0.1`。

## 3. [ ] 單頁 UI

驗收：
- `GET /` 回傳單一靜態 HTML，內含 SPEC「流程」五個步驟所需的全部元件，文字為繁體中文。
- 上傳後譜名欄位預填預設譜名且可編輯；轉換中有進行中狀態；完成後顯示三個 PDF 連結與警告。
- 錯誤訊息顯示在頁面上。
- 鍵盤可操作，表單元件有 label。
- 測試：`GET /` 回 200 且包含上傳欄位、譜名欄位、轉換按鈕。
- 新增一個啟動指令（啟動伺服器並開啟瀏覽器），並更新 `convert.bat` 或新增對應的 .bat。

## 4. [ ] 六弦與和弦 — 阻擋：需要使用者在 `samples/` 提供吉他樣本

需要至少兩份吉他譜頁：一份單音旋律、一份含和弦。沒有樣本時跳過此項並回報。

驗收：
- 兩份吉他樣本皆可轉換，三種 .ly 都能通過 LilyPond 編譯。
- 和弦在 LilyPond 以 `<...>` 輸出、MusicXML 以 `<chord/>` 輸出，每個音的弦與格正確。
- 每小節拍數檢查對和弦仍然正確（和弦只算一次時值）。
- bass 樣本的 golden 不變。
- 產生吉他樣本的 golden，並在 PR 說明請使用者對照原譜檢查 PDF 的哪些小節。

## 5. [ ] README 安裝與使用說明

驗收：
- 涵蓋：安裝 uv 與 LilyPond（Windows / macOS / Linux）、如何從 Songsterr 另存完整頁面、啟動方式、輸出位置、已知限制。
- 註明不可將 Songsterr 頁面或轉換結果提交回 repo。

## 之後再考慮

- 手工合成的最小 HTML 樣本提交進 repo，讓沒有真實樣本的人與 CI 也能跑 golden 測試。
- GitHub Actions。
- 技巧記號（推弦、滑音、悶音、連結線）。
- 小節範圍選擇、批次上傳。
