# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [V. 0.1]

### Added
- Initial project structure
- Basic PDF to audio conversion functionality
- Support for text-based and image-based PDFs
- OCR capabilities using Tesseract
- Text cleaning using Google Gemini Pro
- Multiple TTS engine support (Coqui TTS, gTTS, Bark)
- Web interface for file upload and audio playback
- GPU acceleration support for TTS
- Development tools and configuration (black, isort, flake8, mypy)
- Pre-commit hooks for code quality
- Package management with setup.py and pyproject.toml
- MIT License
- Contributing guidelines
- Basic documentation

### Changed
- Environment files and some basic cleanup of random crap-functions I use for debugging
- MASSIVE mega-overdrive refactor to use dependency-injection rather than my ahem prototype-code. Thanks Roo-code. 

### Deprecated
- None yet

### Removed
- None yet

### Fixed
- None yet

### Security
- None yet 