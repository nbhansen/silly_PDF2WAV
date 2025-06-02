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

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all functions and classes
- Format code using black
- Sort imports using isort
- Run mypy for type checking
- Run flake8 for linting

### Testing

1. Write tests for new features
2. Ensure all tests pass:
   ```bash
   pytest
   ```
3. Check test coverage:
   ```bash
   pytest --cov=pdf_to_audio
   ```

### Documentation

- Update README.md if necessary
- Add docstrings to new functions and classes
- Update API documentation if needed
- Add comments for complex code sections

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the CHANGELOG.md with a summary of changes
3. Ensure all tests pass
4. Ensure code style checks pass
5. The PR will be merged once you have the sign-off of at least one maintainer

## Questions?

Feel free to open an issue for any questions about contributing. 