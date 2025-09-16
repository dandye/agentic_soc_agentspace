---
title: Troubleshooting Guide
description: Solutions for common deployment and operation issues
---

# Troubleshooting Guide

Common issues and solutions for MCP agent deployment and operation.

## Deployment Issues

### Agent Engine Deployment Fails

**Error**: `Failed to create reasoning engine`

**Causes & Solutions**:

1. **Missing APIs**
   ```bash
   # Enable required APIs
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable discoveryengine.googleapis.com
   gcloud services enable storage.googleapis.com
   ```

2. **Insufficient Permissions**
   ```bash
   # Grant necessary roles to your service account
   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
     --member="user:your-email@domain.com" \
     --role="roles/aiplatform.user"
   
   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
     --member="user:your-email@domain.com" \
     --role="roles/discoveryengine.admin"
   ```

3. **Staging Bucket Issues**
   ```bash
   # Create staging bucket if it doesn't exist
   gsutil mb -p ${PROJECT_ID} -l ${LOCATION} gs://${STAGING_BUCKET}
   
   # Verify bucket permissions
   gsutil iam get gs://${STAGING_BUCKET}
   ```

### MCP Submodule Not Found

**Error**: `ModuleNotFoundError: No module named 'mcp-security'`

**Solution**:
```bash
# Initialize submodules
git submodule update --init --recursive

# Verify submodule status
git submodule status
```

### Environment Variables Not Loading

**Error**: `KeyError: 'PROJECT_ID'`

**Solution**:
```bash
# Ensure .env file exists
cp .env.example .env

# Verify file permissions
chmod 600 .env

# Test environment loading
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('PROJECT_ID'))"
```

## AgentSpace Issues

### Agent Not Appearing in AgentSpace

**Error**: Agent deployed but not visible in AgentSpace UI

**Solutions**:

1. **Verify Agent Registration**
   ```bash
   make agentspace-verify
   ```

2. **Check Resource Name Format**
   ```bash
   # Ensure AGENT_ENGINE_RESOURCE_NAME is correctly formatted
   echo $AGENT_ENGINE_RESOURCE_NAME
   # Should be: projects/{number}/locations/{location}/reasoningEngines/{id}
   ```

3. **Re-link Agent**
   ```bash
   make agentspace-link-agent
   ```

### Data Store Creation Fails

**Error**: `Engines with a single data store cannot add or remove data stores`

**Solution**:
This is expected behavior. Engines with existing data stores will use them for search.
```bash
# Verify data store status
make agentspace-datastore
```

### OAuth Authorization Errors

**Error**: `401 Unauthorized` when accessing AgentSpace

**Solutions**:

1. **Regenerate OAuth Token**
   ```bash
   make oauth-setup CLIENT_SECRET=client_secret.json
   ```

2. **Verify OAuth Configuration**
   ```bash
   make oauth-verify
   ```

3. **Check Token Expiry**
   ```bash
   # Refresh token if expired
   python installation_scripts/manage_oauth.py refresh
   ```

## Runtime Issues

### Agent Not Responding

**Symptoms**: Agent deployed but not responding to queries

**Diagnostic Steps**:

1. **Check Agent Status**
   ```bash
   V=1 make agent-engine-list
   ```

2. **View Logs**
   ```bash
   gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine AND resource.labels.reasoning_engine_id=${REASONING_ENGINE}" --limit 50
   ```

3. **Test Direct Query**
   ```python
   # test_direct.py
   import vertexai
   from vertexai import agent_engines
   
   vertexai.init(project=PROJECT_ID, location=LOCATION)
   agent = agent_engines.get(f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE}")
   response = agent.query(input="test")
   print(response)
   ```

### SOAR Connection Failures

**Error**: `Connection refused` or `SSL verification failed`

**Solutions**:

1. **Verify SOAR URL**
   ```bash
   # Test connectivity
   curl -I "${SOAR_URL}/api/external/v1/health"
   ```

2. **Check API Key**
   ```bash
   # Verify API key format
   echo $SOAR_APP_KEY | grep -E '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
   ```

3. **SSL Certificate Issues**
   ```python
   # For self-signed certificates (development only)
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   ```

### Memory/Resource Issues

**Error**: `ResourceExhausted` or agent becomes unresponsive

**Solutions**:

1. **Increase Quotas**
   ```bash
   # Check current quotas
   gcloud compute project-info describe --project=${PROJECT_ID}
   
   # Request quota increase via Console
   ```

2. **Optimize Agent Configuration**
   - Reduce concurrent tool calls
   - Implement rate limiting
   - Use batch operations where possible

## Common Error Messages

### API Errors

| Error Code | Message | Solution |
|------------|---------|----------|
| 403 | Permission denied | Check IAM roles and API enablement |
| 404 | Resource not found | Verify resource IDs and paths |
| 409 | Already exists | Resource already created, use update instead |
| 429 | Rate limit exceeded | Implement exponential backoff |
| 500 | Internal error | Retry with backoff, check service status |

### Python Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependency | Run `pip install -r requirements.txt` |
| `FileNotFoundError` | Missing config file | Check file paths and working directory |
| `KeyError` | Missing env variable | Verify .env file configuration |
| `ConnectionError` | Network issue | Check firewall and proxy settings |

## Debugging Tools

### Enable Verbose Logging

```python
# Add to your scripts
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Individual Components

```bash
# Test MCP tools
cd mcp-security/server
python -m secops_mcp test

# Test OAuth
python installation_scripts/manage_oauth.py test

# Test AgentSpace search
make agentspace-test
```

### Monitor Resources

```bash
# Watch agent logs in real-time
gcloud logging tail "resource.type=aiplatform.googleapis.com/ReasoningEngine"

# Monitor API usage
gcloud monitoring dashboards list
```

## Getting Help

If you encounter issues not covered here:

1. **Check Logs**
   - Application logs: `gcloud logging read`
   - Agent logs: Check Vertex AI console
   - System logs: `journalctl -xe`

2. **Gather Information**
   - Error messages and stack traces
   - Environment configuration
   - Steps to reproduce

3. **Contact Support**
   - GitHub Issues: [Report Issue](https://github.com/your-org/agentic_soc_agentspace/issues)
   - Google Cloud Support: [Console](https://console.cloud.google.com/support)
   - Community Forum: [Stack Overflow](https://stackoverflow.com/questions/tagged/vertex-ai)

## Preventive Measures

1. **Regular Backups**
   ```bash
   # Backup configuration
   cp .env .env.backup.$(date +%Y%m%d)
   ```

2. **Monitor Quotas**
   ```bash
   # Set up alerts for quota usage
   gcloud monitoring policies create --notification-channels=${CHANNEL_ID}
   ```

3. **Test Changes**
   - Use development environment first
   - Implement gradual rollouts
   - Maintain rollback procedures

