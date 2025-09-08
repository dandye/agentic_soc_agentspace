---
title: Google Cloud Security MCP Agent Documentation
description: Deployment guide for MCP security agents on Google Cloud
---

# Google MCP Security Agent

Documentation for deploying MCP security agents to Vertex AI Agent Engine and AgentSpace.

## What is this?

This repository documents the steps needed to:
- Deploy an agent with MCP security tools to Vertex AI Agent Engine
- Connect the deployed agent to AgentSpace for UI access
- Configure OAuth authentication for secure API access
- Integrate with Google Security products (Chronicle, SOAR, SCC)

## Components

- **Vertex AI Agent Engine**: Deployment target for the agent
- **MCP Security Tools**: Security product integrations via Model Context Protocol
- **AgentSpace**: UI for interacting with deployed agents
- **SOAR Integration**: Connection to Security Operations SOAR platform

## Documentation

### Getting Started
- [**Quick Start Guide**](./quick-start.md) - Deploy your first agent in minutes
- [Prerequisites](./prerequisites.md) - System requirements and setup
- [Installation](./installation.md) - Detailed installation instructions

### Core Concepts
- [Architecture Overview](./architecture.md) - How the system works
- [MCP Security Tools](./mcp-tools.md) - Available security integrations
- [Agent Engine Basics](./agent-engine.md) - Understanding Vertex AI agents

### Deployment Guides
- [Agent Engine Deployment](./deploy-agent-engine.md) - Step-by-step deployment
- [AgentSpace Setup](./agentspace-setup.md) - Configure the UI
- [OAuth Configuration](./oauth-setup.md) - Secure authentication

### Integration Guides
- [Chronicle Integration](./integrations/chronicle.md) - SIEM setup
- [SOAR Integration](./integrations/soar.md) - Automation workflows
- [Security Command Center](./integrations/scc.md) - Cloud security posture
- [Threat Intelligence](./integrations/threat-intel.md) - IOC analysis

### Operations
- [Managing Agents](./operations/manage-agents.md) - Lifecycle management
- [Monitoring & Logging](./operations/monitoring.md) - Observability
- [Scaling & Performance](./operations/scaling.md) - Production considerations
- [Backup & Recovery](./operations/backup.md) - Data protection

### Development
- [Adding Custom Tools](./development/custom-tools.md) - Extend functionality
- [Testing Agents](./development/testing.md) - Quality assurance
- [CI/CD Pipeline](./development/cicd.md) - Automation
- [API Reference](./api-reference.md) - Programmatic access

### Troubleshooting
- [Common Issues](./troubleshooting.md) - Quick fixes
- [FAQ](./faq.md) - Frequently asked questions
- [Support](./support.md) - Getting help

## Quick Links

- [GitHub Repository](https://github.com/your-org/agentic_soc_agentspace)
- [Google Cloud Console](https://console.cloud.google.com)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [MCP Protocol Specification](https://github.com/anthropics/mcp)

## System Requirements

- Google Cloud Project with billing enabled
- Python 3.10 or higher
- 4GB RAM minimum
- Network access to Google Cloud APIs

## Quick Start Example

```bash
# Clone the repository
git clone https://github.com/your-org/agentic_soc_agentspace.git
cd agentic_soc_agentspace

# Setup environment and install dependencies
make setup
# Edit .env with your configuration

# Complete deployment workflow
make full-deploy

# Or deploy with OAuth integration
make full-deploy-with-oauth
```

## Architecture Diagram

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   AgentSpace    │────▶│ Agent Engine │────▶│ MCP Tools   │
│   (UI Layer)    │     │  (AI Core)   │     │ (Security)  │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │                     │
                               ▼                     ▼
                        ┌──────────────┐     ┌─────────────┐
                        │   Vertex AI  │     │  Chronicle  │
                        │    Models    │     │  SOAR, SCC  │
                        └──────────────┘     └─────────────┘
```

## Support Matrix

| Component | Version | Status |
|-----------|---------|--------|
| Python | 3.10+ | Supported |
| Agent Engine | v1beta1 | Supported |
| AgentSpace | v1alpha | Supported |
| Chronicle | Latest | Supported |
| SOAR | Latest | Supported |
| Security Command Center | v1 | Supported |

