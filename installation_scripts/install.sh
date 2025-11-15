#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting setup..."

# Install uv
apt-get update
apt-get install -y curl
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

# These commands will now work for ANY user because uv and uvx
# are installed in /usr/local/bin/ which is in everyone's default PATH.
uv --version
uvx --version
