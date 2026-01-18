#!/bin/bash
# Deploy Claude Code CLI POC to EC2
# Usage: ./deploy.sh <EC2_HOST> [SSH_KEY]

set -e

EC2_HOST=${1:-""}
SSH_KEY=${2:-"~/.ssh/id_rsa"}

if [ -z "$EC2_HOST" ]; then
    echo "Usage: ./deploy.sh <EC2_HOST> [SSH_KEY]"
    echo "Example: ./deploy.sh ubuntu@ec2-12-34-56-78.compute.amazonaws.com"
    exit 1
fi

REMOTE_DIR="/home/ubuntu/claude-agent-poc"
LOCAL_DIR=$(dirname $(dirname $(realpath $0)))

echo "=== Deploying Claude Code CLI POC ==="
echo "Host: $EC2_HOST"
echo "Local: $LOCAL_DIR"
echo "Remote: $REMOTE_DIR"

# Create remote directory
echo ">>> Creating remote directory..."
ssh -i "$SSH_KEY" "$EC2_HOST" "mkdir -p $REMOTE_DIR"

# Sync files
echo ">>> Syncing files..."
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude '*.pyc' \
    --exclude '.env' \
    -e "ssh -i $SSH_KEY" \
    "$LOCAL_DIR/" "$EC2_HOST:$REMOTE_DIR/"

# Check if .env exists on remote
echo ">>> Checking configuration..."
ssh -i "$SSH_KEY" "$EC2_HOST" "
    cd $REMOTE_DIR
    if [ ! -f .env ]; then
        echo 'WARNING: .env file not found!'
        echo 'Please create .env from .env.example and configure it.'
        cp .env.example .env
        echo 'Created .env from template - please edit it!'
    fi
"

# Build and start containers
echo ">>> Building and starting containers..."
ssh -i "$SSH_KEY" "$EC2_HOST" "
    cd $REMOTE_DIR
    docker compose build
    docker compose up -d
"

# Show status
echo ">>> Checking status..."
ssh -i "$SSH_KEY" "$EC2_HOST" "
    cd $REMOTE_DIR
    docker compose ps
"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Webhook endpoints:"
echo "  - Jira:   http://$EC2_HOST:8000/jira-webhook"
echo "  - Sentry: http://$EC2_HOST:8000/sentry-webhook"
echo "  - GitHub: http://$EC2_HOST:8000/github-webhook"
echo ""
echo "To view logs:"
echo "  ssh -i $SSH_KEY $EC2_HOST 'cd $REMOTE_DIR && docker compose logs -f'"
echo ""
