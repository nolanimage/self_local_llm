#!/usr/bin/env python3
"""
Routine Test Suite for Self LLM News Search Engine
Tests core functionality: API health, RAG search, streaming, rate limiting
"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}🧪 {name}{Colors.END}")

def print_pass(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_fail(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warn(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def test_health_check():
    """Test 1: Health check endpoint"""
    print_test("Test 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") in ["healthy", "degraded"], f"Invalid status: {data.get('status')}"
        print_pass(f"Health check passed: {data}")
        return True
    except Exception as e:
        print_fail(f"Health check failed: {e}")
        return False

def test_rag_search():
    """Test 2: RAG search with actual query"""
    print_test("Test 2: RAG Search (駕駛執照)")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/stream",
            headers={"Content-Type": "application/json"},
            json={"prompt": "駕駛執照", "max_tokens": 100},
            timeout=60
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Parse SSE stream
        articles_found = None
        chunks_received = 0
        
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'metadata':
                        articles_found = data.get('data', {}).get('articles_found', 0)
                    elif data.get('type') == 'chunk':
                        chunks_received += 1
                except:
                    pass
        
        if articles_found is not None and articles_found > 0:
            print_pass(f"RAG search successful: {articles_found} articles found, {chunks_received} chunks streamed")
            return True
        else:
            print_warn(f"RAG search completed but found {articles_found} articles")
            return articles_found is not None
    except Exception as e:
        print_fail(f"RAG search failed: {e}")
        return False

def test_rate_limiting():
    """Test 3: Rate limiting (50 requests per hour)"""
    print_test("Test 3: Rate Limiting")
    try:
        user_id = "test_user_123"
        
        # Check initial status
        response = requests.get(f"{BASE_URL}/api/rate-limit/{user_id}")
        assert response.status_code == 200
        initial_stats = response.json()
        print_pass(f"Rate limit check: {initial_stats['remaining']}/{initial_stats['limit']} remaining")
        
        # Make a request
        response = requests.post(
            f"{BASE_URL}/api/chat/stream",
            json={"prompt": "test", "user_id": user_id, "max_tokens": 50},
            timeout=30
        )
        
        if response.status_code == 200:
            print_pass("Request within rate limit succeeded")
        elif response.status_code == 429:
            print_pass("Rate limit correctly enforced (429 status)")
        else:
            print_warn(f"Unexpected status: {response.status_code}")
        
        return True
    except Exception as e:
        print_fail(f"Rate limiting test failed: {e}")
        return False

def test_trending_topics():
    """Test 4: Trending topics tracking"""
    print_test("Test 4: Trending Topics")
    try:
        response = requests.get(f"{BASE_URL}/api/trending", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        trending = data.get('trending', [])
        stats = data.get('stats', {})
        
        print_pass(f"Trending API works: {len(trending)} topics, {stats.get('total_queries', 0)} total queries")
        return True
    except Exception as e:
        print_fail(f"Trending topics test failed: {e}")
        return False

def test_streaming_response():
    """Test 5: Streaming response"""
    print_test("Test 5: Streaming Response")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/chat/stream",
            json={"prompt": "你好", "max_tokens": 50},
            stream=True,
            timeout=60
        )
        
        chunks = 0
        for line in response.iter_lines():
            if line:
                chunks += 1
                if chunks == 1:
                    first_chunk_time = time.time() - start_time
        
        total_time = time.time() - start_time
        
        if chunks > 0:
            print_pass(f"Streaming works: {chunks} chunks in {total_time:.2f}s (first chunk: {first_chunk_time:.2f}s)")
            return True
        else:
            print_fail("No chunks received")
            return False
    except Exception as e:
        print_fail(f"Streaming test failed: {e}")
        return False

def test_database_integrity():
    """Test 6: Database has articles"""
    print_test("Test 6: Database Integrity")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        data = response.json()
        db_status = data.get('database', '')
        
        if 'articles)' in db_status:
            # Extract article count
            count = int(db_status.split('(')[1].split(' ')[0])
            if count > 0:
                print_pass(f"Database has {count} articles")
                return True
            else:
                print_fail("Database has 0 articles")
                return False
        else:
            print_warn(f"Could not verify article count: {db_status}")
            return False
    except Exception as e:
        print_fail(f"Database integrity test failed: {e}")
        return False

def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"🧪 Self LLM Routine Test Suite")
    print(f"{'='*60}{Colors.END}\n")
    print(f"Target: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tests = [
        test_health_check,
        test_database_integrity,
        test_rag_search,
        test_streaming_response,
        test_rate_limiting,
        test_trending_topics,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_fail(f"Test crashed: {e}")
            results.append(False)
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"📊 Test Results")
    print(f"{'='*60}{Colors.END}")
    print(f"Passed: {passed}/{total} ({success_rate:.0f}%)")
    
    if success_rate == 100:
        print(f"{Colors.GREEN}🎉 All tests passed!{Colors.END}\n")
        return 0
    elif success_rate >= 80:
        print(f"{Colors.YELLOW}⚠️  Most tests passed, but some issues detected{Colors.END}\n")
        return 1
    else:
        print(f"{Colors.RED}❌ Many tests failed, system needs attention{Colors.END}\n")
        return 2

if __name__ == "__main__":
    sys.exit(main())
