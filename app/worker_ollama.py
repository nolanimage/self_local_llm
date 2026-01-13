"""
RabbitMQ Worker that processes messages and sends them to Ollama server or OpenRouter
Supports both local Ollama and OpenRouter API for faster testing
"""
import os
import json
import logging
import pika
import requests
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
# Security: Use environment variable for password (default for development only)
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'admin123')  # ⚠️ Change in production!
if RABBITMQ_PASS == 'admin123':
    logger.warning("⚠️  Using default RabbitMQ password. Set RABBITMQ_PASS environment variable for production!")
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')  # Qwen2.5 1.5B model (available, good quality)

# NEW: OpenRouter configuration for faster testing
USE_OPENROUTER = os.getenv('USE_OPENROUTER', 'false').lower() == 'true'
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'moonshotai/kimi-k2:free')  # MoonshotAI Kimi K2 - excellent for Chinese

# RabbitMQ queue names
REQUEST_QUEUE = 'llm_requests'
RESPONSE_QUEUE = 'llm_responses'


class LLMWorker:
    def __init__(self):
        """Initialize the LLM worker with RabbitMQ and Ollama/OpenRouter connections"""
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
        self.use_openrouter = USE_OPENROUTER
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.openrouter_model = OPENROUTER_MODEL
        self.connection = None
        self.channel = None
        
        if self.use_openrouter:
            if not self.openrouter_api_key:
                logger.warning("USE_OPENROUTER=true but OPENROUTER_API_KEY is not set. Falling back to Ollama.")
                self.use_openrouter = False
            else:
                logger.info(f"✓ OpenRouter mode enabled: {self.openrouter_model}")
        else:
            logger.info(f"✓ Ollama mode: {self.ollama_model}")
        
    def call_openrouter(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7) -> str:
        """Call OpenRouter API for faster inference"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",  # Optional
                "X-Title": "Self-LLM News Search"  # Optional
            }
            
            payload = {
                "model": self.openrouter_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result['choices'][0]['message']['content']
                logger.info(f"OpenRouter response length: {len(generated_text)}")
                return generated_text
            else:
                logger.warning(f"⚠️ OpenRouter error ({response.status_code}): {response.text}. Falling back to local Ollama...")
                return self.call_ollama(prompt, max_tokens, temperature)
                
        except Exception as e:
            logger.error(f"OpenRouter call failed: {e}. Falling back to local Ollama...")
            return self.call_ollama(prompt, max_tokens, temperature)
    
    def call_ollama(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7, timeout: int = 30) -> str:
        """Call local Ollama API"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                        "num_ctx": 1024, # Reduced context for speed
                        "repeat_penalty": 1.1,
                        "num_thread": 4,
                        "use_mmap": True,
                        "use_mlock": False
                    }
                },
                timeout=timeout # Optimized timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                if not generated_text and result.get('thinking'):
                    generated_text = result.get('thinking', '')
                    logger.info("Using thinking content as response (response was empty)")
                logger.info(f"Ollama response length: {len(generated_text)}")
                return generated_text
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return f"Ollama Error: {response.text}"
                
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return f"Error calling Ollama: {str(e)}"
        
    def connect_rabbitmq(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queues
            self.channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
            self.channel.queue_declare(queue=RESPONSE_QUEUE, durable=True)
            
            logger.info(f"Connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def process_request(self, ch, method, properties, body):
        """Process incoming LLM request from RabbitMQ"""
        try:
            # Parse request
            request_data = json.loads(body)
            request_id = request_data.get('request_id', 'unknown')
            prompt = request_data.get('prompt', '')
            max_tokens = request_data.get('max_tokens', 100)
            temperature = request_data.get('temperature', 0.7)
            
            logger.info(f"Processing request {request_id}: {prompt[:50]}...")
            
            # Route to appropriate backend
            if self.use_openrouter:
                logger.info(f"Using OpenRouter: {self.openrouter_model}")
                generated_text = self.call_openrouter(prompt, max_tokens, temperature)
            else:
                logger.info(f"Using Ollama: {self.ollama_model}")
                generated_text = self.call_ollama(prompt, max_tokens, temperature)
            
            # Send response back to RabbitMQ
            response_data = {
                'request_id': request_id,
                'response': generated_text,
                'model': self.openrouter_model if self.use_openrouter else self.ollama_model,
                'backend': 'openrouter' if self.use_openrouter else 'ollama',
                'status': 'success'
            }
            
            # Use reply_to if available (RPC pattern), otherwise fallback to default response queue
            reply_to = properties.reply_to if properties.reply_to else RESPONSE_QUEUE
            
            self.channel.basic_publish(
                exchange='',
                routing_key=reply_to,
                body=json.dumps(response_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    correlation_id=properties.correlation_id
                )
            )
            
            logger.info(f"Request {request_id} completed successfully")
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            # Reject message and don't requeue (to avoid infinite loops)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start(self):
        """Start consuming messages from RabbitMQ"""
        self.connect_rabbitmq()
        
        # Set QoS to process one message at a time
        self.channel.basic_qos(prefetch_count=1)
        
        # Start consuming
        self.channel.basic_consume(
            queue=REQUEST_QUEUE,
            on_message_callback=self.process_request
        )
        
        logger.info("Worker started. Waiting for messages. To exit press CTRL+C")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping worker...")
            self.channel.stop_consuming()
            self.connection.close()


def main():
    """Main entry point"""
    worker = LLMWorker()
    worker.start()


if __name__ == '__main__':
    main()
