# test_ssml_complete.py - Comprehensive SSML Testing and Examples
"""
Complete SSML implementation testing and examples for PDF to Audio Converter

This script provides:
1. Unit tests for SSML functionality
2. Integration tests with all TTS engines
3. Real-world usage examples
4. Performance benchmarks
5. Configuration validation
"""

import os
import sys
import time
import tempfile
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.interfaces import SSMLCapability
from domain.services.ssml_generation_service import SSMLGenerationService, AcademicSSMLEnhancer
from domain.config import PiperConfig, GeminiConfig, CoquiConfig, GTTSConfig

class SSMLTestSuite:
    """Comprehensive test suite for SSML functionality"""
    
    def __init__(self):
        self.test_results = {}
        self.sample_texts = self._load_sample_texts()
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete SSML test suite"""
        print("🧪 Starting Comprehensive SSML Test Suite")
        print("=" * 60)
        
        # Test 1: SSML Generation Service
        print("\n1️⃣ Testing SSML Generation Service...")
        self.test_results['ssml_generation'] = self._test_ssml_generation()
        
        # Test 2: TTS Engine SSML Processing
        print("\n2️⃣ Testing TTS Engine SSML Processing...")
        self.test_results['tts_processing'] = self._test_tts_engine_processing()
        
        # Test 3: Academic Content Enhancement
        print("\n3️⃣ Testing Academic Content Enhancement...")
        self.test_results['academic_enhancement'] = self._test_academic_enhancement()
        
        # Test 4: Integration with Text Cleaning
        print("\n4️⃣ Testing Integration with Text Cleaning...")
        self.test_results['text_cleaning_integration'] = self._test_text_cleaning_integration()
        
        # Test 5: Performance and Chunking
        print("\n5️⃣ Testing Performance and Chunking...")
        self.test_results['performance'] = self._test_performance_and_chunking()
        
        # Test 6: Configuration Validation
        print("\n6️⃣ Testing Configuration Validation...")
        self.test_results['configuration'] = self._test_configuration_validation()
        
        # Generate summary
        self._print_test_summary()
        return self.test_results
    
    def _test_ssml_generation(self) -> Dict[str, Any]:
        """Test SSML generation service"""
        results = {'passed': 0, 'failed': 0, 'details': []}
        
        try:
            # Test basic SSML generation
            generator = SSMLGenerationService(SSMLCapability.BASIC)
            basic_result = generator.generate_ssml_for_academic_content(
                self.sample_texts['simple'], SSMLCapability.BASIC
            )
            
            if '<speak>' in basic_result and '<break' in basic_result:
                results['passed'] += 1
                results['details'].append("✅ Basic SSML generation works")
            else:
                results['failed'] += 1
                results['details'].append("❌ Basic SSML generation failed")
            
            # Test advanced SSML generation
            advanced_result = generator.generate_ssml_for_academic_content(
                self.sample_texts['with_numbers'], SSMLCapability.ADVANCED
            )
            
            if '<say-as interpret-as="number">' in advanced_result:
                results['passed'] += 1
                results['details'].append("✅ Advanced SSML number processing works")
            else:
                results['failed'] += 1
                results['details'].append("❌ Advanced SSML number processing failed")
            
            # Test emphasis generation
            if '<emphasis level="moderate">' in advanced_result:
                results['passed'] += 1
                results['details'].append("✅ Emphasis generation works")
            else:
                results['failed'] += 1
                results['details'].append("❌ Emphasis generation failed")
            
            # Test pause generation
            if '<break time=' in advanced_result:
                results['passed'] += 1
                results['details'].append("✅ Pause generation works")
            else:
                results['failed'] += 1
                results['details'].append("❌ Pause generation failed")
                
        except Exception as e:
            results['failed'] += 1
            results['details'].append(f"❌ SSML generation crashed: {e}")
        
        return results
    
    def _test_tts_engine_processing(self) -> Dict[str, Any]:
        """Test SSML processing across different TTS engines"""
        results = {'passed': 0, 'failed': 0, 'details': [], 'engines': {}}
        
        # Test data
        ssml_input = """<speak>
        <p>This is a <emphasis level="moderate">test</emphasis> of SSML processing.</p>
        <break time="1s"/>
        <p>We found <say-as interpret-as="number">73.2</say-as> percent improvement.</p>
        <voice name="alternative">This is unsupported voice.</voice>
        </speak>"""
        
        # Test each engine type
        engines_to_test = [
            ('piper', 'infrastructure.tts.piper_tts_provider', 'PiperTTSProvider', PiperConfig()),
            ('gemini', 'infrastructure.tts.gemini_tts_provider', 'GeminiTTSProvider', GeminiConfig()),
            ('coqui', 'infrastructure.tts.coqui_tts_provider', 'CoquiTTSProvider', CoquiConfig()),
            ('gtts', 'infrastructure.tts.gtts_provider', 'GTTSProvider', GTTSConfig())
        ]
        
        for engine_name, module_path, class_name, config in engines_to_test:
            try:
                # Import and test engine
                module = __import__(module_path, fromlist=[class_name])
                engine_class = getattr(module, class_name)
                
                # Create engine instance
                engine = engine_class(config)
                
                # Test SSML capability detection
                if hasattr(engine, 'get_ssml_capability'):
                    capability = engine.get_ssml_capability()
                    results['engines'][engine_name] = {
                        'capability': capability.value,
                        'supported_tags': engine.get_supported_tags() if hasattr(engine, 'get_supported_tags') else []
                    }
                    
                    # Test SSML processing
                    if hasattr(engine, 'process_ssml'):
                        processed = engine.process_ssml(ssml_input)
                        
                        if capability == SSMLCapability.NONE:
                            # Should strip all SSML
                            if '<' not in processed:
                                results['passed'] += 1
                                results['details'].append(f"✅ {engine_name}: Correctly strips SSML")
                            else:
                                results['failed'] += 1
                                results['details'].append(f"❌ {engine_name}: Failed to strip SSML")
                        else:
                            # Should preserve some SSML
                            if '<speak>' in processed or '<break' in processed:
                                results['passed'] += 1
                                results['details'].append(f"✅ {engine_name}: Preserves supported SSML")
                            else:
                                results['failed'] += 1
                                results['details'].append(f"❌ {engine_name}: Lost all SSML")
                        
                        results['engines'][engine_name]['processed_sample'] = processed[:100] + "..."
                
            except ImportError:
                results['details'].append(f"⚠️ {engine_name}: Engine not available (import failed)")
            except Exception as e:
                results['failed'] += 1
                results['details'].append(f"❌ {engine_name}: Testing failed - {e}")
        
        return results
    
    def _test_academic_enhancement(self) -> Dict[str, Any]:
        """Test academic content enhancement"""
        results = {'passed': 0, 'failed': 0, 'details': []}
        
        try:
            # Test research paper enhancement
            enhancer = AcademicSSMLEnhancer('research_paper')
            enhanced = enhancer.enhance_research_paper(
                self.sample_texts['research_paper'], SSMLCapability.ADVANCED
            )
            
            # Check for academic-specific enhancements
            if '<say-as interpret-as="number">' in enhanced:
                results['passed'] += 1
                results['details'].append("✅ Research paper number enhancement works")
            else:
                results['failed'] += 1
                results['details'].append("❌ Research paper number enhancement failed")
            
            # Test literature review enhancement
            lit_review_enhanced = enhancer.enhance_literature_review(
                self.sample_texts['literature_review'], SSMLCapability.ADVANCED
            )
            
            if '<break time=' in lit_review_enhanced:
                results['passed'] += 1
                results['details'].append("✅ Literature review enhancement works")
            else:
                results['failed'] += 1
                results['details'].append("❌ Literature review enhancement failed")
                
        except Exception as e:
            results['failed'] += 1
            results['details'].append(f"❌ Academic enhancement crashed: {e}")
        
        return results    def _test_text_cleaning_integration(self) -> Dict[str, Any]:
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
        
        return results
    
    def _test_performance_and_chunking(self) -> Dict[str, Any]:
        """Test performance and chunking with SSML"""
        results = {'passed': 0, 'failed': 0, 'details': [], 'performance': {}}
        
        try:
            from domain.services.text_cleaning_service import TextCleaningService
            from domain.services.ssml_generation_service import SSMLGenerationService
            
            # Test chunking with SSML
            ssml_generator = SSMLGenerationService(SSMLCapability.ADVANCED)
            text_cleaner = TextCleaningService(ssml_generator=ssml_generator)
            
            # Generate large SSML content
            large_ssml = """<speak>
            <p>This is a large SSML document for testing chunking performance.</p>
            <break time="1s"/>
            """ + ("<p>Test paragraph with <emphasis>emphasis</emphasis>.</p><break time=\"500ms\"/>" * 100) + "</speak>"
            
            # Test SSML-aware chunking
            start_time = time.time()
            chunks = text_cleaner._chunk_ssml_aware(large_ssml)
            end_time = time.time()
            
            chunking_time = end_time - start_time
            results['performance']['chunking_time'] = chunking_time
            results['performance']['chunks_created'] = len(chunks)
            results['performance']['average_chunk_size'] = sum(len(c) for c in chunks) // len(chunks) if chunks else 0
            
            if chunks and len(chunks) > 1:
                results['passed'] += 1
                results['details'].append(f"✅ SSML chunking works ({len(chunks)} chunks in {chunking_time:.3f}s)")
                
                # Verify chunks are properly formed SSML
                valid_chunks = sum(1 for chunk in chunks if chunk.startswith('<speak>') and chunk.endswith('</speak>'))
                if valid_chunks == len(chunks):
                    results['passed'] += 1
                    results['details'].append("✅ All chunks are properly formed SSML")
                else:
                    results['failed'] += 1
                    results['details'].append(f"❌ Only {valid_chunks}/{len(chunks)} chunks properly formed")
            else:
                results['failed'] += 1
                results['details'].append("❌ SSML chunking failed")
                
        except Exception as e:
            results['failed'] += 1
            results['details'].append(f"❌ Performance testing crashed: {e}")
        
        return results
    
    def _test_configuration_validation(self) -> Dict[str, Any]:
        """Test configuration validation and environment setup"""
        results = {'passed': 0, 'failed': 0, 'details': [], 'configurations': {}}
        
        try:
            from application.composition_root import validate_engine_config, get_ssml_configuration_guide
            
            # Test engine validation
            engines = ['piper', 'gemini', 'coqui', 'gtts']
            
            for engine in engines:
                try:
                    config_result = validate_engine_config(engine)
                    results['configurations'][engine] = config_result
                    
                    if config_result['valid']:
                        results['passed'] += 1
                        results['details'].append(f"✅ {engine}: Configuration valid")
                        
                        if config_result['supports_ssml']:
                            results['details'].append(f"   SSML: {config_result['ssml_capability']}")
                            results['details'].append(f"   Tags: {', '.join(config_result['supported_ssml_tags'][:3])}...")
                    else:
                        results['failed'] += 1
                        results['details'].append(f"❌ {engine}: Configuration invalid - {config_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append(f"❌ {engine}: Validation crashed - {e}")
            
            # Test configuration guide
            guide = get_ssml_configuration_guide()
            if guide and 'ssml_capabilities' in guide:
                results['passed'] += 1
                results['details'].append("✅ Configuration guide available")
            else:
                results['failed'] += 1
                results['details'].append("❌ Configuration guide missing")
                
        except Exception as e:
            results['failed'] += 1
            results['details'].append(f"❌ Configuration validation crashed: {e}")
        
        return results
    
    def _load_sample_texts(self) -> Dict[str, str]:
        """Load sample texts for testing"""
        return {
            'simple': "However, this study demonstrates significant improvements in efficiency.",
            
            'with_numbers': "The results show a 73.2 percent increase in accuracy during 2024, with p < 0.001.",
            
            'research_paper': """Abstract. This study investigates machine learning algorithms for text analysis. 
            However, previous research showed mixed results. We analyzed 1,247 papers published between 2020 and 2024. 
            Results indicate a 95.5 percent improvement in processing speed. Therefore, we conclude that the new approach is effective.""",
            
            'literature_review': """Several studies have investigated this phenomenon (Smith, 2023; Jones, 2024). 
            Similarly, other researchers found comparable results. In contrast, earlier work by Brown (2022) showed different patterns. 
            Conversely, recent meta-analyses suggest a different interpretation.""",
            
            'messy_academic': """
            --- Header: Journal of Advanced Studies ---
            Page 15
            
            This is the actual content of the academic paper that we want to convert to speech.
            It contains various artifacts like [15] citations and (Author, 2023) references.
            
            The methodology showed F(2, 47) = 15.3, p < 0.001.
            
            --- Footer: Copyright 2024 ---
            """
        }
    
    def _print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 SSML Test Suite Summary")
        print("=" * 60)
        
        total_passed = sum(result.get('passed', 0) for result in self.test_results.values())
        total_failed = sum(result.get('failed', 0) for result in self.test_results.values())
        success_rate = (total_passed / (total_passed + total_failed)) * 100 if (total_passed + total_failed) > 0 else 0
        
        print(f"Overall Results: {total_passed} passed, {total_failed} failed")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Detailed results per category
        for category, results in self.test_results.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for detail in results.get('details', []):
                print(f"  {detail}")
        
        # Performance summary
        if 'performance' in self.test_results and 'performance' in self.test_results['performance']:
            perf = self.test_results['performance']['performance']
            print(f"\nPerformance Metrics:")
            print(f"  Chunking Time: {perf.get('chunking_time', 0):.3f}s")
            print(f"  Chunks Created: {perf.get('chunks_created', 0)}")
            print(f"  Average Chunk Size: {perf.get('average_chunk_size', 0)} chars")
        
        # Configuration summary
        if 'configuration' in self.test_results and 'configurations' in self.test_results['configuration']:
            print(f"\nEngine SSML Support:")
            for engine, config in self.test_results['configuration']['configurations'].items():
                if config.get('valid'):
                    capability = config.get('ssml_capability', 'unknown')
                    print(f"  {engine}: {capability}")


class SSMLUsageExamples:
    """Real-world usage examples for SSML functionality"""
    
    def __init__(self):
        self.examples = self._create_examples()
    
    def run_all_examples(self):
        """Run all usage examples"""
        print("📚 SSML Usage Examples")
        print("=" * 40)
        
        for example_name, example_func in self.examples.items():
            print(f"\n🔍 {example_name.replace('_', ' ').title()}")
            print("-" * 30)
            try:
                example_func()
            except Exception as e:
                print(f"❌ Example failed: {e}")
    
    def _create_examples(self) -> Dict[str, callable]:
        """Create example functions"""
        return {
            'basic_ssml_generation': self._example_basic_ssml,
            'academic_paper_processing': self._example_academic_paper,
            'engine_comparison': self._example_engine_comparison,
            'performance_optimization': self._example_performance,
            'configuration_setup': self._example_configuration
        }
    
    def _example_basic_ssml(self):
        """Example: Basic SSML generation"""
        from domain.services.ssml_generation_service import SSMLGenerationService
        
        generator = SSMLGenerationService(SSMLCapability.ADVANCED)
        
        input_text = "However, we found a 73.2 percent increase in efficiency during 2024."
        
        # Generate SSML
        ssml_output = generator.generate_ssml_for_academic_content(input_text, SSMLCapability.ADVANCED)
        
        print("Input:", input_text)
        print("SSML Output:")
        print(ssml_output)
    
    def _example_academic_paper(self):
        """Example: Processing a complete academic paper section"""
        from domain.services.ssml_generation_service import AcademicSSMLEnhancer
        
        enhancer = AcademicSSMLEnhancer('research_paper')
        
        paper_section = """
        Results. The analysis revealed significant differences between groups (F(2, 97) = 15.3, p < 0.001). 
        Specifically, we observed a 73.2 percent improvement in the treatment condition compared to control. 
        However, the effect size was moderate (η² = 0.24). Furthermore, post-hoc analyses indicated 
        that the improvement was most pronounced in the first 2024 quarter.
        """
        
        enhanced = enhancer.enhance_research_paper(paper_section, SSMLCapability.ADVANCED)
        
        print("Original Paper Section:")
        print(paper_section.strip())
        print("\nSSML-Enhanced Version:")
        print(enhanced)
    
    def _example_engine_comparison(self):
        """Example: Comparing SSML output across engines"""
        ssml_input = """<speak>
        <p>This study shows <emphasis level="moderate">significant</emphasis> results.</p>
        <break time="1s"/>
        <p>We found <say-as interpret-as="number">95.5</say-as> percent accuracy.</p>
        <voice name="alternative">This uses voice change.</voice>
        </speak>"""
        
        print("Input SSML:")
        print(ssml_input)
        
        # Test with different engine types (mock)
        engines = {
            'Piper (Basic SSML)': self._mock_piper_processing,
            'Gemini (Full SSML)': self._mock_gemini_processing,
            'gTTS (No SSML)': self._mock_gtts_processing
        }
        
        for engine_name, processor in engines.items():
            print(f"\n{engine_name} Output:")
            try:
                result = processor(ssml_input)
                print(result)
            except Exception as e:
                print(f"Error: {e}")
    
    def _example_performance(self):
        """Example: Performance optimization for large documents"""
        print("Simulating large document processing...")
        
        # Simulate large document
        large_text = "This is a test paragraph. " * 200  # ~5000 chars
        
        print(f"Document size: {len(large_text):,} characters")
        
        # Time chunking process
        start_time = time.time()
        
        from domain.services.text_cleaning_service import TextCleaningService
        text_cleaner = TextCleaningService()
        
        chunks = text_cleaner._chunk_for_audio_optimized(large_text)
        
        end_time = time.time()
        
        print(f"Chunking completed in {end_time - start_time:.3f} seconds")
        print(f"Created {len(chunks)} chunks")
        print(f"Average chunk size: {sum(len(c) for c in chunks) // len(chunks)} characters")
    
    def _example_configuration(self):
        """Example: Setting up SSML configuration"""
        print("Environment Configuration for SSML:")
        
        configs = {
            'High-Quality Academic Papers': {
                'TTS_ENGINE': 'gemini',
                'ENABLE_SSML': 'True',
                'DOCUMENT_TYPE': 'research_paper',
                'VOICE_QUALITY': 'high',
                'GEMINI_VOICE_NAME': 'Kore'
            },
            'Local Processing with SSML': {
                'TTS_ENGINE': 'piper',
                'ENABLE_SSML': 'True',
                'PIPER_MODEL_NAME': 'en_US-lessac-high',
                'VOICE_QUALITY': 'high'
            },
            'Fast Processing without SSML': {
                'TTS_ENGINE': 'gtts',
                'ENABLE_SSML': 'False',
                'VOICE_QUALITY': 'medium'
            }
        }
        
        for config_name, config in configs.items():
            print(f"\n{config_name}:")
            for key, value in config.items():
                print(f"  {key}={value}")
    
    def _mock_piper_processing(self, ssml_text: str) -> str:
        """Mock Piper SSML processing"""
        # Simulate Piper keeping basic SSML, removing unsupported features
        import re
        text = ssml_text
        text = re.sub(r'<voice[^>]*>([^<]*)</voice>', r'\1', text)  # Remove voice tags
        return text
    
    def _mock_gemini_processing(self, ssml_text: str) -> str:
        """Mock Gemini SSML processing"""
        # Gemini supports full SSML
        return ssml_text
    
    def _mock_gtts_processing(self, ssml_text: str) -> str:
        """Mock gTTS SSML processing"""
        # Strip all SSML tags
        import re
        text = re.sub(r'<[^>]+>', '', ssml_text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def main():
    """Main function to run all tests and examples"""
    print("🚀 PDF to Audio Converter - SSML Implementation Test Suite")
    print("=" * 70)
    
    # Run comprehensive tests
    test_suite = SSMLTestSuite()
    test_results = test_suite.run_all_tests()
    
    # Run usage examples
    print("\n" + "=" * 70)
    examples = SSMLUsageExamples()
    examples.run_all_examples()
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎯 Quick Start Guide")
    print("=" * 70)
    
    print("""
1. UPDATE YOUR .env FILE:
   TTS_ENGINE=piper          # or 'gemini' for full SSML
   ENABLE_SSML=True
   VOICE_QUALITY=high
   DOCUMENT_TYPE=research_paper

2. INSTALL DEPENDENCIES:
   pip install piper-tts     # for Piper TTS with SSML
   
3. TEST SSML FUNCTIONALITY:
   python test_ssml_complete.py

4. PROCESS A PDF:
   - Upload via web interface
   - SSML will be automatically applied based on your TTS engine
   - Listen to enhanced audio with natural pauses and emphasis

5. SSML FEATURES BY ENGINE:
   📌 Piper: Basic SSML (breaks, emphasis, prosody)
   📌 Gemini: Full SSML (all features + voice changes)
   📌 Coqui: Basic SSML (model-dependent)
   📌 gTTS: No SSML (tags stripped, converted to pauses)
""")
    
    total_passed = sum(result.get('passed', 0) for result in test_results.values())
    total_failed = sum(result.get('failed', 0) for result in test_results.values())
    
    if total_failed == 0:
        print("🎉 All tests passed! Your SSML implementation is ready to use.")
    else:
        print(f"⚠️ {total_failed} tests failed. Check the output above for details.")
    
    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)