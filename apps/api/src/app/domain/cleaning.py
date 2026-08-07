"""Nettoyage / normalisation des données extraites (porté du POC `data_cleaner.py`).

Adapté au schéma normalisé : les compétences sont manipulées en **listes**
(et non plus en chaînes CSV comme dans le POC SQLite).
"""

import re
from collections.abc import Iterable

from app.domain.taxonomies import CITY_MAPPINGS, SKILL_MAPPINGS


def clean_text(text: str | None) -> str:
    """Compacte les espaces multiples et retire les blancs de bord."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_skill(skill: str | None) -> str:
    """Ramène une compétence à sa forme canonique (via SKILL_MAPPINGS), sinon la nettoie."""
    if not skill:
        return ""
    cleaned = skill.strip()
    return SKILL_MAPPINGS.get(cleaned.lower(), cleaned)


def normalize_skills(skills: Iterable[str]) -> list[str]:
    """Normalise une liste de compétences : canonise + déduplique (insensible à
    la casse) en **préservant l'ordre d'apparition**. Ignore les valeurs vides.
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in skills:
        skill = normalize_skill(raw)
        if not skill:
            continue
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            result.append(skill)
    return result


def format_title(text: str | None) -> str:
    """Met en casse Titre (ex. prénom, nom, poste)."""
    if not text:
        return ""
    return text.title().strip()


def normalize_city(city: str | None) -> str:
    """Normalise une ville : ramène un quartier connu à sa ville principale
    (Maroc), sinon nettoie (retire chiffres/ponctuation) et met en casse Titre.
    """
    if not city:
        return ""

    cleaned = city.strip().lower()

    # 1) Quartier ou ville principale connus -> ville principale.
    for main_city, quartiers in CITY_MAPPINGS.items():
        if main_city in cleaned:
            return main_city.title()
        if any(quartier in cleaned for quartier in quartiers):
            return main_city.title()

    # 2) Nettoyage générique : retirer chiffres puis ponctuation (sauf tiret).
    generic = re.sub(r"\d+", "", city).strip()
    generic = re.sub(r"[^\w\s-]", "", generic).strip()
    return generic.title()
