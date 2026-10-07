from app.index import tokenize


def test_tokenize_drops_stop_words_and_stems_plurals():
    assert tokenize("Do you repair heat pumps on weekends?") == ["repair", "heat", "pump", "weekend"]


def test_tokenize_keeps_numbers_and_codes():
    assert tokenize("Error E05 and 1,464.89 EUR") == ["error", "e05", "1,464.89", "eur"]


def test_tokenize_leaves_short_and_double_s_words_alone():
    assert tokenize("gas boss bus") == ["gas", "boss", "bus"]
