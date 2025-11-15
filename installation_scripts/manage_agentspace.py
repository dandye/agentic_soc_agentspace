#!/usr/bin/env python3
"""
AgentSpace Manager for Google MCP Security Agent

This script manages AgentSpace operations including registration, updates,
verification, and deletion of agents in AgentSpace.
"""

import os
from pathlib import Path
from typing import Annotated, Any

import google.auth
import requests
import typer
from dotenv import load_dotenv
from google.auth.transport import requests as google_requests


app = typer.Typer(
    add_completion=False,
    help="Manage AgentSpace operations for the Google MCP Security Agent.",
)

DISCOVERY_ENGINE_API_BASE = "https://discoveryengine.googleapis.com/v1alpha"
# Note: Using v1alpha as per notebook example, though agents endpoint may not exist for all apps

"""
https://cloud.google.com/agentspace/docs/reference/rest/v1/SolutionType

SOLUTION_TYPE_UNSPECIFIED	Default value.
SOLUTION_TYPE_RECOMMENDATION	Used for Recommendations AI.
SOLUTION_TYPE_SEARCH	Used for Discovery Search.
SOLUTION_TYPE_CHAT	Used for use cases related to the Generative AI agent.
SOLUTION_TYPE_GENERATIVE_CHAT	Used for use cases related to the Generative Chat agent. It's used for Generative chat engine only, the associated data stores must enrolled with SOLUTION_TYPE_CHAT solution.
"""


class AgentSpaceManager:
    """Manages AgentSpace configuration and operations."""

    def __init__(self, env_file: Path):
        """
        Initialize the AgentSpace manager.

        Args:
            env_file: Path to the environment file.
        """
        self.env_file = env_file
        self.env_vars = self._load_env_vars()
        self.creds, self.project = google.auth.default()

    def _load_env_vars(self) -> dict[str, str]:
        """Load environment variables from the .env file using python-dotenv."""
        # Load .env file into environment
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)

        # Get all environment variables (includes both .env and system env vars)
        # dotenv handles quotes, comments, and spaces properly
        env_vars = dict(os.environ)
        return env_vars

    def _update_env_var(self, key: str, value: str) -> None:
        """Update an environment variable in the .env file."""
        if not self.env_file.exists():
            self.env_file.touch()

        lines = []
        if self.env_file.exists():
            with open(self.env_file) as f:
                lines = f.readlines()

        # Find existing key or add new one
        key_found = False
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                existing_key = line.split("=", 1)[0].strip()
                if existing_key == key:
                    lines[i] = f"{key}={value}\n"
                    key_found = True
                    break

        if not key_found:
            lines.append(f"{key}={value}\n")

        with open(self.env_file, "w") as f:
            f.writelines(lines)

        # Update in-memory env_vars
        self.env_vars[key] = value

    def _get_access_token(self) -> str | None:
        """Get Google Cloud access token."""
        if not self.creds.valid:
            self.creds.refresh(google_requests.Request())
        return self.creds.token

    def _validate_environment(self) -> tuple[bool, list]:
        """Validate required environment variables for AgentSpace operations."""
        required_vars = [
            "GCP_PROJECT_ID",
            "GCP_PROJECT_NUMBER",
            "AGENTSPACE_APP_ID",
            "AGENT_ENGINE_RESOURCE_NAME",
            "GCP_LOCATION",
        ]
        missing = [var for var in required_vars if not self.env_vars.get(var)]
        return not missing, missing

    def _make_request(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response | None:
        """Make an authenticated request to the Discovery Engine API."""
        access_token = self._get_access_token()
        if not access_token:
            return None

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.env_vars["GCP_PROJECT_NUMBER"],
        }
        headers.update(kwargs.pop("headers", {}))

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            typer.secho(f" API request failed: {e}", fg=typer.colors.RED)
            if e.response is not None:
                typer.echo(f"  Response: {e.response.text}")
            return None

    def _get_agent_api_url(self, agent_id: str | None = None) -> str:
        """Construct the API URL for AgentSpace agents."""
        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        app_id = self.env_vars["AGENTSPACE_APP_ID"]
        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")
        assistant = self.env_vars.get("AGENTSPACE_ASSISTANT", "default_assistant")

        url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines/{app_id}/"
            f"assistants/{assistant}/agents"
        )
        if agent_id:
            url += f"/{agent_id}"
        return url

    def _build_agent_config(self) -> dict[str, Any]:
        """Build the agent configuration payload."""
        config = {
            "displayName": self.env_vars.get(
                "AGENT_DISPLAY_NAME", "Google Security Agent"
            ),
            "description": self.env_vars.get(
                "AGENT_DESCRIPTION",
                "Allows security operations on Google Security Products",
            ),
            "adk_agent_definition": {
                "tool_settings": {
                    "tool_description": self.env_vars.get(
                        "AGENT_TOOL_DESCRIPTION",
                        "Various Tools from SIEM, SOAR and SCC",
                    )
                },
                "provisioned_reasoning_engine": {
                    "reasoning_engine": self.env_vars["AGENT_ENGINE_RESOURCE_NAME"]
                },
            },
        }
        if oauth_auth_id := self.env_vars.get("OAUTH_AUTH_ID"):
            config["adk_agent_definition"]["authorizations"] = [
                f"projects/{self.env_vars['GCP_PROJECT_NUMBER']}/locations/global/authorizations/{oauth_auth_id}"
            ]
        else:
            config["adk_agent_definition"]["authorizations"] = []
        return config

    def register_agent(self, force: bool = False) -> bool:
        """Register agent with AgentSpace."""
        typer.echo("Registering agent with AgentSpace...")
        is_valid, missing = self._validate_environment()
        if not is_valid:
            typer.secho(
                f" Missing required variables: {', '.join(missing)}",
                fg=typer.colors.RED,
            )
            return False

        if self.env_vars.get("AGENTSPACE_AGENT_ID") and not force:
            typer.secho(
                " Agent already registered. Use --force to re-register.",
                fg=typer.colors.YELLOW,
            )
            return False

        api_url = self._get_agent_api_url()
        agent_config = self._build_agent_config()

        access_token = self._get_access_token()
        if not access_token:
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.env_vars["GCP_PROJECT_NUMBER"],
        }

        try:
            response = requests.post(api_url, headers=headers, json=agent_config)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            typer.secho(f" API request failed: {e}", fg=typer.colors.RED)
            if e.response is not None:
                typer.echo(f"  Response: {e.response.text}")
            return False
        if response and response.status_code == 200:
            result = response.json()
            agent_name = result.get("name", "")
            agent_id = agent_name.split("/")[-1] if agent_name else ""
            typer.secho(" Agent registered successfully!", fg=typer.colors.GREEN)
            typer.echo(f"  Agent Name: {agent_name}")
            typer.echo(f"  Agent ID: {agent_id}")
            if agent_id:
                self._update_env_var("AGENTSPACE_AGENT_ID", agent_id)
            return True
        return False

    def update_agent(self) -> bool:
        """Update existing AgentSpace agent configuration."""
        typer.echo("Updating AgentSpace agent...")
        agent_id = self.env_vars.get("AGENTSPACE_AGENT_ID")
        if not agent_id:
            typer.secho(
                " No agent registered yet. Run 'register' first.", fg=typer.colors.RED
            )
            return False

        api_url = self._get_agent_api_url(agent_id)
        agent_config = self._build_agent_config()

        response = self._make_request("PATCH", api_url, json=agent_config)
        if response and response.status_code == 200:
            typer.secho(" Agent updated successfully!", fg=typer.colors.GREEN)
            return True
        return False

    def verify_agent(self) -> bool:
        """Verify AgentSpace agent configuration and status."""
        typer.echo("Verifying AgentSpace configuration...")
        is_valid, missing = self._validate_environment()
        if not is_valid:
            typer.secho(
                f" Missing required variables: {', '.join(missing)}",
                fg=typer.colors.RED,
            )
            return False

        agent_id = self.env_vars.get("AGENTSPACE_AGENT_ID")
        if not agent_id:
            typer.secho(" No agent registered yet.", fg=typer.colors.YELLOW)
            return False

        api_url = self._get_agent_api_url(agent_id)
        response = self._make_request("GET", api_url)
        if response and response.status_code == 200:
            typer.secho(
                " AgentSpace agent verified successfully!", fg=typer.colors.GREEN
            )
            return True
        return False

    def delete_agent(self, force: bool = False) -> bool:
        """Delete agent from AgentSpace."""
        agent_id = self.env_vars.get("AGENTSPACE_AGENT_ID")
        if not agent_id:
            typer.secho(" No agent registered to delete.", fg=typer.colors.RED)
            return True

        if not force and not typer.confirm(
            f"Are you sure you want to delete agent {agent_id}?"
        ):
            typer.echo("Cancelled.")
            return False

        api_url = self._get_agent_api_url(agent_id)
        response = self._make_request("DELETE", api_url)
        if response and response.status_code in [200, 204]:
            typer.secho(" Agent deleted successfully!", fg=typer.colors.GREEN)
            self._update_env_var("AGENTSPACE_AGENT_ID", "")
            return True
        return False

    def create_app(
        self,
        app_name: str | None = None,
        solution_type: str = "SOLUTION_TYPE_SEARCH",
        data_store_ids: list | None = None,
        enable_chat: bool = False,
    ) -> bool:
        """
        Create a new AgentSpace app (engine) in Discovery Engine.

        Args:
            app_name: Name for the app (will be used to generate app_id)
            solution_type: Type of solution (SOLUTION_TYPE_SEARCH, SOLUTION_TYPE_CHAT, etc.)
            data_store_ids: List of data store IDs to associate with the app
            enable_chat: Whether to enable chat features (requires Dialogflow API)

        Returns:
            True if successful, False otherwise
        """
        typer.echo("Creating new AgentSpace app...")

        # Validate required environment variables
        required_vars = ["GCP_PROJECT_NUMBER", "GCP_PROJECT_ID"]
        missing = [var for var in required_vars if not self.env_vars.get(var)]
        if missing:
            typer.secho(
                f" Missing required variables: {', '.join(missing)}",
                fg=typer.colors.RED,
            )
            return False

        # Generate app ID with timestamp
        import time

        if not app_name:
            app_name = "agentic-soc-app"
        app_id = f"{app_name.lower().replace(' ', '-')}_{int(time.time())}"

        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")

        # Build the API URL
        url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines"
        )

        # Build the app configuration
        app_config = {
            "displayName": app_name,
            "solutionType": solution_type,
        }

        # Add data stores if provided
        if data_store_ids:
            app_config["dataStoreIds"] = data_store_ids
        elif solution_type == "SOLUTION_TYPE_CHAT":
            # Chat apps require at least one data store
            typer.secho(
                " Warning: SOLUTION_TYPE_CHAT requires at least one data store",
                fg=typer.colors.YELLOW,
            )
            return False

        # Add chat configuration if enabled
        if enable_chat and solution_type == "SOLUTION_TYPE_CHAT":
            app_config["chatEngineConfig"] = {
                "agentCreationConfig": {
                    "business": self.env_vars.get(
                        "AGENT_BUSINESS", "Security Operations"
                    ),
                    "defaultLanguageCode": self.env_vars.get("AGENT_LANGUAGE", "en"),
                    "timeZone": self.env_vars.get("AGENT_TIMEZONE", "America/New_York"),
                }
            }

        # Make the API request
        typer.echo(f"  Creating app with ID: {app_id}")
        typer.echo(f"  Solution type: {solution_type}")

        response = self._make_request(
            "POST", url, json=app_config, params={"engineId": app_id}
        )

        if response and response.status_code in [200, 201]:
            typer.secho(" App created successfully!", fg=typer.colors.GREEN)
            typer.echo(f"  App ID: {app_id}")
            typer.echo(f"  Display Name: {app_name}")

            # Update environment file with new app ID
            self._update_env_var("AGENTSPACE_APP_ID", app_id)

            typer.echo("\n" + "=" * 80)
            typer.echo("IMPORTANT: Save this app ID to your .env file:")
            typer.echo(f"AGENTSPACE_APP_ID={app_id}")
            typer.echo("=" * 80)

            return True
        else:
            typer.secho(" Failed to create app", fg=typer.colors.RED)
            if response and hasattr(response, "text"):
                typer.echo(f"  Response: {response.text}")
            return False

    def display_url(self) -> None:
        """Display AgentSpace UI URL."""
        project_id = self.env_vars.get("GCP_PROJECT_ID")
        app_id = self.env_vars.get("AGENTSPACE_APP_ID")
        if not all([project_id, app_id]):
            typer.secho(
                " Cannot generate URL - missing configuration.", fg=typer.colors.RED
            )
            return

        url = f"https://console.cloud.google.com/gen-ai-studio/agentspace/apps/{app_id}?project={project_id}"
        typer.echo("AgentSpace UI URL:")
        typer.echo("=" * 80)
        typer.echo(url)
        typer.echo("=" * 80)

    def _ensure_data_store_exists(self) -> bool:
        """Ensure the engine has at least one data store configured."""
        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        app_id = self.env_vars["AGENTSPACE_APP_ID"]
        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")

        # Check if engine has data stores
        engine_url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines/{app_id}"
        )

        response = self._make_request("GET", engine_url)
        if not response:
            typer.secho(" Failed to get engine details", fg=typer.colors.RED)
            return False

        engine_data = response.json()
        data_store_ids = engine_data.get("dataStoreIds", [])

        typer.echo(f"  Engine info: {engine_data.get('name', 'unknown')}")
        typer.echo(f"  Display name: {engine_data.get('displayName', 'N/A')}")
        typer.echo(f"  Data stores: {data_store_ids}")

        if data_store_ids:
            typer.echo(
                f"  Engine has {len(data_store_ids)} data store(s) configured: {', '.join(data_store_ids)}"
            )

            # Verify each data store exists
            for ds_id in data_store_ids:
                ds_url = (
                    f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
                    f"locations/global/collections/{collection}/dataStores/{ds_id}"
                )
                ds_response = self._make_request("GET", ds_url)
                if ds_response:
                    ds_data = ds_response.json()
                    typer.echo(f"    - {ds_id}: {ds_data.get('displayName', 'exists')}")
                else:
                    typer.echo(f"    - {ds_id}: NOT FOUND")

            # If we have at least one data store, we can use it for search
            # Engines with a single data store cannot add or remove data stores
            typer.secho(
                "  Using existing data store(s) for search", fg=typer.colors.GREEN
            )
            return True

        typer.secho(
            " No data stores found. Creating unstructured data store...",
            fg=typer.colors.YELLOW,
        )
        return self._create_website_datastore()

    def _create_website_datastore(self) -> bool:
        """Create an unstructured data store for search."""
        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        app_id = self.env_vars["AGENTSPACE_APP_ID"]
        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")

        # Create an unstructured data store
        data_store_id = f"{app_id}_unstructured_datastore"
        data_store_url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/dataStores"
        )

        data_store_config = {
            "displayName": "Unstructured Data Store for SOC Agent",
            "industryVertical": "GENERIC",
            "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
            "contentConfig": "CONTENT_REQUIRED",
        }

        # Create the data store
        create_response = self._make_request(
            "POST",
            data_store_url,
            json=data_store_config,
            params={"dataStoreId": data_store_id},
        )

        if not create_response:
            # Check if it already exists (409 error)
            typer.echo(
                f"  Data store may already exist, attempting to link: {data_store_id}"
            )
        else:
            typer.echo(f"  Created data store: {data_store_id}")

        # Link data store to engine using PATCH
        typer.echo("  Linking data store to engine...")
        engine_url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines/{app_id}"
        )

        # Get existing data stores
        engine_response = self._make_request("GET", engine_url)
        existing_ids = []
        if engine_response:
            engine_data = engine_response.json()
            existing_ids = engine_data.get("dataStoreIds", [])

        # Add new data store to existing ones
        all_data_stores = list(set(existing_ids + [data_store_id]))

        # Update engine with new data store list using PATCH
        update_config = {"dataStoreIds": all_data_stores}

        patch_response = self._make_request(
            "PATCH",
            engine_url,
            json=update_config,
            params={"updateMask": "dataStoreIds"},
        )
        if patch_response:
            typer.secho(
                " Unstructured data store created and linked successfully!",
                fg=typer.colors.GREEN,
            )
            return True
        else:
            typer.secho(" Failed to link data store to engine", fg=typer.colors.RED)
            return False

    def link_agent_to_agentspace(
        self,
        display_name: str | None = None,
        description: str | None = None,
        tool_description: str | None = None,
        auth_id: str | None = None,
    ) -> bool:
        """
        Link an existing agent engine to AgentSpace with OAuth authorization.

        Args:
            display_name: Display name for the agent in AgentSpace
            description: Description of the agent
            tool_description: Description of what the agent tool does
            auth_id: OAuth authorization ID

        Returns:
            True if successful, False otherwise
        """
        valid, missing = self._validate_environment()
        if not valid:
            typer.echo(
                f"Error: Missing required environment variables: {', '.join(missing)}",
                err=True,
            )
            return False

        # Get values from environment if not provided
        if not display_name:
            display_name = self.env_vars.get("AGENT_DISPLAY_NAME", "MCP Security Agent")
        if not description:
            description = self.env_vars.get(
                "AGENT_DESCRIPTION",
                "AI-powered security operations agent with Google Security tools integration",
            )
        if not tool_description:
            tool_description = self.env_vars.get(
                "AGENT_TOOL_DESCRIPTION",
                "Security operations agent for threat analysis and incident response",
            )
        if not auth_id:
            auth_id = self.env_vars.get("OAUTH_AUTH_ID")

        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        as_app = self.env_vars["AGENTSPACE_APP_ID"]
        reasoning_engine = self.env_vars["AGENT_ENGINE_RESOURCE_NAME"]

        access_token = self._get_access_token()
        if not access_token:
            typer.echo("Error: Failed to get access token", err=True)
            return False

        url = f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/locations/global/collections/default_collection/engines/{as_app}/assistants/default_assistant/agents"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_number,
        }

        data = {
            "displayName": display_name,
            "description": description,
            "adk_agent_definition": {
                "tool_settings": {"tool_description": tool_description},
                "provisioned_reasoning_engine": {"reasoning_engine": reasoning_engine},
            },
        }

        # Add authorization if provided
        if auth_id:
            data["adk_agent_definition"]["authorizations"] = [
                f"projects/{project_number}/locations/global/authorizations/{auth_id}"
            ]

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            agent_name = result.get("name", "")

            typer.echo("Successfully linked agent to AgentSpace!")
            typer.echo(f"Agent name: {agent_name}")

            # Extract and save agent ID if present
            if "/" in agent_name:
                agent_id = agent_name.split("/")[-1]
                self._update_env_var("AGENTSPACE_AGENT_ID", agent_id)
                typer.echo(f"Agent ID saved to environment: {agent_id}")

            return True

        except requests.exceptions.RequestException as e:
            typer.echo(f"Error linking agent to AgentSpace: {e}", err=True)
            if hasattr(e.response, "text"):
                typer.echo(f"Response: {e.response.text}", err=True)
            return False

    def unlink_agent_from_agentspace(
        self,
        agent_id: str | None = None,
        force: bool = False,
    ) -> bool:
        """
        Unlink (remove) an agent from AgentSpace while keeping the app intact.

        Args:
            agent_id: ID of the agent to unlink (defaults to AGENTSPACE_AGENT_ID from env)
            force: Skip confirmation prompt if True

        Returns:
            True if successful, False otherwise
        """
        # Get agent ID from parameter or environment
        if not agent_id:
            agent_id = self.env_vars.get("AGENTSPACE_AGENT_ID")

        if not agent_id:
            typer.secho(" No agent ID found to unlink.", fg=typer.colors.RED)
            return False

        # Validate required environment variables
        required_vars = ["GCP_PROJECT_NUMBER", "AGENTSPACE_APP_ID"]
        missing = [var for var in required_vars if not self.env_vars.get(var)]
        if missing:
            typer.secho(
                f" Missing required variables: {', '.join(missing)}",
                fg=typer.colors.RED,
            )
            return False

        # Confirm deletion unless force flag is set
        if not force and not typer.confirm(
            f"Are you sure you want to unlink agent {agent_id} from AgentSpace?"
        ):
            typer.echo("Cancelled.")
            return False

        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        as_app = self.env_vars["AGENTSPACE_APP_ID"]
        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")
        assistant = self.env_vars.get("AGENTSPACE_ASSISTANT", "default_assistant")

        url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines/{as_app}/"
            f"assistants/{assistant}/agents/{agent_id}"
        )

        access_token = self._get_access_token()
        if not access_token:
            typer.echo("Error: Failed to get access token", err=True)
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Goog-User-Project": project_number,
        }

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()

            typer.secho(
                " Agent unlinked successfully from AgentSpace!", fg=typer.colors.GREEN
            )
            typer.echo(f"  Agent ID {agent_id} removed from app {as_app}")
            typer.echo("  Note: The AgentSpace app remains intact")

            # Clear agent ID from environment if it matches
            if agent_id == self.env_vars.get("AGENTSPACE_AGENT_ID"):
                self._update_env_var("AGENTSPACE_AGENT_ID", "")
                typer.echo("  Cleared AGENTSPACE_AGENT_ID from environment")

            return True

        except requests.exceptions.RequestException as e:
            typer.echo(f"Error unlinking agent from AgentSpace: {e}", err=True)
            if hasattr(e.response, "text"):
                typer.echo(f"Response: {e.response.text}", err=True)
            return False

    def update_agent_config(
        self,
        agent_id: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        tool_description: str | None = None,
    ) -> bool:
        """
        Update an existing agent's configuration in AgentSpace.

        Args:
            agent_id: ID of the agent to update
            display_name: New display name for the agent
            description: New description of the agent
            tool_description: New description of what the agent tool does

        Returns:
            True if successful, False otherwise
        """
        if not agent_id:
            agent_id = self.env_vars.get("AGENTSPACE_AGENT_ID")
            if not agent_id:
                typer.echo(
                    "Error: No agent ID provided or found in environment", err=True
                )
                return False

        project_number = self.env_vars.get("GCP_PROJECT_NUMBER")
        if not project_number:
            typer.echo("Error: GCP_PROJECT_NUMBER not found in environment", err=True)
            return False

        as_app = self.env_vars.get("AGENTSPACE_APP_ID")
        if not as_app:
            typer.echo("Error: AGENTSPACE_APP_ID not found in environment", err=True)
            return False

        access_token = self._get_access_token()
        if not access_token:
            typer.echo("Error: Failed to get access token", err=True)
            return False

        url = f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/locations/global/collections/default_collection/engines/{as_app}/assistants/default_assistant/agents/{agent_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_number,
        }

        # Build update mask and data
        update_mask = []
        data = {}

        if display_name:
            data["displayName"] = display_name
            update_mask.append("displayName")

        if description:
            data["description"] = description
            update_mask.append("description")

        if tool_description:
            if "adk_agent_definition" not in data:
                data["adk_agent_definition"] = {}
            data["adk_agent_definition"]["tool_settings"] = {
                "tool_description": tool_description
            }
            update_mask.append("adk_agent_definition.tool_settings.tool_description")

        if not update_mask:
            typer.echo("Warning: No fields to update", err=True)
            return True

        params = {"updateMask": ",".join(update_mask)}

        try:
            response = requests.patch(url, headers=headers, json=data, params=params)
            response.raise_for_status()

            typer.echo("Successfully updated agent configuration!")
            return True

        except requests.exceptions.RequestException as e:
            typer.echo(f"Error updating agent configuration: {e}", err=True)
            if hasattr(e.response, "text"):
                typer.echo(f"Response: {e.response.text}", err=True)
            return False

    def list_apps(self) -> bool:
        """
        List all apps in the AgentSpace collection.

        Returns:
            True if successful, False otherwise
        """
        project_number = self.env_vars.get("GCP_PROJECT_NUMBER")
        if not project_number:
            typer.echo("Error: GCP_PROJECT_NUMBER not found in environment", err=True)
            return False

        access_token = self._get_access_token()
        if not access_token:
            typer.echo("Error: Failed to get access token", err=True)
            return False

        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")
        url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Goog-User-Project": project_number,
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            result = response.json()
            engines = result.get("engines", [])

            if not engines:
                typer.echo("No apps found in AgentSpace collection.")
                return True

            typer.echo(f"\nFound {len(engines)} app(s) in AgentSpace:\n")
            for i, engine in enumerate(engines, 1):
                name = engine.get("name", "")
                app_id = name.split("/")[-1] if "/" in name else name
                display_name = engine.get("displayName", "N/A")
                solution_type = engine.get("solutionType", "N/A")
                data_store_ids = engine.get("dataStoreIds", [])
                create_time = engine.get("createTime", "N/A")

                typer.echo(f"{i}. App ID: {app_id}")
                typer.echo(f"   Display Name: {display_name}")
                typer.echo(f"   Solution Type: {solution_type}")

                if data_store_ids:
                    typer.echo(f"   Data Stores: {', '.join(data_store_ids)}")
                else:
                    typer.echo("   Data Stores: None")

                typer.echo(f"   Create Time: {create_time}")
                typer.echo()

            return True

        except requests.exceptions.RequestException as e:
            typer.echo(f"Error listing apps: {e}", err=True)
            if hasattr(e.response, "text"):
                typer.echo(f"Response: {e.response.text}", err=True)
            return False

    def list_agents(self) -> bool:
        """
        List all agents in the AgentSpace app.

        Returns:
            True if successful, False otherwise
        """
        project_number = self.env_vars.get("GCP_PROJECT_NUMBER")
        if not project_number:
            typer.echo("Error: GCP_PROJECT_NUMBER not found in environment", err=True)
            return False

        as_app = self.env_vars.get("AGENTSPACE_APP_ID")
        if not as_app:
            typer.echo("Error: AGENTSPACE_APP_ID not found in environment", err=True)
            return False

        access_token = self._get_access_token()
        if not access_token:
            typer.echo("Error: Failed to get access token", err=True)
            return False

        url = f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/locations/global/collections/default_collection/engines/{as_app}/assistants/default_assistant/agents"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Goog-User-Project": project_number,
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            result = response.json()
            agents = result.get("agents", [])

            if not agents:
                typer.echo("No agents found in AgentSpace app.")
                return True

            # Get engine details to show solution type
            engine_url = (
                f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
                f"locations/global/collections/default_collection/engines/{as_app}"
            )
            engine_response = self._make_request("GET", engine_url)
            solution_type = "N/A"
            if engine_response:
                engine_data = engine_response.json()
                solution_type = engine_data.get("solutionType", "N/A")

            typer.echo(f"\nFound {len(agents)} agent(s) in AgentSpace:\n")
            typer.echo(f"Engine Solution Type: {solution_type}\n")
            for i, agent in enumerate(agents, 1):
                name = agent.get("name", "")
                agent_id = name.split("/")[-1] if "/" in name else name
                display_name = agent.get("displayName", "N/A")
                description = agent.get("description", "N/A")

                typer.echo(f"{i}. Agent ID: {agent_id}")
                typer.echo(f"   Display Name: {display_name}")
                typer.echo(f"   Description: {description}")

                # Show tool description if available
                adk_def = agent.get("adk_agent_definition", {})
                tool_settings = adk_def.get("tool_settings", {})
                if tool_settings.get("tool_description"):
                    typer.echo(
                        f"   Tool Description: {tool_settings['tool_description']}"
                    )

                # Show reasoning engine if available
                prov_engine = adk_def.get("provisioned_reasoning_engine", {})
                if prov_engine.get("reasoning_engine"):
                    typer.echo(
                        f"   Reasoning Engine: {prov_engine['reasoning_engine']}"
                    )

                typer.echo()

            return True

        except requests.exceptions.RequestException as e:
            typer.echo(f"Error listing agents: {e}", err=True)
            if hasattr(e.response, "text"):
                typer.echo(f"Response: {e.response.text}", err=True)
            return False

    def search_agentspace(self, query: str = "test query") -> bool:
        """Test AgentSpace search functionality via Discovery Engine API."""
        typer.echo(f"Testing AgentSpace search with query: '{query}'...")

        # Validate required environment variables
        required_vars = ["GCP_PROJECT_NUMBER", "AGENTSPACE_APP_ID"]
        missing = [var for var in required_vars if not self.env_vars.get(var)]
        if missing:
            typer.secho(
                f" Missing required variables: {', '.join(missing)}",
                fg=typer.colors.RED,
            )
            return False

        # Ensure data store exists before searching
        if not self._ensure_data_store_exists():
            typer.secho(" Cannot search without a data store", fg=typer.colors.RED)
            return False

        project_number = self.env_vars["GCP_PROJECT_NUMBER"]
        app_id = self.env_vars["AGENTSPACE_APP_ID"]
        collection = self.env_vars.get("AGENTSPACE_COLLECTION", "default_collection")

        # Build the Discovery Engine search URL
        url = (
            f"{DISCOVERY_ENGINE_API_BASE}/projects/{project_number}/"
            f"locations/global/collections/{collection}/engines/{app_id}/"
            f"servingConfigs/default_search:search"
        )

        # Build the search payload
        search_payload = {
            "query": query,
            "pageSize": 10,
            "spellCorrectionSpec": {"mode": "AUTO"},
            "languageCode": "en-US",
            "relevanceScoreSpec": {"returnRelevanceScore": True},
            "userInfo": {"timeZone": "America/New_York"},
            "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}},
            "naturalLanguageQueryUnderstandingSpec": {
                "filterExtractionCondition": "ENABLED"
            },
        }

        response = self._make_request("POST", url, json=search_payload)
        if response and response.status_code == 200:
            result = response.json()
            typer.secho(" AgentSpace search test successful!", fg=typer.colors.GREEN)

            # Display search results
            results = result.get("results", [])
            total_size = result.get("totalSize", 0)

            typer.echo(f"  Total results: {total_size}")
            typer.echo(f"  Returned results: {len(results)}")

            if results:
                typer.echo("  Search results:")
                for i, result_item in enumerate(results[:3], 1):  # Show first 3 results
                    document = result_item.get("document", {})
                    title = document.get("title", "No title")
                    snippet = result_item.get("snippet", "No snippet available")
                    relevance = result_item.get("relevanceScore", "N/A")

                    typer.echo(f"    {i}. Title: {title}")
                    typer.echo(f"       Relevance: {relevance}")
                    typer.echo(
                        f"       Snippet: {snippet[:100]}{'...' if len(snippet) > 100 else ''}"
                    )
                    typer.echo("")
            else:
                typer.echo("  No search results returned")

            return True
        else:
            typer.secho(" AgentSpace search test failed!", fg=typer.colors.RED)
            return False


@app.command()
def register(
    force: Annotated[
        bool, typer.Option("--force", help="Force re-registration if agent exists.")
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Register the agent with AgentSpace."""
    manager = AgentSpaceManager(env_file)
    if not manager.register_agent(force):
        raise typer.Exit(code=1)


@app.command()
def update(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Update the existing AgentSpace agent configuration."""
    manager = AgentSpaceManager(env_file)
    if not manager.update_agent():
        raise typer.Exit(code=1)


@app.command()
def verify(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Verify the AgentSpace agent configuration and status."""
    manager = AgentSpaceManager(env_file)
    if not manager.verify_agent():
        raise typer.Exit(code=1)


@app.command()
def delete(
    force: Annotated[
        bool, typer.Option("--force", help="Force deletion without confirmation.")
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Delete the agent from AgentSpace."""
    manager = AgentSpaceManager(env_file)
    if not manager.delete_agent(force):
        raise typer.Exit(code=1)


@app.command()
def url(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Display the AgentSpace UI URL."""
    manager = AgentSpaceManager(env_file)
    manager.display_url()


@app.command()
def search(
    query: Annotated[
        str, typer.Option("--query", help="Search query to test with.")
    ] = "test security operations",
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Test AgentSpace search functionality via Discovery Engine API."""
    manager = AgentSpaceManager(env_file)
    if not manager.search_agentspace(query):
        raise typer.Exit(code=1)


@app.command()
def ensure_datastore(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Ensure the AgentSpace engine has a data store configured."""
    manager = AgentSpaceManager(env_file)
    if not manager._ensure_data_store_exists():
        raise typer.Exit(code=1)


@app.command()
def link_agent(
    display_name: Annotated[
        str | None,
        typer.Option("--display-name", help="Display name for the agent."),
    ] = None,
    description: Annotated[
        str | None, typer.Option("--description", help="Description of the agent.")
    ] = None,
    tool_description: Annotated[
        str | None,
        typer.Option(
            "--tool-description", help="Description of what the agent tool does."
        ),
    ] = None,
    auth_id: Annotated[
        str | None, typer.Option("--auth-id", help="OAuth authorization ID.")
    ] = None,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Link an existing agent engine to AgentSpace with OAuth authorization."""
    manager = AgentSpaceManager(env_file)
    if not manager.link_agent_to_agentspace(
        display_name, description, tool_description, auth_id
    ):
        raise typer.Exit(code=1)


@app.command()
def unlink_agent(
    agent_id: Annotated[
        str | None,
        typer.Option(
            "--agent-id", help="ID of the agent to unlink (defaults to env var)."
        ),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Force unlinking without confirmation.")
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Unlink (remove) an agent from AgentSpace while keeping the app intact."""
    manager = AgentSpaceManager(env_file)
    if not manager.unlink_agent_from_agentspace(agent_id, force):
        raise typer.Exit(code=1)


@app.command()
def update_agent_config(
    agent_id: Annotated[
        str | None, typer.Option("--agent-id", help="ID of the agent to update.")
    ] = None,
    display_name: Annotated[
        str | None,
        typer.Option("--display-name", help="New display name for the agent."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description of the agent."),
    ] = None,
    tool_description: Annotated[
        str | None,
        typer.Option(
            "--tool-description", help="New description of what the agent tool does."
        ),
    ] = None,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Update an existing agent's configuration in AgentSpace."""
    manager = AgentSpaceManager(env_file)
    if not manager.update_agent_config(
        agent_id, display_name, description, tool_description
    ):
        raise typer.Exit(code=1)


@app.command()
def list_apps(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """List all apps in the AgentSpace collection."""
    manager = AgentSpaceManager(env_file)
    if not manager.list_apps():
        raise typer.Exit(code=1)


@app.command()
def list_agents(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """List all agents in the AgentSpace app."""
    manager = AgentSpaceManager(env_file)
    if not manager.list_agents():
        raise typer.Exit(code=1)


@app.command()
def create_app(
    app_name: Annotated[
        str | None, typer.Option("--name", help="Display name for the app.")
    ] = None,
    solution_type: Annotated[
        str,
        typer.Option(
            "--type", help="Solution type (SOLUTION_TYPE_SEARCH, SOLUTION_TYPE_CHAT)."
        ),
    ] = "SOLUTION_TYPE_SEARCH",
    data_store_id: Annotated[
        str | None,
        typer.Option("--data-store", help="Data store ID to associate with the app."),
    ] = None,
    enable_chat: Annotated[
        bool,
        typer.Option(
            "--enable-chat",
            help="Enable chat features (requires Dialogflow API for CHAT type).",
        ),
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Create a new AgentSpace app in Discovery Engine."""
    manager = AgentSpaceManager(env_file)

    # Convert single data store ID to list if provided
    data_store_ids = [data_store_id] if data_store_id else None

    if not manager.create_app(
        app_name=app_name,
        solution_type=solution_type,
        data_store_ids=data_store_ids,
        enable_chat=enable_chat,
    ):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
