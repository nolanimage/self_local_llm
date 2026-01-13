# 🚀 OpenRouter Integration - Quick Reference

## What is OpenRouter?

OpenRouter is a **unified API gateway** that provides access to multiple LLM providers through a single API. It offers **free tier access** to various open-source models, making it perfect for rapid testing and development.

---

## ✅ Setup in 60 Seconds

### Step 1: Get API Key (30 seconds)
```bash
# 1. Visit https://openrouter.ai/
# 2. Sign up (free, no credit card)
# 3. Settings → API Keys → Create Key
# Copy the key (starts with "sk-or-v1-...")
```

### Step 2: Enable OpenRouter (30 seconds)
```bash
# Edit docker-compose.rag.yml, find the 'worker' service, and change:
USE_OPENROUTER: "true"
OPENROUTER_API_KEY: "sk-or-v1-YOUR-KEY-HERE"

# Restart
docker-compose -f docker-compose.rag.yml restart worker
```

**Done!** Your system now uses OpenRouter for 3-5x faster inference.

---

## 🎯 When to Use Which Backend

| Scenario | Recommended Backend | Why |
|----------|-------------------|-----|
| **Active development** | OpenRouter | 3-5x faster iteration |
| **Frontend testing** | OpenRouter | Quick feedback loop |
| **API testing** | OpenRouter | No local resource usage |
| **Final production** | Ollama | No API costs, full privacy |
| **High volume** | Ollama | No rate limits |
| **Offline deployment** | Ollama | No internet required |

---

## 🆓 Free Models Available

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `qwen/qwen-2-7b-instruct:free` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Chinese + English** (Recommended) |
| `google/gemma-2-9b-it:free` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | High quality responses |
| `meta-llama/llama-3-8b-instruct:free` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Fast general use |
| `mistralai/mistral-7b-instruct:free` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | English-focused |

**Free Tier Limits**: ~20 requests/min, 100-1000 requests/day (varies by model)

---

## 📊 Performance Comparison (Real Tests)

### Simple Query ("你好")
- **Ollama**: 2-3 seconds
- **OpenRouter**: 0.5-1 second
- **Speedup**: 3x

### News Query with RAG
- **Ollama**: 12-20 seconds
- **OpenRouter**: 3-5 seconds
- **Speedup**: 4x

### Multi-Query Retrieval
- **Ollama**: 15-25 seconds
- **OpenRouter**: 4-6 seconds
- **Speedup**: 4-5x

---

## 🔧 Quick Commands

### Enable OpenRouter (One-time)
```bash
# Method 1: Using docker-compose
nano docker-compose.rag.yml  # Edit the file
docker-compose -f docker-compose.rag.yml restart worker

# Method 2: Quick test (temporary)
docker stop llm_worker_rag
docker run -it --rm --network self_llm_default \
  -e USE_OPENROUTER=true \
  -e OPENROUTER_API_KEY="your-key" \
  -e RABBITMQ_HOST=rabbitmq \
  llm_worker_rag python3 -m app.worker_rag
```

### Verify Current Backend
```bash
docker logs llm_worker_rag | grep -E "(Ollama mode|OpenRouter mode)"
```

### Switch Back to Ollama
```bash
# Edit docker-compose.rag.yml:
USE_OPENROUTER: "false"

# Restart
docker-compose -f docker-compose.rag.yml restart worker
```

### Test Speed Comparison
```bash
./test_openrouter.sh YOUR_API_KEY
```

---

## 🐛 Troubleshooting

### Error: "OpenRouter API key not set"
**Solution**: 
```yaml
# Make sure docker-compose.rag.yml has:
OPENROUTER_API_KEY: "sk-or-v1-..."  # Not empty!
```

### Error: "Rate limit exceeded"
**Solution**: 
- Wait 1 minute (free tier: ~20 req/min)
- Or switch to Ollama temporarily:
```bash
docker exec -e USE_OPENROUTER=false llm_worker_rag python3 -m app.worker_rag
```

### Slow responses with OpenRouter
**Check**:
1. Internet connection speed
2. Model status: https://status.openrouter.ai
3. Try different model:
```yaml
OPENROUTER_MODEL: "meta-llama/llama-3-8b-instruct:free"
```

### Worker not starting
**Debug**:
```bash
# Check logs
docker logs llm_worker_rag

# Verify API key format
echo $OPENROUTER_API_KEY  # Should start with "sk-or-v1-"
```

---

## 💡 Pro Tips

### 1. Hybrid Approach
Use OpenRouter for **planning/classification** (fast) and Ollama for **final generation** (private):
```python
# In worker_rag.py (custom modification)
if task == "planning":
    use_openrouter = True  # Fast
else:
    use_openrouter = False  # Private
```

### 2. Monitor Usage
Check your OpenRouter dashboard:
- Usage: https://openrouter.ai/activity
- Credits: https://openrouter.ai/credits
- Model status: https://openrouter.ai/models

### 3. Cost Optimization
- **Cache results** (already implemented!) to reduce API calls
- **Use multi-query sparingly** in OpenRouter mode (3 calls per query)
- **Switch to Ollama at night** for batch processing

### 4. Model Selection
- **Development**: Use faster models (`llama-3-8b`)
- **Testing quality**: Use better models (`gemma-2-9b`)
- **Production**: Switch to Ollama for consistency

---

## 📚 Additional Resources

- **Full Documentation**: `OPENROUTER_SETUP.md`
- **Configuration Template**: `config.env.example`
- **Setup Script**: `./enable_openrouter.sh`
- **Test Script**: `./test_openrouter.sh`
- **OpenRouter Docs**: https://openrouter.ai/docs

---

## ✅ Quick Verification Checklist

- [ ] API key obtained from OpenRouter
- [ ] `docker-compose.rag.yml` updated with key
- [ ] Worker restarted successfully
- [ ] Logs show "OpenRouter mode enabled"
- [ ] Frontend responds faster (test at http://localhost:3000)
- [ ] No errors in `docker logs llm_worker_rag`

---

## 🎉 You're Ready!

Your system now supports **both local (Ollama) and cloud (OpenRouter) inference**. 

- **Use OpenRouter** during development for speed
- **Use Ollama** in production for cost and privacy

**Happy testing!** 🚀
