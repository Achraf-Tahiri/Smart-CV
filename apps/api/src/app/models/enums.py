"""Énumérations métier, stockées en base sous forme de VARCHAR + CHECK."""

from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    recruteur = "recruteur"
    lecteur = "lecteur"


class CandidateStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    success = "success"
    manual_review = "manual_review"
    failed = "failed"


class Source(StrEnum):
    local = "local"
    google_drive = "google_drive"


class SkillType(StrEnum):
    hard = "hard"
    soft = "soft"


class ImportJobSource(StrEnum):
    local_upload = "local_upload"
    drive_sync = "drive_sync"


class ImportJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
