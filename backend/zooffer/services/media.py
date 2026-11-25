from __future__ import annotations

import hashlib
import io
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import anyio
import anyio.to_thread
from PIL import Image, ImageOps

from zooffer.config import settings
from zooffer.core.errors import ValidationAppError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGES_PER_ANIMAL = 10
FULL_SIZE = (1600, 2000)
THUMB_SIZE = (640, 800)


class MediaStorage(Protocol):
    async def save(self, key: str, data: bytes, content_type: str) -> None: ...
    async def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...


def _resolve_media_root(value: str | Path) -> Path:
    """Resolve relative media paths against the repository root.

    The backend may be started from either the repository root or ``backend/``;
    relative media paths must not silently point at different directories.
    """
    path = Path(value)
    if path.is_absolute():
        return path
    repository_root = Path(__file__).resolve().parents[3]
    return (repository_root / path).resolve()


class LocalMediaStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = _resolve_media_root(root or settings.media_local_path)

    def _path(self, key: str) -> Path:
        # Keys are generated server-side; still defend against traversal.
        if ".." in key or key.startswith("/") or "\\" in key:
            raise ValidationAppError("Некорректный файл", code="invalid_media_key")
        return self.root / key

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def read(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise ValidationAppError("Файл не найден", code="media_not_found", status_code=404)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class S3MediaStorage:
    def __init__(self) -> None:
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValidationAppError(
                "boto3 не установлен", code="s3_unavailable", status_code=503
            ) from exc
        self.bucket = settings.s3_bucket
        if not self.bucket:
            raise ValidationAppError(
                "S3 bucket не настроен", code="s3_unconfigured", status_code=503
            )
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
        )

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        import anyio

        def _put() -> None:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

        await anyio.to_thread.run_sync(_put)

    async def read(self, key: str) -> bytes:
        import anyio

        def _get() -> bytes:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()

        try:
            return await anyio.to_thread.run_sync(_get)
        except Exception as exc:
            raise ValidationAppError(
                "Файл не найден", code="media_not_found", status_code=404
            ) from exc

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_storage() -> MediaStorage:
    if settings.media_backend == "s3":
        return S3MediaStorage()
    return LocalMediaStorage()


@dataclass(slots=True)
class ProcessedImage:
    full_key: str
    thumb_key: str
    width: int
    height: int
    content_hash: str


INVALID_IMAGE_MESSAGE = "Поддерживаются только JPG, PNG и WebP"


def _validate_and_normalise(content: bytes) -> Image.Image:
    if not content:
        raise ValidationAppError("Пустой файл", code="empty_upload")
    if len(content) > settings.max_upload_bytes:
        raise ValidationAppError("Файл слишком большой", code="file_too_large")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content))
    except Exception as exc:
        raise ValidationAppError(INVALID_IMAGE_MESSAGE, code="invalid_image") from exc
    if image.format not in ALLOWED_FORMATS:
        raise ValidationAppError(INVALID_IMAGE_MESSAGE, code="invalid_image")
    width, height = image.size
    if width <= 0 or height <= 0 or width * height > settings.max_image_pixels:
        raise ValidationAppError("Слишком большое изображение", code="image_too_large")
    if width < 200 or height < 200:
        raise ValidationAppError("Изображение слишком маленькое", code="image_too_small")
    # Re-encoding below strips EXIF/GPS and any embedded payloads.
    return ImageOps.exif_transpose(image).convert("RGB")


def _fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def _webp_bytes(image: Image.Image, quality: int = 82) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=4, exif=b"")
    return buffer.getvalue()


def _process_bytes(content: bytes) -> tuple[Image.Image, bytes, bytes]:
    """CPU-bound Pillow pipeline, run in a worker thread."""
    image = _validate_and_normalise(content)
    full = _fit(image, FULL_SIZE)
    thumb = _fit(image, THUMB_SIZE)
    return full, _webp_bytes(full), _webp_bytes(thumb, quality=78)


async def process_and_store_image(content: bytes, *, prefix: str = "animals") -> ProcessedImage:
    # Pillow decodes/encodes synchronously; keep the event loop responsive.
    full, full_bytes, thumb_bytes = await anyio.to_thread.run_sync(_process_bytes, content)
    token = uuid.uuid4().hex
    base = f"{prefix}/{token[:2]}/{token}"
    full_key = f"{base}/full.webp"
    thumb_key = f"{base}/thumb.webp"
    storage = get_storage()
    await storage.save(full_key, full_bytes, "image/webp")
    await storage.save(thumb_key, thumb_bytes, "image/webp")
    return ProcessedImage(
        full_key=full_key,
        thumb_key=thumb_key,
        width=full.width,
        height=full.height,
        content_hash=hashlib.sha256(full_bytes).hexdigest(),
    )


def media_url(key: str) -> str:
    base = settings.media_cdn_base_url or settings.media_public_base_url
    return f"{base.rstrip('/')}/media/{key}"


def thumb_key_for(full_key: str) -> str:
    return full_key.rsplit("/", 1)[0] + "/thumb.webp"
