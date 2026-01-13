import pika
import json
import uuid
import time
import sys
import re

# Test queries for the new professional prompts
TEST_QUERIES = [
    "今天關於內蒙古校服的調查有什麼進展？",  # Complex query for structured output
    "馬拉松"                                # Check for professional 'No Info' response
]

def run_test():
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                port=5672,
                credentials=pika.PlainCredentials('admin', 'admin123')
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue='llm_requests', durable=True)
        # Use a private reply queue per request to avoid interference with other clients/tests
        
        print(f"🚀 Starting Professional Intelligence Report Test...")
        print("-" * 60)

        for query in TEST_QUERIES:
            request_id = str(uuid.uuid4())
            result = channel.queue_declare(queue='', exclusive=True, auto_delete=True)
            callback_queue = result.method.queue

            message = {
                'request_id': request_id,
                'prompt': query,
                'max_tokens': 800, # Increased for detailed reports
                'temperature': 0.1
            }
            
            print(f"📡 Query: '{query}'")
            channel.basic_publish(
                exchange='',
                routing_key='llm_requests',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2, reply_to=callback_queue)
            )
            
            # Wait for response
            response_data = None
            start_time = time.time()
            timeout = 150 
            
            while (time.time() - start_time) < timeout:
                method_frame, header_frame, body = channel.basic_get(queue=callback_queue, auto_ack=True)
                if body:
                    data = json.loads(body)
                    if data.get('request_id') == request_id:
                        response_data = data
                        break
                time.sleep(1)
            
            if response_data:
                res = response_data.get('response', '')
                print(f"✅ Received ({int(time.time() - start_time)}s):")
                print("-" * 30)
                print(res)
                print("-" * 30)
                
                # Check for structured headers
                if "### ⚡ 今日快訊" in res or "News Flash" in res:
                    print("✨ VERIFIED: Structured Journalistic Format detected.")
                else:
                    print("⚠️ WARNING: Structured format missing.")
            else:
                print(f"❌ Timed out waiting for response to: {query}")
            print("-" * 60)

        connection.close()
        print("Professional prompt test completed.")

    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    run_test()
