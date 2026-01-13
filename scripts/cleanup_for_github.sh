#!/bin/bash
# Cleanup script to prepare repository for GitHub upload
# Removes logs, sensitive data, and temporary files

set -e

echo "🧹 Cleaning up repository for GitHub upload..."

# Remove all log files
echo "  Removing log files..."
find . -name "*.log" -type f -delete 2>/dev/null || true
find . -name "*.log.*" -type f -delete 2>/dev/null || true

# Remove database files
echo "  Removing database files..."
find . -name "*.db" -type f -delete 2>/dev/null || true
find . -name "*.db-shm" -type f -delete 2>/dev/null || true
find . -name "*.db-wal" -type f -delete 2>/dev/null || true
find . -name "*.sqlite" -type f -delete 2>/dev/null || true
find . -name "*.sqlite3" -type f -delete 2>/dev/null || true

# Remove backup directories
echo "  Removing backup directories..."
find . -type d -name "backup_*" -exec rm -rf {} + 2>/dev/null || true

# Remove .env files (keep .env.example)
echo "  Removing .env files (keeping .env.example)..."
find . -name ".env" -type f -delete 2>/dev/null || true
find . -name ".env.local" -type f -delete 2>/dev/null || true
find . -name "config.env" -type f -delete 2>/dev/null || true

# Remove test data files
echo "  Removing test data files..."
find . -name "test_articles.json" -type f -delete 2>/dev/null || true

# Remove Python cache
echo "  Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -type f -delete 2>/dev/null || true
find . -name "*.pyo" -type f -delete 2>/dev/null || true

# Remove temporary files
echo "  Removing temporary files..."
find . -name "*.tmp" -type f -delete 2>/dev/null || true
find . -name "*.temp" -type f -delete 2>/dev/null || true
find . -name "*.bak" -type f -delete 2>/dev/null || true
find . -name "*.backup" -type f -delete 2>/dev/null || true

# Remove OS files
echo "  Removing OS files..."
find . -name ".DS_Store" -type f -delete 2>/dev/null || true
find . -name "Thumbs.db" -type f -delete 2>/dev/null || true

# Remove docker-compose backup files
echo "  Removing docker-compose backup files..."
find . -name "docker-compose*.backup*" -type f -delete 2>/dev/null || true

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "⚠️  IMPORTANT: Before pushing to GitHub, make sure to:"
echo "   1. Review all files for any remaining secrets"
echo "   2. Create a .env file from config.env.example with your actual secrets"
echo "   3. Never commit .env files or actual secrets"
echo "   4. Check that .gitignore is properly configured"
echo ""
echo "📝 Next steps:"
echo "   git add ."
echo "   git commit -m 'Initial commit'"
echo "   git push"
