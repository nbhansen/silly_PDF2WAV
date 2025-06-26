"""
Concrete implementation of IFileManager for local file system operations.
Handles file I/O, directory management, and temporary file creation.
"""
import os
import tempfile
from typing import Optional
from datetime import datetime

from domain.interfaces import IFileManager
from domain.models import FileInfo


class FileManager(IFileManager):
    """Manages file I/O, directory paths, and temporary file creation."""

    def __init__(self, upload_folder: str, output_folder: str):
        self.upload_folder = os.path.abspath(upload_folder)
        self.output_folder = os.path.abspath(output_folder)
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

    def get_output_dir(self) -> str:
        """Returns the absolute path to the output directory."""
        return self.output_folder

    def get_upload_dir(self) -> str:
        """Returns the absolute path to the upload directory."""
        return self.upload_folder

    def save_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """Saves content to a temporary file and returns its full path."""
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.output_folder)
        with os.fdopen(fd, 'wb') as tmp:
            tmp.write(content)
        return path

    def save_output_file(self, content: bytes, filename: str) -> str:
        """Saves content to a final output file and returns its full path."""
        if not filename:
            raise ValueError("Filename cannot be empty")

        # Sanitize filename to prevent directory traversal
        base_filename = os.path.basename(filename)
        output_path = os.path.join(self.output_folder, base_filename)

        with open(output_path, "wb") as f:
            f.write(content)

        return output_path

    def delete_file(self, filepath: str) -> None:
        """Deletes a file if it exists."""
        # Security check: ensure path is within managed directories
        abs_path = os.path.abspath(filepath)
        if not (abs_path.startswith(self.output_folder) or abs_path.startswith(self.upload_folder)):
            raise ValueError(f"Cannot delete file outside managed directories: {filepath}")

        if os.path.exists(abs_path):
            os.remove(abs_path)
