#!/bin/bash

REPOS_DIR="/app/repos"
mkdir -p "$REPOS_DIR"

if [ -n "$GITHUB_REPOS" ]; then
    IFS=',' read -ra REPOS <<< "$GITHUB_REPOS"
    for repo in "${REPOS[@]}"; do
        repo_name=$(basename "$repo" .git)
        if [ ! -d "$REPOS_DIR/$repo_name" ]; then
            echo "Cloning $repo..."
            git clone "https://github.com/$repo.git" "$REPOS_DIR/$repo_name"
        else
            echo "Updating $repo_name..."
            cd "$REPOS_DIR/$repo_name" && git pull
        fi
    done
fi

echo "Repository setup complete"
