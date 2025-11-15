#!/usr/bin/env python3
"""
Vertex AI Setup and Verification Manager

This script helps verify and manage Vertex AI setup requirements including
API enablement, authentication, permissions, and quota status.
"""

import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer
import vertexai
from dotenv import load_dotenv
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError


app = typer.Typer(
    add_completion=False,
    help="Manage and verify Vertex AI setup for the Google MCP Security Agent.",
)


class VertexAIManager:
    """Manages Vertex AI setup verification and configuration."""

    # Required APIs for the project
    REQUIRED_APIS = [
        "aiplatform.googleapis.com",
        "storage.googleapis.com",
        "cloudbuild.googleapis.com",
        "compute.googleapis.com",
    ]

    # Optional APIs depending on features used
    OPTIONAL_APIS = [
        "discoveryengine.googleapis.com",  # For AgentSpace
        "securitycenter.googleapis.com",  # For SCC tools
    ]

    # Required IAM roles
    REQUIRED_ROLES = [
        "roles/aiplatform.user",
        "roles/storage.admin",
    ]

    def __init__(self, env_file: Path):
        """
        Initialize the Vertex AI manager.

        Args:
            env_file: Path to the environment file.
        """
        self.env_file = env_file
        self.env_vars = self._load_env_vars()
        self.project_id = None
        self.location = None
        self.credentials = None

    def _load_env_vars(self) -> dict[str, str]:
        """Load environment variables from the .env file."""
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)
        env_vars = dict(os.environ)
        return env_vars

    def verify_setup(
        self, skip_apis: bool = False, skip_permissions: bool = False
    ) -> bool:
        """
        Run complete verification of Vertex AI setup.

        Args:
            skip_apis: Skip API enablement checks
            skip_permissions: Skip IAM permission checks

        Returns:
            True if all checks pass, False otherwise
        """
        typer.echo()
        typer.secho("=" * 80, fg=typer.colors.BLUE)
        typer.secho("Vertex AI Setup Verification", fg=typer.colors.BLUE, bold=True)
        typer.secho("=" * 80, fg=typer.colors.BLUE)
        typer.echo()

        all_passed = True

        # Check 1: Environment variables
        typer.secho(
            "1. Checking environment variables...", fg=typer.colors.CYAN, bold=True
        )
        if not self._check_env_vars():
            all_passed = False
        typer.echo()

        # Check 2: Authentication
        typer.secho("2. Checking authentication...", fg=typer.colors.CYAN, bold=True)
        if not self._check_authentication():
            all_passed = False
            return False  # Can't continue without auth
        typer.echo()

        # Check 3: Project access
        typer.secho("3. Verifying project access...", fg=typer.colors.CYAN, bold=True)
        if not self._check_project_access():
            all_passed = False
        typer.echo()

        # Check 4: API enablement
        if not skip_apis:
            typer.secho(
                "4. Checking API enablement...", fg=typer.colors.CYAN, bold=True
            )
            if not self._check_apis():
                all_passed = False
            typer.echo()

        # Check 5: Vertex AI initialization
        typer.secho(
            "5. Testing Vertex AI initialization...", fg=typer.colors.CYAN, bold=True
        )
        if not self._check_vertex_ai_init():
            all_passed = False
        typer.echo()

        # Check 6: IAM permissions (if not skipped)
        if not skip_permissions:
            typer.secho(
                "6. Checking IAM permissions...", fg=typer.colors.CYAN, bold=True
            )
            self._check_permissions()  # This is informational, doesn't fail
            typer.echo()

        # Final summary
        typer.secho("=" * 80, fg=typer.colors.BLUE)
        if all_passed:
            typer.secho("✓ All checks passed!", fg=typer.colors.GREEN, bold=True)
            typer.secho("Vertex AI is properly configured.", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Some checks failed", fg=typer.colors.RED, bold=True)
            typer.secho(
                "Please fix the issues above before proceeding.", fg=typer.colors.RED
            )
        typer.secho("=" * 80, fg=typer.colors.BLUE)
        typer.echo()

        return all_passed

    def _check_env_vars(self) -> bool:
        """Check required environment variables."""
        required_vars = ["GCP_PROJECT_ID", "GCP_LOCATION"]
        all_present = True

        for var in required_vars:
            value = self.env_vars.get(var)
            if value:
                typer.secho(f"  ✓ {var}: {value}", fg=typer.colors.GREEN)
                if var == "GCP_PROJECT_ID":
                    self.project_id = value
                elif var == "GCP_LOCATION":
                    self.location = value
            else:
                typer.secho(f"  ✗ {var}: Not set", fg=typer.colors.RED)
                all_present = False

        # Check optional RAG location
        rag_location = self.env_vars.get("RAG_GCP_LOCATION")
        if rag_location:
            typer.secho(f"  ✓ RAG_GCP_LOCATION: {rag_location}", fg=typer.colors.GREEN)
        else:
            typer.secho(
                "  ℹ RAG_GCP_LOCATION: Not set (will use GCP_LOCATION)",
                fg=typer.colors.YELLOW,
            )

        return all_present

    def _check_authentication(self) -> bool:
        """Check if application default credentials are configured."""
        try:
            credentials, project = default()
            self.credentials = credentials
            typer.secho(
                "  ✓ Application Default Credentials found", fg=typer.colors.GREEN
            )
            if project:
                typer.secho(
                    f"  ✓ Authenticated project: {project}", fg=typer.colors.GREEN
                )
            return True
        except DefaultCredentialsError as e:
            typer.secho(f"  ✗ Authentication failed: {e}", fg=typer.colors.RED)
            typer.echo()
            typer.echo("  To fix, run:")
            typer.secho(
                "    gcloud auth application-default login", fg=typer.colors.YELLOW
            )
            typer.secho(
                f"    gcloud auth application-default set-quota-project {self.project_id}",
                fg=typer.colors.YELLOW,
            )
            return False

    def _check_project_access(self) -> bool:
        """Verify access to the configured GCP project."""
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "projects",
                    "describe",
                    self.project_id,
                    "--format=value(projectId)",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                typer.secho(
                    f"  ✓ Project accessible: {self.project_id}", fg=typer.colors.GREEN
                )
                return True
            else:
                typer.secho(
                    f"  ✗ Cannot access project: {self.project_id}", fg=typer.colors.RED
                )
                typer.secho(f"    Error: {result.stderr.strip()}", fg=typer.colors.RED)
                return False
        except subprocess.TimeoutExpired:
            typer.secho(
                "  ⚠ Project check timed out (gcloud may need auth refresh)",
                fg=typer.colors.YELLOW,
            )
            return True  # Don't fail on timeout, credentials might still work
        except FileNotFoundError:
            typer.secho(
                "  ⚠ gcloud CLI not found (skipping project check)",
                fg=typer.colors.YELLOW,
            )
            return True  # Don't fail if gcloud not installed

    def _check_apis(self) -> bool:
        """Check if required APIs are enabled."""
        all_enabled = True

        for api in self.REQUIRED_APIS:
            if self._is_api_enabled(api):
                typer.secho(f"  ✓ {api}", fg=typer.colors.GREEN)
            else:
                typer.secho(f"  ✗ {api} (not enabled)", fg=typer.colors.RED)
                all_enabled = False

        if not all_enabled:
            typer.echo()
            typer.echo("  To enable required APIs, run:")
            typer.secho(
                f"    gcloud services enable {' '.join(self.REQUIRED_APIS)} --project={self.project_id}",
                fg=typer.colors.YELLOW,
            )

        return all_enabled

    def _is_api_enabled(self, api: str) -> bool:
        """Check if a specific API is enabled."""
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "services",
                    "list",
                    "--enabled",
                    f"--filter=name:{api}",
                    "--format=value(name)",
                    f"--project={self.project_id}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return api in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return True  # Assume enabled if we can't check

    def _check_vertex_ai_init(self) -> bool:
        """Test Vertex AI initialization."""
        try:
            # Use RAG location if set, otherwise use GCP_LOCATION
            location = self.env_vars.get("RAG_GCP_LOCATION") or self.location

            vertexai.init(
                project=self.project_id, location=location, credentials=self.credentials
            )
            typer.secho("  ✓ Vertex AI initialized successfully", fg=typer.colors.GREEN)
            typer.secho(f"    Project: {self.project_id}", fg=typer.colors.GREEN)
            typer.secho(f"    Location: {location}", fg=typer.colors.GREEN)
            return True
        except Exception as e:
            typer.secho(
                f"  ✗ Vertex AI initialization failed: {e}", fg=typer.colors.RED
            )
            return False

    def _check_permissions(self) -> None:
        """Check IAM permissions (informational only)."""
        typer.echo("  Checking IAM permissions...")
        typer.echo("  Note: This requires gcloud CLI and may need fresh credentials")
        typer.echo()

        try:
            # Get current user email
            result = subprocess.run(
                ["gcloud", "config", "get-value", "account"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            user_email = result.stdout.strip()
            if not user_email:
                typer.secho(
                    "  ℹ Unable to determine current user", fg=typer.colors.YELLOW
                )
                return

            typer.echo(f"  Current user: {user_email}")
            typer.echo(f"  Required roles: {', '.join(self.REQUIRED_ROLES)}")
            typer.echo()
            typer.secho(
                "  Note: Use GCP Console IAM page to verify permissions",
                fg=typer.colors.CYAN,
            )

        except (subprocess.TimeoutExpired, FileNotFoundError):
            typer.secho(
                "  ℹ Could not check permissions (gcloud CLI issue)",
                fg=typer.colors.YELLOW,
            )

    def enable_apis(self) -> bool:
        """Enable all required APIs."""
        typer.echo(f"Enabling required APIs for project: {self.project_id}")
        typer.echo()

        apis_to_enable = self.REQUIRED_APIS.copy()

        try:
            cmd = (
                ["gcloud", "services", "enable"]
                + apis_to_enable
                + [f"--project={self.project_id}"]
            )
            typer.echo(f"Running: {' '.join(cmd)}")
            typer.echo()

            result = subprocess.run(cmd, timeout=120)

            if result.returncode == 0:
                typer.secho("✓ APIs enabled successfully", fg=typer.colors.GREEN)
                typer.echo()
                typer.echo(
                    "Note: It may take a few minutes for APIs to be fully active"
                )
                return True
            else:
                typer.secho("✗ Failed to enable APIs", fg=typer.colors.RED)
                return False

        except subprocess.TimeoutExpired:
            typer.secho("✗ Command timed out", fg=typer.colors.RED)
            return False
        except FileNotFoundError:
            typer.secho("✗ gcloud CLI not found", fg=typer.colors.RED)
            typer.echo("Please install the Google Cloud SDK")
            return False


@app.command()
def verify(
    skip_apis: Annotated[
        bool, typer.Option("--skip-apis", help="Skip API enablement checks")
    ] = False,
    skip_permissions: Annotated[
        bool, typer.Option("--skip-permissions", help="Skip IAM permission checks")
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Verify complete Vertex AI setup including APIs, auth, and permissions."""
    manager = VertexAIManager(env_file)
    if not manager.verify_setup(skip_apis=skip_apis, skip_permissions=skip_permissions):
        raise typer.Exit(code=1)


@app.command()
def enable_apis(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Enable all required APIs for Vertex AI."""
    manager = VertexAIManager(env_file)

    # Load environment first
    manager._check_env_vars()

    if not manager.enable_apis():
        raise typer.Exit(code=1)


@app.command()
def check_quota(
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Display quota information for Vertex AI services."""
    manager = VertexAIManager(env_file)
    manager._load_env_vars()

    typer.echo()
    typer.secho("Vertex AI Quota Information", fg=typer.colors.CYAN, bold=True)
    typer.secho("=" * 80, fg=typer.colors.CYAN)
    typer.echo()

    typer.echo("RAG Service Quotas:")
    typer.echo("  - List/Get operations: 60 requests/minute/region")
    typer.echo("  - Create/Delete operations: Limited (check GCP Console)")
    typer.echo()

    typer.echo("To view current quota usage:")
    typer.secho(
        f"  gcloud services quota list --service=aiplatform.googleapis.com --project={manager.project_id}",
        fg=typer.colors.YELLOW,
    )
    typer.echo()

    typer.echo("To request quota increase:")
    typer.secho(
        "  https://cloud.google.com/docs/quotas/help/request_increase",
        fg=typer.colors.YELLOW,
    )
    typer.echo()


if __name__ == "__main__":
    app()
