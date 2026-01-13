import pika
import json
import uuid
import time
import sys

# Feeds to test
TEST_QUERIES = [
    "你好",              # Should detect greeting
    "馬拉松",            # Should NOT match Maresca (M馬利斯卡)
    "今天有什麼新聞？",    # Should trigger RAG
    "香港天氣"           # Should trigger RAG (likely no info, but should be honest)
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
        channel.queue_declare(queue='llm_responses', durable=True)
        
        print(f"🚀 Starting RAG Fixes Verification Test...")
        print("-" * 50)

        for query in TEST_QUERIES:
            request_id = str(uuid.uuid4())
            message = {
                'request_id': request_id,
                'prompt': query,
                'max_tokens': 300,
                'temperature': 0.1 # Low temp for consistency
            }
            
            print(f"📡 Sending query: '{query}'...")
            channel.basic_publish(
                exchange='',
                routing_key='llm_requests',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            # Wait for response
            response_data = None
            start_time = time.time()
            timeout = 120 # RAG can take a while if processing multiple steps
            
            while (time.time() - start_time) < timeout:
                method_frame, header_frame, body = channel.basic_get(queue='llm_responses', auto_ack=True)
                if body:
                    data = json.loads(body)
                    if data.get('request_id') == request_id:
                        response_data = data
                        break
                    else:
                        # Put back other responses
                        channel.basic_publish(exchange='', routing_key='llm_responses', body=body)
                time.sleep(1)
            
            if response_data:
                print(f"✅ Response received ({int(time.time() - start_time)}s):")
                print(f"   [{response_data.get('model', 'unknown')}]")
                print(f"   {response_data.get('response', '').strip()[:300]}...")
                
                # Check for Maresca in Marathon query
                if query == "馬拉松" and "马利斯卡" in response_data.get('response', ''):
                    print("❌ FAILED: 'Marathon' query still contains 'Maresca' football news!")
                elif query == "馬拉松":
                    print("✨ PASSED: 'Marathon' query did not hallucinate football news.")
            else:
                print(f"❌ Timed out waiting for response to: {query}")
            print("-" * 50)

        connection.close()
        print("Test completed.")

    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    run_test()
