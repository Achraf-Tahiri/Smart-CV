"""Tests du mapping de migration POC -> CVExtraction (pur, sans DB)."""

import json

from app.models.enums import CandidateStatus, Source
from app.scripts.migrate_poc import poc_row_to_extraction, poc_source, poc_status


def test_poc_row_to_extraction():
    row = {
        "prenom": "Camille",
        "nom": "Exemple",
        "secteur": "Industrie / Production",
        "hard_skills": "Excel, Word",
        "soft_skills": "Rigueur, Travail en équipe",
        "langues": "Arabe, Français (natif)",
        "details_json": json.dumps(
            {
                "experiences": [
                    {
                        "poste": "Agent",
                        "entreprise": "X",
                        "date_debut": "2020-01",
                        "date_fin": "PRESENT",
                    }
                ],
                "formations": [
                    {"diplome": "Licence", "ecole": "Institut Exemple", "annee": "2019"}
                ],
                "activites_extra": [],
            }
        ),
    }
    ex = poc_row_to_extraction(row)
    assert ex.prenom == "Camille"
    assert ex.secteur == "Industrie / Production"
    assert ex.hard_skills == ["Excel", "Word"]
    assert ex.langues == ["Arabe", "Français (natif)"]
    assert len(ex.experiences) == 1 and ex.experiences[0].poste == "Agent"
    assert len(ex.formations) == 1 and ex.formations[0].annee == "2019"


def test_unknown_secteur_coerced_to_autre():
    assert poc_row_to_extraction({"secteur": "Truc inconnu"}).secteur == "Autre"


def test_empty_and_malformed_details_json():
    assert poc_row_to_extraction({}).experiences == []
    assert poc_row_to_extraction({"details_json": "pas du json"}).experiences == []


def test_poc_status_and_source_mapping():
    assert poc_status("SUCCESS") == CandidateStatus.success
    assert poc_status("MANUAL_REVIEW") == CandidateStatus.manual_review
    assert poc_status("OCR_FAILED") == CandidateStatus.failed
    assert poc_status(None) == CandidateStatus.manual_review
    assert poc_source("google_drive") == Source.google_drive
    assert poc_source("local") == Source.local
