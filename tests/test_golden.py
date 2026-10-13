"""Golden tests against real Songsterr pages in samples/ (gitignored, local only).

Each samples/*.html is rendered and compared with samples/golden/. With no samples
present the tests are skipped. Regenerate deliberately with UPDATE_GOLDEN=1.
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
    if os.environ.get('UPDATE_GOLDEN'):
        GOLDEN.mkdir(exist_ok=True)
        for name, text in out.items():
            (GOLDEN/name).write_text(text, encoding='utf-8')
    for name, text in out.items():
        f = GOLDEN/name
        assert f.exists(), '缺少 golden %s；確認輸出正確後以 UPDATE_GOLDEN=1 產生' % name
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
