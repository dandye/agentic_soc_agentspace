---
title: Frequently Asked Questions
description: Common questions about MCP agent deployment
---

# Frequently Asked Questions

## General Questions

### What is the Google MCP Security Agent?

An agent deployed to Vertex AI Agent Engine that:
- Uses MCP protocol to connect to security tools
- Integrates with Google Security products (Chronicle, SOAR, SCC)
- Can be accessed through AgentSpace UI
- Supports automated workflows via SOAR

### What are the prerequisites?

- Google Cloud Project with billing enabled
- Python 3.10 or higher
- Access to Google Security products you want to integrate
- Appropriate IAM permissions

### How much does it cost?

Costs depend on usage:
- **Vertex AI**: Pay per API call and model usage
- **AgentSpace**: Included with Vertex AI
- **Storage**: Minimal costs for staging bucket
- **Security Products**: Separate licensing (Chronicle, SOAR)

### What is the current status?

- Agent Engine is GA (Generally Available)
- AgentSpace is in Preview (v1alpha)
- MCP tools are community-maintained
- Consider starting with non-critical workflows

## Setup Questions

### How long does setup take?

- Basic deployment: 10-15 minutes
- Full configuration with integrations: 1-2 hours
- Production setup: 1-2 days

### Can I use this without SOAR?

Yes. SOAR integration is optional. The agent works with:
- Chronicle SIEM only
- Security Command Center only
- Google Threat Intelligence only
- Any combination of the above

### Do I need OAuth setup?

OAuth is recommended but not required. Benefits include:
- Secure API access
- User-specific permissions
- Audit logging
- Token refresh handling

### Can I deploy multiple agents?

Yes. You can:
- Deploy multiple agents to different projects
- Have specialized agents for different tasks
- Share AgentSpace apps between agents
- Manage agents programmatically

## Technical Questions

### What AI models are used?

The agent uses Vertex AI's latest models:
- **Default**: Gemini Pro for reasoning
- **Configurable**: Can use any Vertex AI supported model
- **Context window**: Up to 1M tokens with Gemini 1.5

### How do I add custom tools?

1. Create your tool following MCP protocol
2. Add to the agent's tool configuration
3. Redeploy the agent
4. See [Adding Custom Tools](./development/custom-tools.md) guide

### Can I integrate with non-Google tools?

Yes, through:
- Custom MCP tool development
- REST API integrations
- Webhook connections
- Cloud Functions as middleware

### How do I handle sensitive data?

- Use Secret Manager for credentials
- Enable VPC Service Controls
- Implement data loss prevention policies
- Use private endpoints where available
- Enable audit logging

### What are the API rate limits?

Default limits:
- **Vertex AI**: 600 requests/minute
- **Chronicle**: 1000 requests/minute
- **SOAR**: Depends on license
- **AgentSpace**: 100 requests/second

Limits can be increased via quota requests.

## Operations Questions

### How do I monitor the agent?

- **Logs**: Cloud Logging (included)
- **Metrics**: Cloud Monitoring dashboards
- **Traces**: Cloud Trace for latency analysis
- **Alerts**: Configure via Monitoring policies

### How do I update the agent?

```bash
# Update code
git pull origin main

# Redeploy agent
make deploy

# Update AgentSpace configuration
make manage-agentspace-update
```

### Can I rollback deployments?

Yes:
1. Keep track of reasoning engine IDs
2. Use version tags in git
3. Redeploy previous version
4. Or use `manage_agent_engine.py` to switch agents

### How do I backup configurations?

```bash
# Backup environment
cp .env .env.backup

# Export agent configuration
make manage-agentspace-list-agents > agent_config.txt

# Backup to Cloud Storage
gsutil cp .env gs://your-backup-bucket/
```

## Security Questions

### What security considerations apply?

Key security points:
- Enable all security features
- Use least-privilege IAM
- Implement network restrictions
- Regular security audits
- Follow Google's security best practices

### What data is sent to AI models?

- Only data you explicitly query
- No automatic data collection
- Data stays within your Google Cloud project
- Subject to Vertex AI data governance

### Can I use this in regulated industries?

Yes, with compliance considerations:
- Enable appropriate compliance features
- Implement data residency requirements
- Configure audit logging
- Review with compliance team

### How are credentials managed?

- Service account keys (not recommended)
- Application Default Credentials (recommended)
- Workload Identity Federation (best)
- OAuth for user authentication
- Secret Manager for API keys

## Troubleshooting Questions

### Why is my agent not responding?

Common causes:
1. Agent not fully deployed (wait 2-3 minutes)
2. Missing permissions
3. Incorrect environment configuration
4. API quotas exceeded

See [Troubleshooting Guide](./troubleshooting.md)

### Why can't I see my agent in AgentSpace?

1. Verify registration: `manage_agentspace.py verify`
2. Check reasoning engine ID is correct
3. Ensure AgentSpace app exists
4. Re-link if necessary

### How do I debug MCP tool issues?

```bash
# Test tools individually
cd mcp-security/server
python -m secops_mcp test

# Check tool logs
gcloud logging read "mcp-security"
```

### Why am I getting permission errors?

Check IAM roles:
```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:${USER_EMAIL}"
```

## Best Practices

### Development

- Use separate projects for dev/staging/prod
- Implement CI/CD pipelines
- Write tests for custom tools
- Document all customizations

### Operations

- Monitor costs regularly
- Set up budget alerts
- Implement rate limiting
- Regular security reviews

### Performance

- Batch operations when possible
- Cache frequently accessed data
- Optimize tool selection
- Use appropriate model sizes

## Getting More Help

### Resources

- [Documentation](./index.md)
- [GitHub Repository](https://github.com/your-org/agentic_soc_agentspace)
- [Google Cloud Documentation](https://cloud.google.com/vertex-ai/docs)
- [MCP Protocol Docs](https://github.com/anthropics/mcp)

### Support Channels

- **GitHub Issues**: Bug reports and feature requests
- **Stack Overflow**: Tag with `vertex-ai` and `mcp`
- **Google Cloud Support**: For production issues
- **Community Forum**: Discussion and best practices

### Training

- Google Cloud Skills Boost
- Vertex AI Quickstarts
- Security Operations courses
- Custom training available

