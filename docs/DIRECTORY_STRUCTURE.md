# Directory Structure

This document describes the organization of the Self LLM project.

## Root Directory

```
self_llm/
├── api_server.py              # FastAPI server (main entry point)
├── web_interface.py           # Streamlit web interface (legacy)
├── rate_limiter.py            # Rate limiting for API
├── trending.py                # Trending topics tracker
├── config.env.example         # Environment variables template
├── requirements.txt           # Python dependencies
├── Dockerfile.worker          # Docker image for workers
├── docker-compose.rag.yml     # Docker Compose configuration
├── README.md                  # Main documentation
│
├── app/                       # Main application code
│   ├── __init__.py
│   ├── client.py              # LLM client library
│   ├── client_simple.py       # Simple client wrapper
│   ├── worker_rag.py          # RAG-enabled worker
│   ├── worker_ollama.py       # Ollama/OpenRouter worker
│   ├── rag_system.py          # RAG system core
│   ├── worker.py              # Legacy worker (may be obsolete)
│   └── prompts/               # LLM prompt templates
│       ├── __init__.py
│       └── *.txt              # Prompt files (14 files)
│
├── docs/                      # Documentation
│   ├── SECURITY.md            # Security guide
│   ├── RAG_SETUP.md          # RAG setup guide
│   ├── TROUBLESHOOTING.md     # Troubleshooting guide
│   ├── UPGRADE_GUIDE.md      # Upgrade instructions
│   └── ...                    # Other documentation files
│
├── scripts/                   # Shell scripts
│   ├── setup_rag_docker.sh    # Setup Docker services
│   ├── start_web_interface.sh # Start web interface
│   ├── cleanup_for_github.sh  # Cleanup for GitHub
│   └── ...                    # Other setup/utility scripts
│
├── tests/                     # Test files
│   ├── test_fixes.py
│   ├── test_professional_prompts.py
│   ├── test_quality_improvements.py
│   └── test_routine.py
│
├── utils/                     # Utility scripts
│   ├── update_rss_periodic.py # RSS feed updater (used by Docker)
│   ├── update_rss_feeds.py    # One-time RSS update
│   ├── re_embed_articles.py   # Re-embed articles
│   ├── re_enrich_articles.py  # Re-enrich articles
│   └── lightweight_enrich.py  # Lightweight enrichment
│
└── web/                       # Next.js web interface
    ├── package.json
    ├── next.config.js
    └── ...                    # Next.js application files
```

## Key Directories

### `app/`
Core application code including:
- Workers for processing LLM requests
- RAG system for article retrieval
- Client libraries for interacting with the system
- Prompt templates for LLM interactions

### `docs/`
All documentation files including:
- Setup guides
- Security documentation
- Troubleshooting guides
- Upgrade instructions

### `scripts/`
Shell scripts for:
- Setting up the system
- Starting services
- Maintenance tasks
- GitHub preparation

### `tests/`
Test files for:
- Quality improvements
- Professional prompts
- System fixes
- Routine testing

### `utils/`
Utility scripts for:
- RSS feed management
- Article enrichment
- Database maintenance

### `web/`
Next.js frontend application (modern web interface)

## File Organization Principles

1. **Documentation**: All `.md` files (except `README.md`) are in `docs/`
2. **Scripts**: All `.sh` files are in `scripts/`
3. **Tests**: All `test_*.py` files are in `tests/`
4. **Utilities**: Standalone utility scripts are in `utils/`
5. **Core Code**: Main application code stays in `app/` or root (for entry points)

## Important Files

- **`api_server.py`**: Main FastAPI server - entry point for API requests
- **`docker-compose.rag.yml`**: Docker Compose configuration - defines all services
- **`config.env.example`**: Template for environment variables - copy to `.env` and fill in secrets
- **`README.md`**: Main documentation - start here for setup instructions
