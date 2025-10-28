#!/usr/bin/env python3
"""
TeleStore Backend API Testing Suite
Tests the automatic credential management feature
"""

import requests
import json
import sys
import os
from datetime import datetime

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return "http://localhost:8001"

BASE_URL = get_backend_url() + "/api"
print(f"Testing backend at: {BASE_URL}")

class TeleStoreAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_email = "testuser@telestore.com"
        self.test_user_password = "TestPassword123!"
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {details}")
        
        self.results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_signup(self):
        """Test user signup endpoint"""
        try:
            payload = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            
            response = self.session.post(f"{BASE_URL}/auth/signup", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'token_type' in data:
                    self.auth_token = data['access_token']
                    self.log_result("User Signup", True, "Successfully created user and received token")
                    return True
                else:
                    self.log_result("User Signup", False, "Missing token in response", data)
                    return False
            elif response.status_code == 400 and "already registered" in response.text:
                # User already exists, try login instead
                self.log_result("User Signup", True, "User already exists (expected)", response.text)
                return self.test_login()
            else:
                self.log_result("User Signup", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("User Signup", False, f"Request failed: {str(e)}")
            return False
    
    def test_login(self):
        """Test user login endpoint"""
        try:
            payload = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'token_type' in data:
                    self.auth_token = data['access_token']
                    self.log_result("User Login", True, "Successfully logged in and received token")
                    return True
                else:
                    self.log_result("User Login", False, "Missing token in response", data)
                    return False
            else:
                self.log_result("User Login", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("User Login", False, f"Request failed: {str(e)}")
            return False
    
    def test_auth_me(self):
        """Test /auth/me endpoint"""
        if not self.auth_token:
            self.log_result("Auth Me", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{BASE_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if 'email' in data and data['email'] == self.test_user_email:
                    self.log_result("Auth Me", True, "Successfully retrieved user profile")
                    return True
                else:
                    self.log_result("Auth Me", False, "Invalid user data returned", data)
                    return False
            else:
                self.log_result("Auth Me", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Auth Me", False, f"Request failed: {str(e)}")
            return False
    
    def test_worker_credentials_not_configured(self):
        """Test /worker/credentials endpoint when Telegram not configured"""
        if not self.auth_token:
            self.log_result("Worker Credentials (Not Configured)", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{BASE_URL}/worker/credentials", headers=headers)
            
            if response.status_code == 400:
                data = response.json()
                if "not fully configured" in data.get('detail', '').lower():
                    self.log_result("Worker Credentials (Not Configured)", True, "Correctly returned 400 for unconfigured Telegram")
                    return True
                else:
                    self.log_result("Worker Credentials (Not Configured)", False, "Wrong error message", data)
                    return False
            else:
                self.log_result("Worker Credentials (Not Configured)", False, f"Expected 400, got HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Worker Credentials (Not Configured)", False, f"Request failed: {str(e)}")
            return False
    
    def test_bot_token_invalid(self):
        """Test /settings/bot-token endpoint with invalid token"""
        if not self.auth_token:
            self.log_result("Bot Token (Invalid)", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            payload = {"bot_token": "invalid_bot_token_123"}
            
            response = self.session.post(f"{BASE_URL}/settings/bot-token", json=payload, headers=headers)
            
            if response.status_code == 400:
                data = response.json()
                if "invalid" in data.get('detail', '').lower():
                    self.log_result("Bot Token (Invalid)", True, "Correctly rejected invalid bot token")
                    return True
                else:
                    self.log_result("Bot Token (Invalid)", False, "Wrong error message", data)
                    return False
            else:
                self.log_result("Bot Token (Invalid)", False, f"Expected 400, got HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Bot Token (Invalid)", False, f"Request failed: {str(e)}")
            return False
    
    def test_bot_token_format_validation(self):
        """Test bot token format validation"""
        if not self.auth_token:
            self.log_result("Bot Token Format Validation", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test various invalid formats
            invalid_tokens = [
                "",  # Empty
                "123",  # Too short
                "not_a_token",  # Wrong format
                "123:ABC",  # Too short bot ID
            ]
            
            for token in invalid_tokens:
                payload = {"bot_token": token}
                response = self.session.post(f"{BASE_URL}/settings/bot-token", json=payload, headers=headers)
                
                if response.status_code != 400:
                    self.log_result("Bot Token Format Validation", False, f"Should reject token '{token}', got HTTP {response.status_code}")
                    return False
            
            self.log_result("Bot Token Format Validation", True, "Correctly validates bot token formats")
            return True
                
        except Exception as e:
            self.log_result("Bot Token Format Validation", False, f"Request failed: {str(e)}")
            return False
    
    def test_valid_bot_token_format(self):
        """Test with a valid-looking bot token format (will fail at Telegram API validation)"""
        if not self.auth_token:
            self.log_result("Valid Bot Token Format", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            # Use a valid format but fake token (10 digits:35 chars)
            fake_valid_token = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
            payload = {"bot_token": fake_valid_token}
            
            response = self.session.post(f"{BASE_URL}/settings/bot-token", json=payload, headers=headers)
            
            # Should get 400 because token is invalid at Telegram API level
            if response.status_code == 400:
                data = response.json()
                if "invalid" in data.get('detail', '').lower():
                    self.log_result("Valid Bot Token Format", True, "Correctly validates token with Telegram API")
                    return True
                else:
                    self.log_result("Valid Bot Token Format", False, "Wrong error message", data)
                    return False
            else:
                self.log_result("Valid Bot Token Format", False, f"Expected 400, got HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Valid Bot Token Format", False, f"Request failed: {str(e)}")
            return False
    
    def test_unauthorized_access(self):
        """Test endpoints without authentication"""
        try:
            # Test worker credentials without auth
            response = self.session.get(f"{BASE_URL}/worker/credentials")
            if response.status_code not in [401, 403]:
                self.log_result("Unauthorized Access", False, f"Worker credentials should require auth, got HTTP {response.status_code}")
                return False
            
            # Test bot token without auth
            response = self.session.post(f"{BASE_URL}/settings/bot-token", json={"bot_token": "test"})
            if response.status_code not in [401, 403]:
                self.log_result("Unauthorized Access", False, f"Bot token endpoint should require auth, got HTTP {response.status_code}")
                return False
            
            # Test auth/me without auth
            response = self.session.get(f"{BASE_URL}/auth/me")
            if response.status_code not in [401, 403]:
                self.log_result("Unauthorized Access", False, f"Auth/me should require auth, got HTTP {response.status_code}")
                return False
            
            self.log_result("Unauthorized Access", True, "All protected endpoints correctly require authentication")
            return True
                
        except Exception as e:
            self.log_result("Unauthorized Access", False, f"Request failed: {str(e)}")
            return False
    
    def test_backend_connectivity(self):
        """Test basic backend connectivity"""
        try:
            # Try to reach the backend
            response = self.session.get(BASE_URL.replace('/api', '/'))
            if response.status_code in [200, 404, 422]:  # Any response means backend is up
                self.log_result("Backend Connectivity", True, f"Backend is reachable (HTTP {response.status_code})")
                return True
            else:
                self.log_result("Backend Connectivity", False, f"Unexpected response: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Backend Connectivity", False, f"Cannot reach backend: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 60)
        print("TeleStore Backend API Test Suite")
        print("=" * 60)
        
        tests = [
            ("Backend Connectivity", self.test_backend_connectivity),
            ("Unauthorized Access", self.test_unauthorized_access),
            ("User Signup", self.test_signup),
            ("User Login", self.test_login),
            ("Auth Me", self.test_auth_me),
            ("Worker Credentials (Not Configured)", self.test_worker_credentials_not_configured),
            ("Bot Token (Invalid)", self.test_bot_token_invalid),
            ("Bot Token Format Validation", self.test_bot_token_format_validation),
            ("Valid Bot Token Format", self.test_valid_bot_token_format),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n--- Running: {test_name} ---")
            if test_func():
                passed += 1
        
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        print("=" * 60)
        
        # Print failed tests
        failed_tests = [r for r in self.results if not r['success']]
        if failed_tests:
            print("\nFAILED TESTS:")
            for test in failed_tests:
                print(f"❌ {test['test']}: {test['message']}")
                if test['details']:
                    print(f"   Details: {test['details']}")
        
        return passed == total

if __name__ == "__main__":
    tester = TeleStoreAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)