"""Calcul d'expérience et de séniorité (porté du POC `analyzer.py` v2).

Différences avec le POC (améliorations) :
- fonction **pure** : ne mute pas les données d'entrée (le POC réécrivait les dicts) ;
- **horloge injectable** (`today`) → tests déterministes ;
- **séniorité unifiée** sur un seul barème (`SENIORITE_THRESHOLDS`).

Le décompte de mois `(fin.year-debut.year)*12 + (fin.month-debut.month)` est
équivalent au `relativedelta` du POC car tous les débuts sont ramenés au 1er du mois.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.domain.date_normalizer import parse_to_datetime
from app.domain.taxonomies import SENIORITE_THRESHOLDS

# Détecte un intervalle « YYYY<sep>YYYY » (ex. « 2023-2024 », « 2023.2024 »).
_RANGE_RE = re.compile(r"(\d{4})\s*[^a-zA-Z0-9]\s*(\d{4})")

# Mots-clés signalant une période en cours.
_PRESENT_KEYWORDS = {"PRESENT", "ACTUELLEMENT", "AUJOURD'HUI", "NOW", "CURRENT", "EN COURS"}


@dataclass(frozen=True)
class RawPeriod:
    """Période brute issue de l'extraction (dates non normalisées)."""

    date_debut: str | None = None
    date_fin: str | None = None


@dataclass(frozen=True)
class Period:
    """Période normalisée (dates réelles)."""

    start: date
    end: date
    is_present: bool = False


@dataclass(frozen=True)
class ExperienceResult:
    """Résultat du calcul d'expérience."""

    years: float  # ex. 3.5
    label: str  # ex. « 3 ans et 6 mois »
    seniority: str  # ex. « Intermédiaire »
    periods: list[Period] = field(default_factory=list)  # périodes fusionnées


def seniority_for(years: float) -> str:
    """Libellé de séniorité pour un nombre d'années d'expérience."""
    for min_exp, max_exp, label in SENIORITE_THRESHOLDS:
        if min_exp <= years < max_exp:
            return label
    return "Lead / Expert"  # fallback cohérent avec le dernier palier


def normalize_period(raw: RawPeriod, *, today: date) -> Period | None:
    """Normalise une période brute en `Period`, ou None si inexploitable.

    Règles (fidèles au POC) : un intervalle « YYYY-YYYY » présent dans la date de
    début prime et écrase la date de fin ; « présent » = date du jour ; une année
    de fin seule identique à l'année de début devient le 31 décembre ; les dates
    incohérentes sont corrigées (échange) ou ignorées (futur > 30 j).
    """
    raw_debut = str(raw.date_debut or "")
    raw_fin = str(raw.date_fin or "")

    # Un range explicite dans date_debut prime sur une éventuelle fin hallucinée.
    range_match = _RANGE_RE.search(raw_debut.strip())
    if range_match:
        raw_debut = range_match.group(1)
        raw_fin = range_match.group(2)

    debut_dt = parse_to_datetime(raw_debut)
    if debut_dt is None:
        return None  # sans début exploitable, on ignore la période
    start = debut_dt.date()

    if raw_fin.upper().strip() in _PRESENT_KEYWORDS:
        end = today
        is_present = True
    else:
        fin_dt = parse_to_datetime(raw_fin)
        if fin_dt is None:
            return None  # fin non exploitable (et non « présent »)
        end = fin_dt.date()
        is_present = False
        # Année seule de fin, même année que le début -> année pleine (31/12).
        if len(raw_fin.strip()) == 4 and raw_fin.strip().isdigit() and end.year == start.year:
            end = date(end.year, 12, 31)

    if start > end:  # inversion -> auto-correction
        start, end = end, start
    if start > today + timedelta(days=30):  # début dans le futur -> ignoré
        return None

    return Period(start=start, end=end, is_present=is_present)


def merge_overlapping_periods(periods: list[Period]) -> list[Period]:
    """Fusionne les périodes qui se chevauchent (tri par début, union des intervalles)."""
    if not periods:
        return []
    ordered = sorted(periods, key=lambda p: p.start)
    merged = [ordered[0]]
    for current in ordered[1:]:
        last = merged[-1]
        if current.start <= last.end:  # chevauchement
            merged[-1] = Period(
                start=last.start,
                end=max(last.end, current.end),
                is_present=last.is_present or current.is_present,
            )
        else:
            merged.append(current)
    return merged


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _format_label(total_months: int) -> str:
    years, months = divmod(total_months, 12)
    if years == 0:
        return f"{months} mois"
    if months == 0:
        return "1 an" if years == 1 else f"{years} ans"
    year_word = "an" if years == 1 else "ans"
    return f"{years} {year_word} et {months} mois"


def compute_experience(
    raw_periods: list[RawPeriod], *, today: date | None = None
) -> ExperienceResult:
    """Calcule l'expérience totale (années + libellé + séniorité) à partir des
    périodes brutes, en fusionnant les chevauchements.
    """
    today = today or date.today()

    normalized = [
        period
        for period in (normalize_period(raw, today=today) for raw in raw_periods)
        if period is not None
    ]
    if not normalized:
        return ExperienceResult(years=0.0, label="0 an", seniority=seniority_for(0.0), periods=[])

    merged = merge_overlapping_periods(normalized)
    total_months = sum(max(0, _months_between(p.start, p.end)) for p in merged)
    if total_months == 0:  # au moins une période valide -> plancher à 1 mois
        total_months = 1

    years = round(total_months / 12, 2)
    return ExperienceResult(
        years=years,
        label=_format_label(total_months),
        seniority=seniority_for(years),
        periods=merged,
    )
