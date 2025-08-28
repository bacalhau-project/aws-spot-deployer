#!/bin/bash
# Setup branch protection rules for main branch

set -e

echo "🔒 Setting up branch protection rules for main branch..."

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed. Please install it first:"
    echo "   brew install gh"
    echo "   or visit: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "🔐 Please authenticate with GitHub first:"
    gh auth login
fi

# Set up branch protection for main using gh CLI commands
echo "📋 Creating branch protection rule for 'main'..."

# Use GitHub CLI branch protection command (simpler)
gh api \
  --method PUT \
  --header "Accept: application/vnd.github+json" \
  --header "X-GitHub-Api-Version: 2022-11-28" \
  /repos/:owner/:repo/branches/main/protection \
  --input - >/dev/null <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false
}
EOF

echo "✅ Branch protection enabled for 'main' with:"
echo "   - Require PR reviews (1 approval minimum)"
echo "   - Require status checks to pass"
echo "   - Require branches to be up to date"
echo "   - Dismiss stale reviews"
echo "   - No force pushes allowed"
echo "   - No deletions allowed"

# Optional: Also protect develop branch
read -p "🤔 Do you want to protect 'develop' branch as well? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📋 Creating branch protection rule for 'develop'..."

    gh api \
      --method PUT \
      --header "Accept: application/vnd.github+json" \
      --header "X-GitHub-Api-Version: 2022-11-28" \
      /repos/:owner/:repo/branches/develop/protection \
      --input - >/dev/null <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false
}
EOF

    echo "✅ Branch protection enabled for 'develop' as well!"
fi

echo ""
echo "🎉 Branch protection setup complete!"
echo ""
echo "Next steps:"
echo "1. Create feature branches: gh repo clone && git checkout -b feature/your-feature"
echo "2. Push changes: git push -u origin feature/your-feature"
echo "3. Open PR: gh pr create --base develop"
echo "4. After review & CI passes, merge via GitHub UI"
echo ""
echo "For more info, see DEVELOP.md"
