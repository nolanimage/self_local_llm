# Next.js Web Interface Setup

## Overview

A modern Next.js 14 web interface has been created to replace the Streamlit interface. The architecture uses:

- **Frontend**: Next.js 14 with React and Tailwind CSS
- **Backend API**: FastAPI server (Python) that bridges Next.js with RabbitMQ
- **Communication**: Next.js → FastAPI → RabbitMQ → Worker → Ollama

## Architecture

```
Next.js (Port 3000) → FastAPI (Port 8000) → RabbitMQ → Worker → Ollama
```

## Setup Instructions

### 1. Install Next.js Dependencies

```bash
cd web
npm install
```

### 2. Install Python API Dependencies

```bash
pip install fastapi uvicorn pydantic
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 3. Start the System

**Option A: Use the start script**
```bash
./start_nextjs.sh
```

**Option B: Manual start**

Terminal 1 - Start API server:
```bash
python3 api_server.py
```

Terminal 2 - Start Next.js:
```bash
cd web
npm run dev
```

### 4. Access the Interface

- **Web Interface**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health

## Features

- ✨ Modern, responsive UI with Tailwind CSS
- 💬 Real-time chat interface
- 🔄 RAG-enhanced responses
- 🌐 Supports English and Traditional Chinese
- ⚙️ Adjustable parameters (max tokens, temperature, timeout)
- 📊 Response metadata display
- 🎨 Beautiful gradient designs

## API Endpoints

### POST `/api/chat`

Request:
```json
{
  "prompt": "Your question here",
  "max_tokens": 250,
  "temperature": 0.7,
  "timeout": 120,
  "use_rag": true
}
```

Response:
```json
{
  "request_id": "uuid",
  "response": "Generated response",
  "status": "success",
  "rag_used": true,
  "articles_found": 3
}
```

### GET `/health`

Returns system health status.

## Configuration

Environment variables for API server (can be set in `.env` or system environment):

- `RABBITMQ_HOST` (default: localhost)
- `RABBITMQ_PORT` (default: 5672)
- `RABBITMQ_USER` (default: admin)
- `RABBITMQ_PASS` (default: admin123)

## Development

### Next.js Development

```bash
cd web
npm run dev
```

### Production Build

```bash
cd web
npm run build
npm start
```

### API Server Development

```bash
python3 api_server.py
```

Or with auto-reload (if using uvicorn directly):

```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

## Comparison with Streamlit

| Feature | Streamlit | Next.js |
|---------|-----------|---------|
| UI Framework | Streamlit | React + Tailwind |
| Performance | Good | Excellent |
| Customization | Limited | Full control |
| Mobile Support | Basic | Excellent |
| API Integration | Direct | Via FastAPI |
| Deployment | Simple | Flexible |

## Migration Notes

- Streamlit interface (`web_interface.py`) is still available
- Next.js interface is the new recommended option
- Both can run simultaneously (different ports)
- API server handles RabbitMQ communication for Next.js
