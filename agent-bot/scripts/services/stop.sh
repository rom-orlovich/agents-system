#!/bin/bash
set -e

DC="docker-compose"

echo "Stopping Agent Bot services..."
$DC down
echo "✅ Services stopped"
