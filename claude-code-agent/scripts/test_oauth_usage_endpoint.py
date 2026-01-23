#!/usr/bin/env python3
"""
Test script to verify if the OAuth usage endpoint exists.
Tests: https://api.anthropic.com/api/oauth/usage
"""

import json
import sys
from pathlib import Path
from typing import Optional

import httpx
from shared.machine_models import ClaudeCredentials
from core.config import settings


def load_credentials() -> Optional[ClaudeCredentials]:
    """Load credentials from file."""
    creds_path = settings.credentials_path
    if not creds_path.exists():
        print(f"❌ Credentials file not found at: {creds_path}")
        return None
    
    try:
        creds_data = json.loads(creds_path.read_text())
        creds = ClaudeCredentials(**creds_data)
        
        if creds.is_expired:
            print(f"⚠️  Warning: Credentials are expired (expired at: {creds.expires_at_datetime})")
            print("   Will still attempt request, but it may fail.")
        elif creds.needs_refresh:
            print(f"⚠️  Warning: Credentials need refresh (expires at: {creds.expires_at_datetime})")
        
        return creds
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return None


def test_oauth_usage_endpoint(creds: ClaudeCredentials) -> None:
    """Test the OAuth usage endpoint."""
    url = "https://api.anthropic.com/api/oauth/usage"
    
    # Try both Authorization header and x-api-key header
    headers_variants = [
        {
            "Authorization": f"{creds.token_type} {creds.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "claude-code-agent-test/1.0",
        },
        {
            "Authorization": f"{creds.token_type} {creds.access_token}",
            "x-api-key": creds.access_token,
            "Content-Type": "application/json",
            "User-Agent": "claude-code-agent-test/1.0",
        },
    ]
    
    for i, headers in enumerate(headers_variants, 1):
        print(f"\n🔍 Attempt {i}: Testing with {'Authorization + x-api-key' if 'x-api-key' in headers else 'Authorization only'}")
    
        print(f"   Method: GET")
        print(f"   Authorization: {creds.token_type} {creds.access_token[:20]}...")
        if 'x-api-key' in headers:
            print(f"   x-api-key: {creds.access_token[:20]}...")
        print()
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                
                print(f"📊 Response Status: {response.status_code} {response.reason_phrase}")
                
                # Try to parse response
                try:
                    response_data = response.json()
                    print("✅ Response (JSON):")
                    print(json.dumps(response_data, indent=2))
                except Exception:
                    print("📄 Response (Text):")
                    print(response.text[:1000])  # First 1000 chars
                
                print()
                
                # Analyze result
                if response.status_code == 200:
                    print("✅ SUCCESS: Endpoint exists and returned 200 OK")
                    if isinstance(response_data, dict):
                        if "session" in response_data or "weekly" in response_data:
                            print("   ✓ Response contains usage data (session/weekly fields)")
                            return  # Success, no need to try other variants
                        else:
                            print("   ⚠️  Response doesn't contain expected usage fields")
                            print("   Keys found:", list(response_data.keys()))
                elif response.status_code == 401:
                    print("❌ FAILED: 401 Unauthorized")
                    if i < len(headers_variants):
                        print("   Will try next authentication variant...")
                elif response.status_code == 404:
                    print("❌ FAILED: 404 Not Found")
                    print("   Endpoint does not exist at this URL")
                    return
                elif response.status_code == 403:
                    print("❌ FAILED: 403 Forbidden")
                    print("   Endpoint exists but access is denied")
                elif response.status_code == 405:
                    print("❌ FAILED: 405 Method Not Allowed")
                    print("   Endpoint exists but doesn't accept GET requests")
                else:
                    print(f"⚠️  Unexpected status code: {response.status_code}")
                    print("   Endpoint may exist but returned an error")
                    
        except httpx.TimeoutException:
            print("❌ FAILED: Request timed out")
            print("   Endpoint may not exist or is unreachable")
        except httpx.ConnectError as e:
            print(f"❌ FAILED: Connection error: {e}")
            print("   Cannot reach api.anthropic.com")
            return
        except Exception as e:
            print(f"❌ FAILED: Unexpected error: {e}")
            print(f"   Type: {type(e).__name__}")


def test_endpoint_without_auth() -> None:
    """Test endpoint without authentication to see if it exists."""
    url = "https://api.anthropic.com/api/oauth/usage"
    print(f"\n🔍 Testing endpoint WITHOUT authentication: {url}")
    print(f"   Method: GET")
    print()
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            
            print(f"📊 Response Status: {response.status_code} {response.reason_phrase}")
            print(f"   Headers: {dict(response.headers)}")
            print()
            
            # Try to parse response body
            try:
                response_data = response.json()
                print(f"   Response body: {json.dumps(response_data, indent=2)}")
            except Exception:
                print(f"   Response body (text): {response.text[:500]}")
            
            if response.status_code == 401:
                print("\n✅ Endpoint EXISTS (401 Unauthorized - expected without auth)")
                print("   The endpoint is real and requires authentication")
            elif response.status_code == 404:
                print("\n❌ Endpoint DOES NOT EXIST (404 Not Found)")
            elif response.status_code == 403:
                print("\n✅ Endpoint EXISTS (403 Forbidden - requires auth)")
            else:
                print(f"\n⚠️  Unexpected status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    print("=" * 70)
    print("OAuth Usage Endpoint Test")
    print("=" * 70)
    print()
    
    # First, test without auth to see if endpoint exists
    print("Step 1: Testing endpoint existence (without authentication)")
    test_endpoint_without_auth()
    
    print("\n" + "=" * 70 + "\n")
    
    # Load credentials
    print("Step 2: Testing endpoint with authentication")
    creds = load_credentials()
    if not creds:
        print("\n💡 Tip: Upload credentials via /api/credentials/upload endpoint")
        print("   Or place credentials at: ~/.claude/claude.json")
        print("\n   Skipping authenticated test...")
    else:
        # Test endpoint with auth
        test_oauth_usage_endpoint(creds)
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
