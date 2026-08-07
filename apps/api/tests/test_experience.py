"""Tests du calcul d'expérience et de séniorité (horloge figée pour déterminisme)."""

from datetime import date

from app.domain.experience import (
    RawPeriod,
    compute_experience,
    merge_overlapping_periods,
    normalize_period,
    seniority_for,
)

TODAY = date(2026, 1, 1)


def test_seniority_thresholds():
    assert seniority_for(0.0) == "Stage / Junior"
    assert seniority_for(0.25) == "Stage / Junior"
    assert seniority_for(0.5) == "Junior"
    assert seniority_for(2.9) == "Junior"
    assert seniority_for(3.0) == "Intermédiaire"
    assert seniority_for(6.0) == "Senior"
    assert seniority_for(10.0) == "Lead / Expert"
    assert seniority_for(150.0) == "Lead / Expert"


def test_empty_experience():
    result = compute_experience([], today=TODAY)
    assert result.years == 0.0
    assert result.label == "0 an"
    assert result.periods == []


def test_single_period_months():
    # Jan 2023 -> Dec 2023 (année pleine) = 11 mois.
    result = compute_experience([RawPeriod("2023-01", "2023-12")], today=TODAY)
    assert result.label == "11 mois"


def test_overlapping_periods_are_merged_not_double_counted():
    periods = [RawPeriod("2020-01", "2021-12"), RawPeriod("2021-06", "2022-12")]
    result = compute_experience(periods, today=TODAY)
    # Fusion -> 2020-01..2022-12 = 35 mois (2 ans 11 mois), et non 41 (somme brute).
    assert result.label == "2 ans et 11 mois"
    assert result.years == round(35 / 12, 2)
    assert len(result.periods) == 1


def test_present_uses_today():
    result = compute_experience([RawPeriod("2020-01", "PRESENT")], today=TODAY)
    assert result.label == "6 ans"
    assert result.seniority == "Senior"
    assert result.periods[0].is_present is True


def test_range_in_date_debut_overrides_end():
    # « 2019-2021 » dans date_debut prime sur un « PRESENT » halluciné.
    period = normalize_period(RawPeriod("2019-2021", "PRESENT"), today=TODAY)
    assert period is not None
    assert period.is_present is False
    assert period.start == date(2019, 1, 1)
    assert period.end == date(2021, 1, 1)


def test_inverted_dates_are_swapped():
    period = normalize_period(RawPeriod("2022-01", "2020-01"), today=TODAY)
    assert period is not None
    assert period.start == date(2020, 1, 1)
    assert period.end == date(2022, 1, 1)


def test_unparseable_period_is_ignored():
    result = compute_experience(
        [RawPeriod("n'importe quoi", "bof"), RawPeriod("2021-01", "2022-01")],
        today=TODAY,
    )
    assert result.label == "1 an"  # seule la période valide compte


def test_future_start_is_ignored():
    assert normalize_period(RawPeriod("2099-01", "2100-01"), today=TODAY) is None


def test_merge_overlapping_periods_direct():
    from app.domain.experience import Period

    periods = [
        Period(date(2020, 1, 1), date(2022, 12, 1)),
        Period(date(2021, 6, 1), date(2021, 12, 1)),
    ]
    merged = merge_overlapping_periods(periods)
    assert len(merged) == 1
    assert merged[0].start == date(2020, 1, 1)
    assert merged[0].end == date(2022, 12, 1)
