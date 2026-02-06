#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for replacing project tokens in a new project from the template.

This script permanently replaces __PROJECT_NAME__ and __PROJECT_LABEL__ tokens in:
- Filenames (e.g., __PROJECT_NAME__Home.flexipage-meta.xml -> YourProjectNameHome.flexipage-meta.xml)
- File contents
- Directory names (e.g., robot/__PROJECT_LABEL__/ -> robot/Your-Project-Name/)

Run this script once at the beginning of a new project setup.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_project_values_from_cumulusci():
    """Read project name, package name, and name_managed from cumulusci.yml."""
    file_path = Path("cumulusci.yml")
    
    if not file_path.exists():
        return None, None, None
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = file_path.read_text(encoding='latin-1')
    
    # Extract values using regex
    # Handle both quoted and unquoted values
    project_name_match = re.search(r'project:\s*\n\s*name:\s*(?:"([^"]+)"|([^\n]+))', content)
    package_name_match = re.search(r'package:\s*\n\s*name:\s*(\w+)', content)
    name_managed_match = re.search(r'name_managed:\s*(?:"([^"]+)"|([^\n]+))', content)
    
    # Extract matched groups (handle both quoted and unquoted)
    project_name = None
    if project_name_match:
        project_name = project_name_match.group(1) or project_name_match.group(2)
        if project_name:
            project_name = project_name.strip()
    
    name_managed = None
    if name_managed_match:
        name_managed = name_managed_match.group(1) or name_managed_match.group(2)
        if name_managed:
            name_managed = name_managed.strip()
    
    package_name = package_name_match.group(1) if package_name_match else None
    
    return project_name, package_name, name_managed


def replace_tokens_in_files(package_name: str, name_managed: str, project_name: str = None):
    """
    Replace __PROJECT_NAME__ and __PROJECT_LABEL__ tokens in filenames and file contents.
    
    Args:
        package_name: Package name (e.g., "StandardUnlockedShulman")
        name_managed: Name managed (e.g., "Standard Unlocked Shulman")
        project_name: Project name (e.g., "Standard Unlocked Shulman"). If None, uses name_managed.
    """
    if project_name is None:
        project_name = name_managed
    renamed_count = 0
    updated_count = 0
    
    # Rename directories with tokens in their names
    # First, handle robot/__PROJECT_LABEL__ directory
    robot_token_dir = Path("robot/__PROJECT_LABEL__")
    if robot_token_dir.exists():
        # Use name_managed format (spaces -> hyphens) for robot directory name
        robot_project_name = name_managed.replace(" ", "-")
        robot_new_dir = Path("robot") / robot_project_name
        try:
            if robot_new_dir.exists():
                print(f"[WARNING] Robot directory {robot_new_dir} already exists, skipping rename")
            else:
                robot_token_dir.rename(robot_new_dir)
                print(f"[OK] Renamed robot/__PROJECT_LABEL__ -> robot/{robot_project_name}")
                renamed_count += 1
        except Exception as e:
            print(f"[WARNING] Could not rename robot/__PROJECT_LABEL__ directory: {e}")
    
    # First, update cumulusci.yml to replace tokens and update project values
    cumulusci_yml = Path("cumulusci.yml")
    if cumulusci_yml.exists():
        try:
            content = cumulusci_yml.read_text(encoding='utf-8')
            original_content = content
            
            # Replace tokens in cumulusci.yml
            # __PROJECT_NAME__ -> package_name (spaces removed, e.g., YourProjectName)
            # __PROJECT_LABEL__ -> name_managed with hyphens (spaces -> hyphens, e.g., Your-Project-Name)
            name_managed_hyphenated = name_managed.replace(" ", "-")
            content = content.replace('__PROJECT_NAME__', package_name)
            content = content.replace('__PROJECT_LABEL__', name_managed_hyphenated)
            
            # Also update the actual project.name, package.name, and name_managed fields
            # This ensures cumulusci.yml reflects the repository name when using a template
            # Update project.name (format: "project:\n    name: value")
            content = re.sub(
                r'(project:\s*\n\s+name:\s+)(["\']?)([^\n"\']+)(["\']?)',
                rf'\1\2{project_name}\4',
                content,
                flags=re.MULTILINE
            )
            # Update package.name (format: "package:\n        name: value" - note 8 spaces for name)
            content = re.sub(
                r'(package:\s*\n\s+name:\s+)(\w+)',
                rf'\1{package_name}',
                content,
                flags=re.MULTILINE
            )
            # Update name_managed (format: "        name_managed: value" - 8 spaces)
            content = re.sub(
                r'(\s+name_managed:\s+)(["\']?)([^\n"\']+)(["\']?)',
                rf'\1\2{name_managed}\4',
                content,
                flags=re.MULTILINE
            )
            
            if content != original_content:
                cumulusci_yml.write_text(content, encoding='utf-8')
                print(f"[OK] Updated cumulusci.yml with project values")
                updated_count += 1
        except Exception as e:
            print(f"[WARNING] Could not update cumulusci.yml: {e}")
    
    # Search in common directories
    # Note: .cci directory is included but may not always exist
    search_dirs = ["force-app", "datasets", "robot", "category", ".cci"]
    
    # First pass: rename directories and files with tokens
    for search_dir in search_dirs:
        dir_path = Path(search_dir)
        if not dir_path.exists():
            continue
        
        # Rename directories with tokens (process from deepest to shallowest)
        dirs_to_rename = []
        for dir_path_item in sorted(dir_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if dir_path_item.is_dir():
                if '__PROJECT_NAME__' in dir_path_item.name:
                    dirs_to_rename.append((dir_path_item, '__PROJECT_NAME__', package_name))
                elif '__PROJECT_LABEL__' in dir_path_item.name:
                    dirs_to_rename.append((dir_path_item, '__PROJECT_LABEL__', name_managed.replace(" ", "-")))
        
        for dir_path_item, token, replacement in dirs_to_rename:
            try:
                new_name = dir_path_item.name.replace(token, replacement)
                new_path = dir_path_item.parent / new_name
                # Avoid renaming if target already exists
                if new_path.exists() and new_path != dir_path_item:
                    print(f"[WARNING] Target directory already exists, skipping: {new_path}")
                    continue
                dir_path_item.rename(new_path)
                print(f"[OK] Renamed directory {dir_path_item.relative_to(Path.cwd())} -> {new_path.name}")
                renamed_count += 1
            except Exception as e:
                print(f"[WARNING] Could not rename directory {dir_path_item}: {e}")
        
        # Rename files with tokens
        files_to_rename = []
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and '__PROJECT_NAME__' in file_path.name:
                files_to_rename.append(file_path)
        
        for file_path in files_to_rename:
            try:
                new_name = file_path.name.replace('__PROJECT_NAME__', package_name)
                new_path = file_path.parent / new_name
                # Avoid renaming if target already exists
                if new_path.exists() and new_path != file_path:
                    print(f"[WARNING] Target file already exists, skipping: {new_path}")
                    continue
                file_path.rename(new_path)
                print(f"[OK] Renamed {file_path.relative_to(Path.cwd())} -> {new_path.name}")
                renamed_count += 1
            except Exception as e:
                print(f"[WARNING] Could not rename {file_path}: {e}")
    
    # Second pass: update file contents (including renamed files)
    all_files = []
    for search_dir in search_dirs:
        dir_path = Path(search_dir)
        if dir_path.exists():
            all_files.extend(dir_path.rglob("*"))
    
    # Also include root-level files and orgs directory
    root_files = [Path(".gitignore"), Path("sfdx-project.json"), Path("README.md")]
    for root_file in root_files:
        if root_file.exists():
            all_files.append(root_file)
    
    # Include orgs directory files
    orgs_dir = Path("orgs")
    if orgs_dir.exists():
        all_files.extend(orgs_dir.glob("*.json"))
    
    # Include .cci directory files (if present)
    cci_dir = Path(".cci")
    if cci_dir.exists():
        # Include .cci/snapshot/*.json files
        cci_snapshot_dir = cci_dir / "snapshot"
        if cci_snapshot_dir.exists():
            all_files.extend(cci_snapshot_dir.glob("*.json"))
    
    for file_path in all_files:
        if not file_path.is_file():
            continue
        
        # Skip certain file types and directories
        # Note: Check for .git/ directory, not .gitignore file
        skip_patterns = ['__pycache__', '.pyc', 'node_modules']
        file_path_str = str(file_path)
        # Skip .git directory but not .gitignore file
        # Check if any parent directory is named .git
        skip_file = False
        try:
            for parent in file_path.parents:
                if parent.name == '.git':
                    skip_file = True
                    break
        except (AttributeError, ValueError):
            pass
        if skip_file:
            continue
        # Skip cumulusci.yml (handled separately)
        if file_path.name == 'cumulusci.yml':
            continue
        if any(pattern in file_path_str for pattern in skip_patterns):
            continue
        
        try:
            # Try to read as text
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            original_content = content
            
            # Replace tokens in content
            # __PROJECT_LABEL__ should use hyphenated format for paths and org names
            name_managed_hyphenated = name_managed.replace(" ", "-")
            content = content.replace('__PROJECT_NAME__', package_name)
            content = content.replace('__PROJECT_LABEL__', name_managed_hyphenated)
            
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                rel_path = file_path.relative_to(Path.cwd())
                print(f"[OK] Updated {rel_path}")
                updated_count += 1
        except (UnicodeDecodeError, PermissionError):
            # Skip binary files or files that can't be read/written
            pass
        except Exception as e:
            print(f"[WARNING] Could not update {file_path}: {e}")
    
    return renamed_count, updated_count


def check_for_tokens():
    """Check for any remaining __PROJECT_NAME__ or __PROJECT_LABEL__ tokens."""
    tokens_found = []
    
    # Search in common directories
    # Note: .cci directory is included but may not always exist
    search_dirs = ["force-app", "datasets", "robot", "category", ".cci"]
    
    for search_dir in search_dirs:
        dir_path = Path(search_dir)
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                try:
                    # Check filename
                    if '__PROJECT_NAME__' in file_path.name or '__PROJECT_LABEL__' in file_path.name:
                        tokens_found.append((file_path, 'filename'))
                    
                    # Check content
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if '__PROJECT_NAME__' in content:
                        tokens_found.append((file_path, '__PROJECT_NAME__'))
                    if '__PROJECT_LABEL__' in content:
                        tokens_found.append((file_path, '__PROJECT_LABEL__'))
                except Exception:
                    # Skip binary files or files that can't be read
                    pass
    
    # Also check root-level files and orgs directory
    root_files = [Path(".gitignore"), Path("sfdx-project.json"), Path("README.md"), Path("cumulusci.yml")]
    for root_file in root_files:
        if root_file.exists():
            try:
                # Check filename (unlikely but possible)
                if '__PROJECT_NAME__' in root_file.name or '__PROJECT_LABEL__' in root_file.name:
                    tokens_found.append((root_file, 'filename'))
                
                # Check content
                content = root_file.read_text(encoding='utf-8', errors='ignore')
                if '__PROJECT_NAME__' in content:
                    tokens_found.append((root_file, '__PROJECT_NAME__'))
                if '__PROJECT_LABEL__' in content:
                    tokens_found.append((root_file, '__PROJECT_LABEL__'))
            except Exception:
                pass
    
    # Check orgs directory
    orgs_dir = Path("orgs")
    if orgs_dir.exists():
        for org_file in orgs_dir.glob("*.json"):
            try:
                content = org_file.read_text(encoding='utf-8', errors='ignore')
                if '__PROJECT_NAME__' in content:
                    tokens_found.append((org_file, '__PROJECT_NAME__'))
                if '__PROJECT_LABEL__' in content:
                    tokens_found.append((org_file, '__PROJECT_LABEL__'))
            except Exception:
                pass
    
    # Check .cci directory (if present)
    cci_dir = Path(".cci")
    if cci_dir.exists():
        cci_snapshot_dir = cci_dir / "snapshot"
        if cci_snapshot_dir.exists():
            for cci_file in cci_snapshot_dir.glob("*.json"):
                try:
                    content = cci_file.read_text(encoding='utf-8', errors='ignore')
                    if '__PROJECT_NAME__' in content:
                        tokens_found.append((cci_file, '__PROJECT_NAME__'))
                    if '__PROJECT_LABEL__' in content:
                        tokens_found.append((cci_file, '__PROJECT_LABEL__'))
                except Exception:
                    pass
    
    return tokens_found


def derive_project_values(repo_name: str):
    """
    Derive project values from repository name.
    
    Examples:
    - "Standard-Unlocked-Shulman" -> project_name: "Standard Unlocked Shulman", package_name: "StandardUnlockedShulman", name_managed: "Standard Unlocked Shulman"
    - "My-Awesome-Project" -> project_name: "My Awesome Project", package_name: "MyAwesomeProject", name_managed: "My Awesome Project"
    """
    # Convert hyphenated repo name to project name (hyphens -> spaces)
    project_name = repo_name.replace("-", " ").replace("_", " ")
    # Package name: remove spaces and hyphens
    package_name = repo_name.replace("-", "").replace("_", "").replace(" ", "")
    # Name managed: use project name as-is (spaces preserved)
    name_managed = project_name
    
    return project_name, package_name, name_managed


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(
        description="Replace __PROJECT_NAME__ and __PROJECT_LABEL__ tokens in filenames and file contents."
    )
    parser.add_argument(
        '--repo-name',
        type=str,
        help='Repository name (e.g., "Standard-Unlocked-Shulman"). If not provided, will try to read from cumulusci.yml or prompt.'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode (skip prompts, use defaults)'
    )
    parser.add_argument(
        '--project-name',
        type=str,
        help='Project name (e.g., "Standard Unlocked Shulman"). Overrides repo-name derivation.'
    )
    parser.add_argument(
        '--package-name',
        type=str,
        help='Package name (e.g., "StandardUnlockedShulman"). Overrides repo-name derivation.'
    )
    parser.add_argument(
        '--name-managed',
        type=str,
        help='Name managed (e.g., "Standard Unlocked Shulman"). Overrides repo-name derivation.'
    )
    
    args = parser.parse_args()
    
    # Check for environment variables (for GitHub Actions)
    repo_name = args.repo_name or os.getenv('GITHUB_REPOSITORY_NAME') or os.getenv('REPO_NAME')
    non_interactive = args.non_interactive or os.getenv('CI') == 'true'
    
    # CRITICAL SAFETY CHECK: Prevent running in template repository when in CI mode
    # This provides defense-in-depth protection (workflow also has this check)
    if non_interactive:
        github_repo = os.getenv('GITHUB_REPOSITORY', '').lower()
        template_repos = [
            'sdbingham/standard-unlocked-shulman',
            'sdbingham/standardunlockedshulman'
        ]
        
        if github_repo in template_repos:
            print("=" * 60)
            print("❌ ERROR: Template Repository Protection")
            print("=" * 60)
            print()
            print("This script is running in CI mode on the template repository.")
            print("The template repository should NEVER be modified by this script.")
            print()
            print(f"Detected repository: {os.getenv('GITHUB_REPOSITORY', 'unknown')}")
            print()
            print("This script should only run in NEW repositories created from the template.")
            print("Aborting to protect the template repository.")
            sys.exit(1)
    
    # Debug output (only in CI mode)
    if non_interactive:
        print(f"[DEBUG] repo_name from args: {args.repo_name}")
        print(f"[DEBUG] GITHUB_REPOSITORY_NAME env: {os.getenv('GITHUB_REPOSITORY_NAME')}")
        print(f"[DEBUG] REPO_NAME env: {os.getenv('REPO_NAME')}")
        print(f"[DEBUG] GITHUB_REPOSITORY env: {os.getenv('GITHUB_REPOSITORY', 'not set')}")
        print(f"[DEBUG] Final repo_name: {repo_name}")
    
    # Check if we're in a template repository (has tokens but cumulusci.yml has template values)
    # This prevents accidentally running the script in the template repo
    cumulusci_yml = Path("cumulusci.yml")
    if cumulusci_yml.exists() and not repo_name and not args.project_name:
        try:
            # Check if tokens still exist in key files (indicates this is still a template)
            has_tokens = False
            key_files = [cumulusci_yml, Path("README.md"), Path(".gitignore")]
            for key_file in key_files:
                if key_file.exists():
                    content = key_file.read_text(encoding='utf-8', errors='ignore')
                    if '__PROJECT_NAME__' in content or '__PROJECT_LABEL__' in content:
                        has_tokens = True
                        break
            
            # If tokens exist and no repo_name provided, warn user
            if has_tokens and not non_interactive:
                print("=" * 60)
                print("⚠️  WARNING: Template Repository Detected")
                print("=" * 60)
                print()
                print("This appears to be a template repository with tokens.")
                print("The script should be run in a NEW repository created from this template.")
                print()
                print("If you want to run it here anyway, provide --repo-name:")
                print("  python scripts/setup_new_project.py --repo-name 'Your-New-Project-Name'")
                print()
                confirm = input("Continue anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Cancelled.")
                    sys.exit(0)
        except Exception:
            pass  # If we can't check, continue normally
    
    print("=" * 60)
    print("Project Token Replacement Script")
    print("=" * 60)
    print()
    print("This script permanently replaces __PROJECT_NAME__ and __PROJECT_LABEL__")
    print("tokens in filenames and file contents.")
    print()
    
    # Determine project values
    project_name = None
    package_name = None
    name_managed = None
    
    # Priority 1: Command-line arguments (explicit values) - highest priority
    if args.project_name and args.package_name and args.name_managed:
        project_name = args.project_name
        package_name = args.package_name
        name_managed = args.name_managed
        print("Using explicit values from command-line arguments:")
        print(f"  Project Name: {project_name}")
        print(f"  Package Name: {package_name}")
        print(f"  Name Managed: {name_managed}")
    # Priority 2: Repository name (derive values) - use this when repo name is provided
    # This takes precedence over cumulusci.yml because when using a template,
    # the repository name is the source of truth, not the template's cumulusci.yml
    elif repo_name:
        # ALWAYS use repository name when provided - NEVER read from cumulusci.yml
        # This is critical for template repositories where cumulusci.yml contains tokens
        project_name, package_name, name_managed = derive_project_values(repo_name)
        print(f"✅ Using repository name '{repo_name}' to derive project values:")
        print(f"  Project Name: {project_name}")
        print(f"  Package Name: {package_name}")
        print(f"  Name Managed: {name_managed}")
        print()
        print("⚠️  IMPORTANT: Ignoring any values in cumulusci.yml.")
        print("   The repository name is the source of truth for template repositories.")
        print("   cumulusci.yml will be updated with these values.")
    # Priority 3: Try to read from cumulusci.yml (fallback when no repo name provided)
    else:
        project_name, package_name, name_managed = get_project_values_from_cumulusci()
        # Check if the values are actually tokens (should not be used)
        if project_name and package_name and name_managed:
            # If values contain tokens, they're not real values - treat as None
            if '__PROJECT_NAME__' in project_name or '__PROJECT_LABEL__' in project_name or \
               '__PROJECT_NAME__' in package_name or '__PROJECT_LABEL__' in package_name or \
               '__PROJECT_NAME__' in name_managed or '__PROJECT_LABEL__' in name_managed:
                print("Warning: cumulusci.yml contains tokens, not actual values. Skipping.")
                project_name = None
                package_name = None
                name_managed = None
            else:
                print("Found values in cumulusci.yml:")
                print(f"  Project Name: {project_name}")
                print(f"  Package Name: {package_name}")
                print(f"  Name Managed: {name_managed}")
    
    # If we still don't have values, prompt (unless non-interactive)
    if not (project_name and package_name and name_managed):
        if non_interactive:
            print("Error: Could not determine project values and running in non-interactive mode.")
            print("Please provide --repo-name or ensure cumulusci.yml has the required values.")
            sys.exit(1)
        
        # Prompt for values
        print("Could not read values from cumulusci.yml.")
        print("Please provide the following values:")
        print()
        project_name = input("Project Name (e.g., 'Shulman Intake Platform'): ").strip()
        if not project_name:
            print("Error: Project name is required!")
            sys.exit(1)
        
        # Derive values from project name
        package_name = project_name.replace(" ", "")
        name_managed = project_name.replace(" ", "-")
        
        print()
        print("Derived values:")
        print(f"  Package Name: {package_name} (spaces removed)")
        print(f"  Name Managed: {name_managed} (spaces -> hyphens)")
    
    # Confirm (unless non-interactive)
    if not non_interactive:
        print()
        confirm = input("Use these values to replace tokens? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    # Replace tokens
    print()
    print("=" * 60)
    print("Replacing Tokens")
    print("=" * 60)
    print()
    renamed_count, updated_count = replace_tokens_in_files(package_name, name_managed, project_name)
    
    if renamed_count > 0 or updated_count > 0:
        print()
        print(f"[OK] Renamed {renamed_count} file(s) and updated {updated_count} file(s)")
    else:
        print()
        print("[OK] No files needed token replacement")
    
    # Check for remaining tokens
    print()
    print("=" * 60)
    print("Checking for Remaining Tokens")
    print("=" * 60)
    print()
    tokens_found = check_for_tokens()
    
    if tokens_found:
        print(f"[WARNING] Found {len(tokens_found)} file(s) with remaining tokens:")
        for file_path, token in tokens_found:
            print(f"  - {file_path} ({token})")
        print()
        print("These files need manual token replacement.")
    else:
        print("[OK] No remaining tokens found.")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review the changes made")
    print("  2. Commit the changes to git")
    print("  3. Continue with your project setup")
    print()


if __name__ == "__main__":
    main()
