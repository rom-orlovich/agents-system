#!/bin/bash
# Machine Setup Script for Claude Code CLI POC
# Run this on a fresh Ubuntu 22.04/24.04 EC2 instance

set -e

echo "=== Claude Code CLI POC - Machine Setup ==="

# Update system
echo ">>> Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# Install core tools
echo ">>> Installing core tools..."
sudo apt-get install -y \
    git \
    curl \
    jq \
    docker.io \
    docker-compose-plugin

# Install Node.js 20
echo ">>> Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Claude Code CLI
echo ">>> Installing Claude Code CLI..."
sudo npm install -g @anthropic-ai/claude-code

# Install GitHub CLI
echo ">>> Installing GitHub CLI..."
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update \
    && sudo apt install gh -y

# Docker setup
echo ">>> Configuring Docker..."
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# Create directory structure
echo ">>> Creating directory structure..."
mkdir -p ~/claude-agent-poc
mkdir -p ~/workspace/repos

# Print next steps
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Log out and log back in (for docker group)"
echo "2. Authenticate Claude CLI: claude login"
echo "3. Authenticate GitHub CLI: gh auth login"
echo "4. Clone the POC repository"
echo "5. Configure .env file"
echo "6. Run: docker compose up -d"
echo ""
