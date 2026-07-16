# How to Run & Connect with GitHub

This guide explains how to run the self-healing documentation tool locally and how to integrate it as a GitHub Action in your target repository.

---

## 1. Running the Project Locally

### Prerequisites
* Python 3.12+ installed
* Anthropic API Key (Claude Sonnet 4.6)

### Installation
Run the following command to bootstrap your virtual environment and install dependencies:
```bash
make install
```

### Running Checks
Set your Anthropic key and run the script:
```bash
make run
```

### Running Tests and Linters
To run code styling rules and the test suite:
```bash
make lint
make test
```

---

## 2. Connecting to your GitHub Repository

To integrate this tool directly into your repository's Pull Request workflow:

### Step 1: Add a Workflow File
Create a new file in your target repository under `.github/workflows/self-healing-docs.yml`:

```yaml
name: Self-Healing Technical Documentation

on:
  pull_request:
    paths:
      - '**.py' # Triggers checks only when Python code changes

jobs:
  check-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # FETCH FULL HISTORY FOR GIT DIFF PARSING

      - name: Run Self-Healing Docs
        uses: owner/self-healing-technical-documentation@main # Replace with your action path or repository name
        with:
          llm_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          confidence_threshold: '0.8'
          auto_merge: 'true'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Step 2: Configure Secrets
1. Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Name it `ANTHROPIC_API_KEY` and paste your Anthropic API key value.

### Step 3: Enable Pull Request Permissions
Make sure GitHub Actions can create PR branches and post comments:
1. Go to **Settings** -> **Actions** -> **General**.
2. Scroll to **Workflow permissions**.
3. Select **Read and write permissions** and check **Allow GitHub Actions to create and approve pull requests**.
