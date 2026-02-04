#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for creating a new project from the Standard-Unlocked-Shulman template.

This script automates the initial setup steps:
1. Forks the repository to a new name
2. Updates project name and package name in cumulusci.yml
3. Updates org names in orgs/*.json files
4. Provides a checklist of remaining manual steps
"""

import os
import re
import sys
import subprocess
import json
import time
from pathlib import Path

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)


def update_cumulusci_yml(project_name: str, project_label: str):
    """Update cumulusci.yml with new project name and label."""
    file_path = Path("cumulusci.yml")
    
    if not file_path.exists():
        print(f"Error: {file_path} not found!")
        return False
    
    content = file_path.read_text()
    
    # Convert label to API name (remove spaces, keep capitalization)
    api_name = project_label.replace(" ", "")
    
    # Update project name (first "name:" under "project:")
    # Match: project: ... name: "..." (with any indentation)
    lines = content.split('\n')
    in_project_section = False
    in_package_section = False
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('project:'):
            in_project_section = True
            in_package_section = False
        elif stripped.startswith('package:'):
            in_package_section = True
        elif in_project_section and not in_package_section and stripped.startswith('name:'):
            # This is the project name
            lines[i] = re.sub(r'name:\s*"[^"]*"', f'name: "{project_label}"', line)
            in_project_section = False  # Only update first occurrence
        elif in_package_section and stripped.startswith('name:'):
            # This is the package name
            lines[i] = re.sub(r'name:\s*\w+', f'name: {api_name}', line)
        elif in_package_section and stripped.startswith('name_managed:'):
            # This is name_managed
            lines[i] = re.sub(r'name_managed:\s*"[^"]*"', f'name_managed: "{project_label}"', line)
    
    content = '\n'.join(lines)
    file_path.write_text(content)
    print(f"[OK] Updated {file_path}")
    return True


def update_org_json_files(project_label: str):
    """Update org names in all orgs/*.json files."""
    orgs_dir = Path("orgs")
    
    if not orgs_dir.exists():
        print(f"Warning: {orgs_dir} directory not found!")
        return False
    
    updated_files = []
    for json_file in orgs_dir.glob("*.json"):
        content = json_file.read_text()
        
        # Update orgName field
        # Pattern: "orgName": "Standard-Unlocked-Shulman - X Org"
        pattern = r'"orgName":\s*"[^"]*"'
        replacement = f'"orgName": "{project_label} - {json_file.stem.capitalize()} Org"'
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            json_file.write_text(new_content)
            updated_files.append(json_file.name)
            print(f"[OK] Updated {json_file}")
    
    return len(updated_files) > 0


def update_permission_set_references(api_name: str):
    """Update permission set group references in cumulusci.yml."""
    file_path = Path("cumulusci.yml")
    
    if not file_path.exists():
        return False
    
    content = file_path.read_text()
    
    # Update assign_permission_set_groups api_names
    pattern = r'api_names:\s*\w+'
    replacement = f'api_names: {api_name}Admin'
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        file_path.write_text(new_content)
        print(f"[OK] Updated permission set group references in {file_path}")
        return True
    
    return False


def get_git_remote_info():
    """Get the current git remote repository information."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        
        # Parse GitHub URL (supports https://github.com/owner/repo.git or git@github.com:owner/repo.git)
        if "github.com" in remote_url:
            if remote_url.startswith("https://"):
                # https://github.com/owner/repo.git
                parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
            elif remote_url.startswith("git@"):
                # git@github.com:owner/repo.git
                parts = remote_url.split(":")[1].replace(".git", "").split("/")
            else:
                return None
            
            if len(parts) >= 2:
                return {
                    "owner": parts[0],
                    "repo": parts[1],
                    "full_name": f"{parts[0]}/{parts[1]}"
                }
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        print(f"Warning: Could not determine git remote: {e}")
    
    return None


def verify_token_permissions(github_token: str):
    """Verify that the token has the necessary permissions."""
    api_base = "https://api.github.com"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Check token validity and get user info
    try:
        user_response = requests.get(f"{api_base}/user", headers=headers)
        if user_response.status_code != 200:
            return False, "Invalid token or insufficient permissions"
        
        # Check token scopes from response headers
        scopes = user_response.headers.get("X-OAuth-Scopes", "")
        token_type = "classic"
        
        # Fine-grained tokens don't return scopes in headers the same way
        # We'll test by attempting operations
        
        return True, {
            "valid": True,
            "scopes": scopes,
            "type": token_type
        }
    except Exception as e:
        return False, f"Error verifying token: {str(e)}"


def fork_repository(github_token: str, source_owner: str, source_repo: str, new_repo_name: str):
    """Fork a repository using GitHub API."""
    api_base = "https://api.github.com"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Step 1: Fork the repository
    fork_url = f"{api_base}/repos/{source_owner}/{source_repo}/forks"
    print(f"Forking repository {source_owner}/{source_repo}...")
    
    try:
        response = requests.post(fork_url, headers=headers, json={}, timeout=30)
        
        if response.status_code == 202:
            # Fork is being processed asynchronously
            try:
                fork_data = response.json()
                fork_owner = fork_data.get("owner", {}).get("login")
            except (ValueError, KeyError, AttributeError):
                # If we can't get owner from response, get it from authenticated user
                user_response = requests.get(f"{api_base}/user", headers=headers, timeout=10)
                if user_response.status_code == 200:
                    fork_owner = user_response.json().get("login")
                else:
                    return {
                        "success": False,
                        "error": "Could not determine fork owner"
                    }
            
            print(f"[OK] Fork initiated. Waiting for fork to complete...")
            
            # Wait for fork to complete (poll the repository)
            max_attempts = 30
            fork_ready = False
            for attempt in range(max_attempts):
                time.sleep(2)
                check_url = f"{api_base}/repos/{fork_owner}/{source_repo}"
                try:
                    check_response = requests.get(check_url, headers=headers, timeout=10)
                    if check_response.status_code == 200:
                        print(f"[OK] Fork completed: {fork_owner}/{source_repo}")
                        fork_ready = True
                        break
                except requests.exceptions.RequestException:
                    # Continue polling
                    pass
            
            if not fork_ready:
                print("[WARNING] Fork may still be processing. Continuing anyway...")
            
            # Step 2: Rename the forked repository
            if new_repo_name and new_repo_name != source_repo:
                rename_url = f"{api_base}/repos/{fork_owner}/{source_repo}"
                rename_data = {"name": new_repo_name}
                
                print(f"Renaming repository to '{new_repo_name}'...")
                rename_response = requests.patch(rename_url, headers=headers, json=rename_data)
                
                if rename_response.status_code == 200:
                    print(f"[OK] Repository renamed to '{new_repo_name}'")
                    return {
                        "success": True,
                        "owner": fork_owner,
                        "repo": new_repo_name,
                        "url": f"https://github.com/{fork_owner}/{new_repo_name}"
                    }
                else:
                    error_msg = rename_response.json().get("message", "Unknown error")
                    print(f"[ERROR] Failed to rename repository: {error_msg}")
                    
                    # Check if it's a permissions issue
                    if "insufficient" in error_msg.lower() or "permission" in error_msg.lower():
                        print()
                        print("[WARNING] Permission Error:")
                        print("   Renaming a repository requires 'Administration' permission.")
                        print("   If using a Fine-Grained PAT, ensure 'Administration' is set to 'Read and write'.")
                        print("   If using a Classic PAT, ensure 'repo' scope is selected.")
                    
                    return {
                        "success": False,
                        "error": f"Rename failed: {error_msg}",
                        "owner": fork_owner,
                        "repo": source_repo,
                        "url": f"https://github.com/{fork_owner}/{source_repo}"
                    }
            else:
                return {
                    "success": True,
                    "owner": fork_owner,
                    "repo": source_repo,
                    "url": f"https://github.com/{fork_owner}/{source_repo}"
                }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Authentication failed. Please check your token."
            }
        elif response.status_code == 403:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("message", "Forbidden - insufficient permissions")
            return {
                "success": False,
                "error": f"Permission denied: {error_msg}"
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Repository {source_owner}/{source_repo} not found or not accessible"
            }
        elif response.status_code == 422:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", "Unknown error")
            except ValueError:
                error_msg = f"Unprocessable entity (status {response.status_code})"
            if "already exists" in error_msg.lower() or "name already exists" in error_msg.lower():
                # Try to get the authenticated user's username
                user_response = requests.get(f"{api_base}/user", headers=headers)
                if user_response.status_code == 200:
                    fork_owner = user_response.json().get("login")
                    print(f"[WARNING] Repository already forked or name exists. Checking existing fork...")
                    
                    # Check if fork exists with original name
                    check_fork_url = f"{api_base}/repos/{fork_owner}/{source_repo}"
                    check_fork_response = requests.get(check_fork_url, headers=headers)
                    
                    if check_fork_response.status_code == 200:
                        # Fork exists, try to rename it
                        rename_url = f"{api_base}/repos/{fork_owner}/{source_repo}"
                        rename_data = {"name": new_repo_name}
                        rename_response = requests.patch(rename_url, headers=headers, json=rename_data)
                        if rename_response.status_code == 200:
                            print(f"[OK] Existing fork renamed to '{new_repo_name}'")
                            return {
                                "success": True,
                                "owner": fork_owner,
                                "repo": new_repo_name,
                                "url": f"https://github.com/{fork_owner}/{new_repo_name}"
                            }
                        else:
                            rename_error = rename_response.json().get("message", "Unknown error")
                            return {
                                "success": False,
                                "error": f"Could not rename existing fork: {rename_error}"
                            }
                    else:
                        # Check if new name already exists
                        check_new_name_url = f"{api_base}/repos/{fork_owner}/{new_repo_name}"
                        check_new_response = requests.get(check_new_name_url, headers=headers)
                        if check_new_response.status_code == 200:
                            print(f"[OK] Repository '{new_repo_name}' already exists")
                            return {
                                "success": True,
                                "owner": fork_owner,
                                "repo": new_repo_name,
                                "url": f"https://github.com/{fork_owner}/{new_repo_name}"
                            }
            return {
                "success": False,
                "error": f"Fork failed: {error_msg}"
            }
        else:
            # Handle other status codes
            try:
                error_data = response.json()
                error_msg = error_data.get("message", f"Unexpected status code: {response.status_code}")
            except ValueError:
                error_msg = f"Unexpected status code: {response.status_code}"
            
            return {
                "success": False,
                "error": f"Fork failed: {error_msg}"
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out. Please try again."
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def check_for_tokens():
    """Check for any remaining __PROJECT_NAME__ or __PROJECT_LABEL__ tokens."""
    tokens_found = []
    
    # Search in common directories
    search_dirs = ["force-app", "datasets", "robot"]
    
    for search_dir in search_dirs:
        dir_path = Path(search_dir)
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if '__PROJECT_NAME__' in content:
                        tokens_found.append((file_path, '__PROJECT_NAME__'))
                    if '__PROJECT_LABEL__' in content:
                        tokens_found.append((file_path, '__PROJECT_LABEL__'))
                except Exception:
                    # Skip binary files or files that can't be read
                    pass
    
    return tokens_found


def main():
    """Main setup function."""
    print("=" * 60)
    print("Standard-Unlocked-Shulman Project Setup Script")
    print("=" * 60)
    print()
    
    # Get git remote information
    remote_info = get_git_remote_info()
    if not remote_info:
        print("Error: Could not determine git remote repository.")
        print("Make sure you're in a git repository with a GitHub remote configured.")
        sys.exit(1)
    
    print(f"Current repository: {remote_info['full_name']}")
    print()
    
    # Get GitHub token
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("=" * 60)
        print("GitHub Token Required")
        print("=" * 60)
        print()
        print("This script requires a GitHub Personal Access Token (PAT) to:")
        print("  - Fork the repository")
        print("  - Rename the forked repository")
        print("  - Access repository information")
        print()
        print("Token Types Supported:")
        print()
        print("1. Classic Personal Access Token:")
        print("   Required Scope: 'repo' (Full control of private repositories)")
        print("   Create at: https://github.com/settings/tokens")
        print("   Click 'Generate new token' -> 'Generate new token (classic)'")
        print()
        print("2. Fine-Grained Personal Access Token:")
        print("   Required Permissions:")
        print("     - Repository access: Selected repositories (or all)")
        print("     - Repository permissions:")
        print("       - Contents: Read and write")
        print("       - Metadata: Read-only")
        print("       - Administration: Read and write (REQUIRED for rename)")
        print("   Create at: https://github.com/settings/tokens")
        print("   Click 'Generate new token' -> 'Generate new token (fine-grained)'")
        print()
        print("[!] Note: 'Contents' permission alone is NOT sufficient.")
        print("   'Administration' permission is REQUIRED to rename repositories.")
        print()
        print("Alternatively, set GITHUB_TOKEN environment variable:")
        print("  export GITHUB_TOKEN=your_token_here")
        print()
        github_token = input("GitHub Token: ").strip()
        
        if not github_token:
            print("Error: GitHub token is required!")
            sys.exit(1)
    
    # Verify token permissions
    print()
    print("Verifying token permissions...")
    token_valid, token_info = verify_token_permissions(github_token)
    if not token_valid:
        print(f"[ERROR] {token_info}")
        print("Please check your token permissions and try again.")
        sys.exit(1)
    print("[OK] Token verified")
    
    # Get new repository name
    print()
    new_repo_name = input("New repository name (e.g., 'my-new-project'): ").strip()
    
    if not new_repo_name:
        print("Error: Repository name is required!")
        sys.exit(1)
    
    # Validate repository name (GitHub rules: alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9._-]+$', new_repo_name):
        print("Error: Invalid repository name. Use only letters, numbers, hyphens, underscores, and dots.")
        sys.exit(1)
    
    # Get project information
    print()
    print("Enter your project details:")
    project_label = input("Project Label (e.g., 'Standard Unlocked Shulman'): ").strip()
    
    if not project_label:
        print("Error: Project label is required!")
        sys.exit(1)
    
    # Convert label to API name (remove spaces, keep capitalization)
    api_name = project_label.replace(" ", "")
    
    print()
    print("Summary:")
    print(f"  Source Repository: {remote_info['full_name']}")
    print(f"  New Repository Name: {new_repo_name}")
    print(f"  Project Label: {project_label}")
    print(f"  API Name: {api_name}")
    print()
    
    confirm = input("Continue with these values? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    
    # Fork and rename repository
    print()
    print("=" * 60)
    print("Forking Repository")
    print("=" * 60)
    fork_result = fork_repository(
        github_token,
        remote_info['owner'],
        remote_info['repo'],
        new_repo_name
    )
    
    if not fork_result['success']:
        print(f"[ERROR] Failed to fork repository: {fork_result.get('error', 'Unknown error')}")
        print()
        print("You can manually fork the repository and continue with file updates.")
        manual_continue = input("Continue with file updates only? (y/n): ").strip().lower()
        if manual_continue != 'y':
            sys.exit(1)
    else:
        print()
        print(f"[OK] Repository forked and renamed successfully!")
        print(f"  URL: {fork_result['url']}")
        print()
        
        # Update git remote to point to the new fork
        update_remote = input("Update git remote to point to the new fork? (y/n): ").strip().lower()
        if update_remote == 'y':
            try:
                new_remote_url = f"https://github.com/{fork_result['owner']}/{fork_result['repo']}.git"
                subprocess.run(
                    ["git", "remote", "set-url", "origin", new_remote_url],
                    check=True,
                    capture_output=True
                )
                print(f"[OK] Git remote updated to: {new_remote_url}")
            except subprocess.CalledProcessError as e:
                print(f"[WARNING] Warning: Could not update git remote: {e}")
            except Exception as e:
                print(f"[WARNING] Warning: Could not update git remote: {e}")
        
        print()
    
    print()
    print("=" * 60)
    print("Updating Files")
    print("=" * 60)
    
    # Update files
    success = True
    success &= update_cumulusci_yml(api_name, project_label)
    success &= update_org_json_files(project_label)
    success &= update_permission_set_references(api_name)
    
    if not success:
        print("Warning: Some files may not have been updated. Please review manually.")
    
    # Check for remaining tokens
    print()
    print("Checking for remaining tokens...")
    print("-" * 60)
    tokens_found = check_for_tokens()
    
    if tokens_found:
        print(f"[WARNING] Warning: Found {len(tokens_found)} file(s) with remaining tokens:")
        for file_path, token in tokens_found:
            print(f"  - {file_path} ({token})")
        print()
        print("These files need manual token replacement.")
    else:
        print("[OK] No remaining tokens found in metadata files.")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("-" * 60)
    if fork_result.get('success'):
        print(f"1. [OK] Repository forked: {fork_result['url']}")
        print("2. Review the changes made to cumulusci.yml and orgs/*.json")
    else:
        print("1. Manually fork the repository on GitHub")
        print("2. Review the changes made to cumulusci.yml and orgs/*.json")
    
    if tokens_found:
        print("3. [WARNING] IMPORTANT: Manually replace tokens in the files listed above")
        print("   Replace '__PROJECT_NAME__' with:", api_name)
        print("   Replace '__PROJECT_LABEL__' with:", project_label)
    else:
        print("3. [OK] No token replacement needed in metadata files")
    
    print("4. Set up GitHub Actions secrets:")
    print("   - DEV_HUB_AUTH_URL (required)")
    print("   - BETA_ORG_AUTH_URL (optional)")
    print("   - PROD_ORG_AUTH_URL (optional)")
    print("5. Follow the Initial Setup instructions in .github/workflows/README.md")
    print()
    print("For more information, see:")
    print("  - README.md")
    print("  - .github/workflows/README.md")
    print()


if __name__ == "__main__":
    main()
