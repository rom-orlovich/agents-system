#!/bin/bash
# ==============================================================================
# Setup Cloudflare Tunnel for persistent webhook URLs
# ==============================================================================
#
# This script sets up a FREE Cloudflare Tunnel for persistent webhook URLs.
# No more ngrok! Your URL never changes.
#
# Features:
# - FREE (no paid subscription needed)
# - Custom domain support
# - Automatic HTTPS
# - DDoS protection
# - Never-changing URL
#
# Prerequisites:
# - Cloudflare account (free)
# - Domain managed by Cloudflare (for named tunnels)
#
# Usage:
#   ./setup-tunnel.sh         # Interactive setup
#   ./setup-tunnel.sh --quick # Quick tunnel (random URL, for testing)
#
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TUNNEL_NAME="${TUNNEL_NAME:-claude-webhooks}"
LOCAL_PORT="${LOCAL_PORT:-8000}"
CONFIG_DIR="${HOME}/.cloudflared"

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           🌐 Cloudflare Tunnel Setup                         ║"
    echo "║           FREE Persistent Webhook URLs                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_cloudflared() {
    if command -v cloudflared &> /dev/null; then
        return 0
    else
        return 1
    fi
}

install_cloudflared() {
    print_step "Installing cloudflared..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install cloudflared
        else
            print_error "Homebrew not found. Please install: https://brew.sh"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        ARCH=$(uname -m)
        if [[ "$ARCH" == "x86_64" ]]; then
            ARCH_PKG="amd64"
        elif [[ "$ARCH" == "aarch64" ]]; then
            ARCH_PKG="arm64"
        else
            print_error "Unsupported architecture: $ARCH"
            exit 1
        fi
        
        curl -L --output /tmp/cloudflared.deb \
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH_PKG}.deb"
        sudo dpkg -i /tmp/cloudflared.deb
        rm /tmp/cloudflared.deb
    else
        print_error "Unsupported OS: $OSTYPE"
        exit 1
    fi
    
    print_success "cloudflared installed"
}

# ==============================================================================
# Quick Tunnel (for testing)
# ==============================================================================

run_quick_tunnel() {
    print_header
    echo ""
    echo -e "${YELLOW}🚀 Starting Quick Tunnel (no account needed)${NC}"
    echo ""
    echo "This creates a temporary tunnel with a random URL."
    echo "URL changes each time you restart!"
    echo ""
    echo "Perfect for:"
    echo "  • Quick testing"
    echo "  • Development"
    echo "  • One-time webhook verification"
    echo ""
    echo "Your webhook will be available at the URL shown below."
    echo "Press Ctrl+C to stop."
    echo ""
    echo "─────────────────────────────────────────────────────────"
    echo ""
    
    cloudflared tunnel --url "http://localhost:${LOCAL_PORT}"
}

# ==============================================================================
# Named Tunnel (persistent URL)
# ==============================================================================

setup_named_tunnel() {
    print_header
    echo ""
    print_step "Setting up Named Tunnel (persistent URL)"
    echo ""
    
    # Check if already logged in
    if [[ -f "${CONFIG_DIR}/cert.pem" ]]; then
        print_success "Already authenticated with Cloudflare"
    else
        print_step "Authenticating with Cloudflare..."
        echo ""
        echo "A browser window will open for login."
        echo "After login, you'll be redirected back."
        echo ""
        read -p "Press Enter to continue..."
        
        cloudflared tunnel login
        
        print_success "Logged in to Cloudflare"
    fi
    
    echo ""
    
    # Check if tunnel exists
    if cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
        print_warning "Tunnel '$TUNNEL_NAME' already exists"
        TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    else
        print_step "Creating tunnel: $TUNNEL_NAME"
        cloudflared tunnel create "$TUNNEL_NAME"
        TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    fi
    
    print_success "Tunnel ID: $TUNNEL_ID"
    echo ""
    
    # Get domain info
    echo "─────────────────────────────────────────────────────────"
    echo ""
    echo "Enter your domain details for the webhook URL."
    echo ""
    read -p "Domain (e.g., example.com): " DOMAIN
    read -p "Subdomain for webhooks (e.g., webhooks): " SUBDOMAIN
    
    if [[ -z "$DOMAIN" ]] || [[ -z "$SUBDOMAIN" ]]; then
        print_error "Domain and subdomain are required"
        exit 1
    fi
    
    WEBHOOK_HOSTNAME="${SUBDOMAIN}.${DOMAIN}"
    
    echo ""
    print_step "Creating tunnel configuration..."
    
    mkdir -p "$CONFIG_DIR"
    
    cat > "${CONFIG_DIR}/config.yml" << EOF
# Cloudflare Tunnel Configuration
# Generated by setup-tunnel.sh
# Date: $(date -Iseconds)

tunnel: ${TUNNEL_ID}
credentials-file: ${CONFIG_DIR}/${TUNNEL_ID}.json

ingress:
  # Main webhook endpoint
  - hostname: ${WEBHOOK_HOSTNAME}
    service: http://localhost:${LOCAL_PORT}
    originRequest:
      noTLSVerify: true
  
  # Catch-all (required)
  - service: http_status:404
EOF
    
    print_success "Configuration saved to ${CONFIG_DIR}/config.yml"
    echo ""
    
    # DNS instructions
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "${YELLOW}📋 DNS Configuration Required${NC}"
    echo ""
    echo "Go to Cloudflare Dashboard → DNS → Add Record:"
    echo ""
    echo "  Type:    CNAME"
    echo "  Name:    ${SUBDOMAIN}"
    echo "  Target:  ${TUNNEL_ID}.cfargotunnel.com"
    echo "  Proxy:   ✅ Enabled (orange cloud)"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    read -p "Press Enter after configuring DNS..."
    
    # Create systemd service file (optional)
    echo ""
    echo "Would you like to run the tunnel as a system service?"
    echo "This will start automatically on boot."
    echo ""
    read -p "Install as service? [y/N]: " INSTALL_SERVICE
    
    if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
        print_step "Installing as service..."
        sudo cloudflared service install
        sudo systemctl enable cloudflared
        sudo systemctl start cloudflared
        print_success "Tunnel service installed and started"
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    print_success "Setup complete!"
    echo ""
    echo "Your persistent webhook URL:"
    echo -e "  ${GREEN}https://${WEBHOOK_HOSTNAME}${NC}"
    echo ""
    echo "This URL will NEVER change!"
    echo ""
    echo "Configure this URL in:"
    echo "  • GitHub Webhooks: https://${WEBHOOK_HOSTNAME}/webhook/github"
    echo "  • Jira Webhooks:   https://${WEBHOOK_HOSTNAME}/webhook/jira"
    echo "  • Slack Events:    https://${WEBHOOK_HOSTNAME}/webhook/slack"
    echo ""
    echo "To start tunnel manually:"
    echo "  cloudflared tunnel run ${TUNNEL_NAME}"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    # Check for quick tunnel flag
    if [[ "$1" == "--quick" ]] || [[ "$1" == "-q" ]]; then
        if ! check_cloudflared; then
            install_cloudflared
        fi
        run_quick_tunnel
        exit 0
    fi
    
    # Interactive setup
    print_header
    echo ""
    
    # Install cloudflared if needed
    if ! check_cloudflared; then
        install_cloudflared
    else
        print_success "cloudflared is installed"
    fi
    
    echo ""
    echo "Choose setup mode:"
    echo ""
    echo "  1) Quick Tunnel"
    echo "     • Random URL (*.trycloudflare.com)"
    echo "     • No account needed"
    echo "     • URL changes each restart"
    echo "     • Great for testing"
    echo ""
    echo "  2) Named Tunnel (Recommended)"
    echo "     • Custom domain (webhooks.yourdomain.com)"
    echo "     • Requires Cloudflare account"
    echo "     • URL never changes"
    echo "     • Production ready"
    echo ""
    read -p "Enter choice [1/2]: " choice
    
    case $choice in
        1)
            run_quick_tunnel
            ;;
        2)
            setup_named_tunnel
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
