from __future__ import annotations

import hashlib
import io
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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


def get_storage() -> MediaStorage:
    # Only the local-disk adapter exists today. Production object storage (S3-compatible) is
    # not implemented and remains blocked on credentials and a deployment target (B9).
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


async def process_and_store_image(content: bytes, *, prefix: str = "animals") -> ProcessedImage:
    image = _validate_and_normalise(content)
    full = _fit(image, FULL_SIZE)
    thumb = _fit(image, THUMB_SIZE)
    full_bytes = _webp_bytes(full)
    thumb_bytes = _webp_bytes(thumb, quality=78)
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
    return f"{settings.media_public_base_url.rstrip('/')}/media/{key}"


def thumb_key_for(full_key: str) -> str:
    return full_key.rsplit("/", 1)[0] + "/thumb.webp"
