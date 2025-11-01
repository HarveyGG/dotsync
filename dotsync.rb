class Dotsync < Formula
  desc "A powerful and versatile dotfiles manager"
  homepage "https://github.com/HarveyGG/dotsync"
  url "https://github.com/HarveyGG/dotsync/archive/v2.2.9.tar.gz"
  sha256 "" # Update this with actual SHA256 after creating release
  license "GPL-2.0"
  head "https://github.com/HarveyGG/dotsync.git", branch: "main"

  depends_on "python@3.9"

  def install
    python3 = "python3"
    system python3, "-m", "pip", "install", *std_pip_args, "."
  end

  test do
    system "#{bin}/dotsync", "--version"
    system "#{bin}/dotsync", "--help"
  end
end

