"""Golden tests against real Songsterr pages in samples/ (gitignored, local only).

Each samples/*.html is rendered and compared with samples/golden/. Samples without a
golden yet are skipped (their output is not trusted). Regenerate deliberately:
UPDATE_GOLDEN=<part of a sample name> for one sample, UPDATE_GOLDEN=1 for all.
"""
import os, pathlib, subprocess
import pytest
from songsterr2score import core

ROOT = pathlib.Path(__file__).parent.parent
SAMPLES = sorted((ROOT/'samples').glob('*.html'))
GOLDEN = ROOT/'samples'/'golden'
MODES = ('both', 'staff', 'tab')


def load(path):
    warns = []
    song = core.finalize(core.parse_html(path.read_text(encoding='utf-8', errors='replace'), warns.append), warns.append)
    return song, min(song['allm']), max(song['allm']), warns


@pytest.mark.parametrize('sample', SAMPLES, ids=lambda p: p.stem)
def test_golden(sample):
    song, first, last, warns = load(sample)
    out = {sample.stem+'.musicxml': core.build_xml(song, first, last),
           sample.stem+'.warnings.txt': '\n'.join(warns)}
    for mode in MODES:
        out['%s_%s.ly' % (sample.stem, mode)] = core.build_ly(song, first, last, mode)
    upd = os.environ.get('UPDATE_GOLDEN')
    if upd == '1' or (upd and upd in sample.stem):
        GOLDEN.mkdir(exist_ok=True)
        for name, text in out.items():
            (GOLDEN/name).write_text(text, encoding='utf-8')
    if not (GOLDEN/(sample.stem+'.musicxml')).exists():
        pytest.skip('尚無 golden；確認輸出正確後以 UPDATE_GOLDEN=1 產生')
    for name, text in out.items():
        f = GOLDEN/name
        assert f.exists(), '缺少 golden %s' % name
        assert text == f.read_text(encoding='utf-8'), '%s 與 golden 不同' % name


@pytest.mark.parametrize('sample', SAMPLES, ids=lambda p: p.stem)
def test_lilypond_compiles(sample, tmp_path):
    lily = core.find_lilypond(None)
    if not lily: pytest.skip('找不到 LilyPond')
    song, first, last, _ = load(sample)
    for mode in MODES:
        f = tmp_path/(mode+'.ly')
        f.write_text(core.build_ly(song, first, last, mode), encoding='utf-8')
        r = subprocess.run([lily, '-s', '-o', str(tmp_path/mode), str(f)], capture_output=True, encoding='utf-8', errors='replace')
        assert r.returncode == 0, r.stderr[-500:]
        assert (tmp_path/(mode+'.pdf')).stat().st_size > 0


NAMES = {'Fear Of The Dark Bass Tab by Iron Maiden': 'Fear Of The Dark - Iron Maiden',
         'OUTSIDER RODEO Tab by RAISE A SUILEN - Distortion Guitar 1': 'OUTSIDER RODEO - RAISE A SUILEN',
         '【MV】プロポーズ Bass Tab by 9Lana': '【MV】プロポーズ - 9Lana',
         'なつのうた Tab by 打首獄門同好会': 'なつのうた - 打首獄門同好会'}
INCOMPLETE = '頁面只包含'


@pytest.mark.parametrize('stem', NAMES)
def test_sample_default_name_and_complete(stem):
    f = ROOT/'samples'/(stem+'.html')
    if not f.exists(): pytest.skip('沒有樣本')
    assert core.default_name(f.read_text(encoding='utf-8', errors='replace')) == NAMES[stem]
    assert not any(INCOMPLETE in w for w in load(f)[3])


def test_incomplete_page_warns():
    f = ROOT/'samples'/'_orig'/'bass-propose.html'
    if not f.exists(): pytest.skip('沒有樣本')
    assert '頁面只包含 10/24 行譜，請用 tools/collect-songsterr.js 收集完整譜面' in load(f)[3]


def test_convert_uses_name(tmp_path):
    f = ROOT/'samples'/'【MV】プロポーズ Bass Tab by 9Lana.html'
    if not f.exists(): pytest.skip('沒有樣本')
    files, warns = core.convert(f, tmp_path, (1, 4), None, name=' My: Song ')
    assert sorted(p.name for p in files) == ['My_ Song.musicxml', 'My_ Song_both.ly', 'My_ Song_staff.ly', 'My_ Song_tab.ly']
    assert 'title = "My: Song"' in (tmp_path/'My_ Song_both.ly').read_text(encoding='utf-8')
    with pytest.raises(core.SongsterrError):
        core.convert(f, tmp_path, None, None, name=' . ')


def test_cli_name_and_default(tmp_path, monkeypatch):
    f = ROOT/'samples'/'【MV】プロポーズ Bass Tab by 9Lana.html'
    if not f.exists(): pytest.skip('沒有樣本')
    monkeypatch.setattr(core, 'find_lilypond', lambda _: None)
    monkeypatch.setattr('sys.argv', ['x', str(f), '-o', str(tmp_path/'a'), '--bars', '1-4', '--name', 'Q"x'])
    core.main()
    assert (tmp_path/'a'/'Q_x_tab.ly').exists()
    monkeypatch.setattr('sys.argv', ['x', str(f), '-o', str(tmp_path/'b'), '--bars', '1-4'])
    core.main()
    ly = tmp_path/'b'/'【MV】プロポーズ - 9Lana_both.ly'
    assert 'title = "【MV】プロポーズ - 9Lana"' in ly.read_text(encoding='utf-8')


@pytest.mark.parametrize('sample', SAMPLES, ids=lambda p: p.stem)
def test_no_rhythm_guess_warnings(sample):
    for w in load(sample)[3]:
        assert not any(k in w for k in ('無符桿', '無法表示', '無法辨識')), w
