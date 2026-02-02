#!/bin/bash
set -e

NGROK_DOMAIN="unabating-unoverdrawn-veronique.ngrok-free.dev"
PORT=8010

echo "Starting ngrok tunnel..."
echo "Domain: $NGROK_DOMAIN"
echo "Port: $PORT"
echo ""
echo "OAuth callback URLs:"
echo "  GitHub: https://$NGROK_DOMAIN/oauth/callback/github"
echo "  Slack:  https://$NGROK_DOMAIN/oauth/callback/slack"
echo "  Jira:   https://$NGROK_DOMAIN/oauth/callback/jira"
echo ""
echo "Press Ctrl+C to stop"
echo ""

ngrok http $PORT --domain=$NGROK_DOMAIN
