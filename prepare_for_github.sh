#!/bin/bash
# Complete script to prepare repository for GitHub upload

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           Preparing Repository for GitHub Upload                ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Run cleanup
echo "Step 1: Running cleanup script..."
./scripts/cleanup_for_github.sh

# Step 2: Run verification
echo ""
echo "Step 2: Running security verification..."
./verify_before_push.sh

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Verification failed. Please fix issues before proceeding."
    exit 1
fi

# Step 3: Initialize git if needed
if [ ! -d ".git" ]; then
    echo ""
    echo "Step 3: Initializing git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo ""
    echo "Step 3: Git repository already initialized"
fi

# Step 4: Show what will be committed
echo ""
echo "Step 4: Files to be committed:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git add .
git status --short | head -20
echo "..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 5: Instructions
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Ready for GitHub Upload!                     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Review the files above to ensure no sensitive data"
echo ""
echo "2. Create initial commit:"
echo "   git commit -m 'Initial commit: Self LLM RAG system'"
echo ""
echo "3. Create a new repository on GitHub:"
echo "   https://github.com/new"
echo "   (Don't initialize with README)"
echo ""
echo "4. Add remote and push:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "📚 See GITHUB_UPLOAD_GUIDE.md for detailed instructions"
echo ""
