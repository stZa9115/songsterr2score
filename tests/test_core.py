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
