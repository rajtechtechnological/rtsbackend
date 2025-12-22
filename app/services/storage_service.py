import os
from pathlib import Path
from typing import BinaryIO
from app.config import settings
import uuid


class StorageService:
    """
    Abstracted storage service that handles both local and cloud storage
    """

    def __init__(self):
        self.use_local = settings.USE_LOCAL_STORAGE
        self.local_dir = settings.LOCAL_UPLOAD_DIR

        # Ensure local upload directory exists
        if self.use_local:
            Path(self.local_dir).mkdir(parents=True, exist_ok=True)

    def upload_file(self, file: BinaryIO, folder: str, filename: str = None) -> str:
        """
        Upload file to storage (local or cloud)

        Args:
            file: Binary file object
            folder: Folder/category (e.g., 'photos', 'certificates', 'payslips')
            filename: Optional custom filename

        Returns:
            URL to access the uploaded file
        """
        if self.use_local:
            return self._upload_local(file, folder, filename)
        else:
            return self._upload_cloudinary(file, folder, filename)

    def _upload_local(self, file: BinaryIO, folder: str, filename: str = None) -> str:
        """Upload file to local filesystem"""

        # Generate unique filename if not provided
        if filename is None:
            ext = file.filename.split('.')[-1] if hasattr(file, 'filename') else 'bin'
            filename = f"{uuid.uuid4()}.{ext}"

        # Create folder path
        folder_path = Path(self.local_dir) / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        # Full file path
        file_path = folder_path / filename

        # Write file
        with open(file_path, "wb") as f:
            content = file.read()
            f.write(content)

        # Return relative URL path
        return f"/uploads/{folder}/{filename}"

    def _upload_cloudinary(self, file: BinaryIO, folder: str, filename: str = None) -> str:
        """Upload file to Cloudinary (for production)"""
        # TODO: Implement Cloudinary upload when moving to production
        # This will require the cloudinary package
        raise NotImplementedError("Cloudinary upload not yet implemented")

    def delete_file(self, file_url: str) -> bool:
        """Delete file from storage"""
        if self.use_local:
            return self._delete_local(file_url)
        else:
            return self._delete_cloudinary(file_url)

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

    def _delete_cloudinary(self, file_url: str) -> bool:
        """Delete file from Cloudinary"""
        # TODO: Implement Cloudinary deletion
        raise NotImplementedError("Cloudinary deletion not yet implemented")


# Create singleton instance
storage = StorageService()
