# Makefile for Agentic SOC AgentSpace Management

# Default target - must be first
.DEFAULT_GOAL := help

.PHONY: help install setup clean deploy test agentspace-register agentspace-update agentspace-verify agentspace-delete agentspace-url oauth-setup oauth-create-auth oauth-verify oauth-delete

# Default environment file
ENV_FILE := .env

# Load environment variables if .env exists
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
export
endif

# Python executable (use venv if available)
PYTHON := $(shell if [ -d "venv" ]; then echo "venv/bin/python"; else echo "python3"; fi)

# Management scripts with consistent naming
MANAGE_AGENTSPACE := installation_scripts/manage_agentspace.py
MANAGE_AGENT_ENGINE := installation_scripts/manage_agent_engine.py
MANAGE_OAUTH := installation_scripts/manage_oauth.py

# Validation targets
.PHONY: check-prereqs check-deploy check-integration

check-prereqs: ## Validate Stage 1 prerequisites
	@if [ -z "$(PROJECT_ID)" ]; then echo "ERROR: PROJECT_ID not set in $(ENV_FILE)"; exit 1; fi
	@if [ -z "$(PROJECT_NUMBER)" ]; then echo "ERROR: PROJECT_NUMBER not set in $(ENV_FILE)"; exit 1; fi
	@if [ -z "$(LOCATION)" ]; then echo "ERROR: LOCATION not set in $(ENV_FILE)"; exit 1; fi
	@if [ -z "$(STAGING_BUCKET)" ]; then echo "ERROR: STAGING_BUCKET not set in $(ENV_FILE)"; exit 1; fi
	@if [ -z "$(GOOGLE_API_KEY)" ]; then echo "ERROR: GOOGLE_API_KEY not set in $(ENV_FILE)"; exit 1; fi
	@echo "Stage 1 prerequisites validated"

check-deploy: ## Validate Stage 2 deployment outputs
	@if [ -z "$(REASONING_ENGINE)" ]; then echo "ERROR: REASONING_ENGINE not set - run 'make deploy' first"; exit 1; fi
	@if [ -z "$(AGENT_ENGINE_RESOURCE_NAME)" ]; then echo "ERROR: AGENT_ENGINE_RESOURCE_NAME not set - run 'make deploy' first"; exit 1; fi
	@echo "Stage 2 deployment outputs validated"

check-integration: check-deploy ## Validate Stage 3 integration requirements
	@if [ -z "$(AGENTSPACE_APP_ID)" ]; then echo "WARNING: AGENTSPACE_APP_ID not set - required for AgentSpace operations"; fi
	@echo "Stage 3 integration requirements checked"

help: ## Show this help message
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════════════════╗"
	@echo "║                    Agentic SOC AgentSpace Management                         ║"
	@echo "╚══════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup & Development"
	@grep -h -E '^(setup|install|clean|lint|format):.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  %-30s %s\n", $$1, $$2}'
	@echo ""
	@echo "Deployment & Testing"
	@grep -h -E '^(deploy|test|full-deploy):.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  %-30s %s\n", $$1, $$2}'
	@echo ""
	@echo "AgentSpace Management"
	@grep -h -E '^manage-agentspace-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  %-40s %s\n", $$1, $$2}'
	@echo ""
	@echo "OAuth Management"
	@grep -h -E '^oauth-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  %-30s %s\n", $$1, $$2}'
	@echo ""
	@echo "Agent Engine Management"
	@grep -h -E '^manage-agent-engine-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  %-45s %s\n", $$1, $$2}'
	@echo ""
	@echo "Workflows & Utilities"
	@grep -h -E '^(status|cleanup|redeploy|full-deploy-with-oauth):.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  %-30s %s\n", $$1, $$2}'
	@echo ""
	@echo "Usage Examples:"
	@echo "  make setup                    - Initialize project and install dependencies"
	@echo "  make deploy                   - Deploy the agent engine"
	@echo "  make test                     - Test the deployed agent"
	@echo "  make manage-agentspace-register - Register agent with AgentSpace"
	@echo "  make manage-agentspace-verify  - Check status and get URLs"
	@echo ""
	@echo "Notes:"
	@echo "  • Environment variables are loaded from .env file"
	@echo "  • Use ENV_FILE=path to specify different environment file"
	@echo "  • See docs/DEPLOYMENT_WORKFLOW.md for detailed instructions"
	@echo ""

install: ## Install Python dependencies
	$(PYTHON) -m pip install -r requirements.txt

setup: ## Set up environment and install dependencies
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example $(ENV_FILE); \
		echo "Please edit $(ENV_FILE) with your configuration"; \
	fi
	@$(MAKE) install

clean: ## Clean up temporary files and cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

deploy: check-prereqs ## Deploy the main agent engine
	@$(PYTHON) main.py
	@echo "========================================"
	@echo "DEPLOYMENT COMPLETE - Save these values to .env:"
	@echo "========================================"
	@echo "Check the output above for:"
	@echo "  REASONING_ENGINE=<numeric_id>"
	@echo "  AGENT_ENGINE_RESOURCE_NAME=<full_resource_path>"
	@echo "========================================"

deploy-and-delete: ## Deploy agent engine and delete after test (for development)
	$(PYTHON) main.py --delete

test: check-deploy ## Test the deployed agent engine
	$(PYTHON) test_agent_engine.py

# AgentSpace management targets
manage-agentspace-register: check-integration ## Register agent with AgentSpace
	@$(PYTHON) $(MANAGE_AGENTSPACE) register --env-file $(ENV_FILE)
	@echo "========================================"
	@echo "REGISTRATION COMPLETE - Save this value to .env:"
	@echo "========================================"
	@echo "Check the output above for:"
	@echo "  AGENTSPACE_AGENT_ID=<numeric_id>"
	@echo "========================================"

manage-agentspace-register-force: ## Force re-register agent with AgentSpace
	$(PYTHON) $(MANAGE_AGENTSPACE) register --force --env-file $(ENV_FILE)

manage-agentspace-update: check-integration ## Update existing AgentSpace agent configuration
	$(PYTHON) $(MANAGE_AGENTSPACE) update --env-file $(ENV_FILE)

manage-agentspace-verify: check-integration ## Verify AgentSpace agent configuration and status
	$(PYTHON) $(MANAGE_AGENTSPACE) verify --env-file $(ENV_FILE)

manage-agentspace-delete: ## Delete agent from AgentSpace
	$(PYTHON) $(MANAGE_AGENTSPACE) delete --env-file $(ENV_FILE)

manage-agentspace-delete-force: ## Force delete agent from AgentSpace without confirmation
	$(PYTHON) $(MANAGE_AGENTSPACE) delete --force --env-file $(ENV_FILE)

manage-agentspace-url: ## Display AgentSpace UI URL
	$(PYTHON) $(MANAGE_AGENTSPACE) url --env-file $(ENV_FILE)

manage-agentspace-test: ## Test AgentSpace search functionality (use: make manage-agentspace-test QUERY="your query")
	@if [ -n "$(QUERY)" ]; then \
		$(PYTHON) $(MANAGE_AGENTSPACE) search --query "$(QUERY)" --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_AGENTSPACE) search --env-file $(ENV_FILE); \
	fi

manage-agentspace-datastore: ## Ensure the AgentSpace engine has a data store configured
	$(PYTHON) $(MANAGE_AGENTSPACE) ensure-datastore --env-file $(ENV_FILE)

manage-agentspace-link-agent: check-integration ## Link deployed agent to AgentSpace with OAuth
	@$(PYTHON) $(MANAGE_AGENTSPACE) link-agent --env-file $(ENV_FILE)
	@echo "========================================"
	@echo "AGENT LINK COMPLETE - Save this value to .env:"
	@echo "========================================"
	@echo "Check the output above for:"
	@echo "  AGENTSPACE_AGENT_ID=<numeric_id>"
	@echo "========================================"

manage-agentspace-update-agent: ## Update agent configuration in AgentSpace
	$(PYTHON) $(MANAGE_AGENTSPACE) update-agent-config --env-file $(ENV_FILE)

manage-agentspace-list-agents: ## List all agents in AgentSpace app
	$(PYTHON) $(MANAGE_AGENTSPACE) list-agents --env-file $(ENV_FILE)

# OAuth management targets
oauth-setup: ## Interactive OAuth client setup from client_secret.json (use: make oauth-setup CLIENT_SECRET=path/to/client_secret.json)
	@if [ -z "$(CLIENT_SECRET)" ]; then \
		echo "Error: CLIENT_SECRET is required. Usage: make oauth-setup CLIENT_SECRET=path/to/client_secret.json"; \
		exit 1; \
	fi
	$(PYTHON) $(MANAGE_OAUTH) setup $(CLIENT_SECRET) --env-file $(ENV_FILE)

oauth-create-auth: ## Create OAuth authorization in Discovery Engine
	@$(PYTHON) $(MANAGE_OAUTH) create-auth --env-file $(ENV_FILE)
	@echo "========================================"
	@echo "OAUTH SETUP COMPLETE - Save this value to .env:"
	@echo "========================================"
	@echo "Check the output above for:"
	@echo "  OAUTH_AUTH_ID=<auth_id>"
	@echo "========================================"

oauth-verify: ## Check OAuth authorization status
	$(PYTHON) $(MANAGE_OAUTH) verify --env-file $(ENV_FILE)

oauth-delete: ## Remove OAuth authorization
	$(PYTHON) $(MANAGE_OAUTH) delete --env-file $(ENV_FILE)

oauth-delete-force: ## Force delete OAuth authorization without confirmation
	$(PYTHON) $(MANAGE_OAUTH) delete --force --env-file $(ENV_FILE)

# Agent Engine management targets
manage-agent-engine-list: ## List all Agent Engine instances
	$(PYTHON) $(MANAGE_AGENT_ENGINE) list

manage-agent-engine-list-verbose: ## List all Agent Engine instances with verbose output
	$(PYTHON) $(MANAGE_AGENT_ENGINE) list --verbose

manage-agent-engine-delete-by-index: ## Delete Agent Engine instance by index (use: make manage-agent-engine-delete-by-index INDEX=1)
	@if [ -z "$(INDEX)" ]; then \
		echo "Error: INDEX is required. Usage: make manage-agent-engine-delete-by-index INDEX=1"; \
		exit 1; \
	fi
	$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --index $(INDEX)

manage-agent-engine-delete-by-resource: ## Delete Agent Engine instance by resource name (use: make manage-agent-engine-delete-by-resource RESOURCE=...)
	@if [ -z "$(RESOURCE)" ]; then \
		echo "Error: RESOURCE is required. Usage: make manage-agent-engine-delete-by-resource RESOURCE=projects/.../reasoningEngines/..."; \
		exit 1; \
	fi
	$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --resource $(RESOURCE)

manage-agent-engine-delete-force: ## Force delete Agent Engine instance by index without confirmation (use: make manage-agent-engine-delete-force INDEX=1)
	@if [ -z "$(INDEX)" ]; then \
		echo "Error: INDEX is required. Usage: make manage-agent-engine-delete-force INDEX=1"; \
		exit 1; \
	fi
	$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --index $(INDEX) --force

# Workflow targets
full-deploy: setup deploy manage-agentspace-register ## Complete deployment workflow: setup, deploy, and register
	@echo "Full deployment completed successfully!"

redeploy: deploy manage-agentspace-update ## Redeploy and update existing agent
	@echo "Redeployment completed successfully!"

oauth-workflow: oauth-create-auth oauth-verify ## Complete OAuth setup (create auth and verify)
	@echo "OAuth authorization setup completed successfully!"

full-deploy-with-oauth: setup deploy oauth-workflow manage-agentspace-link-agent ## Deploy agent with OAuth and link to AgentSpace
	@echo "Full deployment with OAuth completed successfully!"

status: manage-agentspace-verify ## Check status of AgentSpace registration
	@echo "Status check completed!"

cleanup: manage-agent-engine-list ## List agents and interactively clean up old instances
	@echo "Use the agent index numbers shown above with 'make manage-agent-engine-delete-by-index INDEX=<number>' to clean up"

# Development targets
check-env: ## Check if required environment variables are set
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Error: $(ENV_FILE) not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Environment file $(ENV_FILE) exists"

lint: ## Run code linting (if available)
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Running ruff linting..."; \
		ruff check .; \
	elif command -v flake8 >/dev/null 2>&1; then \
		echo "Running flake8 linting..."; \
		flake8 .; \
	else \
		echo "No linter available (install ruff or flake8)"; \
	fi

format: ## Format code (if available)
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Running ruff formatting..."; \
		ruff format .; \
	elif command -v black >/dev/null 2>&1; then \
		echo "Running black formatting..."; \
		black .; \
	else \
		echo "No formatter available (install ruff or black)"; \
	fi