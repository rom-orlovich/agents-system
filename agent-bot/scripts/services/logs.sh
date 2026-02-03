#!/bin/bash
set -e

DC="docker-compose"
SERVICE="${1:-}"

if [ -n "$SERVICE" ]; then
    $DC logs -f "$SERVICE"
else
    $DC logs -f
fi
