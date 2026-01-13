# Troubleshooting Docker Hang Issues

## Common Causes

### 1. **GPU Requirements (Most Common on Mac)**
The docker-compose.yml was configured for NVIDIA GPU, but Mac doesn't have NVIDIA GPUs.

**Solution:** I've updated the configuration to make GPU optional. The vLLM container will now run on CPU (slower but works).

### 2. **Model Loading Takes Time**
A 20B model can take 5-10 minutes to load, especially on CPU.

**Solution:** Be patient and monitor logs:
```bash
docker-compose logs -f vllm
```

### 3. **Docker Desktop Resource Constraints**
Docker Desktop may not have enough memory allocated.

**Solution:**
1. Open Docker Desktop
2. Go to Settings > Resources
3. Increase Memory to at least 8GB (16GB recommended for 20B model)
4. Apply & Restart

### 4. **Disk Space**
Model loading requires temporary space.

**Solution:** Check disk space:
```bash
df -h /System/Volumes/Data
```
Free up space if needed.

## Quick Fix Scripts

### Diagnose the Issue
```bash
cd ~/Desktop/code_for_fun/self_llm
bash diagnose_docker.sh
```

### Fix Docker Hang
```bash
cd ~/Desktop/code_for_fun/self_llm
bash fix_docker_hang.sh
```

## Manual Steps

### 1. Stop Everything
```bash
docker-compose down
docker ps -a | grep -E "vllm|rabbitmq|worker" | awk '{print $1}' | xargs docker rm -f
```

### 2. Rebuild Without GPU
The configuration has been updated. Rebuild:
```bash
docker-compose build --no-cache vllm
```

### 3. Start Services
```bash
# Start RabbitMQ first
docker-compose up -d rabbitmq
sleep 10

# Start vLLM (will be slow on CPU)
docker-compose up -d vllm

# Monitor vLLM loading (this will take 5-10 minutes)
docker-compose logs -f vllm
```

### 4. Wait for vLLM
Look for these messages in logs:
- "Application startup complete"
- "Uvicorn running on http://0.0.0.0:8000"
- "Model loaded successfully"

### 5. Start Worker
Once vLLM is ready:
```bash
docker-compose up -d worker
```

## Performance Notes

**CPU Mode:**
- Model loading: 5-10 minutes
- Inference: Very slow (may take 30+ seconds per request)
- Memory: Requires 16GB+ RAM

**GPU Mode (if you have NVIDIA GPU):**
- Model loading: 2-5 minutes
- Inference: Fast (1-5 seconds per request)
- Memory: Requires 40GB+ VRAM for 20B model

## Check What's Happening

```bash
# Check container status
docker-compose ps

# Check resource usage
docker stats

# Check specific service logs
docker-compose logs -f vllm
docker-compose logs -f worker
docker-compose logs -f rabbitmq

# Check if ports are in use
lsof -i :8000  # vLLM
lsof -i :5672  # RabbitMQ
lsof -i :15672 # RabbitMQ Management
```

## If Still Hanging

1. **Check Docker Desktop is running**
   - Open Docker Desktop
   - Make sure it shows "Docker Desktop is running"

2. **Restart Docker Desktop**
   - Quit Docker Desktop completely
   - Restart it
   - Wait for it to fully start

3. **Check system resources**
   ```bash
   # Check memory
   vm_stat | head -10
   
   # Check CPU
   top -l 1 | head -10
   ```

4. **Try starting services individually**
   ```bash
   # Just RabbitMQ
   docker-compose up -d rabbitmq
   
   # Wait, then vLLM
   docker-compose up -d vllm
   
   # Monitor vLLM separately
   docker-compose logs -f vllm
   ```

## Alternative: Use Smaller Model

If the 20B model is too large for your system, consider using a smaller model:

```bash
# Download a smaller model (e.g., 7B)
python3 download_model.py microsoft/DialoGPT-large ~/models
```

Then update the docker-compose.yml to use the smaller model.
