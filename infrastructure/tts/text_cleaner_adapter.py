# infrastructure/tts/text_cleaner_adapter.py
from typing import List
from domain.models import TextCleaner as TextCleanerInterface
from text_processing import TextCleaner as LegacyTextCleaner

class TextCleanerAdapter(TextCleanerInterface):
    """Adapter for existing TextCleaner to implement domain interface"""
    
    def __init__(self, api_key: str, max_chunk_size: int = 100000):
        self._cleaner = LegacyTextCleaner(api_key, max_chunk_size)
    
    def clean_text(self, raw_text: str) -> List[str]:
        return self._cleaner.clean(raw_text)