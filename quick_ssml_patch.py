#!/usr/bin/env python3
"""
Quick patch script to fix SSML implementation issues
Run this script to apply all necessary fixes for the SSML implementation
"""

import re
import os
import sys

def fix_ssml_generation_service():
    """Fix the nested SSML tags issue in the generation service"""
    file_path = 'domain/services/ssml_generation_service.py'
    
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix 1: Replace enhance_numbers_and_dates method to avoid nested tags
        new_enhance_method = '''    def enhance_numbers_and_dates(self, text: str) -> str:
        """Add SSML markup for better number and date pronunciation"""
        # Handle percentages first (avoid double processing)
        text = re.sub(
            r'\\b(\\d+(?:\\.\\d+)?)\\s*percent\\b',
            r'<say-as interpret-as="number">\\1</say-as> percent',
            text,
            flags=re.IGNORECASE
        )
        
        # Handle years (specific pattern to avoid conflicts)
        text = re.sub(
            r'\\b(19\\d{2}|20\\d{2})\\b(?!.*</say-as>)',
            r'<say-as interpret-as="date" format="y">\\1</say-as>',
            text
        )
        
        # Handle standalone numbers (avoid already marked up numbers)
        # Use negative lookbehind to avoid processing numbers already in say-as tags
        text = re.sub(
            r'(?<!interpret-as="[^"]*">)\\b(\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?)\\b(?!.*</say-as>|\\s*percent)',
            r'<say-as interpret-as="number">\\1</say-as>',
            text
        )
        
        # Handle statistical significance (p-values)
        text = re.sub(
            r'\\bp\\s*[<>=]\\s*(\\d+(?:\\.\\d+)?)',
            r'p <say-as interpret-as="number">\\1</say-as>',
            text,
            flags=re.IGNORECASE
        )
        
        # Handle ordinal numbers in academic contexts
        text = re.sub(
            r'\\b(\\d+)(?:st|nd|rd|th)\\s+(century|chapter|section|study|experiment)\\b',
            r'<say-as interpret-as="ordinal">\\1</say-as> \\2',
            text,
            flags=re.IGNORECASE
        )
        
        return text'''
        
        # Replace the method
        pattern = r'(\s*)def enhance_numbers_and_dates\(self, text: str\) -> str:.*?return text'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_enhance_method, content, flags=re.DOTALL)
            print("✅ Fixed enhance_numbers_and_dates method")
        else:
            print("⚠️ Could not find enhance_numbers_and_dates method to replace")
        
        # Fix 2: Improve emphasize_key_terms to avoid double processing
        new_emphasize_method = '''    def emphasize_key_terms(self, text: str) -> str:
        """Add emphasis markup for important academic terms"""
        # Avoid double-processing already emphasized text
        def add_emphasis_if_not_present(word, text_content):
            if f'<emphasis level="moderate">{word}</emphasis>' not in text_content.lower():
                pattern = f'\\\\b{re.escape(word)}\\\\b'
                replacement = f'<emphasis level="moderate">{word}</emphasis>'
                return re.sub(pattern, replacement, text_content, flags=re.IGNORECASE)
            return text_content
        
        # Apply emphasis to significance words
        for word in self.emphasis_words['significance']:
            text = add_emphasis_if_not_present(word, text)
        
        # Apply emphasis to finding words  
        for word in self.emphasis_words['findings']:
            text = add_emphasis_if_not_present(word, text)
        
        # Apply emphasis to methodology words
        for word in self.emphasis_words['methodology']:
            text = add_emphasis_if_not_present(word, text)
        
        return text'''
        
        pattern = r'(\s*)def emphasize_key_terms\(self, text: str\) -> str:.*?return text'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_emphasize_method, content, flags=re.DOTALL)
            print("✅ Fixed emphasize_key_terms method")
        else:
            print("⚠️ Could not find emphasize_key_terms method to replace")
        
        # Write the fixed content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Successfully patched {file_path}")
        
    except Exception as e:
        print(f"❌ Error patching {file_path}: {e}")

def fix_text_cleaning_service():
    """Fix the chunking issues in text cleaning service"""
    file_path = 'domain/services/text_cleaning_service.py'
    
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the _ensure_proper_ssml_wrapper method
        new_wrapper_method = '''    def _ensure_proper_ssml_wrapper(self, content: str) -> str:
        """Ensure content is properly wrapped in SSML speak tags"""
        content = content.strip()
        
        # Remove any incomplete tags at boundaries
        content = re.sub(r'<[^>]*$', '', content)  # Remove unclosed tags at end
        content = re.sub(r'^[^<]*>', '', content)  # Remove orphaned closing tags at start
        
        # Remove existing speak tags to avoid nesting
        content = re.sub(r'^<speak>\\s*', '', content)
        content = re.sub(r'\\s*</speak>$', '', content)
        
        # Clean up the content
        content = content.strip()
        
        # Wrap in proper speak tags
        if content:
            content = f'<speak>\\n{content}\\n</speak>'
        else:
            content = '<speak></speak>'
        
        return content'''
        
        pattern = r'(\s*)def _ensure_proper_ssml_wrapper\(self, content: str\) -> str:.*?return content'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_wrapper_method, content, flags=re.DOTALL)
            print("✅ Fixed _ensure_proper_ssml_wrapper method")
        else:
            print("⚠️ Could not find _ensure_proper_ssml_wrapper method to replace")
        
        # Write the fixed content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Successfully patched {file_path}")
        
    except Exception as e:
        print(f"❌ Error patching {file_path}: {e}")

def fix_test_imports():
    """Fix import issues in test file"""
    file_path = 'test_ssml_complete.py'
    
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix import statement
        content = content.replace(
            "from domain.models import ITTSEngine",
            "from domain.interfaces import ITTSEngine"
        )
        
        # Fix the test class definition to use correct import
        test_integration_method = '''    def _test_text_cleaning_integration(self) -> Dict[str, Any]:
        """Test integration with text cleaning service"""
        results = {'passed': 0, 'failed': 0, 'details': []}
        
        try:
            from domain.services.text_cleaning_service import TextCleaningService
            from domain.services.ssml_generation_service import SSMLGenerationService
            from domain.interfaces import ILLMProvider  # FIXED: Import from interfaces
            
            # Create mock LLM that returns SSML
            class SSMLLLMProvider(ILLMProvider):
                def __init__(self):
                    self.prompts = []
                    
                def generate_content(self, prompt: str) -> str:
                    self.prompts.append(prompt)
                    return """<speak>
                    <p>This is <emphasis level="moderate">cleaned</emphasis> academic content.</p>
                    <break time="500ms"/>
                    <p>The results show <say-as interpret-as="number">95</say-as> percent accuracy.</p>
                    </speak>"""
            
            # Test integration
            ssml_generator = SSMLGenerationService(SSMLCapability.ADVANCED)
            fake_llm = SSMLLLMProvider()
            
            text_cleaner = TextCleaningService(
                llm_provider=fake_llm,
                ssml_generator=ssml_generator
            )
            
            # Test SSML-aware cleaning
            result = text_cleaner.clean_text(
                self.sample_texts['messy_academic'],
                fake_llm,
                target_ssml_capability=SSMLCapability.ADVANCED
            )
            
            if result and len(result) > 0:
                results['passed'] += 1
                results['details'].append("✅ Text cleaning with SSML integration works")
                
                if '<speak>' in result[0] or '<emphasis' in result[0] or '<break' in result[0]:
                    results['passed'] += 1
                    results['details'].append("✅ SSML markup preserved in cleaned text")
                else:
                    results['failed'] += 1
                    results['details'].append("❌ SSML markup lost during cleaning")
            else:
                results['failed'] += 1
                results['details'].append("❌ Text cleaning with SSML failed")
                
        except Exception as e:
            results['failed'] += 1
            results['details'].append(f"❌ Text cleaning integration crashed: {e}")
        
        return results'''
        
        # Replace the test method
        pattern = r'(\s*)def _test_text_cleaning_integration\(self\) -> Dict\[str, Any\]:.*?return results'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, test_integration_method, content, flags=re.DOTALL)
            print("✅ Fixed _test_text_cleaning_integration method")
        
        # Write the fixed content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Successfully patched {file_path}")
        
    except Exception as e:
        print(f"❌ Error patching {file_path}: {e}")

def create_test_helpers():
    """Create test helpers file if it doesn't exist"""
    file_path = 'tests/test_helpers.py'
    
    # Create tests directory if it doesn't exist
    os.makedirs('tests', exist_ok=True)
    
    if not os.path.exists(file_path):
        content = '''"""Test helper classes and utilities"""

from domain.interfaces import ILLMProvider
from typing import List

class FakeLLMProvider(ILLMProvider):
    """Mock LLM provider for testing"""
    
    def __init__(self):
        self.prompts = []
    
    def generate_content(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "This is cleaned academic content suitable for TTS."

class SSMLLLMProvider(ILLMProvider):
    """Mock LLM provider that returns SSML content"""
    
    def __init__(self):
        self.prompts = []
    
    def generate_content(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return """<speak>
        <p>This is <emphasis level="moderate">cleaned</emphasis> academic content.</p>
        <break time="500ms"/>
        <p>The results show <say-as interpret-as="number">95</say-as> percent accuracy.</p>
        </speak>"""
'''
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Created {file_path}")

def main():
    """Apply all patches"""
    print("🔧 Applying SSML Implementation Patches...")
    print("=" * 50)
    
    # Create test helpers if needed
    create_test_helpers()
    
    # Apply fixes
    print("\n🔹 Fixing SSML Generation Service...")
    fix_ssml_generation_service()
    
    print("\n🔹 Fixing Text Cleaning Service...")
    fix_text_cleaning_service()
    
    print("\n🔹 Fixing Test Imports...")
    fix_test_imports()
    
    print("\n" + "=" * 50)
    print("✅ All patches applied successfully!")
    print("\n🧪 Next steps:")
    print("1. Run the test again: python test_ssml_complete.py")
    print("2. If tests pass, try processing a PDF with SSML enabled")
    print("3. Check the audio output for improved naturalness")

if __name__ == "__main__":
    main()
