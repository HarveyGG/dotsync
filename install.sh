#!/bin/bash
#
# dotsync Installer
# Installs dotsync with zero dependencies
#
# This script will:
# 1. Install uv (if not present)
# 2. Create dotsync launcher
# 3. No Python installation required
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BIN_DIR="${HOME}/.local/bin"
UV_BIN="${HOME}/.cargo/bin"

error() { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
info() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
section() { echo ""; echo -e "${BLUE}━━━ $1 ━━━${NC}"; echo ""; }

# Install uv if needed
install_uv() {
    if command -v uv &> /dev/null; then
        info "uv already installed: $(uv --version)"
        return 0
    fi
    
    section "Installing uv"
    
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        export PATH="$UV_BIN:$PATH"
        info "uv installed successfully"
    else
        error "Failed to install uv"
    fi
}

# Create dotsync launcher
create_launcher() {
    section "Creating dotsync launcher"
    
    mkdir -p "$BIN_DIR"
    
    cat > "$BIN_DIR/dotsync" << 'LAUNCHER_EOF'
#!/bin/bash
# dotsync launcher

# Ensure uv is in PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Run dotsync via uvx (downloads Python + dotsync automatically)
exec uvx dotsync-cli "$@"
LAUNCHER_EOF
    
    chmod +x "$BIN_DIR/dotsync"
    info "Launcher created at $BIN_DIR/dotsync"
}

# Verify installation
verify() {
    section "Verifying installation"
    
    export PATH="$BIN_DIR:$UV_BIN:$PATH"
    
    if command -v dotsync &> /dev/null; then
        info "dotsync command is available"
        
        # Test run (will download Python + dotsync on first run)
        echo "Testing dotsync..."
        if timeout 30 dotsync --version &> /dev/null; then
            info "dotsync is working correctly"
            return 0
        fi
    fi
    
    warn "Could not verify dotsync command"
    return 1
}

# Check PATH
check_path() {
    local needs_update=false
    
    # Check BIN_DIR
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        needs_update=true
    fi
    
    # Check UV_BIN
    if ! echo "$PATH" | grep -q "$UV_BIN"; then
        needs_update=true
    fi
    
    if [ "$needs_update" = true ]; then
        warn ""
        warn "Please add these directories to your PATH:"
        warn ""
        
        # Detect shell
        case "$(basename "$SHELL")" in
            bash)
                RC_FILE="$HOME/.bashrc"
                warn "Add to $RC_FILE:"
                warn '  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"'
                ;;
            zsh)
                RC_FILE="$HOME/.zshrc"
                warn "Add to $RC_FILE:"
                warn '  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"'
                ;;
            fish)
                RC_FILE="$HOME/.config/fish/config.fish"
                warn "Add to $RC_FILE:"
                warn '  set -x PATH $HOME/.local/bin $HOME/.cargo/bin $PATH'
                ;;
            *)
                RC_FILE="$HOME/.profile"
                warn "Add to $RC_FILE:"
                warn '  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"'
                ;;
        esac
        
        warn ""
        warn "Then run: source $RC_FILE"
        warn ""
    fi
}

# Main
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   dotsync Installer                   ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
    echo ""
    
    info "Platform: $(uname -s) $(uname -m)"
    echo ""
    
    install_uv
    create_launcher
    
    section "Installation Complete!"
    
    echo "How it works:"
    echo "  • First run: uvx downloads Python + dotsync automatically"
    echo "  • Future runs: Uses cached version (instant startup)"
    echo "  • No system Python needed!"
    echo ""
    
    check_path
    
    info "✅ dotsync is ready!"
    echo ""
    info "Try it now:"
    info "  export PATH=\"\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH\""
    info "  dotsync --help"
    echo ""
    
    warn "Note: First run may take ~30 seconds to download Python + dotsync"
    echo ""
}

main

