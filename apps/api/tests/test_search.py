"""Tests de la recherche hybride (plein-texte + vecteurs)."""

import pytest

from app.models.candidate import Candidate
from app.models.embedding import CandidateEmbedding
from app.models.enums import CandidateStatus, Source
from app.providers.embeddings.deterministic import DeterministicEmbeddingProvider
from tests.conftest import login

pytestmark = pytest.mark.anyio

_EMB = DeterministicEmbeddingProvider(768)


async def _make_candidate(
    db_session, *, search_text, secteur, with_embedding=True, ville=None, nom=None
):
    candidate = Candidate(
        prenom=(search_text.split()[0] if search_text.split() else None),
        nom=nom,
        secteur=secteur,
        ville=ville,
        status=CandidateStatus.success,
        source=Source.local,
        search_text=search_text,
    )
    db_session.add(candidate)
    await db_session.flush()
    if with_embedding:
        vector = (await _EMB.embed_documents([search_text]))[0]
        db_session.add(CandidateEmbedding(candidate_id=candidate.id, embedding=vector))
    await db_session.commit()
    return candidate


async def _auth(client, make_user):
    _, pwd = await make_user(email="u@example.com")
    return await login(client, "u@example.com", pwd)


async def test_search_requires_auth(client):
    assert (await client.get("/api/v1/candidates/search")).status_code == 401


async def test_fulltext_ranks_matching_candidate_first(client, make_user, db_session):
    a = await _make_candidate(
        db_session, search_text="Developpeur Python Django", secteur="Informatique / Tech"
    )
    await _make_candidate(
        db_session, search_text="Comptable finance", secteur="Finance / Banque / Assurance"
    )
    c = await _make_candidate(
        db_session,
        search_text="Designer UX",
        secteur="Art / Design / Création",
        with_embedding=False,
    )
    headers = await _auth(client, make_user)

    resp = await client.get("/api/v1/candidates/search", params={"q": "Python"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    ids = [item["id"] for item in body["items"]]
    assert ids[0] == str(a.id)  # le candidat Python est en tête
    assert str(c.id) not in ids  # sans embedding ni match plein-texte -> absent


async def test_search_with_sector_filter(client, make_user, db_session):
    await _make_candidate(
        db_session, search_text="Developpeur Python", secteur="Informatique / Tech"
    )
    b = await _make_candidate(
        db_session, search_text="Analyste Python finance", secteur="Finance / Banque / Assurance"
    )
    headers = await _auth(client, make_user)

    resp = await client.get(
        "/api/v1/candidates/search",
        params={"q": "Python", "secteur": "Finance / Banque / Assurance"},
        headers=headers,
    )
    body = resp.json()
    ids = [item["id"] for item in body["items"]]
    assert ids == [str(b.id)]  # seul le candidat Finance passe le filtre


async def test_name_filter_matches_only_that_candidate(client, make_user, db_session):
    # Beaucoup de candidats "bruit" avec embeddings : sans filtre nom, la branche
    # vectorielle les remonterait tous. Le filtre nom doit isoler le bon.
    for i in range(5):
        await _make_candidate(db_session, search_text=f"Bruit{i}", secteur="Autre", nom=f"Zzz{i}")
    target = await _make_candidate(
        db_session, search_text="Marie", secteur="Informatique / Tech", nom="Dupont"
    )
    headers = await _auth(client, make_user)

    resp = await client.get("/api/v1/candidates/search", params={"name": "Dupont"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(target.id)


async def test_name_filter_order_independent(client, make_user, db_session):
    target = await _make_candidate(
        db_session, search_text="Marie", secteur="Informatique / Tech", nom="Dupont"
    )
    await _make_candidate(db_session, search_text="Jean", secteur="Autre", nom="Martin")
    headers = await _auth(client, make_user)

    # "Dupont Marie" (ordre inversé) doit tout de même matcher "Marie Dupont".
    resp = await client.get(
        "/api/v1/candidates/search", params={"name": "Dupont Marie"}, headers=headers
    )
    body = resp.json()
    assert [item["id"] for item in body["items"]] == [str(target.id)]


async def test_empty_search_text_excluded_from_vector_ranking(client, make_user, db_session):
    # Un candidat au search_text vide a un embedding "générique" : il ne doit PAS
    # remonter sur une requête libre (sinon il pollue le haut du classement).
    empty = await _make_candidate(db_session, search_text="", secteur="Autre")
    real = await _make_candidate(
        db_session, search_text="Developpeur Python Django", secteur="Informatique / Tech"
    )
    headers = await _auth(client, make_user)

    resp = await client.get("/api/v1/candidates/search", params={"q": "Python"}, headers=headers)
    ids = [item["id"] for item in resp.json()["items"]]
    assert str(empty.id) not in ids
    assert str(real.id) in ids


async def test_search_without_query_lists_all(client, make_user, db_session):
    await _make_candidate(db_session, search_text="A", secteur="Autre")
    await _make_candidate(db_session, search_text="B", secteur="Autre")
    headers = await _auth(client, make_user)

    resp = await client.get("/api/v1/candidates/search", headers=headers)
    assert resp.json()["total"] == 2
