"""Audio duration measurement using ffprobe with file-size fallback."""

import logging
from pathlib import Path
import subprocess  # nosec B404

from domain.errors import Result, audio_generation_error
from domain.interfaces import IAudioDurationMeasurer

logger = logging.getLogger(__name__)


class AudioDurationMeasurer(IAudioDurationMeasurer):
    """Measures audio file duration using ffprobe, with file-size fallback."""

    def get_duration(self, file_path: str) -> Result[float]:
        """Get audio file duration in seconds."""
        try:
            path_obj = Path(file_path)
            if not path_obj.is_file() or path_obj.is_symlink():
                return Result.failure(audio_generation_error(f"Invalid or unsafe file path: {file_path}"))

            # Try ffprobe first (most accurate)
            cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # nosec B603
            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                logger.debug("ffprobe duration for %s: %.2fs", Path(file_path).name, duration)
                return Result.success(duration)

            # Fallback to file size estimation
            file_size = path_obj.stat().st_size
            estimated_duration = file_size / (24000 * 2)  # 24kHz * 2 bytes per sample
            logger.debug(
                "Estimated duration for %s: %.2fs (from %d bytes)", Path(file_path).name, estimated_duration, file_size
            )
            return Result.success(estimated_duration)

        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to get audio duration: {e}"))
