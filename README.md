# Google Cloud AI Agent with MCP Security Tools

Deployment code and documentation for running MCP security agents on Google Vertex AI Agent Engine.

## Overview

This repository contains the code needed to deploy AI agents with MCP security tool access to Google Cloud. The agents can interact with Google Security Operations (Chronicle), SOAR platforms, Google Threat Intelligence, and Security Command Center through the Model Context Protocol.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   main.py       │───▶│  Vertex AI       │───▶│   MCP Security      │
│   Agent Creator │    │  Agent Engine    │    │   Tools (stdio)     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                               │                        │
┌─────────────────┐            │                ┌───────▼───────┐
│test_agent_engine│◀───────────┘                │ • Chronicle   │
│    Testing      │                             │ • SOAR        │
└─────────────────┘                             │ • GTI         │
                                                │ • SCC         │
                                                └───────────────┘
```

## Prerequisites

- Google Cloud Project with the following APIs enabled:
  - Vertex AI API
  - Agent Builder API
  - Security Command Center API (optional)
- Google Cloud authentication configured (gcloud CLI or service account)
- Python 3.11+
- Access to Google Security Operations (Chronicle) and/or SOAR platform

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/agentic_soc_agentspace.git
   cd agentic_soc_agentspace
   ```

2. **Initialize submodules**:
   ```bash
   git submodule update --init --recursive
   ```

3. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Set up authentication**:
   ```bash
   gcloud auth application-default login
   ```

## Configuration

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure your environment variables**:
   ```bash
   # Required Google Cloud settings
   PROJECT_ID=your-project-name
   LOCATION=us-central1
   STAGING_BUCKET=gs://your-staging-bucket
   PROJECT_NUMBER=1234567890123

   # SOAR Configuration (if using SOAR tools)
   SOAR_URL=https://your-instance.siemplify-soar.com:443
   SOAR_APP_KEY=your-soar-api-key

   # For testing existing agents
   REASONING_ENGINE=deployed-engine-id
   ```

## Usage

### Quick Start

```bash
# Setup and deploy
make setup
make full-deploy

# Or with OAuth
make full-deploy-with-oauth
```

### Deploying a New Agent

```bash
make deploy
```

This will:
- Create a Vertex AI agent with MCP security toolsets
- Deploy it to Google Cloud Agent Engines
- Install required dependencies via the installation script
- Return a reasoning engine ID for future testing

### Testing an Existing Agent

```bash
make test
```

This connects to an existing agent using the `REASONING_ENGINE` ID from your environment.

## MCP Security Tools

This project integrates with the [Google MCP Security](https://github.com/google/mcp-security) toolset, which includes:

- **SecOps MCP**: Chronicle SIEM integration for threat detection and investigation
- **SOAR MCP**: Security orchestration, automation, and response workflows
- **GTI MCP**: Google Threat Intelligence for IOC analysis and threat research
- **SCC MCP**: Security Command Center for cloud security posture management

Each tool runs as an independent MCP server accessed via stdio transport.

## Development

### Project Structure

```
├── main.py                    # Agent creation and deployment
├── test_agent_engine.py       # Testing interface for deployed agents
├── requirements.txt           # Python dependencies
├── installation_scripts/
│   └── install.sh            # Cloud deployment setup script
├── mcp-security/             # Git submodule with MCP security servers
└── .env.example              # Environment configuration template
```

### Adding New MCP Tools

To integrate additional MCP tools:

1. Add the MCP server configuration to the `MCPToolset` in `main.py`
2. Update the `extra_packages` list with the new server path
3. Modify the installation script if additional dependencies are required

### Customizing Agent Behavior

Modify the agent instructions in `main.py`:

```python
root_agent = Agent(
    model="gemini-2.5-flash",
    name="your_agent_name",
    description="Your agent description",
    instruction="Custom instructions for your specific use case",
    tools=[your_toolsets]
)
```

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure Google Cloud authentication is properly configured
2. **MCP tool failures**: Check that the MCP security submodule is properly initialized
3. **Deployment timeouts**: Increase timeout values in the agent configuration
4. **Environment variables**: Verify all required environment variables are set

### Debugging MCP Connections

Test MCP tools locally:
```bash
uv --directory "./mcp-security/server/secops/secops_mcp" run server.py
```

### Logs and Monitoring

Monitor agent performance in Google Cloud Console:
- Navigate to Vertex AI → Agent Builder → Your Agent
- Check logs in Cloud Logging for detailed error information

## See Also

- [Google MCP Security](https://github.com/google/mcp-security) - MCP security tool implementations
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs) - Google Cloud AI platform documentation