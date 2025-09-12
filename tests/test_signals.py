from chess_rag_system.analysis._signals import tokens, pgn_ratio, didactic_hits_per_1k


def test_tokens_basic():
    txt = "1.e4 e5 2.Nf3 Nc6 3.Bb5 a6! +="
    ts = list(tokens(txt))
    assert '1.e4' in ts and 'a6' in ts


def test_pgn_ratio_high_for_moves():
    txt = "1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 1-0"
    r = pgn_ratio(txt)
    assert r > 0.4


def test_pgn_ratio_low_for_prose():
    txt = "This chapter explains typical plans and key ideas in the structure."
    r = pgn_ratio(txt)
    assert r < 0.2


def test_didactic_hits_counts():
    txt = "Typical plan: improve structure and avoid mistakes; strategic idea."
    hits = didactic_hits_per_1k(txt)
    assert hits >= 50  # plenty of didactic words in short text

