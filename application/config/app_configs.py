# application/config/app_configs.py
"""Application-level configuration classes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FlaskConfig:
    """Flask application configuration."""

    debug: bool = True
    host: str = "127.0.0.1"  # Secure default: localhost only
    port: int = 5000
