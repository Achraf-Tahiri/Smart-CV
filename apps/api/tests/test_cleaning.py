"""Tests du nettoyage / normalisation (skills, villes, titres)."""

from app.domain.cleaning import (
    clean_text,
    format_title,
    normalize_city,
    normalize_skill,
    normalize_skills,
)


def test_normalize_skill_canonical_and_passthrough():
    assert normalize_skill("js") == "JavaScript"
    assert normalize_skill("  React.js ") == "React"
    assert normalize_skill("Rust") == "Rust"  # inconnu -> inchangé (nettoyé)
    assert normalize_skill("") == ""


def test_normalize_skills_dedup_preserves_order():
    result = normalize_skills(["js", "JavaScript", "py", "", "  ", "React.js", "reactjs"])
    assert result == ["JavaScript", "Python", "React"]


def test_format_title():
    assert format_title("alex exemple") == "Alex Exemple"
    assert format_title("") == ""


def test_normalize_city_quartier_to_main_city():
    assert normalize_city("Sidi Bernoussi, Casablanca") == "Casablanca"
    assert normalize_city("Ain Sebaa") == "Casablanca"
    assert normalize_city("Agdal") == "Rabat"
    assert normalize_city("Gueliz") == "Marrakech"


def test_normalize_city_generic_cleanup():
    assert normalize_city("Lyon 69003") == "Lyon"
    assert normalize_city("") == ""


def test_clean_text_collapses_whitespace():
    assert clean_text("  a\n\n  b\t c ") == "a b c"
    assert clean_text(None) == ""
