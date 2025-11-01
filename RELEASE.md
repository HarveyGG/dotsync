# Release Guide

This guide explains how to release a new version of dotsync.

## Pre-Release Checklist

- [ ] All tests pass: `pytest tests/`
- [ ] Update version in `dotsync/info.py`
- [ ] Update CHANGELOG.md (if you maintain one)
- [ ] Review and update README.md if needed
- [ ] Ensure all documentation is up to date

## Creating a Release

### 1. Update Version

Edit `dotsync/info.py`:
```python
__version__ = '2.2.10'  # or your new version
```

### 2. Commit and Tag

```bash
git add dotsync/info.py
git commit -m "Bump version to 2.2.10"
git tag -a v2.2.10 -m "Release version 2.2.10"
git push origin main
git push origin v2.2.10
```

### 3. GitHub Actions

The GitHub Actions workflow will automatically:
- Build the Python package
- Publish to PyPI (if PYPI_API_TOKEN is set)
- Create a GitHub release

### 4. Homebrew Formula

If you want to add this to Homebrew:

1. Create a tap repository (or use existing):
   ```bash
   brew tap HarveyGG/dotsync https://github.com/HarveyGG/homebrew-dotsync
   ```

2. Update the formula with the new version and SHA256:
   ```bash
   cd /path/to/homebrew-dotsync
   # Update dotsync.rb with new version and SHA256
   ```

3. Calculate SHA256:
   ```bash
   curl -L https://github.com/HarveyGG/dotsync/archive/v2.2.10.tar.gz | shasum -a 256
   ```

## Manual PyPI Release

If you need to release manually:

```bash
# Build package
python3 -m pip install --upgrade build twine
python3 -m build

# Check package
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

## Post-Release

- [ ] Verify installation works: `pip install --upgrade dotsync`
- [ ] Test on clean environment
- [ ] Announce release (if significant)

