import pytest
from songsterr2score import core


def test_ly_pitch():
    assert core.ly_pitch(60) == "c'"
    assert core.ly_pitch(40) == 'e,'
    assert core.ly_pitch(28) == 'e,,'
    assert core.ly_pitch(61) == "cis'"


def test_measure_units():
    assert core.measure_units([], 1) == (16, (4, 4))
    assert core.measure_units([(1, 4, 4), (5, 3, 4)], 4) == (16, (4, 4))
    assert core.measure_units([(1, 4, 4), (5, 3, 4)], 5) == (12, (3, 4))
    assert core.measure_units([(1, 6, 8)], 1) == (12, (6, 8))


META = '<title>X Tab by Y | Songsterr Tabs with Rhythm</title><script>{"meta":{"current":{"artist":"打首獄門同好会","title":"なつのうた","tracks":[]}}}</script>'


def test_default_name():
    assert core.default_name(META) == 'なつのうた - 打首獄門同好会'
    assert core.default_name('<title>A &amp; B Tab | Songsterr</title>') == 'A & B Tab'
    assert core.default_name('<p>no title</p>') == ''


def test_safe_filename():
    assert core.safe_filename(r'a/b\c:d*e?f"g<h>i|j') == 'a_b_c_d_e_f_g_h_i_j'
    assert core.safe_filename('  .【MV】プロポーズ - 9Lana. ') == '【MV】プロポーズ - 9Lana'
    assert core.safe_filename(' .. ') == ''


def test_line_counts():
    html = ('<svg viewBox="0" data-testid="multitrack-line-group-0"></svg>' * 2 +
            '<div data-player-key="tab" data-line-unit-index="0"></div><div data-player-key="tab" data-line-unit-index="1"></div>'
            '<div data-player-key="tab" data-line-unit-index="2"></div>')
    assert core.line_counts(html) == (1, 3)


def test_parse_html_not_songsterr():
    with pytest.raises(core.SongsterrError):
        core.parse_html('<html><title>hi</title></html>', print)
