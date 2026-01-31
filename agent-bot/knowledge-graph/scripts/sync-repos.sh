#!/bin/bash
set -e

REPOS_DIR="${REPOS_DIR:-/data/repos}"
GKG_DATA_DIR="${GKG_DATA_DIR:-/data/graphs}"
REPOS_CONFIG="${REPOS_CONFIG:-/app/config/repos.json}"
LOG_FILE="${GKG_DATA_DIR}/sync.log"

mkdir -p "$REPOS_DIR" "$GKG_DATA_DIR"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

sync_repo() {
    local repo_url="$1"
    local repo_name="$2"
    local repo_path="${REPOS_DIR}/${repo_name}"

    log "Processing repository: $repo_name"

    if [ -d "$repo_path/.git" ]; then
        log "Updating existing repository..."
        cd "$repo_path"
        git fetch --all --prune 2>/dev/null || log "Fetch failed, continuing..."
        git reset --hard origin/$(git symbolic-ref --short HEAD 2>/dev/null || echo "main") 2>/dev/null || \
            git reset --hard origin/main 2>/dev/null || \
            git reset --hard origin/master 2>/dev/null || \
            log "Reset failed, continuing with existing state"
        cd - > /dev/null
    else
        log "Cloning new repository..."
        git clone --depth=1 "$repo_url" "$repo_path" 2>/dev/null || {
            log "Clone failed for $repo_name"
            return 1
        }
    fi

    return 0
}

index_repo() {
    local repo_name="$1"
    local repo_path="${REPOS_DIR}/${repo_name}"
    local graph_path="${GKG_DATA_DIR}/${repo_name}"

    log "Indexing repository: $repo_name"

    mkdir -p "$graph_path"

    cd "$repo_path"
    gkg index --output "$graph_path" 2>&1 | while read line; do
        log "  [gkg] $line"
    done

    if [ $? -eq 0 ]; then
        log "Indexing completed for $repo_name"
        echo "$(date -Iseconds)" > "${graph_path}/.last_indexed"
    else
        log "Indexing failed for $repo_name"
        return 1
    fi

    cd - > /dev/null
    return 0
}

sync_local_repos() {
    log "Scanning for local repositories..."

    if [ -d "$REPOS_DIR" ]; then
        for repo_path in "$REPOS_DIR"/*/.git; do
            if [ -d "$repo_path" ]; then
                repo_name=$(basename "$(dirname "$repo_path")")
                log "Found local repository: $repo_name"

                cd "$(dirname "$repo_path")"
                git fetch --all --prune 2>/dev/null || log "Fetch failed for $repo_name"
                git pull --ff-only 2>/dev/null || log "Pull failed for $repo_name, continuing..."
                cd - > /dev/null

                index_repo "$repo_name" || log "Index failed for $repo_name"
            fi
        done
    fi
}

sync_from_config() {
    if [ ! -f "$REPOS_CONFIG" ]; then
        log "No repos.json config found at $REPOS_CONFIG"
        return 0
    fi

    log "Reading repositories from config..."

    jq -r '.repositories[] | "\(.url)|\(.name)"' "$REPOS_CONFIG" 2>/dev/null | while IFS='|' read -r url name; do
        if [ -n "$url" ] && [ -n "$name" ]; then
            sync_repo "$url" "$name" && index_repo "$name"
        fi
    done
}

sync_from_env() {
    if [ -n "$REPO_URLS" ]; then
        log "Reading repositories from REPO_URLS environment variable..."

        IFS=',' read -ra repos <<< "$REPO_URLS"
        for repo_url in "${repos[@]}"; do
            repo_name=$(basename "$repo_url" .git)
            sync_repo "$repo_url" "$repo_name" && index_repo "$repo_name"
        done
    fi
}

main() {
    log "========================================="
    log "Starting Knowledge Graph Repository Sync"
    log "========================================="
    log "REPOS_DIR: $REPOS_DIR"
    log "GKG_DATA_DIR: $GKG_DATA_DIR"

    sync_from_env

    sync_from_config

    sync_local_repos

    log "========================================="
    log "Repository sync completed"
    log "========================================="

    echo ""
    log "Graph statistics:"
    for graph_dir in "$GKG_DATA_DIR"/*; do
        if [ -d "$graph_dir" ] && [ -f "${graph_dir}/.last_indexed" ]; then
            graph_name=$(basename "$graph_dir")
            last_indexed=$(cat "${graph_dir}/.last_indexed")
            log "  - $graph_name (last indexed: $last_indexed)"
        fi
    done
}

main "$@"
