"""
Storage abstraction (docs/01 §2, docs/06 §3).

Two backends behind one interface:

- Local disk (dev default, USE_LOCAL_STORAGE=true): files land under
  LOCAL_UPLOAD_DIR and are served by the StaticFiles mount in main.py.
- Supabase Storage (prod, USE_LOCAL_STORAGE=false): plain httpx calls against
  the Storage REST API. Deliberately NOT the supabase python SDK — the API is
  a simple POST/DELETE with the service key as Bearer, and keeping the SDK out
  keeps the serverless bundle small. The bucket is public-read (student
  photos, question images), so upload returns the public CDN URL and exam
  clients fetch images with zero backend involvement.

Images are normalized BEFORE upload (docs/06 §3) on both backends: longest
side capped at 1000 px, re-encoded JPEG/WebP quality 80 (~60-120 KB each), so
the 1 GB free Storage quota holds ~8-15k images.
"""

import io
import uuid
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

import httpx
from PIL import Image

from app.config import settings

# docs/06 §3: resize on upload with Pillow (<= ~1000 px, WebP/JPEG q80)
MAX_IMAGE_DIMENSION = 1000
IMAGE_QUALITY = 80


def _process_image(content: bytes) -> Optional[Tuple[bytes, str, str]]:
    """
    If `content` is an image, resize (longest side <= MAX_IMAGE_DIMENSION) and
    re-encode at quality 80. Transparent images become WebP (keeps alpha);
    everything else becomes JPEG.

    Returns (bytes, extension, content_type), or None when content is not an
    image (non-images pass through upload untouched).
    """
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception:
        return None

    if max(img.size) > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

    out = io.BytesIO()
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if has_alpha:
        img = img.convert("RGBA")
        img.save(out, format="WEBP", quality=IMAGE_QUALITY)
        return out.getvalue(), "webp", "image/webp"

    img = img.convert("RGB")
    img.save(out, format="JPEG", quality=IMAGE_QUALITY, optimize=True)
    return out.getvalue(), "jpg", "image/jpeg"


class StorageService:
    """Local-disk or Supabase Storage uploads behind one interface."""

    def __init__(self):
        self.use_local = settings.USE_LOCAL_STORAGE
        self.local_dir = settings.LOCAL_UPLOAD_DIR

        # Ensure local upload directory exists
        if self.use_local:
            Path(self.local_dir).mkdir(parents=True, exist_ok=True)

    def upload_file(self, file: BinaryIO, folder: str, filename: str = None) -> str:
        """
        Upload a file to storage (local or Supabase).

        Images are resized/re-encoded first (docs/06 §3) regardless of
        backend. Stored names are always fresh UUIDs (no collisions, no
        client-controlled paths); `filename` only contributes the extension
        for non-image files.

        Returns the URL to access the uploaded file: a /uploads/... path for
        local storage, a public Storage CDN URL for Supabase.
        """
        content = file.read()

        processed = _process_image(content)
        if processed is not None:
            content, ext, content_type = processed
        else:
            source_name = filename or getattr(file, "filename", "") or ""
            ext = source_name.rsplit(".", 1)[-1].lower() if "." in source_name else "bin"
            content_type = "application/octet-stream"

        stored_name = f"{uuid.uuid4()}.{ext}"

        if self.use_local:
            return self._upload_local(content, folder, stored_name)
        return self._upload_supabase(content, content_type, folder, stored_name)

    def _upload_local(self, content: bytes, folder: str, filename: str) -> str:
        """Write bytes to the local uploads directory (dev)."""
        folder_path = Path(self.local_dir) / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        with open(folder_path / filename, "wb") as f:
            f.write(content)

        # Served by the StaticFiles mount in main.py (local dev only)
        return f"/uploads/{folder}/{filename}"

    # --- Supabase Storage REST (no SDK) -----------------------------------
    # Upload:  POST   {SUPABASE_URL}/storage/v1/object/{bucket}/{path}
    # Delete:  DELETE {SUPABASE_URL}/storage/v1/object/{bucket}/{path}
    # Public:  GET    {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}
    # Auth: service_role key as Bearer (server-side only, never shipped to
    # the browser).

    def _supabase_headers(self, content_type: Optional[str] = None) -> dict:
        headers = {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _upload_supabase(
        self, content: bytes, content_type: str, folder: str, filename: str
    ) -> str:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "Supabase storage is not configured: set SUPABASE_URL and "
                "SUPABASE_SERVICE_KEY (or USE_LOCAL_STORAGE=true for dev)"
            )
        base = settings.SUPABASE_URL.rstrip("/")
        bucket = settings.SUPABASE_STORAGE_BUCKET
        object_path = f"{folder}/{filename}"

        response = httpx.post(
            f"{base}/storage/v1/object/{bucket}/{object_path}",
            content=content,
            headers={**self._supabase_headers(content_type), "x-upsert": "true"},
            timeout=30.0,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase Storage upload failed ({response.status_code}): "
                f"{response.text[:300]}"
            )

        # Public-read bucket: return the CDN URL clients fetch directly.
        return f"{base}/storage/v1/object/public/{bucket}/{object_path}"

    def delete_file(self, file_url: str) -> bool:
        """Delete a file from storage given the URL upload_file returned."""
        if self.use_local:
            return self._delete_local(file_url)
        return self._delete_supabase(file_url)

    def _delete_local(self, file_url: str) -> bool:
        """Delete file from local filesystem"""
        try:
            # Extract path from URL (/uploads/folder/filename)
            file_path = Path(self.local_dir).parent / file_url.lstrip('/')
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def _delete_supabase(self, file_url: str) -> bool:
        """Delete by public URL: .../object/public/{bucket}/{path}."""
        base = settings.SUPABASE_URL.rstrip("/")
        bucket = settings.SUPABASE_STORAGE_BUCKET
        prefix = f"{base}/storage/v1/object/public/{bucket}/"
        if not file_url.startswith(prefix):
            return False
        object_path = file_url[len(prefix):]

        try:
            response = httpx.delete(
                f"{base}/storage/v1/object/{bucket}/{object_path}",
                headers=self._supabase_headers(),
                timeout=30.0,
            )
            return response.status_code < 400
        except httpx.HTTPError as e:
            print(f"Error deleting file from Supabase Storage: {e}")
            return False


# Create singleton instance
storage = StorageService()
