"""
Legacy RabbitMQ Worker for LLM requests
Simple worker that processes messages and sends them to Ollama server
This is the basic version before RAG and OpenRouter enhancements
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
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'admin123')
if RABBITMQ_PASS == 'admin123':
    logger.warning("⚠️  Using default RabbitMQ password. Set RABBITMQ_PASS environment variable for production!")

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')

# RabbitMQ queue names
REQUEST_QUEUE = 'llm_requests'
RESPONSE_QUEUE = 'llm_responses'


class LLMWorker:
    """Simple LLM worker that processes RabbitMQ messages and calls Ollama"""
    
    def __init__(self):
        """Initialize the LLM worker with RabbitMQ and Ollama connections"""
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
        self.connection = None
        self.channel = None
        logger.info(f"Initialized LLM Worker with Ollama: {self.ollama_model}")
    
    def call_ollama(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7) -> str:
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
                        "temperature": temperature
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                logger.info(f"Generated {len(generated_text)} characters")
                return generated_text
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return f"Error: Ollama API returned {response.status_code}"
                
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
            
            logger.info("✓ Connected to RabbitMQ")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_message(self, ch, method, properties, body):
        """Process a single message from RabbitMQ"""
        try:
            # Parse message
            message = json.loads(body)
            request_id = message.get('request_id')
            prompt = message.get('prompt', '')
            max_tokens = message.get('max_tokens', 100)
            temperature = message.get('temperature', 0.7)
            
            logger.info(f"Processing request {request_id[:8]}...")
            
            # Call Ollama
            response_text = self.call_ollama(prompt, max_tokens, temperature)
            
            # Send response
            response_message = {
                'request_id': request_id,
                'response': response_text,
                'status': 'success'
            }
            
            self.channel.basic_publish(
                exchange='',
                routing_key=RESPONSE_QUEUE,
                body=json.dumps(response_message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✓ Completed request {request_id[:8]}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Send error response
            try:
                error_response = {
                    'request_id': message.get('request_id', 'unknown'),
                    'response': f"Error: {str(e)}",
                    'status': 'error'
                }
                self.channel.basic_publish(
                    exchange='',
                    routing_key=RESPONSE_QUEUE,
                    body=json.dumps(error_response),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
            except:
                pass
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start(self):
        """Start the worker and begin processing messages"""
        if not self.connect_rabbitmq():
            logger.error("Failed to connect to RabbitMQ. Exiting.")
            return
        
        logger.info("Starting worker...")
        logger.info(f"Listening on queue: {REQUEST_QUEUE}")
        
        # Set QoS to process one message at a time
        self.channel.basic_qos(prefetch_count=1)
        
        # Start consuming
        self.channel.basic_consume(
            queue=REQUEST_QUEUE,
            on_message_callback=self.process_message
        )
        
        try:
            logger.info("✓ Worker ready. Waiting for messages...")
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
