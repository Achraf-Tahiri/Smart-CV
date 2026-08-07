"""Tests du normaliseur de dates (repris + étendus depuis le POC)."""

from app.domain.date_normalizer import normalize_date, parse_to_datetime


def test_standard_format():
    assert normalize_date("2012-08") == "2012-08"
    assert normalize_date("2012/08") == "2012-08"
    assert normalize_date("2012.08") == "2012-08"


def test_inverted_format():
    assert normalize_date("08-2012") == "2012-08"
    assert normalize_date("08/2012") == "2012-08"


def test_text_month_format():
    assert normalize_date("Août 2012") == "2012-08"
    assert normalize_date("Aug 2012") == "2012-08"
    assert normalize_date("August 2012") == "2012-08"
    assert normalize_date("Janv 2020") == "2020-01"
    assert normalize_date("déc. 2021") == "2021-12"


def test_year_only_defaults_to_january():
    assert normalize_date("2012") == "2012-01"


def test_loose_year_fallback():
    assert normalize_date("depuis 2012") == "2012-01"


def test_invalid_returns_none_or_year_fallback():
    assert normalize_date("Not a date") is None
    assert normalize_date(None) is None
    assert normalize_date("") is None
    # Mois invalide mais année présente -> fallback à l'année.
    assert normalize_date("13-2020") == "2020-01"
    assert normalize_date("00-2020") == "2020-01"


def test_year_out_of_range_rejected():
    assert normalize_date("1800-05") is None
    assert normalize_date("3000-05") is None


def test_parse_to_datetime():
    dt = parse_to_datetime("Août 2012")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2012, 8, 1)
    assert parse_to_datetime("pas une date") is None
