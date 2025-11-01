# GitHub Actions 发布配置指南

## 当前配置状态

✅ **release.yml** 工作流程已配置好，会在推送 tag 时自动触发

## 需要配置的 GitHub Secrets

### 1. PyPI API Token（必需）

1. 登录 [PyPI](https://pypi.org/)
2. 进入 **Account settings** → **API tokens**
3. 点击 **Add API token**
4. 填写：
   - Token name: `dotsync-release` (或任意名称)
   - Scope: 选择整个账户或特定项目
5. 复制生成的 token（格式：`pypi-xxxxxxxxxxxxxxxxxxxxx`）
6. 在 GitHub 仓库中配置 Secret：
   - 进入 `HarveyGG/dotsync` 仓库
   - Settings → Secrets and variables → Actions
   - 点击 **New repository secret**
   - Name: `PYPI_API_TOKEN`
   - Value: 粘贴刚才复制的 token
   - 点击 **Add secret**

### 2. Homebrew Tap Token（必需，用于自动更新 Homebrew）

用于自动更新 `homebrew-tap` 仓库：

1. 创建 Personal Access Token (Fine-grained)：
   - 访问 GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - 点击 **Generate new token**
   - 填写：
     - Token name: `homebrew-tap-updater`
     - Expiration: 选择合适的过期时间（建议 1 年）
     - Repository access: **Only select repositories** → 选择 `homebrew-tap`
     - Permissions:
       - Contents: **Read and write** （必需）
       - Metadata: **Read-only** （自动）
   - 点击 **Generate token** 并复制

2. 在 `dotsync` 仓库配置 Secret：
   - 进入 `HarveyGG/dotsync` 仓库
   - Settings → Secrets and variables → Actions
   - 点击 **New repository secret**
   - Name: `TAP_GITHUB_TOKEN`
   - Value: 粘贴刚才复制的 token
   - 点击 **Add secret**

**注意：** Fine-grained token 更安全，只能访问指定的 `homebrew-tap` 仓库。

**或者使用 Classic Token：**
- Settings → Developer settings → Personal access tokens → Tokens (classic)
- 勾选 `repo` 权限
- 生成后同样配置为 `TAP_GITHUB_TOKEN`

### 3. GitHub Token（自动，无需配置）

`release.yml` 中的 `Create GitHub Release` 步骤会使用默认的 `GITHUB_TOKEN`，自动提供，无需配置。

## 发布流程

### 步骤 1: 更新版本号

编辑 `dotsync/info.py`:
```python
__version__ = '2.2.10'  # 更新到新版本
```

同时更新 `dotsync.rb` 中的版本占位符（工作流会自动填充实际 SHA256）:
```ruby
url "https://files.pythonhosted.org/packages/source/d/dotsync/dotsync-2.2.10.tar.gz"
sha256 ""
```

### 步骤 2: 提交并推送

```bash
git add dotsync/info.py dotsync.rb
git commit -m "Bump version to 2.2.10"
git push origin main
```

### 步骤 3: 创建并推送 Tag

```bash
git tag -a v2.2.10 -m "Release version 2.2.10"
git push origin v2.2.10
```

### 步骤 4: GitHub Actions 自动执行

推送 tag 后，GitHub Actions 会自动：

**Release 工作流：**
1. ✅ 构建 Python 包
2. ✅ 计算 SHA256 并更新 Homebrew formula
3. ✅ 发布到 PyPI（如果 `PYPI_API_TOKEN` 已配置）
4. ✅ 创建 GitHub Release，包含：
   - 源代码压缩包
   - Python wheel 和 tarball
   - `install.sh` 安装脚本
   - `dotsync.rb` Homebrew formula（已更新 SHA256）

**Homebrew 更新工作流（自动触发）：**
5. ✅ 等待 Release 创建完成
6. ✅ 下载更新后的 `dotsync.rb`
7. ✅ 自动提交到 `homebrew-tap` 仓库

整个过程完全自动化，无需手动操作！

## 验证配置

### 检查 GitHub Secrets

在仓库页面：`Settings → Secrets and variables → Actions`，确认：
- ✅ `PYPI_API_TOKEN` 已配置
- ✅ `TAP_GITHUB_TOKEN` 已配置（用于自动更新 Homebrew tap）

### 检查 Git Remote（重要！）

```bash
cd ~/.dotfiles/dotsync
git remote -v
```

**当前状态：** 指向 `kobus-v-schoor/dotgit`（需要更新）

**需要更新为：**
```bash
git remote set-url origin https://github.com/HarveyGG/dotsync.git
git remote -v  # 验证
```

### 测试发布流程（可选）

可以先创建一个测试 tag 来验证工作流程：

```bash
git tag -a v2.2.9-test -m "Test release"
git push origin v2.2.9-test
```

然后在 GitHub Actions 页面查看运行结果。

## 用户安装方式

发布后，用户可以通过以下方式安装：

### 1. curl 安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
```

**特点：**
- 无需 Python 安装
- 使用 uv 自动管理依赖
- 首次运行约 30 秒，后续秒启动

### 2. Homebrew 安装

```bash
brew tap HarveyGG/tap
brew install dotsync
```

### 3. pip 安装

```bash
pip install dotsync
```

## 注意事项

1. ⚠️ **Tag 格式**：必须是 `v*` 格式（如 `v2.2.10`），否则不会触发
2. ⚠️ **PyPI 版本**：版本号不能重复，确保每次发布使用新版本号
3. ⚠️ **Git Remote**：确保 remote 指向正确的仓库 `HarveyGG/dotsync`
4. ⚠️ **Homebrew Tap**：发布后需要手动更新 `homebrew-tap` 仓库（或设置自动化）
5. ⚠️ **install.sh**：确保脚本在 main 分支可访问，用于 curl 安装

## Homebrew Tap 设置

### 首次设置

1. **创建 Homebrew Tap 仓库**
   ```bash
   # 在 GitHub 上创建新仓库
   # 仓库名必须是: homebrew-tap
   # URL: https://github.com/HarveyGG/homebrew-tap
   ```

2. **初始化仓库结构**
   ```bash
   git clone https://github.com/HarveyGG/homebrew-tap.git
   cd homebrew-tap
   mkdir -p Formula
   
   # 从 dotsync 仓库复制初始 formula
   curl -o Formula/dotsync.rb https://raw.githubusercontent.com/HarveyGG/dotsync/main/dotsync.rb
   
   git add Formula/dotsync.rb
   git commit -m "Add dotsync formula"
   git push origin main
   ```

3. **配置 GitHub Token**
   - 按照上面"Homebrew Tap Token"部分创建 token
   - 在 `dotsync` 仓库配置 `TAP_GITHUB_TOKEN` secret

### 自动更新

配置完成后，每次发布新版本时：
- ✅ `update_homebrew.yml` 工作流自动触发
- ✅ 自动下载更新的 `dotsync.rb`
- ✅ 自动提交到 `homebrew-tap` 仓库
- ✅ 用户可以立即通过 `brew upgrade dotsync` 更新

完全自动化，无需手动操作！详细说明见 `HOMEBREW_TAP.md`。

