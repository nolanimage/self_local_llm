"""
Simple RabbitMQ client for LLM requests
"""
import pika
import json
import uuid
import time
from typing import Dict, Any, Optional


class LLMClient:
    """Client for sending requests to LLM via RabbitMQ"""
    
    def __init__(self, 
                 host='localhost',
                 port=5672,
                 user='admin',
                 password='admin123'):
        """Initialize RabbitMQ connection"""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=host,
                port=port,
                credentials=pika.PlainCredentials(user, password)
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
                 timeout: int = 60) -> Optional[Dict[str, Any]]:
        """Send a prompt and get response"""
        request_id = str(uuid.uuid4())
        
        # Send request
        message = {
            'request_id': request_id,
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        self.channel.basic_publish(
            exchange='',
            routing_key='llm_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        # Wait for response
        response_data = None
        response_received = False
        
        def callback(ch, method, properties, body):
            nonlocal response_data, response_received
            try:
                data = json.loads(body)
                if data.get('request_id') == request_id:
                    response_data = data
                    response_received = True
                    ch.basic_ack(method.delivery_tag)
            except:
                pass
        
        self.channel.basic_consume(
            queue='llm_responses',
            on_message_callback=callback,
            auto_ack=False
        )
        
        start_time = time.time()
        while not response_received and (time.time() - start_time) < timeout:
            self.connection.process_data_events(time_limit=1)
            time.sleep(0.3)
        
        return response_data if response_received else None
    
    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
