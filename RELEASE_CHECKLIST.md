# Release Checklist

发布新版本的快速检查清单。

## 发布前准备

- [ ] 所有测试通过：`pytest tests/`
- [ ] 代码已合并到 `main` 分支
- [ ] 更新 `dotsync/info.py` 中的版本号
- [ ] 更新 `dotsync.rb` 中的版本号（SHA256 留空，CI 会自动填充）
- [ ] 更新 CHANGELOG 或 Release Notes（如果有）

## 发布步骤

### 1. 更新版本号

```bash
# 编辑文件
vim dotsync/info.py        # 更新 __version__
vim dotsync.rb             # 更新 url 中的版本号，sha256 保持为空字符串

# 提交更改
git add dotsync/info.py dotsync.rb
git commit -m "Bump version to vX.Y.Z"
git push origin main
```

### 2. 创建并推送 Tag

```bash
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z
```

### 3. GitHub Actions 自动处理（完全自动化）

推送 tag 后，GitHub Actions 会自动：

**Release 工作流 (`release.yml`)：**
- ✅ 构建 Python 包
- ✅ 计算 SHA256 并更新 dotsync.rb
- ✅ 发布到 PyPI
- ✅ 创建 GitHub Release（包含 install.sh 和更新的 dotsync.rb）

**Homebrew 更新工作流 (`update_homebrew.yml`)：**
- ✅ Release 发布后自动触发
- ✅ 下载更新的 dotsync.rb
- ✅ 自动提交到 `homebrew-tap` 仓库

**无需手动操作！** 整个发布流程完全自动化。

## 发布后验证

### 验证 PyPI

```bash
pip install --upgrade dotsync
dotsync --version
```

### 验证 curl 安装

```bash
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
```

### 验证 Homebrew

```bash
brew update
brew upgrade dotsync
dotsync --version
```

## 用户安装方式

发布成功后，用户可以通过以下方式安装：

1. **curl 安装**（推荐）
   ```bash
   curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
   ```

2. **Homebrew**
   ```bash
   brew tap HarveyGG/tap
   brew install dotsync
   ```

3. **pip**
   ```bash
   pip install dotsync
   ```

## 故障排查

### PyPI 上传失败

- 检查 `PYPI_API_TOKEN` secret 是否正确配置
- 确认版本号未重复
- 查看 GitHub Actions 日志

### GitHub Release 创建失败

- 检查仓库权限设置
- 确认 tag 格式正确（必须是 `v*`）

### Homebrew Formula 问题

- 验证 SHA256 是否匹配 PyPI tarball
- 测试本地安装：`brew install ./dotsync.rb`
- 运行 `brew audit --strict dotsync.rb`

## 回滚

如果发布有问题：

1. 从 PyPI 删除版本（需要 PyPI 账户权限）
2. 删除 GitHub Release 和 tag
   ```bash
   git tag -d vX.Y.Z
   git push origin :refs/tags/vX.Y.Z
   ```
3. 修复问题后重新发布

## 相关文档

- [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) - GitHub Actions 详细配置
- [HOMEBREW_TAP.md](HOMEBREW_TAP.md) - Homebrew Tap 设置指南
- [INSTALL.md](INSTALL.md) - 安装说明

