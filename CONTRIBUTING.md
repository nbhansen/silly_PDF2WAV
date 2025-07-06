# Contributing to PDF to Audio Converter

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the Issues section
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - System information (OS, Python version, etc.)

### Suggesting Features

1. Check if the feature has already been suggested in the Issues section
2. If not, create a new issue with:
   - A clear, descriptive title
   - Detailed description of the feature
   - Use cases and benefits
   - Any implementation ideas you might have

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Run tests and ensure they pass
5. Update documentation if necessary
6. Submit a pull request

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/nbhansen/pdf_to_audio_app.git
   cd pdf_to_audio_app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy and configure the application:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your settings (API keys, preferences)
   ```

5. Run tests to verify setup:
   ```bash
   ./test-tdd.sh
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints with proper TYPE_CHECKING guards for circular imports
- Write comprehensive docstrings for all functions and classes
- Add robust validation to domain models using `__post_init__`
- Use the Strategy pattern for configurable behaviors (like text chunking)
- Separate concerns clearly (TTS vs LLM, text processing vs audio generation)
- Maintain clean architecture principles with proper dependency injection

### Architecture Guidelines

- **Domain Layer**: No external dependencies, pure business logic
- **Modular Factories**: Use specialized factories (`audio_factory.py`, `text_factory.py`, `tts_factory.py`)
- **Strategy Pattern**: Implement configurable strategies for chunking, timing, etc.
- **Validation**: All domain models must have robust validation with clear error messages
- **Separation**: Keep TTS engines and LLM services clearly separated
- **Interfaces**: Define clear interfaces in `domain/interfaces.py` for all external dependencies

### Testing

The project follows Test-Driven Development (TDD) principles:

1. **Write tests first** for new features (TDD cycle)
2. **Run the full test suite**:
   ```bash
   ./test-tdd.sh              # All 205+ TDD tests
   python run_tests.py all    # All tests with coverage
   ```

3. **Test Categories**:
   - **Domain Models**: Validation, immutability, edge cases
   - **Text Processing**: Chunking strategies, pipeline logic
   - **Audio Processing**: Engine integration, timing strategies
   - **Architecture**: Factory integration, service creation
   - **Integration**: Complete end-to-end workflows

4. **Test Requirements**:
   - All new domain models must have comprehensive validation tests
   - All new strategies must implement the interface and pass strategy tests
   - All new factories must be tested for proper service creation
   - Integration tests must verify complete workflows

5. **Test Commands**:
   ```bash
   ./test-commit.sh           # Pre-commit validation
   python run_tests.py models # Domain model tests
   python run_tests.py architecture # Factory and architecture tests
   ```

### Documentation

- Update README.md if architectural changes are made
- Add docstrings to new functions and classes following Google style
- Update CLAUDE.md for development guidance changes
- Update TESTING.md for new test categories or commands
- Add comments for complex code sections, especially strategy implementations
- Document factory changes and new service integrations

### Adding New Features

#### Text Processing Features
1. Define interface in `domain/interfaces.py`
2. Implement in `domain/text/` (for text-specific logic)
3. Add infrastructure provider if needed
4. Wire through `text_factory.py`
5. Write comprehensive TDD tests

#### Audio Processing Features
1. Define interface if needed
2. Implement in `domain/audio/`
3. Wire through `audio_factory.py`
4. Add timing strategy if applicable
5. Test with both TTS engines

#### New Chunking Strategies
1. Implement `ChunkingStrategy` interface
2. Add to `ChunkingService` registry
3. Add configuration option
4. Write strategy-specific tests
5. Test integration with audio generation

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the CHANGELOG.md with a summary of changes
3. Ensure all tests pass
4. Ensure code style checks pass
5. The PR will be merged once you have the sign-off of at least one maintainer

## Questions?

Feel free to open an issue for any questions about contributing.
