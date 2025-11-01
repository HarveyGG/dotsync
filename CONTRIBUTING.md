# Contributing to dotsync

Thank you for your interest in contributing to dotsync! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/dotsync.git
   cd dotsync
   ```
3. Install in development mode:
   ```bash
   pip install -e .
   ```

## Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Write or update tests as needed
4. Ensure all tests pass:
   ```bash
   pytest tests/
   ```
5. Check for linting errors:
   ```bash
   make lint  # or flake8 dotsync/ tests/
   ```
6. Commit your changes with a clear commit message

## Testing

We use pytest for testing. All new features should include tests.

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_main.py

# Run with verbose output
pytest tests/ -v
```

## Code Style

- Follow PEP 8 style guide
- Use flake8 for linting
- Keep functions focused and well-documented
- Add docstrings for public functions

## Submitting Changes

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a Pull Request on GitHub
3. Provide a clear description of your changes
4. Reference any related issues

## Reporting Bugs

Please open an issue with:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, etc.)

## Feature Requests

Feel free to open an issue to discuss new features. Please include:
- Use case description
- Proposed solution
- Alternatives considered

Thank you for contributing!

