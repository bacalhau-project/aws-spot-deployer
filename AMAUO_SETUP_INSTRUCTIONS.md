# 🌟 Amauo Setup Instructions

## Project Rename Complete! ✅

Your project has been successfully renamed from "spot-deployer-cli" to **"Amauo"**!

## What Was Changed ✅

### ✅ Code & Structure
- **Package name**: `spot-deployer-cli` → `amauo`
- **Python module**: `spot_deployer` → `amauo`
- **CLI command**: `spot-deployer` → `amauo`
- **Source directory**: `src/spot_deployer/` → `src/amauo/`
- **All imports updated**: All Python files now import from `amauo`
- **All references updated**: README, docs, scripts, tests
- **CLI branding**: All help text, version output, and UI updated
- **Author info**: "Amauo Team" <hello@amauo.dev>
- **Dynamic versioning**: Using hatch-vcs for git tag-based versioning

### ✅ Files Updated
- `pyproject.toml` - Package name, scripts, author info
- `README.md` - All examples and documentation
- `.github/workflows/pypi-deploy.yml` - CI/CD references
- All shell scripts (`test-*.sh`)
- All documentation files (`.md`)
- Test files (`tests/`)

## External Changes Required ⚠️

You still need to make these changes manually:

### 1. TestPyPI Trusted Publisher Settings

Go to: https://test.pypi.org/manage/account/publishing/

**Remove the old publisher** and **add new publisher** with:
- **Owner**: `bacalhau-project`
- **Repository name**: `amauo` (new repo name)
- **Workflow filename**: `pypi-deploy.yml`
- **Environment name**: `testpypi`

### 2. PyPI Trusted Publisher Settings (when ready)

Go to: https://pypi.org/manage/account/publishing/

Same settings as TestPyPI above.

### 3. Optional: GitHub Repository Name

GitHub repository has been renamed:
- Repository URL changed from: https://github.com/bacalhau-project/aws-spot-deployer
- Repository URL is now: https://github.com/bacalhau-project/amauo
- **If you rename**: Update URLs in `pyproject.toml`:
  ```toml
  [project.urls]
  Homepage = "https://github.com/bacalhau-project/amauo"
  Documentation = "https://github.com/bacalhau-project/amauo#readme"
  Repository = "https://github.com/bacalhau-project/amauo"
  "Bug Tracker" = "https://github.com/bacalhau-project/amauo/issues"
  ```

## Testing Your Changes ✅

### Local Testing
```bash
# Install in development mode
PYTHONPATH=/Users/daaronch/code/bacalhau-skypilot/src python -m amauo --version

# Build package
uv build

# Run test script
./test-pypi-deployment.sh
```

### Expected Output
```bash
amauo version 2.0.3.dev0+g77b79e679.d20250828
```

### Package Files Created
```
dist/
├── amauo-2.0.3.dev0+g77b79e679.d20250828.tar.gz
└── amauo-2.0.3.dev0+g77b79e679.d20250828-py3-none-any.whl
```

## Commit and Deploy 🚀

### 1. Commit Changes
```bash
git add .
git commit -m "feat: rename project from spot-deployer-cli to Amauo

🌟 Complete rebrand to Amauo
- Package name: spot-deployer-cli → amauo
- Python module: spot_deployer → amauo
- CLI command: spot-deployer → amauo
- All imports, references, and branding updated
- Dynamic versioning with hatch-vcs
- Ready for PyPI deployment

BREAKING CHANGE: CLI command changed from 'spot-deployer' to 'amauo'"
```

### 2. Create Version Tag
```bash
git tag v2.1.0  # New major release for the rebrand
git push origin develop
git push origin --tags
```

### 3. Test Deployment
After setting up trusted publishing:
```bash
git push origin develop  # Triggers TestPyPI deployment
```

## New User Experience 🎉

After deployment, users can:

```bash
# Install and use Amauo
uvx amauo create
uvx amauo status
uvx amauo destroy

# Or traditional install
pip install amauo
amauo --version
```

## Version History 📝

- **v2.0.x**: Last spot-deployer-cli versions
- **v2.1.0**: First Amauo release (rebrand)
- **Future**: Clean Amauo versioning

## Next Steps Checklist ✅

- [ ] Set up TestPyPI trusted publisher (required)
- [ ] Test deployment to TestPyPI
- [ ] Set up PyPI trusted publisher (for production)
- [ ] Optional: Rename GitHub repository
- [ ] Update any external documentation
- [ ] Announce the rebrand! 🎉

---

**🌟 Welcome to Amauo! Deploy clusters effortlessly across the cloud. 🌟**
