# Makefile for Agentic SOC AgentSpace Management
.PHONY: help install setup clean deploy test agentspace-register agentspace-update agentspace-verify agentspace-delete agentspace-url oauth-setup oauth-create-auth oauth-verify oauth-delete

# Default environment file
ENV_FILE := .env

# Python executable (use venv if available)
PYTHON := $(shell if [ -d "venv" ]; then echo "venv/bin/python"; else echo "python3"; fi)

# Management scripts with consistent naming
MANAGE_AGENTSPACE := installation_scripts/manage_agentspace.py
MANAGE_AGENT_ENGINE := installation_scripts/manage_agent_engine.py
MANAGE_OAUTH := installation_scripts/manage_oauth.py

help: ## Show this help message
	@echo ""
	@echo "\033[1;34m╔══════════════════════════════════════════════════════════════════════════════╗\033[0m"
	@echo "\033[1;34m║                    Agentic SOC AgentSpace Management                         ║\033[0m"
	@echo "\033[1;34m╚══════════════════════════════════════════════════════════════════════════════╝\033[0m"
	@echo ""
	@echo "\033[1;32mSetup & Development\033[0m"
	@grep -E '^(setup|install|clean|check-env|lint|format):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; max=0} {if(length($$1)>max) max=length($$1)} END {print max}' > /tmp/max_width.tmp
	@grep -E '^(setup|install|clean|check-env|lint|format):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; getline max < "/tmp/max_width.tmp"; max+=5} {printf "  \033[36m%-*s\033[0m %s\n", max, $$1, $$2}'
	@echo ""
	@echo "\033[1;33mDeployment & Testing\033[0m"
	@grep -E '^(deploy|test|full-deploy|redeploy|oauth-workflow|full-deploy-with-oauth):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; max=0} {if(length($$1)>max) max=length($$1)} END {print max}' > /tmp/max_width.tmp
	@grep -E '^(deploy|test|full-deploy|redeploy|oauth-workflow|full-deploy-with-oauth):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; getline max < "/tmp/max_width.tmp"; max+=5} {printf "  \033[36m%-*s\033[0m %s\n", max, $$1, $$2}'
	@echo ""
	@echo "\033[1;35mAgentSpace Management\033[0m"
	@grep -E '^manage-agentspace-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; max=0} {if(length($$1)>max) max=length($$1)} END {print max}' > /tmp/max_width.tmp
	@grep -E '^manage-agentspace-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; getline max < "/tmp/max_width.tmp"; max+=5} {printf "  \033[36m%-*s\033[0m %s\n", max, $$1, $$2}'
	@echo ""
	@echo "\033[1;34mOAuth Management\033[0m"
	@grep -E '^oauth-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; max=0} {if(length($$1)>max) max=length($$1)} END {print max}' > /tmp/max_width.tmp
	@grep -E '^oauth-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; getline max < "/tmp/max_width.tmp"; max+=5} {printf "  \033[36m%-*s\033[0m %s\n", max, $$1, $$2}'
	@echo ""
	@echo "\033[1;31mAgent Engine Management\033[0m"
	@grep -E '^manage-agent-engine-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; max=0} {if(length($$1)>max) max=length($$1)} END {print max}' > /tmp/max_width.tmp
	@grep -E '^manage-agent-engine-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; getline max < "/tmp/max_width.tmp"; max+=5} {printf "  \033[36m%-*s\033[0m %s\n", max, $$1, $$2}'
	@echo ""
	@echo "\033[1;36mWorkflows & Utilities\033[0m"
	@grep -E '^(status|cleanup):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; max=0} {if(length($$1)>max) max=length($$1)} END {print max}' > /tmp/max_width.tmp
	@grep -E '^(status|cleanup):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "; getline max < "/tmp/max_width.tmp"; max+=5} {printf "  \033[36m%-*s\033[0m %s\n", max, $$1, $$2}'
	@echo ""
	@echo "\033[1;37mUsage Examples:\033[0m"
	@echo "  \033[33mmake setup\033[0m                           - Initialize project and install dependencies"
	@echo "  \033[33mmake full-deploy\033[0m                      - Complete deployment workflow"
	@echo "  \033[33mmake oauth-setup CLIENT_SECRET=path/to/client_secret.json\033[0m - Setup OAuth from client secret"
	@echo "  \033[33mmake oauth-workflow\033[0m                   - Create and verify OAuth authorization"
	@echo "  \033[33mmake full-deploy-with-oauth\033[0m           - Full deployment with OAuth integration"
	@echo "  \033[33mmake manage-agentspace-link-agent\033[0m     - Link agent to AgentSpace with OAuth"
	@echo "  \033[33mmake manage-agentspace-list-agents\033[0m    - List all agents in AgentSpace"
	@echo "  \033[33mmake manage-agent-engine-delete-by-index INDEX=1\033[0m - Delete agent by index"
	@echo "  \033[33mmake cleanup\033[0m                          - List and clean up old agents"
	@echo ""
	@echo "\033[1;37mNotes:\033[0m"
	@echo "  • Environment variables are loaded from \033[33m.env\033[0m file"
	@echo "  • Use \033[33mENV_FILE=path\033[0m to specify different environment file"
	@echo "  • Agent deletion requires \033[33mINDEX=number\033[0m or \033[33mRESOURCE=name\033[0m parameter"
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

deploy: ## Deploy the main agent engine
	$(PYTHON) main.py

deploy-and-delete: ## Deploy agent engine and delete after test (for development)
	$(PYTHON) main.py --delete

test: ## Test the deployed agent engine
	$(PYTHON) test_agent_engine.py

# AgentSpace management targets
manage-agentspace-register: ## Register agent with AgentSpace
	$(PYTHON) $(MANAGE_AGENTSPACE) register --env-file $(ENV_FILE)

manage-agentspace-register-force: ## Force re-register agent with AgentSpace
	$(PYTHON) $(MANAGE_AGENTSPACE) register --force --env-file $(ENV_FILE)

manage-agentspace-update: ## Update existing AgentSpace agent configuration
	$(PYTHON) $(MANAGE_AGENTSPACE) update --env-file $(ENV_FILE)

manage-agentspace-verify: ## Verify AgentSpace agent configuration and status
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

manage-agentspace-link-agent: ## Link deployed agent to AgentSpace with OAuth
	$(PYTHON) $(MANAGE_AGENTSPACE) link-agent --env-file $(ENV_FILE)

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
	$(PYTHON) $(MANAGE_OAUTH) create-auth --env-file $(ENV_FILE)

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