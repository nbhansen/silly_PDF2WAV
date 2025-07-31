"""Concrete implementation of IFileManager for local file system operations.

Handles file I/O, directory management, and temporary file creation.
"""

import os
from pathlib import Path
import tempfile

from domain.interfaces import IFileManager


class FileManager(IFileManager):
    """Manages file I/O, directory paths, and temporary file creation."""

    def __init__(self, upload_folder: str, output_folder: str):
        self.upload_folder = str(Path(upload_folder).resolve())
        self.output_folder = str(Path(output_folder).resolve())
        Path(self.upload_folder).mkdir(parents=True, exist_ok=True)
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)

    def get_output_dir(self) -> str:
        """Returns the absolute path to the output directory."""
        return self.output_folder

    def get_upload_dir(self) -> str:
        """Returns the absolute path to the upload directory."""
        return self.upload_folder

    def save_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """Saves content to a temporary file and returns its full path."""
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.output_folder)
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(content)
        return path

    def save_output_file(self, content: bytes, filename: str) -> str:
        """Saves content to a final output file and returns its full path."""
        if not filename:
            raise ValueError("Filename cannot be empty")

        # Sanitize filename to prevent directory traversal
        base_filename = Path(filename).name
        output_path = Path(self.output_folder) / base_filename

        output_path.write_bytes(content)

        return str(output_path)

    def delete_file(self, filepath: str) -> None:
        """Deletes a file if it exists."""
        # Security check: ensure path is within managed directories
        abs_path = Path(filepath).resolve()
        abs_path_str = str(abs_path)
        if not (abs_path_str.startswith((self.output_folder, self.upload_folder))):
            raise ValueError(f"Cannot delete file outside managed directories: {filepath}")

        if abs_path.exists():
            abs_path.unlink()
