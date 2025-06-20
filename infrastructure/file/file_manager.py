"""
A concrete implementation of the IFileManager interface for handling
local file system operations.
"""
import os
import tempfile
from typing import Dict, Optional
from datetime import datetime, timedelta

# Correctly import the interface
from domain.interfaces import IFileManager
from domain.models import FileInfo

# Correctly inherit from the IFileManager interface


class FileManager(IFileManager):
    """Manages file I/O, pathing, and temporary file creation."""

    def __init__(self, upload_folder: str, output_folder: str):
        self.upload_folder = os.path.abspath(upload_folder)
        self.output_folder = os.path.abspath(output_folder)
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        print(f"FileManager initialized. Uploads: '{self.upload_folder}', Outputs: '{self.output_folder}'")

    def get_upload_dir(self) -> str:
        """Returns the absolute path to the upload directory."""
        return self.upload_folder

    def get_output_dir(self) -> str:
        """Returns the absolute path to the output directory."""
        return self.output_folder

    def save_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """Saves content to a temporary file and returns its full path."""
        # Use tempfile for secure temporary file creation
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.output_folder)
        with os.fdopen(fd, 'wb') as tmp:
            tmp.write(content)
        return path

    def save_output_file(self, content: bytes, filename: str) -> str:
        """Saves content to a final output file and returns its full path."""
        if not filename:
            raise ValueError("Filename cannot be empty.")

        # Sanitize filename to prevent directory traversal
        base_filename = os.path.basename(filename)
        output_path = os.path.join(self.output_folder, base_filename)

        with open(output_path, "wb") as f:
            f.write(content)

        print(f"Saved output file: {output_path}")
        return output_path

    def delete_file(self, filepath: str) -> bool:
        """Deletes a file if it exists."""
        try:
            # For security, ensure path is within our managed folders
            abs_path = os.path.abspath(filepath)
            if not (abs_path.startswith(self.output_folder) or abs_path.startswith(self.upload_folder)):
                print(f"Security Warning: Attempted to delete file outside managed directories: {filepath}")
                return False

            if os.path.exists(abs_path):
                os.remove(abs_path)
                print(f"Deleted file: {filepath}")
                return True
            return False
        except OSError as e:
            print(f"Error deleting file {filepath}: {e}")
            return False

    def get_file_info(self, filename: str) -> Optional[FileInfo]:
        """Gets information for a file in the output directory."""
        filepath = os.path.join(self.output_folder, filename)
        if not os.path.exists(filepath):
            return None

        stat = os.stat(filepath)
        return FileInfo(
            name=filename,
            path=filepath,
            size_mb=stat.st_size / (1024 * 1024),
            created_at=datetime.fromtimestamp(stat.st_ctime)
        )
