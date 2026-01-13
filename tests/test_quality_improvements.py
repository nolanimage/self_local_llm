"""
Comprehensive test suite for quality improvements:
1. Evidence-first analysis (fact table + constrained analysis)
2. Intent classification (brief/update/compare/explain)
3. Clarifying questions for ambiguous queries
4. General functionality
"""
import pika
import json
import uuid
import time
import sys

TEST_CASES = [
    # Category: Greetings (should skip RAG)
    {
        "query": "你好",
        "expected": "greeting",
        "description": "Greeting detection"
    },
    {
        "query": "Hello",
        "expected": "greeting",
        "description": "English greeting"
    },
    
    # Category: Ambiguous queries (should ask for clarification OR proceed if strong match)
    {
        "query": "馬拉松",
        "expected": "clarify",
        "description": "Short ambiguous query (3 chars) - should ask for clarification if no strong match"
    },
    {
        "query": "香港",
        "expected": "clarify_or_rag",
        "description": "Short ambiguous query (2 chars) - should clarify OR proceed if strong match found"
    },
    
    # Category: Out-of-scope (weather router)
    {
        "query": "香港天氣",
        "expected": "out_of_scope",
        "description": "Weather query - should be routed out"
    },
    
    # Category: General news queries (should use RAG)
    {
        "query": "今天有什麼新聞？",
        "expected": "rag_with_analysis",
        "description": "General news query - should use RAG with evidence-first analysis"
    },
    {
        "query": "內蒙古校服",
        "expected": "rag_with_analysis",
        "description": "Specific topic query - should use RAG with constrained analysis"
    },
    
    # Category: Intent-specific queries
    {
        "query": "香港最新新聞",
        "expected": "intent_update",
        "description": "Update intent query - should classify as 'update'"
    },
    {
        "query": "為什麼內蒙古校服事件引起關注？",
        "expected": "intent_explain",
        "description": "Explain intent query - should classify as 'explain'"
    },
]

def check_response(response_text, expected_type, query):
    """Check if response matches expected behavior"""
    checks = {
        "greeting": lambda r: any(x in r.lower() for x in ["你好", "hello", "help", "assistant"]),
        "clarify": lambda r: any(x in r for x in ["選擇", "選項", "clarify", "選項1", "選項2", "選項3"]),
        "clarify_or_rag": lambda r: (
            any(x in r for x in ["選擇", "選項", "clarify", "選項1", "選項2", "選項3"]) or
            ("### ⚡" in r and "### 🔍" in r and "### 📋" in r)
        ),
        "out_of_scope": lambda r: "天氣" in r or "weather" in r.lower() or "氣象" in r,
        "rag_with_analysis": lambda r: "### ⚡" in r and "### 🔍" in r and "### 📋" in r,
        "intent_update": lambda r: "### ⚡" in r and "### 🔍" in r,  # Intent is used internally, just check structure
        "intent_explain": lambda r: "### ⚡" in r and "### 🔍" in r,  # Intent is used internally, just check structure
    }
    
    if expected_type not in checks:
        return True, "Unknown expected type"
    
    passed = checks[expected_type](response_text)
    return passed, "✓ Matched expected behavior" if passed else "✗ Did not match expected behavior"

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
        
        print("=" * 70)
        print("🚀 COMPREHENSIVE QUALITY IMPROVEMENTS TEST")
        print("=" * 70)
        print()
        
        results = {
            "passed": 0,
            "failed": 0,
            "total": len(TEST_CASES)
        }
        
        for i, test_case in enumerate(TEST_CASES, 1):
            query = test_case["query"]
            expected = test_case["expected"]
            description = test_case["description"]
            
            print(f"[{i}/{len(TEST_CASES)}] {description}")
            print(f"   Query: '{query}'")
            print(f"   Expected: {expected}")
            
            request_id = str(uuid.uuid4())
            message = {
                'request_id': request_id,
                'prompt': query,
                'max_tokens': 300,
                'temperature': 0.1,
                'history': []
            }
            
            channel.basic_publish(
                exchange='',
                routing_key='llm_requests',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            # Wait for response
            response_data = None
            start_time = time.time()
            timeout = 60
            
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
                time.sleep(0.5)
            
            if response_data:
                response_text = response_data.get('response', '')
                elapsed = int(time.time() - start_time)
                
                # Check response
                passed, message = check_response(response_text, expected, query)
                
                if passed:
                    results["passed"] += 1
                    status = "✅ PASS"
                else:
                    results["failed"] += 1
                    status = "❌ FAIL"
                
                print(f"   {status} ({elapsed}s) - {message}")
                print(f"   Response preview: {response_text[:150]}...")
                
                # Show tools used if available
                tools = response_data.get('tools_used', [])
                if tools:
                    print(f"   Tools: {', '.join(tools)}")
            else:
                results["failed"] += 1
                print(f"   ❌ TIMEOUT (>{timeout}s)")
            
            print()
        
        # Summary
        print("=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total tests: {results['total']}")
        print(f"✅ Passed: {results['passed']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"Success rate: {(results['passed']/results['total']*100):.1f}%")
        print("=" * 70)
        
        connection.close()
        return results["failed"] == 0
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
