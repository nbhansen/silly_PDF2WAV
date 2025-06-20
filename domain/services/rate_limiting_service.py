# domain/services/rate_limiting_service.py
import asyncio
import time
import json
import os
from typing import Dict, Any
from domain.interfaces import ITTSEngine


class RateLimitingService:
    """Service responsible for managing API rate limiting and request throttling"""

    def __init__(self, max_concurrent_requests: int = 4, rate_limits_config: str = "config/rate_limits.json"):
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.last_request_time = 0.0
        self.rate_limits = self._load_rate_limits(rate_limits_config)

    def _load_rate_limits(self, config_path: str) -> Dict:
        """Load rate limits from configuration file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"Loaded rate limits from {config_path}")
                return config.get('rate_limits', {})
            else:
                print(f"Warning: Rate limits config not found at {config_path}, using defaults")
                return {}
        except Exception as e:
            print(f"Warning: Failed to load rate limits from {config_path}: {e}")
            return {}

    def get_base_delay_for_engine(self, tts_engine: ITTSEngine) -> float:
        """Determine appropriate delay based on TTS engine type"""
        engine_type = type(tts_engine).__name__

        # Check configured rate limits first
        if engine_type in self.rate_limits:
            return self.rate_limits[engine_type].get('delay_seconds', 1.0)

        # Fallback to hardcoded defaults
        delays = {
            'GeminiTTSProvider': 2.0,     # Gemini has stricter rate limits
            'OpenAITTSProvider': 1.0,     # OpenAI has moderate limits
            'PiperTTSProvider': 0.1,      # Local TTS, minimal delay
            'CoquiTTSProvider': 0.1,      # Local TTS, minimal delay
        }

        return delays.get(engine_type, 1.0)  # Default 1 second delay

    async def acquire_with_rate_limit(self, base_delay: float) -> None:
        """Acquire semaphore slot with rate limiting"""
        async with self.semaphore:
            # Apply rate limiting delay
            elapsed = time.time() - self.last_request_time
            if elapsed < base_delay:
                sleep_time = base_delay - elapsed
                await asyncio.sleep(sleep_time)

            self.last_request_time = time.time()

    def get_retry_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate exponential backoff delay for retries"""
        return min(base_delay * (2 ** attempt), 30.0)  # Max 30 seconds

    async def execute_with_retry(self, operation, max_retries: int = 3,
                                 base_delay: float = 1.0) -> Any:
        """Execute operation with exponential backoff retry logic"""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                await self.acquire_with_rate_limit(base_delay)
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    retry_delay = self.get_retry_delay(attempt, base_delay)
                    print(f"RateLimitingService: Attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"RateLimitingService: All {max_retries + 1} attempts failed")
                    break

        raise last_exception if last_exception else Exception("Operation failed with unknown error")
