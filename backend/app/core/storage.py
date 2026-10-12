import asyncio
from datetime import UTC, datetime
from typing import Any, Protocol

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger


class StorageError(AppException):
    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            status_code=500,
            code="STORAGE_ERROR",
            message=message,
            details=details,
        )


class StorageBackend(Protocol):
    """Protocol for object storage backends (MinIO, Cloudflare R2, AWS S3)."""

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        """Uploads raw bytes to storage and returns the object key."""
        ...

    async def download(self, key: str, bucket: str | None = None) -> bytes:
        """Downloads raw bytes of an object from storage."""
        ...

    async def generate_presigned_upload_url(
        self,
        key: str,
        expires_in: int = 900,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        """Generates a short-lived presigned URL for direct client PUT upload."""
        ...

    async def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 300,
        filename: str | None = None,
        bucket: str | None = None,
    ) -> str:
        """Generates a short-lived presigned URL for client GET download."""
        ...

    async def delete(self, key: str, bucket: str | None = None) -> None:
        """Deletes an object from storage. Idempotent (does not raise if missing)."""
        ...

    async def delete_many(self, keys: list[str], bucket: str | None = None) -> None:
        """Deletes multiple objects from storage."""
        ...

    async def exists(self, key: str, bucket: str | None = None) -> bool:
        """Checks if an object exists in storage."""
        ...

    async def get_metadata(
        self, key: str, bucket: str | None = None
    ) -> dict[str, Any]:
        """Returns metadata such as size and content type for an object."""
        ...

    async def check_health(self) -> dict[str, Any]:
        """Checks connectivity to object storage."""
        ...


class S3StorageBackend:
    """S3-compatible storage implementation for MinIO, Cloudflare R2, or AWS S3."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str | None = None,
        use_ssl: bool | None = None,
        inputs_bucket: str | None = None,
        outputs_bucket: str | None = None,
        provider: str | None = None,
        public_domain: str | None = None,
        presigned_endpoint_override: str | None = None,
    ) -> None:
        self.session = aioboto3.Session()
        self.endpoint_url = endpoint_url or settings.STORAGE_ENDPOINT
        self.aws_access_key_id = aws_access_key_id or settings.STORAGE_ACCESS_KEY
        self.aws_secret_access_key = aws_secret_access_key or settings.STORAGE_SECRET_KEY
        self.region_name = region_name or settings.STORAGE_REGION
        self.use_ssl = use_ssl if use_ssl is not None else settings.STORAGE_USE_SSL
        self.inputs_bucket = inputs_bucket or settings.STORAGE_BUCKET_INPUTS
        self.outputs_bucket = outputs_bucket or settings.STORAGE_BUCKET_OUTPUTS
        self.provider = (provider or settings.STORAGE_PROVIDER).lower()
        self.public_domain = public_domain or settings.STORAGE_PUBLIC_DOMAIN
        self.presigned_endpoint_override = (
            presigned_endpoint_override or settings.STORAGE_PRESIGNED_ENDPOINT_OVERRIDE
        )

    def _resolve_bucket(self, key: str, bucket: str | None = None) -> str:
        if bucket:
            return bucket
        if key.startswith("outputs/"):
            return self.outputs_bucket
        return self.inputs_bucket

    def _apply_presigned_url_override(self, url: str) -> str:
        """Replace internal endpoint host with externally accessible host if configured."""
        if self.presigned_endpoint_override and self.endpoint_url:
            # Replace configured endpoint_url prefix with presigned_endpoint_override
            from urllib.parse import urlparse
            endpoint_parsed = urlparse(self.endpoint_url)
            override_parsed = urlparse(self.presigned_endpoint_override)
            endpoint_base = f"{endpoint_parsed.scheme}://{endpoint_parsed.netloc}"
            override_base = f"{override_parsed.scheme}://{override_parsed.netloc}"
            if url.startswith(endpoint_base):
                return override_base + url[len(endpoint_base):]
        return url

    def _get_client_context(self):
        s3_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3, "mode": "standard"},
        )
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url if self.endpoint_url else None,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            use_ssl=self.use_ssl,
            config=s3_config,
        )

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        target_bucket = self._resolve_bucket(key, bucket)
        try:
            async with self._get_client_context() as s3:
                await s3.put_object(
                    Bucket=target_bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
                return key
        except Exception as e:
            logger.error(f"Failed to upload {key} to {target_bucket}: {e}")
            raise StorageError(f"Failed to upload object: {str(e)}")

    async def download(self, key: str, bucket: str | None = None) -> bytes:
        target_bucket = self._resolve_bucket(key, bucket)
        try:
            async with self._get_client_context() as s3:
                resp = await s3.get_object(Bucket=target_bucket, Key=key)
                async with resp["Body"] as stream:
                    return await stream.read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise StorageError(f"Object {key} not found in {target_bucket}")
            raise StorageError(f"Failed to download object: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to download {key} from {target_bucket}: {e}")
            raise StorageError(f"Failed to download object: {str(e)}")

    async def generate_presigned_upload_url(
        self,
        key: str,
        expires_in: int = 900,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        target_bucket = bucket or self.inputs_bucket
        try:
            async with self._get_client_context() as s3:
                url = await s3.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": target_bucket,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=expires_in,
                )
                return self._apply_presigned_url_override(url)
        except Exception as e:
            logger.error(f"Failed to generate upload URL for {key}: {e}")
            raise StorageError(f"Failed to generate presigned upload URL: {str(e)}")

    async def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 300,
        filename: str | None = None,
        bucket: str | None = None,
    ) -> str:
        target_bucket = self._resolve_bucket(key, bucket)
        params: dict[str, Any] = {
            "Bucket": target_bucket,
            "Key": key,
        }
        if filename:
            safe_name = filename.replace('"', "").replace("\n", "").replace("\r", "")
            params["ResponseContentDisposition"] = f'attachment; filename="{safe_name}"'

        try:
            async with self._get_client_context() as s3:
                url = await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params=params,
                    ExpiresIn=expires_in,
                )
                return self._apply_presigned_url_override(url)
        except Exception as e:
            logger.error(f"Failed to generate download URL for {key}: {e}")
            raise StorageError(f"Failed to generate presigned download URL: {str(e)}")

    async def delete(self, key: str, bucket: str | None = None) -> None:
        target_bucket = self._resolve_bucket(key, bucket)
        try:
            async with self._get_client_context() as s3:
                await s3.delete_object(Bucket=target_bucket, Key=key)
        except Exception as e:
            logger.warning(f"Failed to delete {key} from {target_bucket}: {e}")

    async def delete_many(self, keys: list[str], bucket: str | None = None) -> None:
        if not keys:
            return
        # Group keys by bucket
        buckets_map: dict[str, list[str]] = {}
        for k in keys:
            b = self._resolve_bucket(k, bucket)
            buckets_map.setdefault(b, []).append(k)

        for b, b_keys in buckets_map.items():
            try:
                async with self._get_client_context() as s3:
                    delete_objects = [{"Key": k} for k in b_keys]
                    await s3.delete_objects(
                        Bucket=b,
                        Delete={"Objects": delete_objects, "Quiet": True},
                    )
            except Exception as e:
                logger.warning(f"Failed to batch delete from {b}: {e}")

    async def exists(self, key: str, bucket: str | None = None) -> bool:
        target_bucket = self._resolve_bucket(key, bucket)
        try:
            async with self._get_client_context() as s3:
                await s3.head_object(Bucket=target_bucket, Key=key)
                return True
        except Exception:
            return False

    async def get_metadata(
        self, key: str, bucket: str | None = None
    ) -> dict[str, Any]:
        target_bucket = self._resolve_bucket(key, bucket)
        try:
            async with self._get_client_context() as s3:
                resp = await s3.head_object(Bucket=target_bucket, Key=key)
                return {
                    "size_bytes": resp.get("ContentLength", 0),
                    "content_type": resp.get("ContentType", ""),
                    "last_modified": resp.get("LastModified"),
                }
        except Exception as e:
            raise StorageError(f"Object metadata not found: {str(e)}")

    async def check_health(self) -> dict[str, Any]:
        """Verify storage connection by listing or inspecting configured buckets."""
        try:
            async with asyncio.timeout(3.0):
                async with self._get_client_context() as s3:
                    try:
                        resp = await s3.list_buckets()
                        buckets = [b["Name"] for b in resp.get("Buckets", [])]
                        return {
                            "status": "connected",
                            "provider": self.provider,
                            "buckets_available": buckets,
                        }
                    except ClientError as ce:
                        # Scoped tokens (such as Cloudflare R2 per-bucket API tokens) may not allow list_buckets
                        error_code = ce.response.get("Error", {}).get("Code", "")
                        if error_code in ("AccessDenied", "403"):
                            await s3.head_bucket(Bucket=self.inputs_bucket)
                            return {
                                "status": "connected",
                                "provider": self.provider,
                                "buckets_available": [self.inputs_bucket, self.outputs_bucket],
                                "scoped_token": True,
                            }
                        raise
        except Exception as e:
            logger.warning(f"Storage health check failed: {e}")
            return {"status": "disconnected", "provider": self.provider, "error": str(e)}

    async def ensure_buckets_exist(self) -> None:
        """Create required buckets if they do not exist (idempotent, tolerant of production permissions)."""
        try:
            async with self._get_client_context() as s3:
                try:
                    existing = await s3.list_buckets()
                    names = {b["Name"] for b in existing.get("Buckets", [])}
                    for bucket in [self.inputs_bucket, self.outputs_bucket]:
                        if bucket not in names:
                            logger.info(f"Creating bucket: {bucket}")
                            try:
                                await s3.create_bucket(Bucket=bucket)
                            except ClientError as ce:
                                code = ce.response.get("Error", {}).get("Code", "")
                                if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                                    raise
                except ClientError as ce:
                    code = ce.response.get("Error", {}).get("Code", "")
                    if code in ("AccessDenied", "403"):
                        # Bucket list not permitted, verify buckets exist with head_bucket
                        for bucket in [self.inputs_bucket, self.outputs_bucket]:
                            try:
                                await s3.head_bucket(Bucket=bucket)
                            except Exception as head_err:
                                logger.warning(f"Could not verify existence of bucket {bucket}: {head_err}")
                    else:
                        raise
        except Exception as e:
            logger.warning(f"Could not auto-create or verify buckets: {e}")


class InMemoryStorageBackend:
    """In-memory storage implementation for unit tests and local mock isolation."""

    def __init__(self) -> None:
        self.buckets: dict[str, dict[str, dict[str, Any]]] = {
            settings.STORAGE_BUCKET_INPUTS: {},
            settings.STORAGE_BUCKET_OUTPUTS: {},
        }
        self.inputs_bucket = settings.STORAGE_BUCKET_INPUTS
        self.outputs_bucket = settings.STORAGE_BUCKET_OUTPUTS

    def _resolve_bucket(self, key: str, bucket: str | None = None) -> str:
        if bucket:
            return bucket
        if key.startswith("outputs/"):
            return self.outputs_bucket
        return self.inputs_bucket

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        b = self._resolve_bucket(key, bucket)
        if b not in self.buckets:
            self.buckets[b] = {}
        self.buckets[b][key] = {
            "data": data,
            "content_type": content_type,
            "size_bytes": len(data),
            "updated_at": datetime.now(UTC),
        }
        return key

    async def download(self, key: str, bucket: str | None = None) -> bytes:
        b = self._resolve_bucket(key, bucket)
        if b not in self.buckets or key not in self.buckets[b]:
            raise StorageError(f"Object {key} not found in {b}")
        return self.buckets[b][key]["data"]

    async def generate_presigned_upload_url(
        self,
        key: str,
        expires_in: int = 900,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        b = self._resolve_bucket(key, bucket)
        return f"http://mock-storage.local/{b}/{key}?upload_expires={expires_in}"

    async def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 300,
        filename: str | None = None,
        bucket: str | None = None,
    ) -> str:
        b = self._resolve_bucket(key, bucket)
        url = f"http://mock-storage.local/{b}/{key}?download_expires={expires_in}"
        if filename:
            url += f"&filename={filename}"
        return url

    async def delete(self, key: str, bucket: str | None = None) -> None:
        b = self._resolve_bucket(key, bucket)
        if b in self.buckets and key in self.buckets[b]:
            del self.buckets[b][key]

    async def delete_many(self, keys: list[str], bucket: str | None = None) -> None:
        for k in keys:
            b = self._resolve_bucket(k, bucket)
            if b in self.buckets:
                self.buckets[b].pop(k, None)

    async def exists(self, key: str, bucket: str | None = None) -> bool:
        b = self._resolve_bucket(key, bucket)
        return b in self.buckets and key in self.buckets[b]

    async def get_metadata(
        self, key: str, bucket: str | None = None
    ) -> dict[str, Any]:
        b = self._resolve_bucket(key, bucket)
        if b not in self.buckets or key not in self.buckets[b]:
            raise StorageError(f"Object {key} not found in {b}")
        item = self.buckets[b][key]
        return {
            "size_bytes": item["size_bytes"],
            "content_type": item["content_type"],
            "last_modified": item["updated_at"],
        }

    async def check_health(self) -> dict[str, Any]:
        return {
            "status": "connected",
            "buckets_available": list(self.buckets.keys()),
        }

    async def ensure_buckets_exist(self) -> None:
        pass


storage_backend: StorageBackend = S3StorageBackend()


def get_storage() -> StorageBackend:
    """Dependency / accessor for storage backend."""
    return storage_backend


def set_storage_backend(backend: StorageBackend) -> None:
    """Allows swapping storage backend (e.g., during tests)."""
    global storage_backend
    storage_backend = backend


async def check_storage_health() -> dict[str, Any]:
    return await storage_backend.check_health()
