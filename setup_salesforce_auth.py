#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for configuring Salesforce authentication in GitHub Secrets.

This script:
1. Prompts for Salesforce credentials
2. Authenticates to Salesforce using Salesforce CLI
3. Retrieves the SFDX auth URL
4. Creates GitHub repository secrets via GitHub API

Prerequisites:
- Salesforce CLI installed and in PATH
- GitHub Personal Access Token with 'repo' and 'admin:repo' scopes
- Python 3.7+
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_github_repo_info():
    """Extract GitHub repository owner and name from git remote."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        
        # Handle both HTTPS and SSH URLs
        if remote_url.startswith('https://github.com/'):
            parts = remote_url.replace('https://github.com/', '').replace('.git', '').split('/')
        elif remote_url.startswith('git@github.com:'):
            parts = remote_url.replace('git@github.com:', '').replace('.git', '').split('/')
        else:
            return None, None
        
        if len(parts) >= 2:
            return parts[0], parts[1]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None, None


def create_github_secret(owner, repo, secret_name, secret_value, github_token):
    """Create or update a GitHub repository secret using GitHub API."""
    # GitHub API endpoint for creating/updating repository secrets
    # We need to use the public key first, then encrypt the secret
    
    # Step 1: Get the repository's public key
    public_key_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(public_key_url, headers=headers)
        response.raise_for_status()
        public_key_data = response.json()
        public_key = public_key_data["key"]
        key_id = public_key_data["key_id"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving GitHub public key: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return False
    
    # Step 2: Encrypt the secret using libsodium (via PyNaCl)
    try:
        from nacl import encoding, public
        public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key_obj)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_value = encoding.Base64Encoder().encode(encrypted).decode("utf-8")
    except ImportError:
        print("❌ Error: 'PyNaCl' library is required for encryption.")
        print("   Install it with: pip install pynacl")
        return False
    except Exception as e:
        print(f"❌ Error encrypting secret: {e}")
        return False
    
    # Step 3: Create/update the secret
    secret_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    
    try:
        response = requests.put(secret_url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating GitHub secret '{secret_name}': {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return False


def authenticate_salesforce(org_alias, instance_url=None, username=None, password=None):
    """Authenticate to Salesforce using Salesforce CLI."""
    print(f"\n{'='*60}")
    print("Salesforce Authentication")
    print(f"{'='*60}\n")
    
    # Check if Salesforce CLI is installed
    try:
        result = subprocess.run(['sf', '--version'], capture_output=True, text=True, check=True)
        print(f"✅ Salesforce CLI found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Salesforce CLI (sf) is not installed or not in PATH.")
        print("   Install it from: https://developer.salesforce.com/tools/salesforcecli")
        return None
    
    # Authenticate to Salesforce
    print(f"\nAuthenticating to Salesforce org '{org_alias}'...")
    
    if instance_url and username and password:
        # JWT or username/password flow
        print("Using provided credentials...")
        # Note: This is a simplified example - you may need to adjust based on auth method
        cmd = ['sf', 'org', 'login', 'web', '--alias', org_alias]
    else:
        # Web-based OAuth flow (most common)
        print("Opening browser for web-based authentication...")
        cmd = ['sf', 'org', 'login', 'web', '--alias', org_alias]
    
    try:
        # Run the authentication command
        # Note: This will open a browser for web-based auth
        result = subprocess.run(cmd, check=True)
        print("✅ Authentication successful!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Authentication failed: {e}")
        return None
    
    return org_alias


def get_sfdx_auth_url(org_alias):
    """Retrieve the SFDX auth URL for the authenticated org."""
    print(f"\nRetrieving SFDX auth URL for org '{org_alias}'...")
    
    try:
        # Get org info in JSON format
        result = subprocess.run(
            ['sf', 'org', 'display', '--target-org', org_alias, '--verbose', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        org_info = json.loads(result.stdout)
        
        if 'result' in org_info and 'sfdxAuthUrl' in org_info['result']:
            auth_url = org_info['result']['sfdxAuthUrl']
            print("✅ SFDX auth URL retrieved successfully!")
            return auth_url
        else:
            print("❌ Error: SFDX auth URL not found in org info")
            print(f"   Org info: {json.dumps(org_info, indent=2)}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error retrieving org info: {e}")
        print(f"   Output: {e.stdout if hasattr(e, 'stdout') else ''}")
        print(f"   Error: {e.stderr if hasattr(e, 'stderr') else ''}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing org info JSON: {e}")
        return None


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(
        description="Configure Salesforce authentication in GitHub Secrets."
    )
    parser.add_argument(
        '--org-alias',
        type=str,
        help='Salesforce org alias (e.g., "MyDevHub"). If not provided, will prompt.'
    )
    parser.add_argument(
        '--github-token',
        type=str,
        help='GitHub Personal Access Token. If not provided, will prompt or use GITHUB_TOKEN env var.'
    )
    parser.add_argument(
        '--github-owner',
        type=str,
        help='GitHub repository owner. If not provided, will try to detect from git remote.'
    )
    parser.add_argument(
        '--github-repo',
        type=str,
        help='GitHub repository name. If not provided, will try to detect from git remote.'
    )
    parser.add_argument(
        '--secret-name',
        type=str,
        default='DEV_HUB_AUTH_URL',
        help='GitHub secret name (default: DEV_HUB_AUTH_URL)'
    )
    parser.add_argument(
        '--skip-auth',
        action='store_true',
        help='Skip Salesforce authentication (use existing authenticated org)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Salesforce Authentication Setup for GitHub")
    print("=" * 60)
    print()
    
    # Get GitHub repository info
    owner, repo = args.github_owner, args.github_repo
    if not owner or not repo:
        owner, repo = get_github_repo_info()
        if not owner or not repo:
            print("❌ Error: Could not determine GitHub repository.")
            print("   Please provide --github-owner and --github-repo, or ensure")
            print("   you're in a git repository with a 'origin' remote pointing to GitHub.")
            sys.exit(1)
    
    print(f"GitHub Repository: {owner}/{repo}")
    
    # Get GitHub token
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    if not github_token:
        github_token = input("\nGitHub Personal Access Token (with 'repo' and 'admin:repo' scopes): ").strip()
        if not github_token:
            print("❌ Error: GitHub token is required")
            sys.exit(1)
    
    # Get Salesforce org alias
    org_alias = args.org_alias
    if not org_alias:
        org_alias = input("\nSalesforce Org Alias (e.g., 'MyDevHub'): ").strip()
        if not org_alias:
            print("❌ Error: Org alias is required")
            sys.exit(1)
    
    # Authenticate to Salesforce (unless skipped)
    if not args.skip_auth:
        authenticated_alias = authenticate_salesforce(org_alias)
        if not authenticated_alias:
            print("\n❌ Failed to authenticate to Salesforce")
            sys.exit(1)
        org_alias = authenticated_alias
    else:
        print(f"\n⚠️  Skipping authentication - using existing org '{org_alias}'")
        print("   Make sure this org is already authenticated with: sf org login web --alias " + org_alias)
    
    # Get SFDX auth URL
    auth_url = get_sfdx_auth_url(org_alias)
    if not auth_url:
        print("\n❌ Failed to retrieve SFDX auth URL")
        sys.exit(1)
    
    print(f"\n✅ SFDX Auth URL retrieved:")
    print(f"   {auth_url[:50]}...")
    
    # Confirm before creating secret
    print(f"\n{'='*60}")
    print("Create GitHub Secret")
    print(f"{'='*60}\n")
    print(f"Repository: {owner}/{repo}")
    print(f"Secret Name: {args.secret_name}")
    print(f"Auth URL: {auth_url[:50]}...")
    print()
    
    confirm = input("Create this GitHub secret? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Create GitHub secret
    print(f"\nCreating GitHub secret '{args.secret_name}'...")
    success = create_github_secret(owner, repo, args.secret_name, auth_url, github_token)
    
    if success:
        print(f"\n✅ Successfully created GitHub secret '{args.secret_name}'!")
        print(f"\nNext steps:")
        print(f"  1. Verify the secret in GitHub: Settings > Secrets and variables > Actions")
        print(f"  2. The secret '{args.secret_name}' is now available for your workflows")
    else:
        print(f"\n❌ Failed to create GitHub secret")
        sys.exit(1)


if __name__ == "__main__":
    main()
