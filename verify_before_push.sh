#!/bin/bash
# Pre-push verification script to ensure no sensitive files are committed

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔍 Pre-Push Security Verification"
echo "=================================="
echo ""

ERRORS=0

# Check for .env files (except .env.example)
echo -n "[1/6] Checking for .env files... "
ENV_FILES=$(find . -name ".env" -not -name ".env.example" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null)
if [ -n "$ENV_FILES" ]; then
    echo "❌ FAIL"
    echo "   Found .env files:"
    echo "$ENV_FILES" | sed 's/^/   - /'
    ERRORS=$((ERRORS + 1))
else
    echo "✅ PASS"
fi

# Check for database files
echo -n "[2/6] Checking for database files... "
DB_FILES=$(find . -name "*.db" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null)
if [ -n "$DB_FILES" ]; then
    echo "❌ FAIL"
    echo "   Found database files:"
    echo "$DB_FILES" | sed 's/^/   - /'
    ERRORS=$((ERRORS + 1))
else
    echo "✅ PASS"
fi

# Check for log files
echo -n "[3/6] Checking for log files... "
LOG_FILES=$(find . -name "*.log" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -5)
if [ -n "$LOG_FILES" ]; then
    echo "⚠️  WARNING"
    echo "   Found log files (may contain sensitive data):"
    echo "$LOG_FILES" | sed 's/^/   - /'
    echo "   Consider removing these before pushing"
else
    echo "✅ PASS"
fi

# Check for backup directories
echo -n "[4/6] Checking for backup directories... "
BACKUP_DIRS=$(find . -type d -name "backup_*" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null)
if [ -n "$BACKUP_DIRS" ]; then
    echo "❌ FAIL"
    echo "   Found backup directories:"
    echo "$BACKUP_DIRS" | sed 's/^/   - /'
    ERRORS=$((ERRORS + 1))
else
    echo "✅ PASS"
fi

# Check for hardcoded default passwords in code (not in docs/examples)
echo -n "[5/6] Checking for hardcoded secrets... "
SECRETS=$(grep -r "admin123" --include="*.py" --include="*.yml" --include="*.yaml" . 2>/dev/null | \
    grep -v ".git" | \
    grep -v "node_modules" | \
    grep -v ".env.example" | \
    grep -v "README" | \
    grep -v "docs/" | \
    grep -v "GITHUB_UPLOAD_GUIDE" | \
    grep -v "verify_before_push" | \
    grep -v "# ⚠️" || true)
if [ -n "$SECRETS" ]; then
    echo "⚠️  WARNING"
    echo "   Found potential hardcoded passwords (may be in comments/examples):"
    echo "$SECRETS" | head -3 | sed 's/^/   - /'
    echo "   Please verify these are safe to commit"
else
    echo "✅ PASS"
fi

# Check .gitignore exists and is comprehensive
echo -n "[6/6] Checking .gitignore... "
if [ ! -f ".gitignore" ]; then
    echo "❌ FAIL"
    echo "   .gitignore file not found!"
    ERRORS=$((ERRORS + 1))
elif ! grep -q "\.env$" .gitignore 2>/dev/null; then
    echo "⚠️  WARNING"
    echo "   .gitignore may not exclude .env files properly"
else
    echo "✅ PASS"
fi

echo ""
echo "=================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed! Safe to push to GitHub."
    echo ""
    echo "Next steps:"
    echo "  1. git add ."
    echo "  2. git commit -m 'Initial commit'"
    echo "  3. git push"
    exit 0
else
    echo "❌ Found $ERRORS critical issue(s). Please fix before pushing."
    echo ""
    echo "Run cleanup script:"
    echo "  ./scripts/cleanup_for_github.sh"
    exit 1
fi
