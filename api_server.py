#!/usr/bin/env python3
"""
FastAPI server to bridge Next.js frontend with RabbitMQ
Supports Real-Time Streaming and Agentic Reasoning
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pika
import json
import uuid
import time
import os
import sqlite3
import subprocess
import requests
from typing import Optional
import asyncio
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import rate limiter and trending tracker
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rate_limiter import rate_limiter
from trending import trending_tracker

app = FastAPI(title="Self LLM API Server")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    if response.status_code == 404:
        logger.warning(f"404 Not Found: {request.method} {request.url.path}")
    return response

@app.get("/")
async def root():
    return {
        "message": "Self LLM API Server is running",
        "endpoints": [
            "/health",
            "/api/rag/stats",
            "/api/trending",
            "/api/rag/articles"
        ]
    }

@app.get("/api")
async def api_root():
    return {"message": "API root. Use specific endpoints like /api/rag/articles"}

# CORS middleware for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', '127.0.0.1')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
# Security: Use environment variable for password (default for development only)
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'admin123')  # ⚠️ Change in production!
if RABBITMQ_PASS == 'admin123':
    logger.warning("⚠️  Using default RabbitMQ password. Set RABBITMQ_PASS environment variable for production!")
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')

# Database path - use environment variable or fallback to absolute path
DB_PATH = os.getenv('RAG_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rag_database.db'))

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    history: list = Field(default_factory=list)  # NEW: Support conversation history
    user_id: Optional[int] = None
    max_tokens: int = Field(default=500, ge=50, le=2000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: int = Field(default=120, ge=30, le=300)

class LoginRequest(BaseModel):
    username: str

def init_user_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Chat History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            prompt TEXT NOT NULL,
            response TEXT,
            rag_used BOOLEAN,
            articles_found INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_user_db()

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username FROM users WHERE username = ?', (request.username,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute('INSERT INTO users (username) VALUES (?)', (request.username,))
            conn.commit()
            user_id = cursor.lastrowid
            username = request.username
        else:
            user_id, username = user
            
        conn.close()
        return {"id": user_id, "username": username}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{user_id}")
async def get_history(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, prompt, response, rag_used, articles_found, created_at 
            FROM chat_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 50
        ''', (user_id,))
        history = []
        for r in cursor.fetchall():
            history.append({
                "id": r[0], "prompt": r[1], "response": r[2], 
                "rag_used": bool(r[3]), "articles_found": r[4], "created_at": r[5]
            })
        conn.close()
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Enhanced health check with service status"""
    status = {"status": "healthy"}
    
    # Check RabbitMQ
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
        conn = pika.BlockingConnection(parameters)
        conn.close()
        status["rabbitmq"] = "connected"
    except Exception as e:
        status["rabbitmq"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    # Check Ollama
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        status["ollama"] = "connected" if response.status_code == 200 else "error"
    except:
        status["ollama"] = "unavailable"
    
    # Check Database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        conn.close()
        status["database"] = f"ok ({count} articles)"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    return status

@app.get("/api/rate-limit/{user_id}")
async def get_rate_limit_status(user_id: str):
    """Get rate limit status for a user"""
    stats = rate_limiter.get_stats(user_id)
    return stats

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Real-time streaming endpoint with rate limiting"""
    
    # Rate limiting check
    user_id = str(request.user_id) if request.user_id else "anonymous"
    is_allowed, remaining, reset_time = rate_limiter.is_allowed(user_id)
    
    if not is_allowed:
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Rate limit exceeded",
                "message": f"You have exceeded the limit of 50 questions per hour. Please try again in {reset_time} seconds.",
                "reset_in_seconds": reset_time,
                "limit": 50
            }
        )
    
    async def event_generator():
        request_id = str(uuid.uuid4())
        
        # Track query for trending
        trending_tracker.add_query(request.prompt)
        
        try:
            # 1. Connect to RabbitMQ to request reasoning
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
            conn = pika.BlockingConnection(parameters)
            ch = conn.channel()
            
            # Create a unique response queue for this request (RPC pattern)
            result = ch.queue_declare(queue='', exclusive=True, auto_delete=True)
            callback_queue = result.method.queue
            
            message = {
                'request_id': request_id,
                'prompt': request.prompt.strip(),
                'history': request.history, # Pass history to worker
                'max_tokens': request.max_tokens,
                'temperature': request.temperature,
                'stream_mode': True 
            }
            
            # Publish with reply_to set to our unique callback queue
            ch.basic_publish(
                exchange='',
                routing_key='llm_requests',
                properties=pika.BasicProperties(reply_to=callback_queue),
                body=json.dumps(message)
            )
            
            # Initial status
            yield f"data: {json.dumps({'type': 'status', 'content': 'Agent is planning and searching knowledge...'})}\n\n"
            
            # 2. Wait for reasoning results on our private callback queue
            start_time = time.time()
            enhanced_data = None
            
            while (time.time() - start_time) < request.timeout:
                method, props, body = ch.basic_get(queue=callback_queue, auto_ack=True)
                if method:
                    enhanced_data = json.loads(body)
                    break
                await asyncio.sleep(0.5)
            
            # Clean up: delete the temporary queue and close connection
            ch.queue_delete(queue=callback_queue)
            conn.close()
            
            if not enhanced_data:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Agent reasoning timeout'})}\n\n"
                return

            # Send metadata (tools used, RAG status)
            yield f"data: {json.dumps({'type': 'metadata', 'data': enhanced_data})}\n\n"

            # 3. Check if response is already generated (OpenRouter) or needs streaming (Ollama)
            final_prompt = enhanced_data.get('final_prompt', None)
            response_text = enhanced_data.get('response', '')
            model = enhanced_data.get('model', 'qwen2.5:1.5b')
            full_response = ""
            
            # Update status
            yield f"data: {json.dumps({'type': 'status', 'content': 'Generating final answer...'})}\n\n"

            # If response is already generated (OpenRouter or greeting), stream it character by character or in small chunks
            if response_text and response_text != "[STREAMING_READY]":
                logger.info(f"Response already generated, streaming to client...")
                # Stream in small chunks to preserve formatting (newlines, etc.)
                chunk_size = 4
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i+chunk_size]
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.02)
            
            # Otherwise stream from Ollama (traditional mode)
            elif final_prompt:
                try:
                    ollama_response = requests.post(
                        f"{OLLAMA_URL}/api/generate",
                        json={
                            "model": model,
                            "prompt": final_prompt,
                            "stream": True,
                            "options": {
                                "num_predict": request.max_tokens,
                                "temperature": request.temperature,
                                "num_ctx": 2048
                            }
                        },
                        stream=True,
                        timeout=120
                    )
                    
                    for line in ollama_response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if chunk.get('response'):
                                    content = chunk['response']
                                    full_response += content
                                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
                                if chunk.get('done'):
                                    break
                            except Exception as parse_err:
                                logger.warning(f"Error parsing Ollama chunk: {parse_err}")
                except Exception as ollama_err:
                    logger.error(f"Ollama streaming error: {ollama_err}")
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Ollama error: {str(ollama_err)}'})}\n\n"
            else:
                # Fallback: just return the response as-is
                full_response = response_text
                yield f"data: {json.dumps({'type': 'chunk', 'content': full_response})}\n\n"
            
            # 4. Save to history if user_id is provided
            if request.user_id:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO chat_history (user_id, prompt, response, rag_used, articles_found)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        request.user_id, 
                        request.prompt, 
                        full_response, 
                        enhanced_data.get('rag_used', False),
                        enhanced_data.get('articles_found', 0)
                    ))
                    conn.commit()
                    conn.close()
                except Exception as history_err:
                    logger.error(f"Error saving history: {history_err}")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- RAG Management Endpoints ---

@app.get("/api/rag/articles")
async def list_articles(limit: int = 100, offset: int = 0):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM articles')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT id, title, content, summary, entities, keywords, category, link, pub_date, source, created_at FROM articles ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset))
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0], 
                'title': row[1], 
                'content': row[2][:300] + "..." if len(row[2]) > 300 else row[2],
                'summary': row[3],
                'entities': row[4],
                'keywords': row[5],
                'category': row[6],
                'link': row[7], 
                'pub_date': row[8], 
                'source': row[9], 
                'created_at': row[10]
            })
        conn.close()
        return {"articles": articles, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/articles/{article_id}")
async def get_article_detail(article_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, content, summary, entities, keywords, category, link, pub_date, source, created_at FROM articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0], 'title': row[1], 'content': row[2], 'summary': row[3], 'entities': row[4], 'keywords': row[5], 'category': row[6], 'link': row[7], 'pub_date': row[8], 'source': row[9], 'created_at': row[10]
            }
        raise HTTPException(status_code=404, detail="Article not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/articles/{article_id}/related")
async def get_related_articles(article_id: int, limit: int = 5):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Get current article metadata
        cursor.execute('SELECT entities, keywords, category FROM articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"related": []}
        
        ent_str, kw_str, category = row
        ent_str = ent_str or ""
        kw_str = kw_str or ""
        target_tags = set([t.strip() for t in (ent_str + "," + kw_str).split(',') if t.strip()])
        
        # 2. Find candidates
        cursor.execute('''
            SELECT id, title, entities, keywords, category, pub_date, source
            FROM articles 
            WHERE id != ? AND (category = ? OR (entities IS NOT NULL AND entities LIKE ?) OR (keywords IS NOT NULL AND keywords LIKE ?))
            ORDER BY created_at DESC LIMIT 50
        ''', (article_id, category, f'%{ent_str[:10]}%', f'%{kw_str[:10]}%'))
        
        candidates = []
        for r_id, r_title, r_ent, r_kw, r_cat, r_date, r_source in cursor.fetchall():
            r_ent = r_ent or ""
            r_kw = r_kw or ""
            r_tags = set([t.strip() for t in (r_ent + "," + r_kw).split(',') if t.strip()])
            
            # Intersection
            shared = target_tags.intersection(r_tags)
            score = len(shared) / len(target_tags.union(r_tags)) if target_tags.union(r_tags) else 0
            
            if r_cat == category: score += 0.1
            
            candidates.append({
                'id': r_id, 'title': r_title, 'score': score, 
                'category': r_cat, 'pub_date': r_date, 'source': r_source,
                'reason': f'Shared: {", ".join(list(shared)[:2])}' if shared else 'Same Topic'
            })
        
        conn.close()
        return {"related": sorted(candidates, key=lambda x: x['score'], reverse=True)[:limit]}
    except Exception as e:
        logger.error(f"Error getting related articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/stats")
async def rag_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM articles')
        count = cursor.fetchone()[0]
        conn.close()
        return {"total_articles": count, "status": "active"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rag/articles/{article_id}")
async def delete_article(article_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM articles WHERE id = ?', (article_id,))
        conn.commit()
        conn.close()
        return {"message": "Deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trending")
async def get_trending(limit: int = 10):
    """Get trending search topics"""
    trending = trending_tracker.get_trending(limit=limit)
    stats = trending_tracker.get_stats()
    return {
        "trending": trending,
        "stats": stats
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
