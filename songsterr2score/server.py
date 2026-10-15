"""本機 Web 後端：上傳 Songsterr 另存的 .html，檢視資訊並轉成 PDF。只聽 127.0.0.1。"""
import pathlib, tempfile
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from . import core

OUTPUT = pathlib.Path(__file__).resolve().parent.parent/'output'
MAX_BYTES = 20*1024*1024

app = FastAPI(title='songsterr2score')

def read_upload(file):
    """檢查副檔名與大小，回傳 html 文字"""
    if not (file.filename or '').lower().endswith('.html'):
        raise HTTPException(400, '只接受 .html 檔')
    data = file.file.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, '檔案超過 20 MB 上限')
    return data.decode('utf-8', errors='replace')

@app.post('/api/inspect')
def inspect(file: UploadFile = File(...)):
    html = read_upload(file)
    warns = []
    try: song = core.finalize(core.parse_html(html, warns.append), warns.append)
    except core.SongsterrError as e: raise HTTPException(422, str(e))
    return dict(title=core.page_title(html), default_name=core.default_name(html), strings=song['ns'],
                tuning=song['tuning'], bars=[min(song['allm']), max(song['allm'])], warnings=warns)

@app.post('/api/convert')
def convert(file: UploadFile = File(...), name: str = Form('')):
    html = read_upload(file)
    if not core.safe_filename(name.strip()):
        raise HTTPException(400, '譜名不可為空')
    lily = core.find_lilypond(None)
    if not lily:
        raise HTTPException(503, '找不到 LilyPond，無法產生 PDF。請到 https://lilypond.org 安裝 2.24 以上版本後重新啟動。')
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp)/'upload.html'
        src.write_text(html, encoding='utf-8')
        try: files, warns = core.convert(src, OUTPUT, None, lily, name)
        except core.SongsterrError as e: raise HTTPException(422, str(e))
    pdfs = ['/files/'+f.name for f in files if f.suffix == '.pdf']
    return dict(pdfs=pdfs, warnings=warns)

@app.get('/files/{name}')
def files(name: str):
    root = OUTPUT.resolve()
    p = (root/name).resolve()
    if p.parent != root or not p.is_file():
        raise HTTPException(404, '找不到檔案')
    return FileResponse(p)

def run():
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

if __name__ == '__main__':
    run()
