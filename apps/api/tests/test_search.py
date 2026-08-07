"""Tests de la recherche hybride (plein-texte + vecteurs)."""

import pytest

from app.models.candidate import Candidate
from app.models.embedding import CandidateEmbedding
from app.models.enums import CandidateStatus, Source
from app.providers.embeddings.deterministic import DeterministicEmbeddingProvider
from tests.conftest import login

pytestmark = pytest.mark.anyio

_EMB = DeterministicEmbeddingProvider(768)


async def _make_candidate(db_session, *, search_text, secteur, with_embedding=True, ville=None):
    candidate = Candidate(
        prenom=search_text.split()[0],
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


async def test_search_without_query_lists_all(client, make_user, db_session):
    await _make_candidate(db_session, search_text="A", secteur="Autre")
    await _make_candidate(db_session, search_text="B", secteur="Autre")
    headers = await _auth(client, make_user)

    resp = await client.get("/api/v1/candidates/search", headers=headers)
    assert resp.json()["total"] == 2
