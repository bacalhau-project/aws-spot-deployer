# Spot Deployer GitHub Pages

This branch (`gh-pages`) hosts the installation scripts and documentation for Spot Deployer.

## Important Notes

⚠️ **This branch is automatically managed by GitHub Actions**

- Do NOT edit files directly in this branch
- All changes should be made in the `main` branch under the `/docs` directory
- This branch is updated automatically when a new version tag is created

## Deployment Process

1. Create a new tag in the main branch: `git tag v1.0.0 && git push origin v1.0.0`
2. GitHub Actions will automatically:
   - Build and publish Docker images with the version tag
   - Update this branch with the latest install scripts
   - Deploy to GitHub Pages

## Files

- `install.sh` - Main installation script
- `spot` - Short redirect script
- `index.html` - Landing page
- `INSTALL.md` - Installation documentation
- `VERSION` - Current deployed version

## Usage

Users can install Spot Deployer with:

```bash
curl -sSL https://{owner}.github.io/{repo}/install.sh | bash -s -- create
```

Or with a custom domain:

```bash
curl -sSL https://bac.al/spot | bash -s -- create
```
