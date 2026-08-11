"""Tests du service de synchro Drive : dédup, idempotence, mise en file."""

import pytest
from sqlalchemy import func, select

from app.models.candidate import Candidate, Document
from app.models.enums import Source
from app.models.job import SyncState
from app.providers.drive.base import DriveFile
from app.providers.drive.fake import FakeDriveProvider
from app.services import drive_sync

pytestmark = pytest.mark.anyio

FOLDER = "folder-1"
PDF_A = b"%PDF-1.4 fichier A"
PDF_B = b"%PDF-1.4 fichier B"


def _file(fid: str, name: str = "cv.pdf") -> DriveFile:
    return DriveFile(id=fid, name=name, mime_type="application/pdf", size=len(PDF_A))


@pytest.fixture
def enqueue_spy(monkeypatch):
    """Remplace `enqueue_process_document` : évite Redis et observe les mises en file."""
    calls: list[str] = []

    async def fake_enqueue(document_id: str) -> None:
        calls.append(document_id)

    monkeypatch.setattr("app.services.drive_sync.enqueue_process_document", fake_enqueue)
    return calls


async def test_sync_imports_new_files_and_enqueues_ingestion(db_session, fake_storage, enqueue_spy):
    drive = FakeDriveProvider()
    drive.add(folder_id=FOLDER, file=_file("drv-A", "a.pdf"), data=PDF_A)
    drive.add(folder_id=FOLDER, file=_file("drv-B", "b.pdf"), data=PDF_B)

    result = await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()

    assert result.listed == 2
    assert result.imported == 2
    assert result.enqueued == 2
    assert result.skipped_by_drive_id == 0
    assert result.skipped_by_hash == 0
    assert len(enqueue_spy) == 2

    total_docs = await db_session.scalar(select(func.count()).select_from(Document))
    total_candidates = await db_session.scalar(select(func.count()).select_from(Candidate))
    assert total_docs == 2
    assert total_candidates == 2

    docs = (await db_session.execute(select(Document))).scalars().all()
    for doc in docs:
        assert doc.source == Source.google_drive
        assert doc.drive_file_id in {"drv-A", "drv-B"}
        assert doc.drive_view_url and doc.drive_file_id in doc.drive_view_url


async def test_sync_is_idempotent_via_drive_file_id(db_session, fake_storage, enqueue_spy):
    """Deuxième passe : même dossier, même fichiers → aucun re-téléchargement."""
    drive = FakeDriveProvider()
    drive.add(folder_id=FOLDER, file=_file("drv-A"), data=PDF_A)

    await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()

    enqueue_spy.clear()
    drive.download_calls.clear()

    second = await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()

    assert second.imported == 0
    assert second.enqueued == 0
    assert second.skipped_by_drive_id == 1
    assert drive.download_calls == []  # zéro téléchargement (dédup avant download)
    assert enqueue_spy == []


async def test_sync_deduplicates_by_content_hash_when_drive_id_differs(
    db_session, fake_storage, enqueue_spy
):
    """Même contenu binaire sous deux ids Drive différents → un seul Document,
    mais on ancre le premier drive_file_id rencontré (les suivants sont
    skippés côté hash)."""
    drive = FakeDriveProvider()
    drive.add(folder_id=FOLDER, file=_file("drv-A"), data=PDF_A)
    drive.add(folder_id=FOLDER, file=_file("drv-A-bis"), data=PDF_A)

    result = await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()

    assert result.listed == 2
    assert result.imported == 1
    assert result.skipped_by_hash == 1
    total_docs = await db_session.scalar(select(func.count()).select_from(Document))
    assert total_docs == 1  # dédup par hash


async def test_sync_updates_sync_state(db_session, fake_storage, enqueue_spy):
    drive = FakeDriveProvider()
    drive.add(folder_id=FOLDER, file=_file("drv-A"), data=PDF_A)

    await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()

    state = await drive_sync.get_sync_state(db_session, FOLDER)
    assert state is not None
    assert state.last_sync_at is not None
    first_time = state.last_sync_at

    await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()
    state2 = await drive_sync.get_sync_state(db_session, FOLDER)
    assert state2 is not None
    assert state2.last_sync_at >= first_time

    # Une seule ligne de sync_state par dossier (upsert logique).
    count = await db_session.scalar(select(func.count()).select_from(SyncState))
    assert count == 1


async def test_download_error_is_captured_and_batch_continues(
    db_session, fake_storage, enqueue_spy, monkeypatch
):
    from app.providers.drive.base import DriveProviderError

    drive = FakeDriveProvider()
    drive.add(folder_id=FOLDER, file=_file("drv-ok"), data=PDF_A)
    drive.add(folder_id=FOLDER, file=_file("drv-ko"), data=PDF_B)

    original = drive.download_file

    async def flaky(file_id: str):
        if file_id == "drv-ko":
            raise DriveProviderError("boom")
        return await original(file_id)

    monkeypatch.setattr(drive, "download_file", flaky)

    result = await drive_sync.sync_drive_folder(
        db_session, folder_id=FOLDER, drive=drive, storage=fake_storage
    )
    await db_session.commit()

    assert result.imported == 1
    assert len(result.errors) == 1
    assert "drv-ko" in result.errors[0]
