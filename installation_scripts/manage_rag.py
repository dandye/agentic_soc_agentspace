#!/usr/bin/env python3
"""
RAG Corpus Manager for Google Vertex AI

This script manages RAG corpus operations including listing, creating,
and deleting RAG corpora in Vertex AI.
"""

import os
from pathlib import Path
from typing import Dict, Optional

from google.auth import default
from google.api_core.exceptions import NotFound, ResourceExhausted
import vertexai
from vertexai.preview import rag
from dotenv import load_dotenv
import typer
from typing_extensions import Annotated

app = typer.Typer(
    add_completion=False,
    help="Manage RAG corpora in Vertex AI for the Google MCP Security Agent.",
)


class RAGManager:
    """Manages RAG corpus operations in Vertex AI."""

    def __init__(self, env_file: Path):
        """
        Initialize the RAG manager.

        Args:
            env_file: Path to the environment file.
        """
        self.env_file = env_file
        self.env_vars = self._load_env_vars()
        self.project_id = None
        self.location = None
        self._initialize_vertex_ai()

    def _load_env_vars(self) -> Dict[str, str]:
        """Load environment variables from the .env file."""
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)
        env_vars = dict(os.environ)
        return env_vars

    def _initialize_vertex_ai(self) -> None:
        """Initialize Vertex AI with project and location from environment."""
        self.project_id = self.env_vars.get("GCP_PROJECT_ID")
        # Use RAG-specific location if set, otherwise fall back to GCP_LOCATION
        self.location = self.env_vars.get("RAG_GCP_LOCATION") or self.env_vars.get("GCP_LOCATION")

        if not self.project_id:
            typer.secho(
                " Missing required variable: GCP_PROJECT_ID",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

        if not self.location:
            typer.secho(
                " Missing required variable: GCP_LOCATION",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

        try:
            credentials, _ = default()
            vertexai.init(
                project=self.project_id, location=self.location, credentials=credentials
            )
        except Exception as e:
            typer.secho(f" Failed to initialize Vertex AI: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    def list_corpora(self, verbose: bool = False) -> bool:
        """
        List all RAG corpora in the project.

        Args:
            verbose: Show detailed information for each corpus

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use pagination to handle large numbers of corpora
            # This also helps with quota limits by making smaller requests
            # Display results as we fetch each page (streaming)
            total_count = 0
            page_num = 0
            page_token = None
            page_size = 10

            typer.echo()  # Blank line before output

            while True:
                page_num += 1
                typer.echo(f"Fetching page {page_num}...")

                # Get the next page of results
                pager = rag.list_corpora(page_size=page_size, page_token=page_token)

                # Process and display each corpus immediately
                page_count = 0
                for corpus in pager:
                    total_count += 1
                    page_count += 1

                    display_name = corpus.display_name
                    corpus_name = corpus.name
                    description = getattr(corpus, "description", "N/A")

                    typer.echo(f"{total_count}. {display_name}")
                    typer.echo(f"   Name: {corpus_name}")
                    if description and description != "N/A":
                        typer.echo(f"   Description: {description}")

                    if verbose:
                        # Show embedding model configuration
                        if hasattr(corpus, "embedding_model_config"):
                            config = corpus.embedding_model_config
                            if hasattr(config, "publisher_model"):
                                typer.echo(f"   Embedding Model: {config.publisher_model}")

                        # Try to list files in the corpus
                        try:
                            files = list(rag.list_files(corpus_name=corpus_name))
                            typer.echo(f"   Files: {len(files)}")
                            if files:
                                for file in files[:3]:  # Show first 3 files
                                    typer.echo(f"     - {file.display_name}")
                                if len(files) > 3:
                                    typer.echo(f"     ... and {len(files) - 3} more")
                        except Exception as e:
                            typer.echo(f"   Files: Unable to retrieve ({str(e)[:50]})")

                    typer.echo()

                typer.echo(f"  (found {page_count} on this page)\n")

                # Check for next page AFTER iterating through current page
                page_token = getattr(pager, 'next_page_token', None)
                if not page_token:
                    break

            if total_count == 0:
                typer.echo("No RAG corpora found.")
            else:
                typer.echo(f"Total: {total_count} RAG corpus/corpora")

            return True

        except ResourceExhausted:
            typer.secho("Error: Quota exceeded for Vertex AI RAG service", fg=typer.colors.RED)
            typer.echo("You have exceeded the API rate limit for RAG operations.")
            typer.echo("Please wait a minute and try again, or request a quota increase.")
            return False
        except Exception as e:
            typer.secho(f"Error listing RAG corpora: {e}", fg=typer.colors.RED)
            return False

    def get_corpus_info(self, corpus_name: str) -> bool:
        """
        Get detailed information about a specific RAG corpus.

        Args:
            corpus_name: Full resource name of the corpus

        Returns:
            True if successful, False otherwise
        """
        typer.echo(f"Getting information for corpus: {corpus_name}")

        try:
            corpus = rag.get_corpus(name=corpus_name)

            typer.echo("\nRAG Corpus Information:")
            typer.echo("=" * 80)
            typer.echo(f"Display Name: {corpus.display_name}")
            typer.echo(f"Resource Name: {corpus.name}")

            if hasattr(corpus, "description") and corpus.description:
                typer.echo(f"Description: {corpus.description}")

            if hasattr(corpus, "embedding_model_config"):
                config = corpus.embedding_model_config
                if hasattr(config, "publisher_model"):
                    typer.echo(f"Embedding Model: {config.publisher_model}")

            if hasattr(corpus, "create_time"):
                typer.echo(f"Created: {corpus.create_time}")

            if hasattr(corpus, "update_time"):
                typer.echo(f"Updated: {corpus.update_time}")

            # List files in the corpus
            typer.echo("\nFiles in corpus:")
            try:
                files = list(rag.list_files(corpus_name=corpus_name))
                if files:
                    typer.echo(f"Total files: {len(files)}")
                    for i, file in enumerate(files, 1):
                        typer.echo(f"{i}. {file.display_name} - {file.name}")
                        if hasattr(file, "description") and file.description:
                            typer.echo(f"   Description: {file.description}")
                else:
                    typer.echo("No files found in corpus.")
            except Exception as e:
                typer.secho(f" Error listing files: {e}", fg=typer.colors.YELLOW)

            return True

        except NotFound:
            typer.secho(f"Corpus not found: {corpus_name}", fg=typer.colors.RED)
            return False
        except Exception as e:
            typer.secho(
                f"Error getting corpus information: {e}", fg=typer.colors.RED
            )
            return False

    def create_corpus(
        self,
        display_name: str,
        description: Optional[str] = None,
        embedding_model: str = "publishers/google/models/text-embedding-004",
    ) -> bool:
        """
        Create a new RAG corpus.

        Args:
            display_name: Display name for the corpus
            description: Optional description of the corpus
            embedding_model: Embedding model to use

        Returns:
            True if successful, False otherwise
        """
        typer.echo(f"Creating RAG corpus: {display_name}")

        try:
            embedding_model_config = rag.EmbeddingModelConfig(
                publisher_model=embedding_model
            )

            # Check if corpus with same display name already exists
            existing_corpora = list(rag.list_corpora())
            for existing_corpus in existing_corpora:
                if existing_corpus.display_name == display_name:
                    typer.secho(
                        f" A corpus with display name '{display_name}' already exists.",
                        fg=typer.colors.YELLOW,
                    )
                    typer.echo(f"   Existing corpus: {existing_corpus.name}")
                    return False

            corpus = rag.create_corpus(
                display_name=display_name,
                description=description or "",
                embedding_model_config=embedding_model_config,
            )

            typer.secho(
                f"Corpus created successfully: {display_name}", fg=typer.colors.GREEN
            )
            typer.echo(f"   Resource name: {corpus.name}")
            typer.echo("\n" + "=" * 80)
            typer.echo("To use this corpus, save the resource name:")
            typer.echo(f"RAG_CORPUS={corpus.name}")
            typer.echo("=" * 80)

            return True

        except ResourceExhausted as e:
            typer.secho(f"Error creating corpus: {e}", fg=typer.colors.RED)
            typer.echo(
                "This error suggests that you have exceeded the API quota for the embedding model."
            )
            typer.echo("This is common for new Google Cloud projects.")
            typer.echo(
                "Please request a quota increase through the Google Cloud Console."
            )
            return False
        except Exception as e:
            typer.secho(f"Error creating corpus: {e}", fg=typer.colors.RED)
            return False

    def delete_corpus(self, corpus_name: str, force: bool = False) -> bool:
        """
        Delete a RAG corpus.

        Args:
            corpus_name: Full resource name of the corpus to delete
            force: Skip confirmation prompt

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get corpus info to show what we're deleting
            corpus = rag.get_corpus(name=corpus_name)
            display_name = corpus.display_name

            if not force:
                typer.echo("\nCorpus to delete:")
                typer.echo(f"  Display Name: {display_name}")
                typer.echo(f"  Resource Name: {corpus_name}")

                if not typer.confirm(
                    "\nAre you sure you want to delete this corpus?"
                ):
                    typer.echo("Cancelled.")
                    return False

            typer.echo(f"Deleting corpus: {display_name}")
            rag.delete_corpus(name=corpus_name)

            typer.secho(
                f"Corpus deleted successfully: {display_name}",
                fg=typer.colors.GREEN,
            )
            return True

        except NotFound:
            typer.secho(f"Corpus not found: {corpus_name}", fg=typer.colors.RED)
            return False
        except Exception as e:
            typer.secho(f"Error deleting corpus: {e}", fg=typer.colors.RED)
            return False


@app.command()
def list(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed information.")
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """List all RAG corpora in the project."""
    manager = RAGManager(env_file)
    if not manager.list_corpora(verbose):
        raise typer.Exit(code=1)


@app.command()
def info(
    corpus_name: Annotated[str, typer.Argument(help="Full resource name of the corpus.")],
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Get detailed information about a specific RAG corpus."""
    manager = RAGManager(env_file)
    if not manager.get_corpus_info(corpus_name):
        raise typer.Exit(code=1)


@app.command()
def create(
    display_name: Annotated[str, typer.Argument(help="Display name for the corpus.")],
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Description of the corpus.")
    ] = None,
    embedding_model: Annotated[
        str,
        typer.Option(
            "--embedding-model",
            "-e",
            help="Embedding model to use.",
        ),
    ] = "publishers/google/models/text-embedding-004",
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Create a new RAG corpus."""
    manager = RAGManager(env_file)
    if not manager.create_corpus(display_name, description, embedding_model):
        raise typer.Exit(code=1)


@app.command()
def delete(
    corpus_name: Annotated[str, typer.Argument(help="Full resource name of the corpus to delete.")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation prompt.")
    ] = False,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Delete a RAG corpus."""
    manager = RAGManager(env_file)
    if not manager.delete_corpus(corpus_name, force):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
