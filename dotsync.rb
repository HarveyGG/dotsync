class Dotsync < Formula
  desc "A powerful and versatile dotfiles manager"
  homepage "https://github.com/HarveyGG/dotsync"
  url "https://github.com/HarveyGG/dotsync/archive/v1.0.12.tar.gz"
  sha256 ""
  license "Non-Commercial"
  head "https://github.com/HarveyGG/dotsync.git", branch: "main"

  depends_on "uv"

  def install
    (bin/"dotsync").write <<~EOS
      #!/bin/bash
      
      # Smart uv/uvx finder - prioritizes user's installation
      # Supports both new (uv tool run) and legacy (uvx) commands
      find_uv() {
        # Priority 1: User's uv in PATH
        local uv_path=$(command -v uv 2>/dev/null)
        if [ -n "$uv_path" ]; then
          echo "$uv_path"
          return 0
        fi
        
        # Priority 2: User's uvx in PATH (legacy)
        local uvx_path=$(command -v uvx 2>/dev/null)
        if [ -n "$uvx_path" ]; then
          echo "$uvx_path"
          return 0
        fi
        
        # Priority 3: Homebrew installation
        for brew_prefix in /opt/homebrew /usr/local; do
          if [ -x "$brew_prefix/bin/uv" ]; then
            echo "$brew_prefix/bin/uv"
            return 0
          fi
          if [ -x "$brew_prefix/bin/uvx" ]; then
            echo "$brew_prefix/bin/uvx"
            return 0
          fi
        done
        
        # Priority 4: Common standalone locations
        for standalone_path in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" "$HOME/.local/bin/uvx" "$HOME/.cargo/bin/uvx"; do
          if [ -x "$standalone_path" ]; then
            echo "$standalone_path"
            return 0
          fi
        done
        
        return 1
      }
      
      # Find uv/uvx
      UV_PATH=$(find_uv)
      
      if [ -z "$UV_PATH" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "⚠️  dotsync requires 'uv' but it's not installed" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "" >&2
        echo "Quick fix - choose one:" >&2
        echo "" >&2
        echo "  Option 1 (Homebrew):" >&2
        echo "    brew install uv" >&2
        echo "" >&2
        echo "  Option 2 (Standalone):" >&2
        echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
        echo "" >&2
        echo "Then run dotsync again!" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        exit 1
      fi
      
      # Determine if we're using new uv (uv tool run) or legacy uvx
      if [[ "$UV_PATH" == *"/uv" ]]; then
        # New uv: use 'uv tool run'
        exec "$UV_PATH" tool run --from dotsync-cli dotsync "$@"
      else
        # Legacy uvx
        exec "$UV_PATH" --from dotsync-cli dotsync "$@"
      fi
    EOS
    
    chmod 0755, bin/"dotsync"
  end

  def caveats
    <<~EOS
      On first run, dotsync will automatically download Python and dependencies.
      This may take ~30 seconds, then subsequent runs are instant.
      
      No system Python installation required!
    EOS
  end

  test do
    assert_predicate bin/"dotsync", :exist?
    assert_predicate bin/"dotsync", :executable?
  end
end

