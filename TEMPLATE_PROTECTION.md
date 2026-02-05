# Template Repository Protection

This document explains the multiple layers of protection that ensure the template repository (`sdbingham/Standard-Unlocked-Shulman`) is **NEVER** modified when used as a GitHub template.

## Protection Layers

### Layer 1: GitHub Actions Workflow Job-Level Check
**Location**: `.github/workflows/setup_project.yml` (line 29-33)

The entire workflow job is **skipped** if the repository matches the template repository name. This prevents ANY steps from executing in the template repository.

```yaml
if: |
  github.repository != 'sdbingham/Standard-Unlocked-Shulman' &&
  github.repository != 'sdbingham/standard-unlocked-shulman' &&
  github.repository != 'sdbingham/StandardUnlockedShulman' &&
  github.repository != 'sdbingham/STANDARD-UNLOCKED-SHULMAN' &&
  (github.event_name == 'workflow_dispatch' || ...)
```

**How it works**: GitHub Actions evaluates this condition BEFORE running any steps. If `github.repository` matches any template variation, the entire job is skipped.

### Layer 2: Setup Script CI Mode Check
**Location**: `setup_new_project.py` (lines 408-430)

When running in CI mode (non-interactive), the script checks the `GITHUB_REPOSITORY` environment variable and exits immediately if it matches the template repository.

```python
if non_interactive:
    github_repo = os.getenv('GITHUB_REPOSITORY', '').lower()
    template_repos = [
        'sdbingham/standard-unlocked-shulman',
        'sdbingham/standardunlockedshulman'
    ]
    
    if github_repo in template_repos:
        print("❌ ERROR: Template Repository Protection")
        sys.exit(1)
```

**How it works**: Even if the workflow somehow runs, the script will detect it's running on the template repository and abort before making any changes.

### Layer 3: Commit Step Safety Check
**Location**: `.github/workflows/setup_project.yml` (lines 114-127)

Before committing changes, the workflow performs a redundant safety check that explicitly compares the current repository to the template repository and exits with an error if they match.

```bash
CURRENT_REPO="${{ github.repository }}"
CURRENT_REPO_LOWER=$(echo "$CURRENT_REPO" | tr '[:upper:]' '[:lower:]')
TEMPLATE_REPOS="sdbingham/standard-unlocked-shulman sdbingham/standardunlockedshulman"

for TEMPLATE_REPO in $TEMPLATE_REPOS; do
  if [ "$CURRENT_REPO_LOWER" = "$TEMPLATE_REPO" ]; then
    echo "❌ ERROR: This is the template repository!"
    exit 1
  fi
done
```

**How it works**: This provides defense-in-depth. Even if both previous checks somehow fail, this check will prevent committing changes to the template.

### Layer 4: Interactive Mode Warning
**Location**: `setup_new_project.py` (lines 419-452)

When running locally in interactive mode, the script detects if it's running in a template repository (by checking for tokens in key files) and warns the user, requiring explicit confirmation.

**How it works**: Prevents accidental local execution on the template repository.

## How Template Usage Works

1. **User creates a new repository** from the template using GitHub's "Use this template" feature
2. **GitHub creates a new repository** with a NEW name (e.g., `user/My-New-Project`)
3. **GitHub pushes the template files** to the new repository's `main` branch
4. **The workflow triggers** on push to `main`
5. **Layer 1 check passes** because `github.repository` = `user/My-New-Project` ≠ template
6. **Workflow runs** and replaces tokens in the NEW repository only
7. **Template repository remains unchanged** because the workflow never runs there

## Verification

To verify protection is working:

1. **Check workflow logs**: When the workflow runs in a new repository, you should see:
   - `✅ Safety check passed - this is NOT the template repository`
   - Repository name in logs should NOT be `sdbingham/Standard-Unlocked-Shulman`

2. **Check template repository**: The template repository should:
   - Still contain `__PROJECT_NAME__` and `__PROJECT_LABEL__` tokens
   - Never have workflow runs that modify files
   - Have no commits from the setup workflow

3. **Test locally**: Running `python setup_new_project.py` in the template repository should:
   - Show a warning in interactive mode
   - Exit with error in CI mode (if `GITHUB_REPOSITORY` is set)

## Important Notes

- **The template repository name is hardcoded** in multiple places. If you rename the template repository, you MUST update:
  - `.github/workflows/setup_project.yml` (job-level `if` condition)
  - `.github/workflows/setup_project.yml` (commit step check)
  - `setup_new_project.py` (CI mode check)

- **Case sensitivity**: GitHub repository names are case-insensitive, but `github.repository` returns the exact case. We check multiple case variations to be safe.

- **Fork vs Template**: If someone **forks** the repository (instead of using it as a template), the fork will have a different repository name, so the workflow will run. This is intentional - forks should get the setup.
