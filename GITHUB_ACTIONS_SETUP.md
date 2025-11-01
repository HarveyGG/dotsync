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

### 2. GitHub Token（可选，用于自动创建 Release）

`release.yml` 中的 `Create GitHub Release` 步骤会使用默认的 `GITHUB_TOKEN`，通常不需要额外配置。

如果需要使用个人访问令牌（PAT）：
- Settings → Developer settings → Personal access tokens → Tokens (classic)
- 创建新 token，权限：`repo` (完整权限)
- 在仓库 Secrets 中添加：`GH_TOKEN`（如果 workflow 需要）

## 发布流程

### 步骤 1: 更新版本号

编辑 `dotsync/info.py`:
```python
__version__ = '2.2.10'  # 更新到新版本
```

### 步骤 2: 提交并推送

```bash
cd ~/.dotfiles/dotsync
git add dotsync/info.py
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
1. ✅ 构建 Python 包
2. ✅ 发布到 PyPI（如果 `PYPI_API_TOKEN` 已配置）
3. ✅ 创建 GitHub Release

## 验证配置

### 检查 GitHub Secrets

在仓库页面：`Settings → Secrets and variables → Actions`，确认：
- ✅ `PYPI_API_TOKEN` 已配置

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

## 注意事项

1. ⚠️ **Tag 格式**：必须是 `v*` 格式（如 `v2.2.10`），否则不会触发
2. ⚠️ **PyPI 版本**：版本号不能重复，确保每次发布使用新版本号
3. ⚠️ **Git Remote**：确保 remote 指向正确的仓库 `HarveyGG/dotsync`

## 其他工作流程文件

发现以下旧的工作流程文件（可能不需要）：
- `publish_pypi.yaml` - 使用旧的 username/password 方式
- `publish_aur.yaml` - AUR 发布（如果不需要可以删除）
- `coverage.yaml` - 代码覆盖率（可选）

可以考虑清理不需要的工作流程文件。

