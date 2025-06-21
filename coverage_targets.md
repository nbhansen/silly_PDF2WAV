# Coverage Analysis & Targets

## Current Status (Domain Layer Unit Tests)
- **Total Coverage: 49%**
- **Target: 80%** 
- **Gap: 31 percentage points**

## Coverage by Module

### ✅ Well Tested (80%+)
- `domain/models.py`: **98%** - Excellent domain model coverage
- `domain/interfaces.py`: **100%** - Complete interface coverage  
- `domain/errors.py`: **84%** - Good error handling coverage

### 🔧 Moderate Coverage (40-80%)
- `domain/services/text_cleaning_service.py`: **60%** - Our main tested service

### ❌ Low Coverage (<40%)
- `domain/services/audio_generation_service.py`: **17%** - Critical service, needs tests
- `domain/services/academic_ssml_service.py`: **29%** - SSML logic needs coverage
- `domain/config/tts_config.py`: **0%** - Simple config, easy wins

## Priority Targets for 80% Coverage

### 🎯 High Impact (Easy wins to reach 80%)

1. **AudioGenerationService** (138 statements)
   - Current: 17% coverage
   - Target: 70% coverage  
   - Impact: Major boost to overall coverage
   - Effort: Medium (service orchestration testing)

2. **AcademicSSMLService** (135 statements)
   - Current: 29% coverage
   - Target: 60% coverage
   - Impact: Significant coverage boost
   - Effort: Low (text processing logic)

3. **TTS Config** (22 statements)
   - Current: 0% coverage
   - Target: 90% coverage
   - Impact: Small but easy wins
   - Effort: Very Low (simple config object tests)

### 📊 Coverage Math
- **Current domain coverage**: 49% of 607 statements = 298 covered
- **Target**: 80% of 607 statements = 486 covered  
- **Need to add**: 188 more covered statements

**Strategy**: Focus on AudioGenerationService + AcademicSSMLService + easy config wins
- AudioGenerationService: +70 statements (138 * 0.53 improvement)
- AcademicSSMLService: +42 statements (135 * 0.31 improvement)  
- TTS Config: +20 statements (22 * 0.90)
- **Total gain**: ~132 statements = **71% total coverage**

Add a few more tests to TextCleaningService and smaller services to reach 80%.

## Professional Coverage Standards

### What Real Companies Expect:
- **Core Business Logic**: 90%+ (domain/services)
- **Domain Models**: 95%+ (domain/models) ✅
- **Configuration**: 80%+ (domain/config)
- **Error Handling**: 85%+ (domain/errors) ✅
- **Infrastructure**: 60%+ (less critical)

### Our Current Standing:
- Domain models: **Professional grade** (98%)
- Error handling: **Professional grade** (84%)
- Core services: **Needs improvement** (17-60%)
- Configuration: **Missing** (0%)

## Next Steps:
1. Add AudioGenerationService unit tests (biggest impact)
2. Add AcademicSSMLService unit tests (medium impact)  
3. Add TTS config tests (easy wins)
4. Fill gaps in TextCleaningService (polish existing)

This strategy will take us from 49% → 80%+ coverage efficiently.