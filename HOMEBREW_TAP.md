# Homebrew Tap Setup Guide

This guide explains how to set up and maintain a Homebrew tap for dotsync.

## What is a Homebrew Tap?

A Homebrew tap is a third-party repository that allows users to install your package with `brew install`.

## Setup Steps

### 1. Create Homebrew Tap Repository

Create a new GitHub repository named `homebrew-tap` (must follow this naming convention).

Repository URL: `https://github.com/HarveyGG/homebrew-tap`

### 2. Add Formula to Tap

In the `homebrew-tap` repository, create a `Formula` directory and add `dotsync.rb`:

```bash
mkdir -p Formula
cp dotsync.rb Formula/dotsync.rb
git add Formula/dotsync.rb
git commit -m "Add dotsync formula"
git push origin main
```

### 3. Users Can Install

Once the tap is set up, users can install with:

```bash
brew tap HarveyGG/tap
brew install dotsync
```

## Updating the Formula

### Automatic Update（已配置，推荐）

**完全自动化！** 已经通过 `update_homebrew.yml` GitHub Action 实现。

每次发布新版本时：
1. ✅ 推送 tag 触发 `release.yml` 工作流
2. ✅ Release 创建完成后自动触发 `update_homebrew.yml`
3. ✅ 从 GitHub Release 下载更新的 `dotsync.rb`
4. ✅ 自动提交到 `homebrew-tap` 仓库

**配置要求：**
- 在 `dotsync` 仓库配置 `TAP_GITHUB_TOKEN` secret
- 确保 `homebrew-tap` 仓库存在且可访问

详见 `GITHUB_ACTIONS_SETUP.md`。

### Manual Update（备用）

如果需要手动更新：

```bash
# In homebrew-tap repository
curl -o Formula/dotsync.rb https://github.com/HarveyGG/dotsync/releases/latest/download/dotsync.rb
git add Formula/dotsync.rb
git commit -m "Update dotsync to vX.Y.Z"
git push
```


## Testing the Formula

Before releasing, test the formula:

```bash
# Audit the formula
brew audit --strict dotsync.rb

# Install from formula
brew install ./dotsync.rb

# Test the installation
dotsync --version
dotsync --help

# Uninstall
brew uninstall dotsync
```

## Troubleshooting

### SHA256 Mismatch

If users get SHA256 mismatch errors:
1. Verify the SHA256 in the formula matches the PyPI tarball
2. Clear Homebrew cache: `brew cleanup`
3. Reinstall: `brew reinstall dotsync`

### Python Version Issues

The formula depends on `python@3.11`. If users have issues:
- Update the Python dependency in the formula
- Or use `python@3` for latest Python 3.x

### Formula Not Found

If `brew install HarveyGG/tap/dotsync` fails:
1. Ensure the tap repository is public
2. Check the repository name is exactly `homebrew-tap`
3. Verify `Formula/dotsync.rb` exists in the tap repo
4. Try: `brew tap HarveyGG/tap` then `brew install dotsync`

## References

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python for Formula Authors](https://docs.brew.sh/Python-for-Formula-Authors)
- [How to Create and Maintain a Tap](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)

