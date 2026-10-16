import pathlib
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from songsterr2score import core, server

ROOT = pathlib.Path(__file__).parent.parent
SAMPLE = ROOT/'samples'/'【MV】プロポーズ Bass Tab by 9Lana.html'
client = TestClient(server.app)


def post(url, content=b'<html></html>', filename='a.html', **data):
    return client.post(url, files={'file': (filename, content, 'text/html')}, data=data)


@pytest.fixture(autouse=True)
def tmp_output(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'OUTPUT', tmp_path)
    return tmp_path


@pytest.mark.parametrize('url', ['/api/inspect', '/api/convert'])
def test_upload_errors(url, monkeypatch):
    monkeypatch.setattr(core, 'find_lilypond', lambda _: None)  # 非譜頁要回 422，而不是缺 LilyPond 的 503
    r = post(url, filename='a.txt', name='x')
    assert r.status_code == 400 and '.html' in r.json()['detail']
    r = post(url, content=b'x'*(server.MAX_BYTES+1), name='x')
    assert r.status_code == 413 and '20 MB' in r.json()['detail']
    r = post(url, name='x')
    assert r.status_code == 422 and '找不到譜面' in r.json()['detail']


def test_convert_empty_name():
    for name in ('', '  ', ' . '):
        r = post('/api/convert', name=name)
        assert r.status_code == 400 and r.json()['detail'] == '譜名不可為空'


def test_missing_file():
    for url in ('/api/inspect', '/api/convert'):
        r = client.post(url, data={'name': 'x'})
        assert r.status_code == 400 and r.json()['detail'] == '請上傳 .html 檔'


def test_convert_no_lilypond(monkeypatch):
    monkeypatch.setattr(core, 'parse_html', lambda html, warn: None)
    monkeypatch.setattr(core, 'find_lilypond', lambda _: None)
    r = post('/api/convert', name='x')
    assert r.status_code == 503 and 'LilyPond' in r.json()['detail']


def test_files(tmp_output):
    (tmp_output/'a.pdf').write_bytes(b'pdf')
    (tmp_output.parent/'secret.txt').write_text('no')
    assert client.get('/files/a.pdf').content == b'pdf'
    for bad in ('missing.pdf', '..%2Fsecret.txt', '..%5Csecret.txt', '%2E%2E%2Fsecret.txt'):
        assert client.get('/files/'+bad).status_code == 404, bad
    for bad in ('../secret.txt', r'..\secret.txt',str(tmp_output.parent/'secret.txt')):
        with pytest.raises(HTTPException): server.files(bad)


def test_run_listens_localhost(monkeypatch):
    import uvicorn
    seen = {}
    monkeypatch.setattr(uvicorn, 'run', lambda app, **kw: seen.update(kw))
    monkeypatch.setattr(server.threading, 'Timer', lambda t, f, a: seen.update(opened=(f, a)) or type('T', (), {'start': lambda self: seen.update(started=True)})())
    server.run()
    assert seen['host'] == '127.0.0.1'
    assert seen['opened'] == (server.webbrowser.open, ['http://127.0.0.1:8000/']) and seen['started']


def test_index_page():
    r = client.get('/')
    assert r.status_code == 200 and 'text/html' in r.headers['content-type']
    t = r.text
    for el in ('<input type="file" id="file"', '<label for="file">',
               '<input type="text" id="name"', '<label for="name">',
               '<button type="submit" id="convert">', 'role="alert"', 'lang="zh-Hant"'):
        assert el in t, el


def test_inspect_sample():
    if not SAMPLE.exists(): pytest.skip('沒有樣本')
    r = post('/api/inspect', content=SAMPLE.read_bytes())
    j = r.json()
    assert r.status_code == 200
    assert j['default_name'] == '【MV】プロポーズ - 9Lana' and j['title']
    assert j['strings'] == 4 and len(j['tuning']) == 4
    assert j['bars'] == [1, 162] and j['warnings'] == []


def test_convert_sample(tmp_output):
    if not SAMPLE.exists(): pytest.skip('沒有樣本')
    if not core.find_lilypond(None): pytest.skip('沒有 LilyPond')
    r = post('/api/convert', content=SAMPLE.read_bytes(), name='My: #Song%')
    j = r.json()
    assert r.status_code == 200, j
    assert sorted(j['pdfs']) == ['/files/My_%%20%%23Song%%25_%s.pdf' % m for m in ('both', 'staff', 'tab')]
    assert j['warnings'] == []
    for url in j['pdfs']: assert client.get(url).content.startswith(b'%PDF')
