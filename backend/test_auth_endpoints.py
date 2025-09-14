#!/usr/bin/env python3
"""
Test script for authentication endpoints

Run this after starting your FastAPI server to test the signup and login endpoints.
Make sure your server is running on http://localhost:8000

Usage:
    python test_auth_endpoints.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_signup():
    """Test user signup endpoint"""
    print("🔸 Testing signup endpoint...")
    
    signup_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/users/signup",
            headers={"Content-Type": "application/json"},
            json=signup_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Signup successful!")
            return response.json()
        elif response.status_code == 409:
            print("⚠️  User already exists (this is expected if running multiple times)")
            return None
        else:
            print("❌ Signup failed!")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_login():
    """Test user login endpoint"""
    print("\n🔸 Testing login endpoint...")
    
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/users/login",
            headers={"Content-Type": "application/json"},
            json=login_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.json()
        else:
            print("❌ Login failed!")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_health():
    """Test health endpoint to verify server is running"""
    print("🔸 Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Server is running!")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print(f"Make sure your FastAPI server is running on {BASE_URL}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Crypto Compliance Copilot Authentication Endpoints")
    print("=" * 60)
    
    # Test if server is running
    if not test_health():
        print("\n❌ Server is not accessible. Please start your FastAPI server first:")
        print("   cd backend && uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Test signup
    signup_result = test_signup()
    
    # Test login
    login_result = test_login()
    
    print("\n" + "=" * 60)
    if login_result:
        print("🎉 All tests passed! Authentication endpoints are working correctly.")
        print("\nYou can now test manually with these curl commands:")
        print("\n📝 Signup:")
        print('curl -X POST http://localhost:8000/v1/users/signup \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"username":"admin","email":"admin@compliance.zk","password":"secret123"}\'')
        print("\n🔑 Login:")
        print('curl -X POST http://localhost:8000/v1/users/login \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"email":"admin@compliance.zk","password":"secret123"}\'')
    else:
        print("❌ Some tests failed. Check the server logs for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()