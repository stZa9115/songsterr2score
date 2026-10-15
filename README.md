# songsterr2score

把瀏覽器另存的 Songsterr 譜頁 (.html) 轉成五線譜、TAB、兩者合併三份 PDF（另附 MusicXML）。
本機工具：在自己電腦上執行，只開在 `127.0.0.1`，不會連到外部網路。

## 安裝

需要 [uv](https://docs.astral.sh/uv/)（Python 套件管理）與 [LilyPond](https://lilypond.org) 2.24 以上（排版 PDF）。

| | uv | LilyPond |
| --- | --- | --- |
| Windows | `winget install astral-sh.uv` | `winget install LilyPond.LilyPond` |
| macOS | `brew install uv` | `brew install lilypond` |
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `sudo apt install lilypond`（Ubuntu 24.04 / Debian 12 以上才是 2.24；較舊的發行版請從 [lilypond.org](https://lilypond.org/download.html) 下載） |

安裝後**重新開一個終端機**，確認 `uv --version` 與 `lilypond --version` 都能執行。
Windows 若 LilyPond 不在 PATH，程式也會到 `C:\Program Files\LilyPond` 底下尋找。
找不到 LilyPond 時網頁會直接告知；命令列則只輸出 .ly 與 .musicxml。

接著取得程式並安裝依賴：

```
git clone https://github.com/stZa9115/songsterr2score.git
cd songsterr2score
uv sync
```

## 取得完整的譜頁

Songsterr 只會渲染畫面附近約 10 行譜，直接 Ctrl+S 或複製 DOM 都存不到整首。請改用收集腳本：

1. 在 Songsterr 打開要轉換的譜，等譜面載入完成（要轉換的音軌就是畫面上顯示的那一軌）。
2. 按 F12 開啟開發者工具，切到 Console。
3. 貼上 [tools/collect-songsterr.js](tools/collect-songsterr.js) 的全部內容後按 Enter。
   瀏覽器若要求先輸入 `allow pasting` 才能貼上，照做即可。
4. 腳本會自動逐行捲動，完成後下載一個 .html。

不完整的頁面仍可轉換，但會出現「頁面只包含 X/Y 行譜」的警告。

## 使用

### 網頁介面

```
uv run python -m songsterr2score.server
```

Windows 也可以直接雙擊 `start.bat`。瀏覽器會自動開啟 http://127.0.0.1:8000/ ：

1. 選擇或拖放剛才下載的 .html。
2. 確認頁面資訊與解析警告，必要時修改譜名（預設「曲名 - 藝人」，同時是 PDF 標題與檔名）。
3. 按「轉換」，完成後點連結開啟或下載 PDF。

關閉終端機視窗即停止伺服器。

### 命令列

```
uv run python -m songsterr2score 譜.html [更多.html 或資料夾 ...] [-o 輸出資料夾] [--bars 1-16] [--name 譜名] [--lilypond lilypond 執行檔路徑]
```

Windows 也可以把 .html 拖到 `convert.bat` 上。

## 輸出位置

| 方式 | 位置 |
| --- | --- |
| 網頁介面 | 專案資料夾下的 `output/` |
| 命令列 | .html 所在資料夾下的 `output/`，或 `-o` 指定的資料夾 |

每份譜產生 `{譜名}_staff.pdf`（五線譜）、`{譜名}_tab.pdf`（TAB）、`{譜名}_both.pdf`（兩者合併），
另有 `{譜名}.musicxml`（可用 MuseScore 等軟體開啟編輯）與 LilyPond 原始檔 `{譜名}_*.ly`。同名檔案會直接覆寫。

## 已知限制

- 推弦、滑音、搥勾弦、顫音等技巧記號目前不會輸出。
- 只轉換另存當下畫面上的那一個音軌。
- 節奏是從譜面圖形推算的，遇到無法辨識的符號或拍數不符的小節會顯示警告，請對照原譜確認。
- PDF 標題若含日文或中文，可能因 LilyPond 找不到合適字型而無法顯示。
- 依賴 Songsterr 頁面的內部結構；Songsterr 改版後可能需要更新程式。

## 版權

Songsterr 的譜頁與轉換出來的 PDF / MusicXML / .ly 都含有受版權保護的譜面內容，只供個人使用。
**請勿將這些檔案提交回此 repo**，也不要貼進 issue 或 PR；`.gitignore` 已排除 `samples/` 與 `output/`。

## 開發

```
git config core.hooksPath .githooks   # 啟用禁止直推 main 的 hook
uv run pytest -q
```

golden 測試需要自行在 `samples/` 放入另存的 Songsterr 頁面；沒有樣本時會自動跳過。
規格與待辦見 [docs/SPEC.md](docs/SPEC.md)、[docs/BACKLOG.md](docs/BACKLOG.md)。
