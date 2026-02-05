#!/usr/bin/env python3
"""
Test script to validate the authentication logic locally.
This simulates what the GitHub Actions workflow does.
"""

import requests
import json
import sys

def test_auth_logic(username, password, security_token, server_url):
    """Test the authentication logic without actually creating secrets."""
    
    # Combine password and security token
    full_password = password + security_token if security_token else password
    
    print("=" * 60)
    print("Testing Salesforce Authentication Logic")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Org URL: {server_url}")
    print(f"Has Security Token: {'Yes' if security_token else 'No'}")
    print()
    
    # Authenticate using Username-Password OAuth Flow
    token_url = f"{server_url}/services/oauth2/token"
    
    payload = {
        'grant_type': 'password',
        'client_id': 'PlatformCLI',
        'client_secret': '',
        'username': username,
        'password': full_password
    }
    
    print("Attempting authentication...")
    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        instance_url = token_data.get('instance_url')
        refresh_token = token_data.get('refresh_token')
        
        print("✅ Authentication successful!")
        print()
        print("Token Details:")
        print(f"  Instance URL: {instance_url}")
        print(f"  Access Token: {access_token[:20]}..." if access_token else "  Access Token: None")
        print(f"  Refresh Token: {'Present' if refresh_token else 'Missing'}")
        print()
        
        if not access_token or not instance_url:
            print("❌ Error: Missing required tokens")
            return False
        
        if not refresh_token:
            print("⚠️  Warning: No refresh token received")
            print("   This will prevent creating a persistent SFDX auth URL")
            print("   Your org may need to allow refresh tokens")
            return False
        
        # Construct SFDX auth URL
        auth_url = f"force://PlatformCLI:::{refresh_token}@{instance_url}"
        
        print("✅ SFDX Auth URL generated:")
        print(f"   {auth_url[:50]}...")
        print()
        print("✅ All checks passed! The workflow should work.")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Authentication failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                print(f"   Description: {error_data.get('error_description', 'No description')}")
            except:
                print(f"   Response: {e.response.text}")
        return False

if __name__ == "__main__":
    print("Salesforce Authentication Test Script")
    print("=" * 60)
    print()
    print("This script tests the authentication logic without creating GitHub secrets.")
    print("You'll need to provide your Salesforce credentials.")
    print()
    
    # Get credentials
    username = input("Salesforce Username: ").strip()
    password = input("Salesforce Password: ").strip()
    security_token = input("Security Token (leave empty if IP whitelisted): ").strip()
    
    print("\nSelect Org Type:")
    print("1. Production (login.salesforce.com)")
    print("2. Sandbox (test.salesforce.com)")
    org_choice = input("Choice (1 or 2): ").strip()
    
    server_url = "https://login.salesforce.com" if org_choice == "1" else "https://test.salesforce.com"
    
    print()
    success = test_auth_logic(username, password, security_token, server_url)
    
    if success:
        print("\n✅ Test passed! The workflow should work with these credentials.")
        sys.exit(0)
    else:
        print("\n❌ Test failed. Please check your credentials and try again.")
        sys.exit(1)
