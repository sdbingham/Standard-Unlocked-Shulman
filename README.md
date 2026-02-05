# __PROJECT_LABEL__

This repository contains everything you need to realize enterprise-grade Salesforce CICD practices without making an enterprise-grade investment. 

The included [Github Actions](.github/workflows) provide a standardized (and mostly automated!) framework for building, testing, and delivering solutions in a consistent and repeatable manner. 

We strongly advocate adhering to a "Release Train" development methodology for Salesforce development. When applied with discipline, this approach consistently balances business demands, development rigor, and the unique constraints of working with Salesforce metadata significantly better than other popular methodologies (Scrum 👀).

## Salesforce Release Train Development Cadence

![image](https://github.com/user-attachments/assets/6b7d1dc8-30cb-4740-964e-8cd55f54a847)
[Image Credit: CumulusCI Documentation](https://cumulusci.readthedocs.io/en/stable/cumulusci-flow.html)

## Getting Started

1. Fork this repository.
2. Make a _new_ Repository in your organization and select your fork as the `Repository Template`
3. Modify the `name` and `name_managed` fields in [cumulusci.yml](cumulusci.yml)<sup>1</sup>
4. **Option A: Automatic Setup (Recommended)** - Use the GitHub Action workflow:
   - Navigate to **Actions** → **Setup Project** → **Run workflow**
   - The workflow will automatically:
     - Extract the repository name
     - Run the setup script to replace all tokens
     - Commit the changes back to the repository
   - Alternatively, push your first commit to `main` branch and the workflow will run automatically if tokens are detected
   
   **Option B: Manual Setup** - Run the setup script locally:
   ```bash
   python setup_new_project.py
   ```
   Or with explicit repository name:
   ```bash
   python setup_new_project.py --repo-name "Your-Project-Name" --non-interactive
   ```
   
   The script will:
   - Read project values from `cumulusci.yml` (or derive from repository name)
   - Permanently replace `__PROJECT_NAME__` and `__PROJECT_LABEL__` tokens in all filenames and file contents
   - Rename directories (e.g., `robot/__PROJECT_LABEL__/` → `robot/Your-Project-Name/`)
   - Update all configuration files (`.gitignore`, `sfdx-project.json`, `orgs/*.json`, etc.)
   
   Then commit the changes:
   ```bash
   git add .
   git commit -m "Replace project tokens with actual project name"
   git push
   ```
5. **Configure Salesforce Authentication**:
   
   **Option A: Automated Setup via GitHub Actions (Recommended)**:
   - **Test first (optional)**: Run `python test_auth_logic.py` locally to verify your credentials work
   - Go to **Actions** → **Setup Salesforce Authentication** → **Run workflow**
   - Provide:
     - **Org URL**: Enter your Salesforce org URL manually (e.g., `https://login.salesforce.com`, `https://test.salesforce.com`, or custom domain)
     - **Username**: Your Salesforce username
     - **Password**: Your Salesforce password (⚠️ Note: Password will be visible in workflow logs - consider using a test/dev org)
     - **Security Token**: (Optional - only if IP is not whitelisted)
     - **Secret Name**: `DEV_HUB_AUTH_URL` (default)
   - Click **Run workflow**
   - The workflow will automatically:
     - Authenticate to Salesforce
     - Generate SFDX auth URL
     - Create GitHub secret
   - **That's it!** No certificates, no Connected Apps, no manual steps.
   
   > ⚠️ **Security Note**: GitHub Actions workflow inputs are visible in workflow logs. For production orgs, consider using the local script (`setup_salesforce_auth.py`) or manually creating the secret.
   
   **Option B: Using Local Script**:
   - Install required Python packages: `pip install requests pynacl`
   - Run the authentication setup script:
     ```bash
     python setup_salesforce_auth.py
     ```
   - The script will:
     - Prompt for Salesforce org alias
     - Open browser for Salesforce authentication
     - Retrieve SFDX auth URL
     - Create `DEV_HUB_AUTH_URL` GitHub secret automatically
   
   **Option C: Manual Setup**:
   - Follow the [`Initial Setup` instructions](https://github.com/Nimba-Solutions/Shulman-API/blob/main/.github/workflows/README.md#initial-setup) to configure secrets manually.

> [!IMPORTANT]
> **Template Protection**: This repository is protected by multiple safeguards to ensure it is NEVER modified when used as a template. See [TEMPLATE_PROTECTION.md](TEMPLATE_PROTECTION.md) for details.

> [!NOTE]
> 1. As you explore this project, you may notice a large number of tokens such as `__PROJECT_LABEL__` and `__PROJECT_NAME__`. These correspond to the `name_managed` and `name` attributes in [cumulusci.yml](cumulusci.yml). **Run `setup_new_project.py` once at project initialization** to permanently replace these tokens. After that, all files will use your actual project name.

## Development

1. [Set up CumulusCI](https://cumulusci.readthedocs.io/en/latest/tutorial.html) in your preferred development environnment.
2. Run `cci flow run dev_org --org dev` to deploy this project.
3. Run `cci org browser dev` to open the org in your browser.
4. Build your solution, periodically run `cci task run retrieve_changes --org dev`, and commit your changes to a `feature/**` branch using your preferred git tooling.
7. When you're ready, run `git push` to send your changes to GitHub.
8. Submit a PR.
9. Monitor for Success/Failure

----

## Releases

### [Recommended] Release this project using the Built-in CICD Actions

Follow the provided [`Release` instructions](https://github.com/Nimba-Solutions/Shulman-API/blob/main/.github/workflows/README.md#releases).


---

### [Advanced] Release this project using your CLI

#### To release a new `beta` version of this package:

1. Run `git checkout main` to switch to the main branch.
2. Run `git pull` to download the latest changes from Github.
3. Run `cci flow run dependencies --org dev` to prepare a scratch org for the process of packaging.
4. Run `cci flow run release_unlocked_beta --org dev` to release a new beta version of this package.
5. [Optional] Run `cci org browser dev` to open the org in your browser.

#### To release a new `production` version of this package:

1. Run `git checkout main` to switch to the main branch.
2. Run `git pull` to download the latest changes from Github.
3. Run `cci flow run release_unlocked_production --org dev --debug` to release a new beta version of this package.
4. Run `cci org browser dev` to open the org in your browser.
5. [OPTIONAL] Run `cci flow run install_prod --org <target-org-alias>` to install the package and _all of its dependencies_ in `<target-org-alias>`.


=====================================