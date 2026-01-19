#!/bin/bash
# Extract OAuth credentials from macOS Keychain for Docker containers
# This allows using Claude Pro/Team subscription instead of pay-per-use API key

CREDS_FILE="${1:-$HOME/.claude/.credentials.json}"
KEYCHAIN_SERVICE="Claude Code-credentials"
KEYCHAIN_ACCOUNT="${USER}"

echo "🔑 Extracting Claude OAuth credentials from macOS Keychain..."

# Extract credentials from Keychain
CREDS=$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null || true)

if [ -z "$CREDS" ] || [ "$CREDS" = "" ]; then
    echo "⚠️  No Claude credentials found in Keychain"
    echo ""
    echo "Running 'claude login' to authenticate..."
    echo ""

    # Run claude login interactively
    if claude login; then
        echo ""
        echo "✅ Login successful! Extracting credentials..."
        # Try again after login
        CREDS=$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null || true)

        if [ -z "$CREDS" ] || [ "$CREDS" = "" ]; then
            echo "❌ Still couldn't find credentials after login"
            echo "Please check your Keychain or use ANTHROPIC_API_KEY instead"
            exit 1
        fi
    else
        echo "❌ Login failed or cancelled"
        echo ""
        echo "You can either:"
        echo "  1. Run 'claude login' manually and try again"
        echo "  2. Set ANTHROPIC_API_KEY in infrastructure/docker/.env"
        exit 1
    fi
fi

# Create directory if needed
mkdir -p "$(dirname "$CREDS_FILE")"

# Write credentials to file
echo "$CREDS" > "$CREDS_FILE"
chmod 600 "$CREDS_FILE"

echo "✅ Credentials extracted to: $CREDS_FILE"
echo ""
echo "You can now start Docker containers that mount this file."
