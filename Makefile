# Makefile for Agentic SOC AgentSpace Management

# Default target - must be first
.DEFAULT_GOAL := help

.PHONY: help install setup clean check-prereqs check-deploy check-integration \
	agent-engine-deploy agent-engine-deploy-and-delete agent-engine-test \
	agent-engine-list agent-engine-delete-by-index agent-engine-delete-by-resource agent-engine-redeploy \
	agent-engine-logs \
	agentspace-register agentspace-update agentspace-verify agentspace-delete \
	agentspace-url agentspace-test agentspace-datastore agentspace-link-agent agentspace-unlink-agent \
	agentspace-update-agent agentspace-list-agents agentspace-list-apps agentspace-create-app agentspace-redeploy \
	datastore-create datastore-list datastore-info datastore-delete \
	rag-list rag-info rag-create rag-delete \
	oauth-setup oauth-create-auth oauth-verify oauth-delete \
	redeploy-all oauth-workflow full-deploy-with-oauth status cleanup check-env lint format

# Default environment file
ENV_FILE ?= .env

# Verbosity control
V ?= 0
ifeq ($(V),1)
	VERBOSE := --verbose
	Q :=
else
	VERBOSE :=
	Q := @
endif

# Parallel jobs control
MAKEFLAGS += --no-print-directory

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
MANAGE_DATASTORE := installation_scripts/manage_datastore.py
MANAGE_RAG := installation_scripts/manage_rag.py

# Validation targets
.PHONY: check-prereqs check-deploy check-integration

check-prereqs: ## Validate Stage 1 prerequisites
	$(Q)if [ -z "$(GCP_PROJECT_ID)" ]; then echo "ERROR: GCP_PROJECT_ID not set in $(ENV_FILE)"; exit 1; fi
	$(Q)if [ -z "$(GCP_LOCATION)" ]; then echo "ERROR: GCP_LOCATION not set in $(ENV_FILE)"; exit 1; fi
	$(Q)if [ -z "$(GCP_STAGING_BUCKET)" ]; then echo "ERROR: GCP_STAGING_BUCKET not set in $(ENV_FILE)"; exit 1; fi
	$(Q)echo "Stage 1 prerequisites validated"

check-deploy: ## Validate Stage 2 deployment outputs
	@if [ -z "$(AGENT_ENGINE_RESOURCE_NAME)" ]; then echo "ERROR: AGENT_ENGINE_RESOURCE_NAME not set - run 'make agent-engine-deploy' first"; exit 1; fi
	@echo "Stage 2 deployment outputs validated"

check-integration: check-deploy ## Validate Stage 3 integration requirements
	@if [ -z "$(AGENTSPACE_APP_ID)" ]; then echo "WARNING: AGENTSPACE_APP_ID not set - required for AgentSpace operations"; fi
	@echo "Stage 3 integration requirements checked"

help: ## Show this help message
	@echo ""
	@echo "\033[1;34m╔══════════════════════════════════════════════════════════════════════════════╗\033[0m"
	@echo "\033[1;34m║                    Agentic SOC AgentSpace Management                         ║\033[0m"
	@echo "\033[1;34m╚══════════════════════════════════════════════════════════════════════════════╝\033[0m"
	@echo ""
	@echo "\033[1;32mSetup & Development\033[0m"
	@grep -h -E '^(setup|install|clean|lint|format):.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;31mAgent Engine Management\033[0m"
	@grep -h -E '^agent-engine-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;35mAgentSpace Management\033[0m"
	@grep -h -E '^agentspace-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;33mData Store Management\033[0m"
	@grep -h -E '^datastore-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;32mRAG Corpus Management\033[0m"
	@grep -h -E '^rag-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;34mOAuth Management\033[0m"
	@grep -h -E '^oauth-[^:]*:.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;36mWorkflows & Utilities\033[0m"
	@grep -h -E '^(status|cleanup|.*-redeploy|redeploy-all|full-deploy-with-oauth):.*?## .*$$' Makefile | sed 's/:.*##/##/' | awk 'BEGIN {FS = "##"} {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[1;37mUsage Examples:\033[0m"
	@echo "  \033[33mmake setup\033[0m                              - Initialize project and install dependencies"
	@echo "  \033[33mmake agent-engine-deploy\033[0m                - Deploy the agent engine"
	@echo "  \033[33mmake agent-engine-test\033[0m                  - Test the deployed agent"
	@echo "  \033[33mmake agentspace-register\033[0m                - Register agent with AgentSpace"
	@echo "  \033[33mFORCE=1 make agentspace-register\033[0m        - Force re-register agent with AgentSpace"
	@echo "  \033[33mmake agentspace-verify\033[0m                  - Check status and get URLs"
	@echo ""
	@echo "\033[1;37mNotes:\033[0m"
	@echo "  • Environment variables are loaded from \033[33m.env\033[0m file"
	@echo "  • Use \033[33mENV_FILE=path\033[0m to specify different environment file"
	@echo "  • Use \033[33mV=1\033[0m for verbose output (shows all commands and detailed script output)"
	@echo "  • Use \033[33mFORCE=1\033[0m with delete/register commands to skip confirmations"
	@echo "  • See docs/DEPLOYMENT_WORKFLOW.md for detailed instructions"
	@echo ""

install: ## Install Python dependencies
	$(PYTHON) -m pip install -r requirements.txt

setup: ## Set up environment and install dependencies
	$(Q)if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example $(ENV_FILE); \
		echo "Please edit $(ENV_FILE) with your configuration"; \
	fi
	$(Q)$(MAKE) install

clean: ## Clean up temporary files and cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

agent-engine-deploy: check-prereqs ## Deploy the main agent engine
	$(Q)$(PYTHON) main.py $(VERBOSE)
	$(Q)echo "========================================"
	$(Q)echo "DEPLOYMENT COMPLETE - Save these values to .env:"
	$(Q)echo "========================================"
	$(Q)echo "Check the output above for:"
	$(Q)echo "  AGENT_ENGINE_ID=<numeric_id>"
	$(Q)echo "  AGENT_ENGINE_RESOURCE_NAME=<full_resource_path>"
	$(Q)echo "========================================"

agent-engine-deploy-and-delete: ## Deploy agent engine and delete after test (for development)
	$(PYTHON) main.py --delete

agent-engine-test: check-deploy ## Test the deployed agent engine
	$(PYTHON) test_agent_engine.py

# AgentSpace management targets
agentspace-register: check-integration ## Register agent with AgentSpace (use FORCE=1 to force re-register)
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_AGENTSPACE) register --force --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_AGENTSPACE) register --env-file $(ENV_FILE); \
		echo "========================================"; \
		echo "REGISTRATION COMPLETE - Save this value to .env:"; \
		echo "========================================"; \
		echo "Check the output above for:"; \
		echo "  AGENTSPACE_AGENT_ID=<numeric_id>"; \
		echo "========================================"; \
	fi

agentspace-update: check-integration ## Update existing AgentSpace agent configuration
	$(PYTHON) $(MANAGE_AGENTSPACE) update --env-file $(ENV_FILE)

agentspace-verify: check-integration ## Verify AgentSpace agent configuration and status
	$(PYTHON) $(MANAGE_AGENTSPACE) verify --env-file $(ENV_FILE)

agentspace-delete: ## Delete agent from AgentSpace (use FORCE=1 to delete without confirmation)
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_AGENTSPACE) delete --force --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_AGENTSPACE) delete --env-file $(ENV_FILE); \
	fi

agentspace-url: ## Display AgentSpace UI URL
	$(PYTHON) $(MANAGE_AGENTSPACE) url --env-file $(ENV_FILE)

agentspace-test: ## Test AgentSpace search functionality (use: make agentspace-test QUERY="your query")
	@if [ -n "$(QUERY)" ]; then \
		$(PYTHON) $(MANAGE_AGENTSPACE) search --query "$(QUERY)" --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_AGENTSPACE) search --env-file $(ENV_FILE); \
	fi

agentspace-datastore: ## Ensure the AgentSpace engine has a data store configured
	$(PYTHON) $(MANAGE_AGENTSPACE) ensure-datastore --env-file $(ENV_FILE)

agentspace-link-agent: check-integration ## Link deployed agent to AgentSpace with OAuth
	@$(PYTHON) $(MANAGE_AGENTSPACE) link-agent --env-file $(ENV_FILE)
	@echo "========================================"
	@echo "AGENT LINK COMPLETE - Save this value to .env:"
	@echo "========================================"
	@echo "Check the output above for:"
	@echo "  AGENTSPACE_AGENT_ID=<numeric_id>"
	@echo "========================================"

agentspace-unlink-agent: ## Unlink agent from AgentSpace (use AGENT_ID=<id> for specific agent, FORCE=1 to skip confirmation)
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_AGENTSPACE) unlink-agent --force $(if $(AGENT_ID),--agent-id $(AGENT_ID)) --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_AGENTSPACE) unlink-agent $(if $(AGENT_ID),--agent-id $(AGENT_ID)) --env-file $(ENV_FILE); \
	fi

agentspace-update-agent: ## Update agent configuration in AgentSpace
	$(PYTHON) $(MANAGE_AGENTSPACE) update-agent-config --env-file $(ENV_FILE)

agentspace-list-agents: ## List all agents in AgentSpace app
	$(PYTHON) $(MANAGE_AGENTSPACE) list-agents --env-file $(ENV_FILE)

agentspace-list-apps: ## List all apps in AgentSpace collection
	$(PYTHON) $(MANAGE_AGENTSPACE) list-apps --env-file $(ENV_FILE)

agentspace-create-app: ## Create a new AgentSpace app (use: APP_NAME="My App" TYPE=SOLUTION_TYPE_SEARCH)
	@echo "Creating new AgentSpace app..."
	@echo "Options:"
	@echo "  APP_NAME='<name>' - App display name (default: agentic-soc-app)"
	@echo "  TYPE=<type> - Solution type (default: SOLUTION_TYPE_SEARCH)"
	@echo "  DATA_STORE=<id> - Data store ID to associate"
	@echo "  ENABLE_CHAT=1 - Enable chat features (for SOLUTION_TYPE_CHAT)"
	@$(PYTHON) $(MANAGE_AGENTSPACE) create-app \
		$(if $(APP_NAME),--name "$(APP_NAME)") \
		$(if $(TYPE),--type $(TYPE)) \
		$(if $(DATA_STORE),--data-store $(DATA_STORE)) \
		$(if $(filter 1,$(ENABLE_CHAT)),--enable-chat) \
		--env-file $(ENV_FILE)

# Data Store management targets
datastore-create: ## Create a new data store (use: NAME="My Store" TYPE=SOLUTION_TYPE_SEARCH)
	@echo "Creating new data store..."
	@echo "Options:"
	@echo "  NAME='<name>' - Data store display name (default: datastore)"
	@echo "  TYPE=<type> - Solution type (default: SOLUTION_TYPE_SEARCH)"
	@echo "  CONTENT=<config> - Content config (default: CONTENT_REQUIRED)"
	@echo "  INDUSTRY=<vertical> - Industry vertical (default: GENERIC)"
	@$(PYTHON) $(MANAGE_DATASTORE) create \
		$(if $(NAME),--name "$(NAME)") \
		$(if $(TYPE),--type $(TYPE)) \
		$(if $(CONTENT),--content $(CONTENT)) \
		$(if $(INDUSTRY),--industry $(INDUSTRY)) \
		--env-file $(ENV_FILE)

datastore-list: ## List all data stores in the project
	@$(PYTHON) $(MANAGE_DATASTORE) list --env-file $(ENV_FILE)

datastore-info: ## Get information about a specific data store (use: DATASTORE_ID=<id>)
	@if [ -z "$(DATASTORE_ID)" ]; then \
		echo "Error: DATASTORE_ID is required. Usage: make datastore-info DATASTORE_ID=<id>"; \
		exit 1; \
	fi
	@$(PYTHON) $(MANAGE_DATASTORE) info $(DATASTORE_ID) --env-file $(ENV_FILE)

datastore-delete: ## Delete a data store (use: DATASTORE_ID=<id> FORCE=1)
	@if [ -z "$(DATASTORE_ID)" ]; then \
		echo "Error: DATASTORE_ID is required. Usage: make datastore-delete DATASTORE_ID=<id>"; \
		exit 1; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_DATASTORE) delete $(DATASTORE_ID) --force --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_DATASTORE) delete $(DATASTORE_ID) --env-file $(ENV_FILE); \
	fi

# RAG Corpus management targets
rag-list: ## List all RAG corpora in the project (use V=1 for verbose output)
	@$(PYTHON) $(MANAGE_RAG) list $(VERBOSE) --env-file $(ENV_FILE)

rag-info: ## Get information about a specific RAG corpus (use: RAG_CORPUS_NAME=<resource_name>)
	@if [ -z "$(RAG_CORPUS_NAME)" ]; then \
		echo "Error: RAG_CORPUS_NAME is required. Usage: make rag-info RAG_CORPUS_NAME=<resource_name>"; \
		exit 1; \
	fi
	@$(PYTHON) $(MANAGE_RAG) info $(RAG_CORPUS_NAME) --env-file $(ENV_FILE)

rag-create: ## Create a new RAG corpus (use: NAME="Corpus Name" DESC="Description")
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required. Usage: make rag-create NAME='My Corpus' DESC='Optional description'"; \
		exit 1; \
	fi
	@$(PYTHON) $(MANAGE_RAG) create "$(NAME)" \
		$(if $(DESC),--description "$(DESC)") \
		$(if $(EMBEDDING_MODEL),--embedding-model $(EMBEDDING_MODEL)) \
		--env-file $(ENV_FILE)

rag-delete: ## Delete a RAG corpus (use: RAG_CORPUS_NAME=<resource_name> FORCE=1)
	@if [ -z "$(RAG_CORPUS_NAME)" ]; then \
		echo "Error: RAG_CORPUS_NAME is required. Usage: make rag-delete RAG_CORPUS_NAME=<resource_name>"; \
		exit 1; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_RAG) delete $(RAG_CORPUS_NAME) --force --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_RAG) delete $(RAG_CORPUS_NAME) --env-file $(ENV_FILE); \
	fi

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

oauth-delete: ## Remove OAuth authorization (use FORCE=1 to delete without confirmation)
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_OAUTH) delete --force --env-file $(ENV_FILE); \
	else \
		$(PYTHON) $(MANAGE_OAUTH) delete --env-file $(ENV_FILE); \
	fi

# Agent Engine management targets
agent-engine-list: ## List all Agent Engine instances (use V=1 for detailed output)
	$(PYTHON) $(MANAGE_AGENT_ENGINE) list $(VERBOSE)

agent-engine-delete-by-index: ## Delete Agent Engine instance by index (use: make agent-engine-delete-by-index INDEX=1, add FORCE=1 to skip confirmation)
	@if [ -z "$(INDEX)" ]; then \
		echo "Error: INDEX is required. Usage: make agent-engine-delete-by-index INDEX=1"; \
		exit 1; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --index $(INDEX) --force; \
	else \
		$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --index $(INDEX); \
	fi

agent-engine-delete-by-resource: ## Delete Agent Engine instance by resource name (use: make agent-engine-delete-by-resource RESOURCE=..., add FORCE=1 to skip confirmation)
	@if [ -z "$(RESOURCE)" ]; then \
		echo "Error: RESOURCE is required. Usage: make agent-engine-delete-by-resource RESOURCE=projects/.../reasoningEngines/..."; \
		exit 1; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
		$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --resource $(RESOURCE) --force; \
	else \
		$(PYTHON) $(MANAGE_AGENT_ENGINE) delete --resource $(RESOURCE); \
	fi

# Workflow targets
agent-engine-redeploy: agent-engine-deploy ## Redeploy the agent engine
	@echo "Agent engine redeployment completed successfully!"

agent-engine-logs: ## Get logs for a specific agent engine (requires: AGENT_ENGINE_RESOURCE_NAME in .env)
ifndef AGENT_ENGINE_RESOURCE_NAME
	$(error AGENT_ENGINE_RESOURCE_NAME is required. Set it in your .env file or run agent-engine-deploy first)
endif
	$(eval ENGINE_ID := $(shell echo $(AGENT_ENGINE_RESOURCE_NAME) | rev | cut -d'/' -f1 | rev))
	gcloud logging read 'resource.labels.reasoning_engine_id="$(ENGINE_ID)"' \
		--project=$(GCP_PROJECT_ID) \
		--format="table(timestamp,severity,textPayload)" \
		--freshness=10m \
		--order=desc

agentspace-redeploy: agentspace-update ## Update AgentSpace configuration
	@echo "AgentSpace configuration update completed successfully!"

redeploy-all: agent-engine-deploy agentspace-update ## Redeploy agent engine and update AgentSpace
	@echo "Full redeployment completed successfully!"

oauth-workflow: oauth-create-auth oauth-verify ## Complete OAuth setup (create auth and verify)
	@echo "OAuth authorization setup completed successfully!"

full-deploy-with-oauth: setup agent-engine-deploy oauth-workflow agentspace-link-agent ## Deploy agent with OAuth and link to AgentSpace
	@echo "Full deployment with OAuth completed successfully!"

status: agentspace-verify ## Check status of AgentSpace registration
	@echo "Status check completed!"

cleanup: agent-engine-list ## List agents and interactively clean up old instances
	@echo "Use the agent index numbers shown above with 'make agent-engine-delete-by-index INDEX=<number>' to clean up"

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