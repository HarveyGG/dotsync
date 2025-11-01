#!/bin/bash
#
# Version Bump Script for dotsync
# Usage: ./scripts/bump_version.sh [major|minor|patch|VERSION]
#
# Examples:
#   ./scripts/bump_version.sh patch     # 2.2.9 -> 2.2.10
#   ./scripts/bump_version.sh minor     # 2.2.9 -> 2.3.0
#   ./scripts/bump_version.sh major     # 2.2.9 -> 3.0.0
#   ./scripts/bump_version.sh 2.3.0     # Set to specific version
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
info() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
section() { echo ""; echo -e "${BLUE}━━━ $1 ━━━${NC}"; }

# Get current version from info.py
get_current_version() {
    grep "__version__ = " dotsync/info.py | cut -d "'" -f 2
}

# Parse version string into components
parse_version() {
    local version=$1
    MAJOR=$(echo "$version" | cut -d. -f1)
    MINOR=$(echo "$version" | cut -d. -f2)
    PATCH=$(echo "$version" | cut -d. -f3)
}

# Calculate new version
calculate_new_version() {
    local bump_type=$1
    local current=$2
    
    parse_version "$current"
    
    case "$bump_type" in
        major)
            NEW_VERSION="$((MAJOR + 1)).0.0"
            ;;
        minor)
            NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
            ;;
        patch)
            NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
            ;;
        *)
            # Assume it's a specific version
            if [[ "$bump_type" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                NEW_VERSION="$bump_type"
            else
                error "Invalid version format. Use: major|minor|patch|X.Y.Z"
            fi
            ;;
    esac
}

# Update version in info.py
update_info_py() {
    local version=$1
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/__version__ = '.*'/__version__ = '$version'/" dotsync/info.py
    else
        sed -i "s/__version__ = '.*'/__version__ = '$version'/" dotsync/info.py
    fi
}

# Update version in pyproject.toml
update_pyproject() {
    local version=$1
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^version = \".*\"/version = \"$version\"/" pyproject.toml
    else
        sed -i "s/^version = \".*\"/version = \"$version\"/" pyproject.toml
    fi
}

# Note: dotsync.rb will be updated automatically by GitHub Actions
# (update_homebrew.yml workflow after release is published)

# Verify changes
verify_changes() {
    local version=$1
    
    section "Verifying changes"
    
    echo "Checking dotsync/info.py:"
    grep "__version__" dotsync/info.py
    
    echo ""
    echo "Checking pyproject.toml:"
    grep "^version = " pyproject.toml
}

# Git status check
check_git_status() {
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        warn "You have uncommitted changes"
        echo ""
        git status --short
        echo ""
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Aborted"
        fi
    fi
}

# Main
main() {
    # Check we're in the right directory
    if [[ ! -f "dotsync/info.py" ]]; then
        error "Must run from repository root (dotsync/info.py not found)"
    fi
    
    # Check argument
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 [major|minor|patch|VERSION]"
        echo ""
        echo "Examples:"
        echo "  $0 patch     # Increment patch version"
        echo "  $0 minor     # Increment minor version"
        echo "  $0 major     # Increment major version"
        echo "  $0 2.3.0     # Set specific version"
        echo ""
        exit 1
    fi
    
    BUMP_TYPE=$1
    CURRENT_VERSION=$(get_current_version)
    
    section "Version Bump"
    echo "Current version: $CURRENT_VERSION"
    
    # Calculate new version
    calculate_new_version "$BUMP_TYPE" "$CURRENT_VERSION"
    echo "New version:     $NEW_VERSION"
    echo ""
    
    # Confirm
    read -p "Proceed with version bump? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        error "Aborted"
    fi
    
    # Check git status
    check_git_status
    
    # Update files
    section "Updating version files"
    
    info "Updating dotsync/info.py..."
    update_info_py "$NEW_VERSION"
    
    info "Updating pyproject.toml..."
    update_pyproject "$NEW_VERSION"
    
    echo ""
    info "Note: dotsync.rb will be updated automatically by GitHub Actions"
    
    # Verify
    verify_changes "$NEW_VERSION"
    
    # Git operations
    section "Git operations"
    
    echo "Files changed:"
    git diff --stat dotsync/info.py pyproject.toml
    echo ""
    
    read -p "Commit changes? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git add dotsync/info.py pyproject.toml
        git commit -m "Bump version to v${NEW_VERSION}"
        info "Changes committed"
        
        echo ""
        read -p "Create and push tag v${NEW_VERSION}? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            git tag -a "v${NEW_VERSION}" -m "Release version ${NEW_VERSION}"
            info "Tag v${NEW_VERSION} created"
            
            echo ""
            read -p "Push to origin (main + tag)? [Y/n] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                git push origin main
                git push origin "v${NEW_VERSION}"
                
                section "Release initiated!"
                info "Version bumped to v${NEW_VERSION}"
                info "Tag pushed - GitHub Actions will now:"
                echo "  1. Build package"
                echo "  2. Publish to PyPI"
                echo "  3. Create GitHub Release"
                echo "  4. Update Homebrew tap"
                echo ""
                info "Monitor progress: https://github.com/HarveyGG/dotsync/actions"
            else
                warn "Tag created locally but not pushed"
                echo "To push later: git push origin main && git push origin v${NEW_VERSION}"
            fi
        else
            warn "Tag not created"
            echo "To create later: git tag -a v${NEW_VERSION} -m \"Release version ${NEW_VERSION}\""
        fi
    else
        warn "Changes not committed"
        echo "Files updated but not committed. Review with: git diff"
    fi
    
    echo ""
}

main "$@"

