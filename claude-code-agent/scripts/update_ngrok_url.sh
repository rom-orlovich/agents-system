#!/bin/bash
# Auto-update WEBHOOK_PUBLIC_DOMAIN in .env with current ngrok URL

echo "🔍 Fetching current ngrok URL..."

# Wait for ngrok to start
sleep 2

# Get ngrok URL from API
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | grep -o 'https://[^"]*' | head -1 | sed 's/https:\/\///')

if [ -z "$NGROK_URL" ]; then
    echo "❌ Error: Could not fetch ngrok URL. Make sure ngrok is running."
    exit 1
fi

echo "✅ Found ngrok URL: $NGROK_URL"

# Update .env file
if [ -f .env ]; then
    # Check if WEBHOOK_PUBLIC_DOMAIN exists
    if grep -q "WEBHOOK_PUBLIC_DOMAIN=" .env; then
        # Update existing line
        sed -i.bak "s|WEBHOOK_PUBLIC_DOMAIN=.*|WEBHOOK_PUBLIC_DOMAIN=$NGROK_URL|" .env
        echo "✅ Updated WEBHOOK_PUBLIC_DOMAIN in .env"
    else
        # Add new line
        echo "WEBHOOK_PUBLIC_DOMAIN=$NGROK_URL" >> .env
        echo "✅ Added WEBHOOK_PUBLIC_DOMAIN to .env"
    fi
    
    # Restart app to pick up new URL
    echo "🔄 Restarting app..."
    docker-compose restart app
    
    echo "✅ Done! Dashboard now shows: https://$NGROK_URL"
else
    echo "❌ Error: .env file not found"
    exit 1
fi
