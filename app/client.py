"""
LLM Client Library for RabbitMQ-based LLM system
Enhanced version with better error handling and reliability
"""
import os
import pika
import json
import uuid
import time
from typing import Dict, Any, Optional


class LLMClient:
    """Client for sending requests to LLM via RabbitMQ"""
    
    def __init__(self, 
                 host: Optional[str] = None,
                 port: int = 5672,
                 user: Optional[str] = None,
                 password: Optional[str] = None):
        """
        Initialize RabbitMQ connection
        
        Args:
            host: RabbitMQ host (defaults to RABBITMQ_HOST env or 'localhost')
            port: RabbitMQ port (defaults to 5672)
            user: RabbitMQ username (defaults to RABBITMQ_USER env or 'admin')
            password: RabbitMQ password (defaults to RABBITMQ_PASS env or 'admin123')
        """
        self.host = host or os.getenv('RABBITMQ_HOST', 'localhost')
        self.port = port
        self.user = user or os.getenv('RABBITMQ_USER', 'admin')
        self.password = password or os.getenv('RABBITMQ_PASS', 'admin123')
        
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=pika.PlainCredentials(self.user, self.password)
            )
        )
        self.channel = self.connection.channel()
        
        # Declare queues
        self.channel.queue_declare(queue='llm_requests', durable=True)
        self.channel.queue_declare(queue='llm_responses', durable=True)
    
    def generate(self, 
                 prompt: str,
                 max_tokens: int = 100,
                 temperature: float = 0.7,
                 timeout: int = 120) -> Optional[Dict[str, Any]]:
        """
        Send a prompt and get response
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation (0.0-2.0)
            timeout: Maximum wait time in seconds
            
        Returns:
            Dictionary with response data or None if timeout/error
        """
        request_id = str(uuid.uuid4())
        
        # Send request
        message = {
            'request_id': request_id,
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key='llm_requests',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
        except Exception as e:
            print(f"Error sending request: {e}")
            return None
        
        # Use basic_get with frequent polling - more reliable
        start_time = time.time()
        response_data = None
        checked_messages = 0
        
        while (time.time() - start_time) < timeout:
            try:
                method, properties, body = self.channel.basic_get(
                    queue='llm_responses', 
                    auto_ack=False
                )
                
                if method:
                    checked_messages += 1
                    try:
                        data = json.loads(body)
                        resp_id = data.get('request_id', '')
                        
                        # Only process if it's our request
                        if resp_id == request_id:
                            # Filter out old error messages
                            response_text = data.get('response', '')
                            if 'llama3' in response_text.lower() and 'not found' in response_text.lower():
                                # Old error - reject and continue looking
                                self.channel.basic_nack(method.delivery_tag, requeue=False)
                                continue
                            # Valid response!
                            response_data = data
                            self.channel.basic_ack(method.delivery_tag)
                            break
                        else:
                            # Not our message - reject and don't requeue
                            self.channel.basic_nack(method.delivery_tag, requeue=False)
                    except json.JSONDecodeError:
                        # Invalid message - reject
                        self.channel.basic_nack(method.delivery_tag, requeue=False)
                    except Exception as e:
                        # Other error - reject
                        self.channel.basic_nack(method.delivery_tag, requeue=False)
                else:
                    # No message available - wait a bit
                    time.sleep(0.05)
            except Exception as e:
                # On error, wait and retry
                time.sleep(0.1)
        
        return response_data
    
    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
