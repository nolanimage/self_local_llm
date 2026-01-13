# Security Guide

## Before Deploying to Production

This repository is configured to use environment variables for all sensitive data. However, **you must change default passwords before deploying to production**.

## Required Security Steps

### 1. Change RabbitMQ Password

The default RabbitMQ password is `admin123` (for development only). **You must change this for production.**

**Option A: Using .env file (Recommended)**

1. Create a `.env` file from the example:
   ```bash
   cp config.env.example .env
   ```

2. Edit `.env` and set a strong password:
   ```bash
   RABBITMQ_PASS=your_secure_password_here
   ```

3. Docker Compose will automatically load variables from `.env` file

**Option B: Using environment variables**

```bash
export RABBITMQ_PASS=your_secure_password_here
docker-compose -f docker-compose.rag.yml up -d
```

### 2. OpenRouter API Key (Optional)

If using OpenRouter, set your API key:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

**Never commit your actual API key to Git!**

### 3. Review Exposed Ports

By default, the following ports are exposed:
- `5672`: RabbitMQ AMQP (should be internal only)
- `15672`: RabbitMQ Management UI (should be internal only)
- `11434`: Ollama API (should be internal only)
- `8000`: API Server (public-facing)

**For production:**
- Use a reverse proxy (nginx, traefik) for the API server
- Do not expose RabbitMQ or Ollama ports publicly
- Use Docker networks to keep services internal

## Files Excluded from Git

The `.gitignore` file excludes:
- `.env` files (actual secrets)
- `*.log` files (may contain sensitive data)
- `*.db` files (database with user data)
- `backup_*/` directories
- `__pycache__/` directories

## Security Checklist

Before pushing to GitHub or deploying:

- [ ] All secrets moved to `.env` file (not committed)
- [ ] Default passwords changed
- [ ] `.env` file added to `.gitignore` (already done)
- [ ] No hardcoded API keys in code
- [ ] Log files reviewed for sensitive data
- [ ] Database files excluded from Git
- [ ] Backup directories excluded from Git

## Running Cleanup Script

Before pushing to GitHub, run:

```bash
./cleanup_for_github.sh
```

This removes:
- All log files
- Database files
- Backup directories
- `.env` files (keeps `.env.example`)
- Python cache
- Temporary files

## Reporting Security Issues

If you discover a security vulnerability, please:
1. Do not open a public issue
2. Contact the repository maintainer directly
3. Provide details about the vulnerability
