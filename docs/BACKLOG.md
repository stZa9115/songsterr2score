# 待辦清單

依序進行。每項的「驗收」全部滿足且 `uv run pytest -q` 全綠才算完成。規格見 [SPEC.md](SPEC.md)。

## 1. [ ] core 可被程式呼叫

現在的 `core.py` 只適合 CLI：找不到譜面時 `sys.exit`，檔名取自 HTML 檔名。

驗收：
- 解析失敗時丟出專用例外（CLI 在 `main()` 內接住並印出訊息後以非零碼結束），不可在函式庫程式碼內 `sys.exit`。
- 新增 `default_name(html)`，依 SPEC「譜名」規則回傳預設譜名；單元測試用小段 HTML 字串涵蓋：有 meta、沒有 meta 退回 `<title>`。
  另以 `samples/` 驗證四份樣本的預設譜名（沒有樣本時跳過）。
- 新增檔名清理函式，依 SPEC 規則；有單元測試。
- `convert()` 可接受譜名，輸出檔名為 `{譜名}_staff/_tab/_both`，PDF 內標題為該譜名；回傳輸出檔路徑與警告清單。
- CLI 新增 `--name`；未指定時使用預設譜名。
- 偵測不完整的頁面：Songsterr 只渲染畫面附近的譜行，其餘留下 `data-player-key="tab" data-line-unit-index="N"` 佔位元素。
  應有行數 = 佔位元素數；實際行數 = `multitrack-line-group-N` 的數量。兩者不同時產生警告：
  「頁面只包含 X/Y 行譜，請用 tools/collect-songsterr.js 收集完整譜面」，並列出缺少的小節範圍（若可推得）。
  `tools/collect-songsterr.js` 產生的檔案不會有佔位元素，視為完整。
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

## 4. [ ] 六弦與和弦

樣本（`samples/`）：
- `OUTSIDER RODEO …Distortion Guitar 1…`：標準調弦，單音速彈與和弦混合。
- `なつのうた …`：Drop D（最低弦 MIDI 38），以和弦為主。
- `Fear Of The Dark Bass Tab …`：四弦 bass，比 bass-propose 難（有無法辨識的符號、重疊音），可當額外回歸樣本。

已知問題（先修這個，否則吉他的節奏全錯）：
- `parse_html` 寫死四弦的座標：符桿 `M x,50v18`、符槓 y=61/66。六弦的符桿在 y=74、符槓在 y=85/90，
  也就是整體下移 `12*(弦數-4)`。目前吉他樣本一條符桿都抓不到，每個音都被當成「無符桿」去估計時值。
- 無法辨識的字形：`9x10`（吉他兩份都有）、`3x13`（なつのうた、Fear Of The Dark）。先查出是什麼符號再決定支援或明確略過。
- 吉他頁面另有 `M x,83v9` 路徑（4 處），用途未明。

驗收：
- 兩份吉他樣本皆可轉換，三種 .ly 都能通過 LilyPond 編譯，且不再出現「無符桿音符」與「時值無法表示」警告（真正無符桿的全音符除外）。
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
