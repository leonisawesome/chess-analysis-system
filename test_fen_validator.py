import pytest
import fen_validator
import chess

VALID_FEN = "r1bq1rk1/pp3ppp/2nbpn2/3p4/3P4/2N1PN2/PP3PPP/R1BQ1RK1 w - - 0 8"  # IQP
INVALID_FEN = "8/8/8/8/8/8/8/8/8"  # Too many ranks

def test_is_legal_fen_valid():
    assert fen_validator.is_legal_fen(VALID_FEN) is True

def test_is_legal_fen_invalid():
    assert fen_validator.is_legal_fen(INVALID_FEN) is False

def test_load_and_save_cache(tmp_path):
    test_file = tmp_path / "test_cache.json"
    data = {"concept": "fenstring"}
    with open(test_file, "w") as f:
        f.write("{}")
    fen_validator.CACHE_FILE = str(test_file)
    fen_validator.save_cache(data)
    loaded = fen_validator.load_cache()
    assert loaded == data

def test_validate_and_cache_fen(monkeypatch, tmp_path):
    fen_validator.CACHE_FILE = str(tmp_path / "test_cache.json")

    def mock_check(fen, concept): return 0.8
    monkeypatch.setattr(fen_validator, "llm_conceptual_check", mock_check)

    result = fen_validator.validate_and_cache_fen(VALID_FEN, "isolated_queen_pawn")
    assert result is True

def test_reject_low_confidence(monkeypatch, tmp_path):
    fen_validator.CACHE_FILE = str(tmp_path / "test_cache.json")

    def mock_check(fen, concept): return 0.3
    monkeypatch.setattr(fen_validator, "llm_conceptual_check", mock_check)

    result = fen_validator.validate_and_cache_fen(VALID_FEN, "isolated_queen_pawn")
    assert result is False
