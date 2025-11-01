#!/bin/bash
#
# dotsync Installation Script
# Installs dotsync using pip in a safe and non-invasive way
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handling
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

# Check if Python 3 is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        # Check if it's Python 3
        if python -c "import sys; exit(0 if sys.version_info >= (3, 6) else 1)" 2>/dev/null; then
            PYTHON_CMD="python"
        else
            error "Python 3.6+ is required but not found. Please install Python 3.6 or later."
        fi
    else
        error "Python 3 is required but not found. Please install Python 3.6 or later."
    fi
    
    # Check version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    info "Found Python $PYTHON_VERSION"
}

# Check if pip is available
check_pip() {
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        warn "pip not found. Attempting to install pip..."
        if ! $PYTHON_CMD -m ensurepip --default-pip; then
            error "Failed to install pip. Please install pip manually and try again."
        fi
        PIP_CMD="$PYTHON_CMD -m pip"
    fi
    
    info "Using $PIP_CMD"
}

# Install dotsync
install_dotsync() {
    info "Installing dotsync..."
    
    # Use --user flag to avoid requiring sudo
    if $PIP_CMD install --user --upgrade dotsync; then
        info "dotsync installed successfully!"
    else
        error "Failed to install dotsync. You may need to run with sudo or install pip packages."
    fi
}

# Verify installation
verify_installation() {
    # Add user's local bin to PATH for this check
    USER_BIN="$HOME/.local/bin"
    
    if [ -d "$USER_BIN" ] && [ -f "$USER_BIN/dotsync" ]; then
        info "Installation verified: dotsync found at $USER_BIN/dotsync"
        return 0
    fi
    
    # Try to find dotsync in PATH
    if command -v dotsync &> /dev/null; then
        DOTSYNC_PATH=$(command -v dotsync)
        info "Installation verified: dotsync found at $DOTSYNC_PATH"
        return 0
    fi
    
    warn "Could not verify installation. You may need to add $USER_BIN to your PATH."
    return 1
}

# Check PATH setup
check_path() {
    USER_BIN="$HOME/.local/bin"
    
    if [ -d "$USER_BIN" ]; then
        if echo "$PATH" | grep -q "$USER_BIN"; then
            info "PATH is already configured correctly"
        else
            warn ""
            warn "⚠️  Important: Add the following to your shell configuration file:"
            warn "   (~/.bashrc, ~/.zshrc, etc.)"
            warn ""
            warn "   export PATH=\"\$HOME/.local/bin:\$PATH\""
            warn ""
        fi
    fi
}

# Show version
show_version() {
    if command -v dotsync &> /dev/null || [ -f "$HOME/.local/bin/dotsync" ]; then
        DOTSYNC_CMD=$(command -v dotsync 2>/dev/null || echo "$HOME/.local/bin/dotsync")
        if [ -f "$DOTSYNC_CMD" ]; then
            VERSION=$($DOTSYNC_CMD --version 2>&1 || echo "unknown")
            info "Installed version: $VERSION"
        fi
    fi
}

# Main installation process
main() {
    echo ""
    info "╔════════════════════════════════════════╗"
    info "║      dotsync Installation Script       ║"
    info "╚════════════════════════════════════════╝"
    echo ""
    
    check_python
    check_pip
    install_dotsync
    
    echo ""
    info "════════════════════════════════════════"
    
    if verify_installation; then
        show_version
        check_path
        echo ""
        info "✅ Installation complete!"
        info "   Run 'dotsync --help' to get started"
        echo ""
    else
        echo ""
        warn "⚠️  Installation may have completed, but dotsync command not found in PATH"
        warn "   Try adding $HOME/.local/bin to your PATH"
        echo ""
    fi
}

# Run main function
main

