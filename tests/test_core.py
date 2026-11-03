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


def test_main_errors(tmp_path, monkeypatch, capsys):
    bad = tmp_path/'bad.html'
    bad.write_text('<html></html>', encoding='utf-8')
    monkeypatch.setattr(core, 'find_lilypond', lambda _: None)
    monkeypatch.setattr('sys.argv', ['x', str(bad)])
    with pytest.raises(SystemExit) as e: core.main()
    assert e.value.code == 1 and '[錯誤]' in capsys.readouterr().out
    monkeypatch.setattr('sys.argv', ['x', str(bad), str(bad), '--name', 'A'])
    with pytest.raises(SystemExit) as e: core.main()
    assert e.value.code != 0


def six_string_page(voice, notes):
    """合成的六弦譜頁：每個音是一個寬 3 高 10 的矩形 (會被辨識成 '1')，notes 為 (x 中心, 弦)"""
    rects = ' '.join('M %g %g h3 v10 h-3 Z' % (x-1.5, 12*s-4.5) for x, s in notes)
    return ('<script>{"tracks":[{"partId":0,"tuning":[64,59,55,50,45,40]}]}</script><div data-part-id="0"></div>'
            '<svg viewBox="0 0 1 1" data-testid="multitrack-line-group-0">'
            '<text x="3.5" y="-8" class="j6szJq_number">1</text>'
            '<path d="%s" class="vENqEG_voice"></path>'
            '<path d="%s" data-notes-measure="1" class="ai7mjG_voice"></path></svg>' % (voice, rects))


def test_six_string_chords():
    # 八分和弦 + 八分單音 (符槓 y=90)、附點四分和弦 (符桿右側小方塊)、連結音 (只有符桿)、十六分 x2 (符槓 85/90)
    voice = ('M10.5,74v18 M30.5,74v18 M10.5,90v2h20v-2z M50.5,74v18 M54.5,85v2h2v-2z M80.5,74v18 '
             'M100.5,74v18 M110.5,74v18 M100.5,90v2h10v-2z M100.5,85v2h10v-2z')
    html = six_string_page(voice, [(10.5, 0), (10.5, 1), (30.5, 2), (50.5, 3), (50.5, 4), (50.5, 5), (100.5, 0), (110.5, 0)])
    warns = []
    song = core.finalize(core.parse_html(html, warns.append), warns.append)
    assert warns == []
    evs = song['meas'][1]
    assert [e['u'] for e in evs] == [2, 2, 6, 4, 1, 1]
    assert [[(n['string'], n['fret']) for n in e['notes']] for e in evs[:3]] == [[(1, 1), (0, 1)], [(2, 1)], [(5, 1), (4, 1), (3, 1)]]
    assert evs[3]['notes'] == evs[2]['notes'] and evs[2]['tie'] and evs[3]['tied']
    ly = core.ly_measure(song, 1)
    assert ly.startswith(r"<c'\2 f'\1>8 gis8\3 <f,\6 ais,\5 dis\4>4.~ <f,\6 ais,\5 dis\4>4 f'16\1")
    xml = core.build_xml(song, 1, 1)
    assert xml.count('<chord/>') == 2*(1+2+2)       # 兩個譜表，每個和弦除第一音外都有 <chord/>
    assert '<string>5</string><fret>1</fret>' in xml and '<clef-octave-change>-1</clef-octave-change>' in xml


def test_six_string_beat_check():
    # 和弦只算一次時值：兩個四分和弦 = 8/16，應警告拍數不符
    html = six_string_page('M10.5,74v18 M30.5,74v18', [(10.5, 0), (10.5, 1), (10.5, 2), (30.5, 0), (30.5, 5)])
    warns = []
    core.finalize(core.parse_html(html, warns.append), warns.append)
    assert warns == ['第 1 小節拍數不符 (8/16 個十六分音符)，請對照原譜']


def test_triplets_and_dead_notes():
    song = dict(sigs=[], meas={1: [dict(kind='note', u=2, tup=(1, 0), notes=[dict(string=0, fret=None, midi=64)]),
                                   dict(kind='note', u=2, tup=(1, 0), notes=[dict(string=0, fret=0, midi=64)]),
                                   dict(kind='erest', u=2, tup=(1, 0)), dict(kind='qrest', u=4), dict(kind='note', u=8, notes=[dict(string=0, fret=0, midi=64)])]},
                allm=[1], ns=6, tuning=[64, 59, 55, 50, 45, 40], title='t', tempo=120)
    assert core.length(song['meas'][1]) == 16
    assert core.ly_measure(song, 1) == r"\tuplet 3/2 { \deadNote e'8\1 e'8\1 r8 } r4 e'2\1"
    xml = core.build_xml(song, 1, 1)
    assert '<divisions>12</divisions>' in xml and '<notehead>x</notehead>' in xml
    assert xml.count('<time-modification>') == 6 and '<duration>4</duration>' in xml


def test_overfull_measure_keeps_barlines():
    note = lambda: dict(kind='note', u=8, notes=[dict(string=0, fret=0, midi=64)])
    song = dict(sigs=[], meas={1: [note(), note(), note()], 2: [note(), note()]},
                allm=[1, 2], ns=6, tuning=[64, 59, 55, 50, 45, 40], title='t', tempo=120)
    ly = core.build_ly(song, 1, 2, 'tab')
    assert ly.index('make-moment 24/16') < ly.index('% 1') < ly.index('make-moment 16/16') < ly.index('% 2')
    assert '<backup><duration>24</duration></backup>' in core.build_xml(song, 1, 2)


def test_musicxml_string_numbers():
    # MusicXML：弦 1 = 最高音弦；LilyPond \1 也是最高音弦
    chord = dict(kind='note', u=16, notes=[dict(string=5, fret=0, midi=40), dict(string=0, fret=3, midi=67)])
    song = dict(sigs=[], meas={1: [chord]}, allm=[1], ns=6, tuning=[64, 59, 55, 50, 45, 40], title='t', tempo=120)
    xml = core.build_xml(song, 1, 1)
    assert '<string>6</string><fret>0</fret>' in xml and '<string>1</string><fret>3</fret>' in xml
    assert core.ly_measure(song, 1) == r"<e,\6 g'\1>1"
