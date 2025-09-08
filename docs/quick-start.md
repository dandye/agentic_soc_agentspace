---
title: Quick Start Guide
description: Steps to deploy MCP security agents to Google Cloud
---

# Quick Start Guide

Steps for deploying an MCP Security Agent to Agent Engine and connecting it to AgentSpace.

## Prerequisites

Before you begin, ensure you have:

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Python 3.10+ installed
- Required APIs enabled:
  - Vertex AI API
  - Discovery Engine API
  - Security Command Center API (if using SCC tools)
  - Chronicle API (if using SecOps tools)

## Part 1: Agent Engine Deployment

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/agentic_soc_agentspace.git
cd agentic_soc_agentspace

# Initialize the MCP security submodule
git submodule update --init --recursive

# Setup environment and install dependencies
make setup

# Edit .env with your values
nano .env
```

Required environment variables:
```bash
PROJECT_ID="your-project-id"
LOCATION="us-central1"
STAGING_BUCKET="your-staging-bucket"
PROJECT_NUMBER="your-project-number"

# SOAR Configuration (if using SOAR tools)
SOAR_URL="https://your-instance.siemplify-soar.com:443"
SOAR_APP_KEY="your-soar-api-key"
```

### Step 2: Configure Environment

Edit the `.env` file with your project details as shown above.

### Step 3: Deploy Agent to Agent Engine

```bash
# Deploy the agent (keeps agent running)
make deploy

# Or for development - deploy, test, then delete
make deploy-and-delete
```

This will:
1. Initialize Vertex AI in your project
2. Package the MCP security tools
3. Create and deploy the agent to Agent Engine
4. Output the reasoning engine ID (save this!)

Expected output:
```
Deploying agent to Agent Engine...
Agent created successfully!
Agent deployed: projects/123456/locations/us-central1/reasoningEngines/789012
```

### Step 4: Test Your Agent

```bash
# Set the reasoning engine ID from the previous step in your .env file
echo "REASONING_ENGINE=789012" >> .env

# Test the deployed agent
make test
```

You should see the agent respond to your test query.

## Part 2: AgentSpace Integration

### Step 1: Create an AgentSpace App

1. Navigate to [Google Cloud Console](https://console.cloud.google.com)
2. Go to **Vertex AI > Search & Conversation > Apps**
3. Click **Create App**
4. Select **Agent** as the app type
5. Configure:
   - App name: `soc-agent-app`
   - Region: `global`
   - Enterprise features: Enable as needed
6. Click **Create**
7. Copy the App ID from the app details page

### Step 2: Configure AgentSpace Environment

Add to your `.env` file:
```bash
# AgentSpace Configuration
AGENTSPACE_PROJECT_ID="${PROJECT_ID}"
AGENTSPACE_PROJECT_NUMBER="${PROJECT_NUMBER}"
AGENTSPACE_APP_ID="soc-agent-app_1234567890"  # Your app ID
AGENT_ENGINE_RESOURCE_NAME="projects/${PROJECT_NUMBER}/locations/${LOCATION}/reasoningEngines/${REASONING_ENGINE}"
GOOGLE_CLOUD_LOCATION="${LOCATION}"

# Agent Display Configuration
AGENT_DISPLAY_NAME="SOC Security Agent"
AGENT_DESCRIPTION="AI-powered security operations agent"
AGENT_TOOL_DESCRIPTION="Security analysis and incident response tools"
```

### Step 3: Set Up OAuth (Optional but Recommended)

```bash
# Generate OAuth configuration from client secret file
make oauth-setup CLIENT_SECRET=path/to/client_secret.json

# Create OAuth authorization
make oauth-create-auth

# Verify OAuth setup
make oauth-verify
```

### Step 4: Link Agent to AgentSpace

```bash
# Link your deployed agent to AgentSpace
make manage-agentspace-link-agent
```

Expected output:
```
Linking agent to AgentSpace...
Successfully linked agent to AgentSpace!
Agent ID: soc_security_agent_001
```

### Step 5: Verify Integration

```bash
# Verify the AgentSpace configuration
make manage-agentspace-verify

# Get the AgentSpace UI URL
make manage-agentspace-url
```

Click the URL to open AgentSpace and interact with your agent through the UI.

## Complete Workflow Commands

The Makefile provides complete workflow commands for common scenarios:

### Basic Deployment
```bash
# Complete deployment workflow: setup, deploy, and register
make full-deploy
```

### Deployment with OAuth
```bash
# Full deployment with OAuth integration
make full-deploy-with-oauth
```

### Redeploy Existing Agent
```bash
# Redeploy and update existing agent
make redeploy
```

### OAuth Workflow Only
```bash
# Setup OAuth authorization (create and verify)
make oauth-workflow
```

## Next Steps

- [Configure MCP Security Tools](./mcp-tools-setup.md)
- [Advanced AgentSpace Features](./agentspace-advanced.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [API Reference](./api-reference.md)

## Quick Commands Reference

### Agent Management
```bash
# List all deployed agents
make manage-agent-engine-list

# List agents with verbose output
make manage-agent-engine-list-verbose

# Delete an agent by index
make manage-agent-engine-delete-by-index INDEX=1

# Force delete without confirmation
make manage-agent-engine-delete-force INDEX=1

# Clean up old agents interactively
make cleanup
```

### AgentSpace Management
```bash
# Register agent with AgentSpace
make manage-agentspace-register

# Update AgentSpace configuration
make manage-agentspace-update

# List all agents in AgentSpace
make manage-agentspace-list-agents

# Test AgentSpace search
make manage-agentspace-test QUERY="security incident"

# Ensure data store exists
make manage-agentspace-datastore
```

### Monitoring
```bash
# Check status
make status

# View agent logs
gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine" --limit 50
```

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**
   - Ensure your service account has the required roles:
     - Vertex AI User
     - Discovery Engine Admin
     - Service Usage Consumer

2. **"API not enabled" errors**
   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable discoveryengine.googleapis.com
   ```

3. **"Staging bucket not found"**
   ```bash
   gsutil mb -p ${PROJECT_ID} gs://${STAGING_BUCKET}
   ```

4. **Agent not appearing in AgentSpace**
   - Verify the reasoning engine ID is correct
   - Check that the AgentSpace app exists
   - Ensure OAuth is properly configured

For detailed troubleshooting, see the [Troubleshooting Guide](./troubleshooting.md).