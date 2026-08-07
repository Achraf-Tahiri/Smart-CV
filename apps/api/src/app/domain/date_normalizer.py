"""Normalisation de dates (FR/EN, inversions MM/YYYY, dates partielles).

Porté fidèlement du POC `date_normalizer.py` (fonction pure). Retourne des dates
au format « YYYY-MM ». « Présent »/« Aujourd'hui » ne sont PAS gérés ici : c'est
l'appelant (calcul d'expérience) qui les traite.
"""

import re
from datetime import datetime

# Mois FR/EN (complets + abrégés), en minuscules -> numéro.
MONTHS_MAP: dict[str, int] = {
    # Français
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
    "janv": 1, "fevr": 2, "févr": 2, "avr": 4, "juil": 7, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12, "déc": 12,
    # Anglais
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
}  # fmt: skip

_MIN_YEAR = 1950
_MAX_YEAR = 2100


def normalize_date(date_str: str | None) -> str | None:
    """Normalise une date en « YYYY-MM ». Retourne None si l'analyse échoue."""
    if not date_str:
        return None

    date_str = date_str.lower().strip()

    # YYYY-MM / YYYY/MM / YYYY.MM / YYYY MM
    match = re.search(r"(\d{4})[\-/\s\.](\d{1,2})", date_str)
    if match:
        year, month = match.groups()
        if _MIN_YEAR <= int(year) <= _MAX_YEAR and 1 <= int(month) <= 12:
            return f"{year}-{int(month):02d}"

    # MM-YYYY / MM/YYYY (inversion courante)
    match = re.search(r"(\d{1,2})[\-/\s\.](\d{4})", date_str)
    if match:
        month, year = match.groups()
        if _MIN_YEAR <= int(year) <= _MAX_YEAR and 1 <= int(month) <= 12:
            return f"{year}-{int(month):02d}"

    # Mois en toutes lettres + année (« Août 2012 », « Aug 2012 »)
    match = re.search(r"([a-zA-Záàâäéèêëíìîïóòôöúùûüç]+)[\s,\-\.]+(\d{4})", date_str)
    if match:
        month_txt, year = match.groups()
        month_idx = MONTHS_MAP.get(month_txt.lower())
        if month_idx and _MIN_YEAR <= int(year) <= _MAX_YEAR:
            return f"{year}-{month_idx:02d}"

    # Année seule stricte -> défaut janvier
    match = re.search(r"^\s*(\d{4})\s*$", date_str)
    if match:
        year = match.group(1)
        if _MIN_YEAR <= int(year) <= _MAX_YEAR:
            return f"{year}-01"

    # Année « loose » n'importe où (« depuis 2012 ») -> défaut janvier
    match = re.search(r"(\d{4})", date_str)
    if match:
        year = match.group(1)
        if _MIN_YEAR <= int(year) <= _MAX_YEAR:
            return f"{year}-01"

    return None


def parse_to_datetime(date_str: str | None) -> datetime | None:
    """Convertit une date en `datetime` (jour = 1) après normalisation, ou None."""
    normalized = normalize_date(date_str)
    if normalized:
        try:
            return datetime.strptime(normalized, "%Y-%m")
        except ValueError:
            return None
    return None
