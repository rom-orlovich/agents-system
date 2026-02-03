#!/bin/bash
set -e

PROVIDER="${1:-claude}"
DC="docker-compose"

$DC -f docker-compose.cli.yml -p "$PROVIDER-cli" logs -f cli
