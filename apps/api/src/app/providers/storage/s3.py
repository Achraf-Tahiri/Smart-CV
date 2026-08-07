"""Stockage S3-compatible (MinIO en local, S3/GCS en cloud) via boto3.

boto3 est synchrone : on exécute chaque appel dans un thread (`anyio.to_thread`)
pour ne pas bloquer la boucle asynchrone. Le bucket est créé à la demande
(idempotent) au premier écrit.
"""

import boto3
from anyio import to_thread
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class S3StorageProvider:
    """Implémentation de `StorageProvider` sur un stockage S3-compatible."""

    def __init__(self) -> None:
        self._bucket = settings.s3_bucket
        common = {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
            "use_ssl": settings.s3_use_ssl,
            "config": Config(signature_version="s3v4"),
        }
        # Client interne (lecture/écriture) et client de signature (URLs publiques).
        self._client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url, **common)
        self._sign_client = boto3.client("s3", endpoint_url=settings.s3_signing_endpoint, **common)
        self._bucket_ready = False

    def _ensure_bucket_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    async def _ensure_bucket(self) -> None:
        if not self._bucket_ready:
            await to_thread.run_sync(self._ensure_bucket_sync)
            self._bucket_ready = True

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        await self._ensure_bucket()

        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type or "application/octet-stream",
            )

        await to_thread.run_sync(_put)

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()

        return await to_thread.run_sync(_get)

    async def delete(self, key: str) -> None:
        await to_thread.run_sync(lambda: self._client.delete_object(Bucket=self._bucket, Key=key))

    async def exists(self, key: str) -> bool:
        def _exists() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError:
                return False

        return await to_thread.run_sync(_exists)

    async def presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        return await to_thread.run_sync(
            lambda: self._sign_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        )
