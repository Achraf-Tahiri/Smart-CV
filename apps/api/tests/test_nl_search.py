"""Tests de la recherche en langage naturel (Phase 2.4b).

Couvre :
- Parsing NL via FakeLLMProvider (sans clé LLM réelle).
- Post-traitements portés du POC : ville ambiguë (AMBIGUOUS_NAMES), stop words,
  mapping séniorité.
- Endpoint GET /api/v1/candidates/nl-search bout-en-bout.
"""

import pytest

from app.models.candidate import Candidate
from app.models.enums import CandidateStatus, Source
from app.providers.llm import get_llm
from app.providers.llm.fake import FakeLLMProvider
from app.services.nl_search import (
    AMBIGUOUS_NAMES,
    STOP_WORDS,
    NLSearchFilters,
    apply_postprocessing,
    parse_nl_query,
)
from tests.conftest import login

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Tests unitaires (pas de DB)
# ---------------------------------------------------------------------------


async def test_parse_nl_query_extrait_filtres():
    """parse_nl_query retourne les filtres extraits par le Fake LLM."""
    fake = FakeLLMProvider(
        response={
            "keywords": ["Python", "Django"],
            "ville": "Casablanca",
            "secteur": "Informatique / Tech",
            "seniorite": "Senior",
            "min_experience": 5.0,
            "max_experience": None,
        }
    )
    filters = await parse_nl_query(fake, "développeur Python senior à Casablanca 5 ans")
    assert filters.keywords == ["Python", "Django"]
    assert filters.ville == "Casablanca"
    assert filters.secteur == "Informatique / Tech"
    assert filters.seniorite == "Senior"
    assert filters.min_experience == 5.0
    assert filters.max_experience is None


async def test_parse_nl_query_llm_failure_retourne_vide():
    """En cas d'erreur LLM, les filtres sont vides sans lever d'exception."""
    fake = FakeLLMProvider(fail=True)
    filters = await parse_nl_query(fake, "n'importe quoi")
    assert filters == NLSearchFilters()


async def test_parse_nl_query_appelle_llm():
    """Le prompt est bien envoyé au LLM (le Fake le trace dans .calls)."""
    fake = FakeLLMProvider(response={"keywords": []})
    await parse_nl_query(fake, "test requête")
    assert len(fake.calls) == 1
    _system, user = fake.calls[0]
    assert "test requête" in user


# ---------------------------------------------------------------------------
# Tests post-traitements (ville ambiguë, stop words)
# ---------------------------------------------------------------------------


async def test_ville_ambigue_deplacee_dans_keywords():
    """Une ville AMBIGUOUS_NAMES est déplacée vers keywords et ville → None."""
    filters = NLSearchFilters(ville="Doha", keywords=["React"])
    result = apply_postprocessing(filters)
    assert result.ville is None
    assert "Doha" in result.keywords
    assert "React" in result.keywords


async def test_ville_ambigue_insensible_casse():
    """La comparaison AMBIGUOUS_NAMES ignore la casse."""
    filters = NLSearchFilters(ville="SOFIA", keywords=[])
    result = apply_postprocessing(filters)
    assert result.ville is None
    assert "SOFIA" in result.keywords


async def test_ville_non_ambigue_conservee():
    """Une ville normale (ex: Casablanca) n'est pas déplacée."""
    filters = NLSearchFilters(ville="Casablanca", keywords=["Python"])
    result = apply_postprocessing(filters)
    assert result.ville == "Casablanca"
    assert "Casablanca" not in result.keywords


async def test_stop_words_retires_des_keywords():
    """Les termes STOP_WORDS sont filtrés des keywords après parsing LLM."""
    filters = NLSearchFilters(keywords=["Python", "senior", "candidat", "React"])
    result = apply_postprocessing(filters)
    assert "senior" not in result.keywords
    assert "candidat" not in result.keywords
    assert "Python" in result.keywords
    assert "React" in result.keywords


async def test_stop_words_insensible_casse():
    """Le filtrage STOP_WORDS est insensible à la casse."""
    filters = NLSearchFilters(keywords=["Python", "SENIOR", "Candidat"])
    result = apply_postprocessing(filters)
    assert "SENIOR" not in result.keywords
    assert "Candidat" not in result.keywords
    assert "Python" in result.keywords


# ---------------------------------------------------------------------------
# Tests mapping séniorité (validator NLSearchFilters)
# ---------------------------------------------------------------------------


async def test_seniorite_label_valide_conserve():
    """Un label valide de SENIORITE_THRESHOLDS est accepté tel quel."""
    f = NLSearchFilters.model_validate({"seniorite": "Senior"})
    assert f.seniorite == "Senior"

    f2 = NLSearchFilters.model_validate({"seniorite": "Lead / Expert"})
    assert f2.seniorite == "Lead / Expert"


async def test_seniorite_terme_informel_mappe():
    """Les termes informels du POC (l.849-852) sont mappés au barème unifié."""
    cases = [
        ("junior", "Junior"),
        ("senior", "Senior"),
        ("expert", "Lead / Expert"),
        ("confirmé", "Intermédiaire"),
        ("débutant", "Stage / Junior"),
        ("expérimenté", "Senior"),
    ]
    for terme, attendu in cases:
        f = NLSearchFilters.model_validate({"seniorite": terme})
        assert f.seniorite == attendu, f"'{terme}' → attendu '{attendu}', obtenu '{f.seniorite}'"


async def test_seniorite_invalide_coerce_a_none():
    """Un label inconnu est silencieusement mis à None (pas d'erreur)."""
    f = NLSearchFilters.model_validate({"seniorite": "Légendaire"})
    assert f.seniorite is None


async def test_secteur_invalide_coerce_a_none():
    """Un secteur non reconnu est mis à None."""
    f = NLSearchFilters.model_validate({"secteur": "Inconnu"})
    assert f.secteur is None


async def test_secteur_valide_conserve():
    """Un secteur reconnu est conservé."""
    f = NLSearchFilters.model_validate({"secteur": "Informatique / Tech"})
    assert f.secteur == "Informatique / Tech"


# ---------------------------------------------------------------------------
# Tests sur les constantes portées du POC
# ---------------------------------------------------------------------------


def test_ambiguous_names_contient_valeurs_poc():
    """AMBIGUOUS_NAMES contient les 8 valeurs du POC (analyzer.py l.887)."""
    # Valeurs extraites de analyzer.py l.887
    expected = {
        "doha",
        "sofia",
        "alexandria",
        "victoria",
        "charlotte",
        "virginia",
        "austin",
        "orlando",
    }
    assert AMBIGUOUS_NAMES >= expected


def test_stop_words_contient_valeurs_poc():
    """STOP_WORDS contient les termes métier du POC (analyzer.py l.898-904)."""
    assert "candidat" in STOP_WORDS
    assert "profil" in STOP_WORDS
    assert "senior" in STOP_WORDS
    assert "expert" in STOP_WORDS
    assert "junior" in STOP_WORDS


# ---------------------------------------------------------------------------
# Tests d'intégration (endpoint)
# ---------------------------------------------------------------------------


async def _make_candidate(db_session, *, prenom, secteur, search_text):
    c = Candidate(
        prenom=prenom,
        secteur=secteur,
        status=CandidateStatus.success,
        source=Source.local,
        search_text=search_text,
    )
    db_session.add(c)
    await db_session.commit()
    return c


async def test_nl_search_requires_auth(client):
    """L'endpoint exige un token JWT."""
    resp = await client.get("/api/v1/candidates/nl-search", params={"q": "test"})
    assert resp.status_code == 401


async def test_nl_search_q_requis(client, app, make_user):
    """Le paramètre q est obligatoire (422 si absent)."""
    app.dependency_overrides[get_llm] = lambda: FakeLLMProvider(response={})
    _, pwd = await make_user(email="u_422@example.com")
    headers = await login(client, "u_422@example.com", pwd)
    resp = await client.get("/api/v1/candidates/nl-search", headers=headers)
    assert resp.status_code == 422


async def test_nl_search_retourne_page(client, app, make_user, db_session):
    """L'endpoint retourne une Page[CandidateRead] avec les bons champs."""
    await _make_candidate(
        db_session,
        prenom="Alice",
        secteur="Informatique / Tech",
        search_text="Alice Python développeur",
    )
    fake_llm = FakeLLMProvider(
        response={
            "keywords": ["Python"],
            "ville": None,
            "secteur": "Informatique / Tech",
            "seniorite": None,
            "min_experience": None,
            "max_experience": None,
        }
    )
    app.dependency_overrides[get_llm] = lambda: fake_llm

    _, pwd = await make_user(email="u_page@example.com")
    headers = await login(client, "u_page@example.com", pwd)

    resp = await client.get(
        "/api/v1/candidates/nl-search",
        params={"q": "développeur Python"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "items" in body
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 1


async def test_nl_search_filtre_secteur(client, app, make_user, db_session):
    """Le filtre secteur extrait par le LLM est bien appliqué."""
    await _make_candidate(
        db_session,
        prenom="Bob",
        secteur="Finance / Banque / Assurance",
        search_text="Bob comptable finance",
    )
    await _make_candidate(
        db_session,
        prenom="Carol",
        secteur="Informatique / Tech",
        search_text="Carol Python dev",
    )

    fake_llm = FakeLLMProvider(
        response={
            "keywords": ["comptable"],
            "ville": None,
            "secteur": "Finance / Banque / Assurance",
            "seniorite": None,
            "min_experience": None,
            "max_experience": None,
        }
    )
    app.dependency_overrides[get_llm] = lambda: fake_llm

    _, pwd = await make_user(email="u_secteur@example.com")
    headers = await login(client, "u_secteur@example.com", pwd)

    resp = await client.get(
        "/api/v1/candidates/nl-search",
        params={"q": "comptable finance"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    ids = [item["id"] for item in body["items"]]
    # Seul Bob (Finance) passe le filtre secteur
    assert len(ids) == 1
    assert body["items"][0]["prenom"] == "Bob"


async def test_nl_search_pagination(client, app, make_user, db_session):
    """Les paramètres limit et offset sont respectés."""
    for i in range(3):
        await _make_candidate(
            db_session,
            prenom=f"Candidat{i}",
            secteur="Autre",
            search_text=f"Candidat{i} data analyst",
        )

    fake_llm = FakeLLMProvider(
        response={
            "keywords": ["data"],
            "ville": None,
            "secteur": None,
            "seniorite": None,
            "min_experience": None,
            "max_experience": None,
        }
    )
    app.dependency_overrides[get_llm] = lambda: fake_llm

    _, pwd = await make_user(email="u_pag@example.com")
    headers = await login(client, "u_pag@example.com", pwd)

    resp = await client.get(
        "/api/v1/candidates/nl-search",
        params={"q": "data analyst", "limit": 2, "offset": 0},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 2
    assert len(body["items"]) <= 2
