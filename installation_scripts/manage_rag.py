#!/usr/bin/env python3
"""
RAG Corpus Manager for Google Vertex AI

This script manages RAG corpus operations including listing, creating,
and deleting RAG corpora in Vertex AI.
"""

import os
from pathlib import Path
from typing import Dict, Optional, List

from google.auth import default
from google.api_core.exceptions import NotFound, ResourceExhausted
from google.cloud import storage
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
            verbose: Show detailed information for each corpus (excluding files to prevent loops)

        Returns:
            True if successful, False otherwise
        """
        try:
            typer.echo()  # Blank line before output

            # Iterate directly over the pager - don't use list() to avoid iteration issues
            corpora = []
            for corpus in rag.list_corpora():
                corpora.append(corpus)

            if not corpora:
                typer.echo("No RAG corpora found.")
                return True

            for i, corpus in enumerate(corpora, 1):
                display_name = corpus.display_name
                corpus_name = corpus.name
                description = getattr(corpus, "description", "")

                typer.echo(f"{i}. {display_name}")
                typer.echo(f"   Name: {corpus_name}")
                if description:
                    typer.echo(f"   Description: {description}")

                if verbose:
                    # Only show embedding model in verbose mode, NOT files
                    # File listing causes the infinite loop issue
                    if hasattr(corpus, "embedding_model_config"):
                        config = corpus.embedding_model_config
                        if hasattr(config, "publisher_model"):
                            typer.echo(f"   Embedding Model: {config.publisher_model}")

                    # Show creation time if available
                    if hasattr(corpus, "create_time"):
                        typer.echo(f"   Created: {corpus.create_time}")

                typer.echo()

            typer.echo(f"Total: {len(corpora)} RAG corpus/corpora")

            if verbose:
                typer.echo()
                typer.echo("Note: Use 'rag-info <corpus_name>' to see files in a specific corpus")

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

            # List files separately - NOT during corpus iteration to avoid loops
            typer.echo("\nFiles in corpus:")
            try:
                # Iterate directly over file_list pager to avoid list() conversion issues
                files = []
                for file in rag.list_files(corpus_name=corpus_name):
                    files.append(file)

                if files:
                    typer.echo(f"Total files: {len(files)}")
                    # Limit display to first 10 files to avoid overwhelming output
                    for i, file in enumerate(files[:10], 1):
                        typer.echo(f"{i}. {file.display_name}")
                        if hasattr(file, "size_bytes"):
                            size_mb = file.size_bytes / (1024 * 1024)
                            typer.echo(f"   Size: {size_mb:.2f} MB")
                    if len(files) > 10:
                        typer.echo(f"... and {len(files) - 10} more files")
                else:
                    typer.echo("No files found in corpus.")
            except Exception as e:
                typer.secho(f"Note: Unable to list files: {str(e)[:100]}", fg=typer.colors.YELLOW)

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
            try:
                pager = rag.list_corpora()
                if pager:
                    for existing_corpus in pager:
                        if existing_corpus.display_name == display_name:
                            typer.secho(
                                f" A corpus with display name '{display_name}' already exists.",
                                fg=typer.colors.YELLOW,
                            )
                            typer.echo(f"   Existing corpus: {existing_corpus.name}")
                            return False
            except Exception as e:
                # If we can't list corpora, just proceed with creation
                typer.echo(f"Note: Could not check for existing corpora: {e}")

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
            typer.echo(f"RAG_CORPUS_ID={corpus.name}")
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

    def import_files(
        self,
        corpus_name: str,
        gcs_paths: list,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        timeout: int = 600
    ) -> bool:
        """
        Import files from Google Cloud Storage into a RAG corpus.

        Args:
            corpus_name: Full resource name of the corpus
            gcs_paths: List of GCS URIs (gs://bucket/path/to/file)
            chunk_size: Size of text chunks for indexing
            chunk_overlap: Overlap between chunks
            timeout: Timeout in seconds for the operation

        Returns:
            True if successful, False otherwise
        """
        typer.echo(f"Importing {len(gcs_paths)} file(s) to corpus: {corpus_name}")
        typer.echo(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
        typer.echo()

        try:
            # Verify corpus exists first
            corpus = rag.get_corpus(name=corpus_name)
            typer.echo(f"Target corpus: {corpus.display_name}")
            typer.echo()

            # Vertex AI RAG has a limit of 25 files per import request
            # Split into batches if needed
            BATCH_SIZE = 25
            total_files = len(gcs_paths)
            total_imported = 0

            if total_files > BATCH_SIZE:
                typer.echo(f"Note: Splitting into batches of {BATCH_SIZE} files (API limit)")
                typer.echo()

            # Process in batches
            for batch_num, i in enumerate(range(0, total_files, BATCH_SIZE), 1):
                batch_paths = gcs_paths[i:i + BATCH_SIZE]
                batch_count = len(batch_paths)

                if total_files > BATCH_SIZE:
                    typer.echo(f"Batch {batch_num}: Importing {batch_count} file(s)...")
                else:
                    typer.echo("Starting import...")

                for path in batch_paths:
                    typer.echo(f"  - {path}")
                typer.echo()

                response = rag.import_files(
                    corpus_name=corpus_name,
                    paths=batch_paths,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    timeout=timeout
                )

                # Show import results
                if hasattr(response, 'imported_rag_files_count'):
                    imported = response.imported_rag_files_count
                    total_imported += imported
                    typer.secho(
                        f"Batch {batch_num}: {imported} file(s) imported successfully",
                        fg=typer.colors.GREEN,
                    )
                else:
                    typer.secho(
                        f"Batch {batch_num}: Import initiated successfully",
                        fg=typer.colors.GREEN,
                    )
                typer.echo()

            typer.echo("=" * 80)
            typer.secho(f"All batches completed!", fg=typer.colors.GREEN)
            if total_imported > 0:
                typer.echo(f"Total files imported: {total_imported}/{total_files}")
            typer.echo()
            typer.echo("Note: File processing may continue in the background.")
            typer.echo("Use 'rag-info' to check the corpus status and file count.")

            return True

        except NotFound:
            typer.secho(f"Corpus not found: {corpus_name}", fg=typer.colors.RED)
            return False
        except Exception as e:
            typer.secho(f"Error importing files: {e}", fg=typer.colors.RED)
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


@app.command()
def import_files(
    corpus_name: Annotated[Optional[str], typer.Argument(help="Full resource name of the corpus (or set RAG_CORPUS_ID in .env).")] = None,
    gcs_paths: Annotated[Optional[List[str]], typer.Argument(help="GCS paths (gs://...) to import, or omit to import all from GCS_DEFAULT_BUCKET.")] = None,
    chunk_size: Annotated[
        int, typer.Option("--chunk-size", "-s", help="Size of text chunks for indexing.")
    ] = 512,
    chunk_overlap: Annotated[
        int, typer.Option("--chunk-overlap", "-o", help="Overlap between chunks.")
    ] = 50,
    timeout: Annotated[
        int, typer.Option("--timeout", "-t", help="Timeout in seconds for the operation.")
    ] = 600,
    env_file: Annotated[
        Path, typer.Option(help="Path to the environment file.")
    ] = Path(".env"),
) -> None:
    """Import files from GCS into a RAG corpus."""
    manager = RAGManager(env_file)

    # Get corpus name from argument or environment
    corpus = corpus_name or manager.env_vars.get("RAG_CORPUS_ID")
    if not corpus:
        typer.secho(
            "Error: Corpus name required. Provide as argument or set RAG_CORPUS_ID in .env",
            fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

    # Handle GCS paths - either provided or auto-discover from default bucket
    paths_to_import = gcs_paths

    if not paths_to_import:
        # Auto-discover all files from default bucket
        default_bucket = manager.env_vars.get("GCS_DEFAULT_BUCKET")
        if not default_bucket:
            typer.secho(
                "Error: No GCS paths provided and GCS_DEFAULT_BUCKET not set in .env",
                fg=typer.colors.RED
            )
            typer.echo("Either provide GCS paths or set GCS_DEFAULT_BUCKET in your .env file")
            raise typer.Exit(code=1)

        try:
            # Initialize storage client to list bucket contents
            credentials, _ = default()
            storage_client = storage.Client(
                project=manager.project_id,
                credentials=credentials
            )

            typer.echo(f"Discovering files in bucket: {default_bucket}")
            bucket = storage_client.get_bucket(default_bucket)

            # Get all files from bucket
            paths_to_import = []
            for blob in bucket.list_blobs():
                uri = f"gs://{default_bucket}/{blob.name}"
                paths_to_import.append(uri)

            if not paths_to_import:
                typer.secho(f"No files found in bucket: {default_bucket}", fg=typer.colors.YELLOW)
                return

            typer.echo(f"Found {len(paths_to_import)} file(s) to import:")
            for uri in paths_to_import:
                typer.echo(f"  - {uri}")
            typer.echo()

        except Exception as e:
            typer.secho(f"Error listing bucket contents: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    if not manager.import_files(corpus, paths_to_import, chunk_size, chunk_overlap, timeout):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
