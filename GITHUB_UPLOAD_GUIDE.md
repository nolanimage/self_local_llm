# GitHub Upload Guide - Safe Repository Setup

This guide will help you safely upload your project to GitHub without exposing sensitive information.

## 🔒 Security Checklist

Before uploading, verify:

- [ ] No `.env` files (only `.env.example` should exist)
- [ ] No database files (`.db`, `.sqlite`)
- [ ] No log files (`.log`)
- [ ] No hardcoded API keys or passwords
- [ ] No backup directories
- [ ] `.gitignore` is properly configured

## 🚀 Step-by-Step Upload Process

### Step 1: Run Cleanup Script

```bash
./scripts/cleanup_for_github.sh
```

This will remove:
- All log files
- Database files
- `.env` files (keeps `.env.example`)
- Backup directories
- Temporary files
- Python cache

### Step 2: Verify No Sensitive Files

```bash
# Check for .env files (should only show .env.example)
find . -name ".env*" -not -name ".env.example" -not -path "*/node_modules/*"

# Check for database files
find . -name "*.db" -not -path "*/node_modules/*"

# Check for log files
find . -name "*.log" -not -path "*/node_modules/*"
```

**Expected**: No results (or only `.env.example`)

### Step 3: Initialize Git Repository

```bash
# Initialize git (if not already done)
git init

# Add all files (respects .gitignore)
git add .

# Check what will be committed
git status
```

**⚠️ IMPORTANT**: Review `git status` output carefully. You should NOT see:
- `.env` files
- `*.db` files
- `*.log` files
- `backup_*/` directories

### Step 4: Create Initial Commit

```bash
git commit -m "Initial commit: Self LLM RAG system"
```

### Step 5: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (don't initialize with README)
3. Copy the repository URL

### Step 6: Add Remote and Push

```bash
# Add remote (replace with your repository URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## 🔍 Pre-Upload Verification

Run this script to verify everything is safe:

```bash
#!/bin/bash
echo "🔍 Pre-Upload Security Check"
echo "============================"

# Check for .env files
echo -n "Checking for .env files... "
if find . -name ".env" -not -name ".env.example" -not -path "*/node_modules/*" | grep -q .; then
    echo "❌ FOUND .env files!"
    find . -name ".env" -not -name ".env.example" -not -path "*/node_modules/*"
    exit 1
else
    echo "✅ OK"
fi

# Check for database files
echo -n "Checking for database files... "
if find . -name "*.db" -not -path "*/node_modules/*" | grep -q .; then
    echo "❌ FOUND database files!"
    find . -name "*.db" -not -path "*/node_modules/*"
    exit 1
else
    echo "✅ OK"
fi

# Check for log files
echo -n "Checking for log files... "
if find . -name "*.log" -not -path "*/node_modules/*" | grep -q .; then
    echo "⚠️  Found log files (may contain sensitive data)"
    find . -name "*.log" -not -path "*/node_modules/*" | head -5
else
    echo "✅ OK"
fi

# Check for hardcoded secrets
echo -n "Checking for hardcoded secrets... "
if grep -r "admin123" --include="*.py" --include="*.yml" --include="*.yaml" . 2>/dev/null | grep -v ".git" | grep -v "node_modules" | grep -v ".env.example" | grep -v "README" | grep -v "docs" | grep -q .; then
    echo "⚠️  Found potential hardcoded passwords (check if in example files)"
    grep -r "admin123" --include="*.py" --include="*.yml" . 2>/dev/null | grep -v ".git" | grep -v "node_modules" | head -3
else
    echo "✅ OK"
fi

echo ""
echo "✅ Security check complete!"
```

## 📝 Files That Should Be Committed

✅ **Safe to commit:**
- All source code (`.py`, `.tsx`, `.ts`, `.js`)
- Configuration examples (`config.env.example`)
- Docker files (`Dockerfile.*`, `docker-compose.*.yml`)
- Documentation (`.md` files)
- Scripts (`.sh` files)
- Requirements (`requirements.txt`, `package.json`)
- `.gitignore`

❌ **Never commit:**
- `.env` files (actual secrets)
- `*.log` files
- `*.db` files (databases)
- `backup_*/` directories
- `__pycache__/` directories
- `node_modules/` (already in .gitignore)
- Any file with actual API keys or passwords

## 🔐 After Uploading

### 1. Create `.env` File Locally

```bash
cp config.env.example .env
# Edit .env with your actual secrets
nano .env
```

### 2. Add `.env` to `.gitignore`

Already done! The `.gitignore` file excludes `.env` files.

### 3. Document Required Environment Variables

The `config.env.example` file documents all required variables. Users should:
1. Copy `config.env.example` to `.env`
2. Fill in their actual secrets
3. Never commit `.env` to Git

## 🛡️ Additional Security Tips

1. **Review Git History**: If you accidentally committed secrets, use `git filter-branch` or BFG Repo-Cleaner to remove them
2. **Use GitHub Secrets**: For CI/CD, use GitHub Secrets instead of environment variables
3. **Rotate Keys**: If you suspect keys were exposed, rotate them immediately
4. **Enable 2FA**: Enable two-factor authentication on your GitHub account
5. **Review Access**: Regularly review who has access to your repository

## 🚨 If You Accidentally Committed Secrets

If you accidentally committed sensitive data:

1. **Immediately rotate the exposed secrets**
2. **Remove from Git history**:
   ```bash
   # Using git filter-branch
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   
   # Force push (WARNING: This rewrites history)
   git push origin --force --all
   ```

3. **Consider using BFG Repo-Cleaner** for large repositories

## ✅ Final Checklist

Before pushing to GitHub:

- [ ] Ran cleanup script
- [ ] Verified no `.env` files (except `.env.example`)
- [ ] Verified no database files
- [ ] Verified no log files
- [ ] Checked `git status` - no sensitive files
- [ ] Reviewed `.gitignore` is complete
- [ ] Created initial commit
- [ ] Ready to push!

## 📚 Additional Resources

- GitHub Security Best Practices: https://docs.github.com/en/code-security
- Gitignore Documentation: https://git-scm.com/docs/gitignore
- Removing Sensitive Data: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

---

**Remember**: When in doubt, don't commit it! It's better to be cautious than to expose sensitive information.
