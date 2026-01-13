# Setup SSH for GitHub

To push using SSH, you need to set up an SSH key and add it to your GitHub account.

## Quick Setup

### Step 1: Generate SSH Key (if you don't have one)

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Press Enter to accept default location (`~/.ssh/id_ed25519`).
You can set a passphrase or leave it empty.

### Step 2: Add SSH Key to SSH Agent

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### Step 3: Copy Public Key

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (starts with `ssh-ed25519`).

### Step 4: Add to GitHub

1. Go to: https://github.com/settings/keys
2. Click "New SSH key"
3. Title: "Mac - Self LLM"
4. Key: Paste the public key you copied
5. Click "Add SSH key"

### Step 5: Test Connection

```bash
ssh -T git@github.com
```

You should see: "Hi nolanimage! You've successfully authenticated..."

### Step 6: Push to GitHub

```bash
cd /Users/nolanlu/Desktop/code_for_fun/self_llm
git push -u origin main
```

## Alternative: Use GitHub CLI with HTTPS

If SSH setup is complicated, you can use GitHub CLI:

```bash
# Configure credential helper
gh auth setup-git

# Then push
git remote set-url origin https://github.com/nolanimage/self_local_llm.git
git push -u origin main
```

## Troubleshooting

### "Permission denied (publickey)"
- Make sure you added the public key to GitHub
- Check: `ssh -T git@github.com`
- Verify key is loaded: `ssh-add -l`

### "Could not read from remote repository"
- Verify repository exists: https://github.com/nolanimage/self_local_llm
- Check you have write access
- Verify remote URL: `git remote -v`

---

**Once SSH is set up, you can push with: `git push -u origin main`**
