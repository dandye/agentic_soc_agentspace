# Deployment Workflow Guide

This guide walks you through the complete deployment process for the Agentic SOC Agent Engine, from initial setup to full integration with AgentSpace.

## Overview

The deployment process consists of three stages:

1. **Prerequisites Setup** - Configure your environment
2. **Agent Deployment** - Deploy the agent engine to Google Cloud
3. **Integration** - Connect to AgentSpace and configure OAuth (optional)

## Environment Variables Lifecycle

```
STAGE 1: Prerequisites (before deployment)
    ├── PROJECT_ID, PROJECT_NUMBER, LOCATION
    ├── STAGING_BUCKET, GOOGLE_API_KEY
    └── Security tool configs (CHRONICLE_*, SOAR_*, VT_APIKEY)
                    ↓
STAGE 2: Deployment Outputs (from 'make agent-engine-deploy')
    ├── REASONING_ENGINE
    └── AGENT_ENGINE_RESOURCE_NAME
                    ↓
STAGE 3: Integration Outputs (from integration commands)
    ├── OAUTH_AUTH_ID (from 'make oauth-create')
    └── AGENTSPACE_AGENT_ID (from 'make agentspace-register')
```

## Step-by-Step Deployment

### Stage 1: Prerequisites

#### 1.1 Create your environment file
```bash
cp .env.example .env
```

#### 1.2 Fill in required variables
Edit `.env` and set these required values:
- `PROJECT_ID` - Your Google Cloud project ID
- `PROJECT_NUMBER` - Your Google Cloud project number
- `LOCATION` - Deployment region (e.g., us-central1)
- `STAGING_BUCKET` - GCS bucket name for staging
- `GOOGLE_API_KEY` - API key from Google AI Studio

#### 1.3 Configure security tools (optional)
If using security integrations, also set:
- Chronicle SIEM: `CHRONICLE_CUSTOMER_ID`, `CHRONICLE_PROJECT_ID`, `CHRONICLE_REGION`, `SECOPS_SA_PATH`
- SOAR: `SOAR_URL`, `SOAR_APP_KEY`
- Threat Intelligence: `VT_APIKEY`

#### 1.4 Initialize the project
```bash
make setup
```

### Stage 2: Agent Deployment

#### 2.1 Deploy the agent engine
```bash
make agent-engine-deploy
```

**Important**: Watch the output for these values and save them to your `.env` file:
- `REASONING_ENGINE` - The numeric engine ID
- `AGENT_ENGINE_RESOURCE_NAME` - The full resource path

Example output:
```
Agent deployed: projects/987654321012/locations/us-central1/reasoningEngines/1234567890987654321
                         987654321012
========================================
DEPLOYMENT COMPLETE - Save these values to .env:
========================================
  REASONING_ENGINE=1234567890987654321
  AGENT_ENGINE_RESOURCE_NAME=projects/987654321012/locations/us-central1/reasoningEngines/1234567890987654321
```

#### 2.2 Test the deployment
```bash
make agent-engine-test
```

### Stage 3: Integration (Optional)

Choose your integration path based on your needs:

#### Option A: Basic AgentSpace Integration

If you just need to register the agent with AgentSpace:

```bash
make agentspace-register
```

Save the displayed `AGENTSPACE_AGENT_ID` to your `.env` file.

#### Option B: OAuth-Enabled Integration

If you need OAuth authentication:

##### B.1 Setup OAuth (if you have client_secret.json)
```bash
make oauth-setup CLIENT_SECRET=path/to/client_secret.json
```

##### B.2 Create OAuth authorization
```bash
make oauth-create-auth
```

Save the displayed `OAUTH_AUTH_ID` to your `.env` file.

##### B.3 Link agent with OAuth
```bash
make agentspace-link-agent
```

Save the displayed `AGENTSPACE_AGENT_ID` to your `.env` file.

#### Option C: Full Deployment with OAuth

For a complete deployment with all integrations:

```bash
OAUTH=1 make full-deploy
```

This runs setup, deploy, and all integration steps automatically.

## Verification

After deployment, verify everything is working:

```bash
make agentspace-verify
```

This will show:
- Agent status
- AgentSpace URL
- Configuration details

## Common Workflows

### Fresh Deployment
```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your values

# 2. Deploy
make agent-engine-deploy
# Save REASONING_ENGINE and AGENT_ENGINE_RESOURCE_NAME to .env

# 3. Register with AgentSpace
make agentspace-register
# Save AGENTSPACE_AGENT_ID to .env

# 4. Verify
make agentspace-verify
```

### Redeployment
```bash
# 1. Deploy new version
make agent-engine-deploy
# Update REASONING_ENGINE and AGENT_ENGINE_RESOURCE_NAME in .env

# 2. Update AgentSpace
make agentspace-update

# 3. Verify
make agentspace-verify
```

### Cleanup Old Deployments
```bash
# List all agent engines
make agent-engine-list

# Delete specific engine by index
make agent-engine-delete-by-index INDEX=2
```

## Troubleshooting

### Missing Environment Variables

If you get errors about missing variables, check which stage they come from:

**Stage 1 errors**: These must be set before deployment
- Solution: Edit `.env` and add the missing prerequisite variables

**Stage 2 errors**: These come from deployment output
- Solution: Run `make agent-engine-deploy` and save the output values

**Stage 3 errors**: These come from integration commands
- Solution: Run the appropriate integration command and save the output

### Permission Errors

Ensure your Google Cloud account has these roles:
- Vertex AI User
- Discovery Engine Admin (for AgentSpace)
- Security Center Admin (if using SCC tools)
- Chronicle API User (if using Chronicle)

### API Not Enabled

Enable required APIs:
```bash
gcloud services enable \
  aiplatform.googleapis.com \
  discoveryengine.googleapis.com \
  securitycenter.googleapis.com
```

### AgentSpace App Not Found

If `AGENTSPACE_APP_ID` is not set:
1. Create an app in Discovery Engine console
2. Copy the app ID (format: `app-name_timestamp`)
3. Add to `.env` as `AGENTSPACE_APP_ID`

## Decision Tree

```
Start
  │
  ├─ Do you have existing Google Cloud resources?
  │   ├─ Yes → Set AGENTSPACE_APP_ID, AGENTSPACE_DATA_STORE_ID in Stage 1
  │   └─ No → Leave them empty, create during deployment
  │
  ├─ Do you need OAuth authentication?
  │   ├─ Yes → Follow Option B or C in Stage 3
  │   └─ No → Follow Option A in Stage 3
  │
  └─ Do you need security tool integrations?
      ├─ Yes → Configure Chronicle/SOAR/VT variables in Stage 1
      └─ No → Skip security tool configuration
```

## Next Steps

After successful deployment:

1. Access your agent through the AgentSpace URL (shown by `make agentspace-verify`)
2. Test agent functionality with security queries
3. Monitor logs in Google Cloud Console
4. Configure additional integrations as needed

## Reference

### Make Targets by Stage

**Stage 1 (Prerequisites)**
- `make setup` - Initialize project

**Stage 2 (Deployment)**
- `make agent-engine-deploy` - Deploy agent engine
- `make agent-engine-test` - Test deployment

**Stage 3 (Integration)**
- `make agentspace-register` - Register with AgentSpace
- `make oauth-create-auth` - Create OAuth authorization
- `make agentspace-link-agent` - Link agent with OAuth

**Verification**
- `make agentspace-verify` - Check status
- `make agent-engine-list` - List all engines

### Environment Variable Reference

See `.env.example` for complete documentation of all variables organized by stage.