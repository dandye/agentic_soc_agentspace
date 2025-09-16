# Agent Engine Deployment Guide

This guide provides step-by-step instructions for deploying a Google Vertex AI Agent with MCP security tools integration.

## Prerequisites

Before starting deployment, ensure you have:

### Required Google Cloud Setup
1. **Google Cloud Project**
   - Active GCP project with billing enabled
   - Project ID and Project Number available

2. **Required APIs Enabled**
   ```bash
   # Enable these APIs in your project:
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable compute.googleapis.com
   ```

3. **IAM Permissions**
   Your account needs these roles:
   - `roles/aiplatform.user` - Create and manage AI Platform resources
   - `roles/storage.admin` - Manage staging bucket
   - `roles/iam.serviceAccountUser` - Create service accounts for agent

### Local Development Setup
1. **Python 3.10+** installed
2. **Google Cloud SDK** installed and configured
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Git** with submodules support

## Step 1: Clone and Setup Repository

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/your-org/agentic_soc_agentspace.git
cd agentic_soc_agentspace

# If already cloned without submodules
git submodule update --init --recursive
```

## Step 2: Configure Environment

1. **Copy environment template**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values**

   **Required for deployment:**
   ```bash
   PROJECT_ID=your-gcp-project-id          # Your Google Cloud Project ID
   LOCATION=us-central1                    # Deployment region
   STAGING_BUCKET=your-staging-bucket      # GCS bucket name (will be created if doesn't exist)
   PROJECT_NUMBER=123456789                # From GCP Console > Project Info
   ```

   **Required for SOAR integration:**
   ```bash
   SOAR_URL=https://your-instance..siemplify-soar.com:443
   SOAR_APP_KEY=your-soar-api-key
   ```

   **For testing existing agents:**
   ```bash
   REASONING_ENGINE=projects/PROJECT_ID/locations/LOCATION/reasoningEngines/ENGINE_ID
   ```

3. **Create staging bucket (if needed)**
   ```bash
   gsutil mb -p $PROJECT_ID -l $LOCATION gs://$STAGING_BUCKET
   ```

## Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify MCP security submodule
ls mcp-security/  # Should show server directories
```

## Step 4: Deploy Agent to Agent Engine

### Option A: Using Makefile (Recommended)
```bash
# Full deployment with all MCP tools
make deploy

### Option B: Direct Python Execution
```bash
python main.py
```

### What Happens During Deployment

1. **Agent Configuration**
   - Creates Vertex AI agent with Gemini 2.0 Flash model
   - Configures system prompt with security operations context
   - Sets up MCP tool integration

2. **MCP Tools Setup**
   - Packages MCP security servers from submodule
   - Configures stdio transport for each tool
   - Sets up authentication via environment variables

3. **Cloud Deployment**
   - Uploads agent package to staging bucket
   - Runs `installation_scripts/install.sh` on cloud instance
   - Installs `uv` package manager for MCP servers
   - Creates reasoning engine resource

4. **Output**
   ```
   Deploying agent...
   Agent deployed successfully!
   Agent ID: projects/PROJECT_ID/locations/LOCATION/reasoningEngines/ENGINE_ID
   ```

## Step 5: Test Deployed Agent

1. **Copy the Agent ID from deployment output**

2. **Update `.env` with the reasoning engine ID**
   ```bash
   REASONING_ENGINE=projects/PROJECT_ID/locations/LOCATION/reasoningEngines/ENGINE_ID
   ```

3. **Run test script**
   ```bash
   python test_agent_engine.py
   ```

4. **Interactive testing**
   ```python
   # The test script will prompt for queries
   > What are the recent security alerts?
   > Analyze threat indicators for domain malicious.com
   > Show me Security Command Center findings
   ```

## Step 6: Verify Deployment

### Check Logs
```bash
# View deployment logs
gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine" --limit=50

# View runtime logs
gcloud logging read "resource.labels.reasoning_engine_id=ENGINE_ID" --limit=50
```

## Deployment Options

### Custom Agent Configuration

Edit `main.py` to customize:

1. **Model Selection**
   ```python
   model = "gemini-2.0-flash-exp"  # or "gemini-1.5-pro", "gemini-1.5-flash"
   ```

2. **System Prompt**
   ```python
   system_prompt = "Your custom security analyst prompt..."
   ```

3. **Tool Selection**
   ```python
   tools = [secops_tool]  # Add/remove tools as needed
   ```

### Staging and Production Deployments

For different environments:

1. **Create environment-specific `.env` files**
   ```bash
   .env.staging
   .env.production
   ```

2. **Deploy with specific config**
   ```bash
   cp .env.staging .env && make deploy
   cp .env.production .env && make deploy
   ```

## Next Steps

- Review [MCP Security Tools Documentation](mcp-security/README.md)
- Configure individual MCP tools with API keys
- Set up monitoring and alerting for the agent
- Create custom runbooks for your security workflows

## Getting Help

- Check the [Troubleshooting Guide](#troubleshooting) below
- Review [Google Vertex AI Agent Documentation](https://cloud.google.com/vertex-ai/docs/agents)
- File issues at [GitHub Issues](https://github.com/your-org/agentic_soc_agentspace/issues)

## Troubleshooting

### Common Deployment Issues

#### 1. Authentication Errors
**Error:** `403 Permission Denied` or `401 Unauthorized`

**Solution:**
```bash
# Re-authenticate
gcloud auth application-default login
gcloud config set project $PROJECT_ID

# Verify authentication
gcloud auth application-default print-access-token
```

#### 2. Missing APIs
**Error:** `API [aiplatform.googleapis.com] not enabled`

**Solution:**
```bash
# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
```

#### 3. Staging Bucket Issues
**Error:** `Bucket not found` or `Access denied to bucket`

**Solution:**
```bash
# Create bucket with correct permissions
gsutil mb -p $PROJECT_ID -l $LOCATION gs://$STAGING_BUCKET
gsutil iam ch user:$(gcloud config get-value account):objectAdmin gs://$STAGING_BUCKET
```

#### 4. MCP Tools Not Working
**Error:** `MCP server failed to start` or tools not responding

**Solution:**
```bash
# Verify submodule is initialized
git submodule update --init --recursive

# Check MCP server directories exist
ls -la mcp-security/servers/

# Test MCP server locally
cd mcp-security/servers/mcp-server-soar
uv run mcp-server-soar
```

#### 5. Agent Creation Timeout
**Error:** `Deployment timed out after 10 minutes`

**Solution:**
- Check Cloud Build logs for errors
- Verify installation script has correct permissions
- Increase timeout in `main.py`:
  ```python
  operation.result(timeout=1200)  # 20 minutes
  ```

#### 6. Environment Variable Issues
**Error:** `KeyError: 'PROJECT_ID'` or similar

**Solution:**
```bash
# Verify .env file exists and is loaded
cat .env
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('PROJECT_ID'))"
```

### Debugging Deployment

1. **Enable verbose logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check intermediate steps**
   ```bash
   # Verify staging bucket upload
   gsutil ls gs://$STAGING_BUCKET/

   # Check Cloud Build logs
   gcloud builds list --limit=5
   ```

3. **Test components individually**
   ```bash
   # Test MCP servers
   make test-mcp-soar
   make test-mcp-secops
   ```

### Getting Support

If issues persist:
1. Collect error logs and deployment output
2. Check [Known Issues](https://github.com/your-org/agentic_soc_agentspace/issues?q=is%3Aissue+label%3Aknown-issue)
3. Create detailed issue report with:
   - Error messages
   - Environment details (`gcloud version`, `python --version`)
   - Steps to reproduce
   - `.env` configuration (sanitized)