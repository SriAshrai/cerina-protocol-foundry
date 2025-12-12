import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_all_endpoints():
    print("🔍 Testing API Endpoints")
    
    # 1. Health check
    print("\n1. Testing /health...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # 2. Invoke endpoint
    print("\n2. Testing POST /invoke...")
    try:
        resp = requests.post(
            f"{BASE_URL}/invoke",
            json={"intent": "Test CBT exercise"},
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}...")
        
        if resp.status_code == 200:
            thread_id = resp.json().get('data', {}).get('thread_id')
            print(f"   Thread ID: {thread_id}")

            # Wait a short bit to let the background task start
            time.sleep(0.5)
            
            # 3. Test state endpoint
            print(f"\n3. Testing GET /state/{thread_id}...")
            state_resp = requests.get(f"{BASE_URL}/state/{thread_id}")
            print(f"   Status: {state_resp.status_code}")
            print(f"   Response: {state_resp.text[:500]}...")
            
    except Exception as e:
        print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    test_all_endpoints()
