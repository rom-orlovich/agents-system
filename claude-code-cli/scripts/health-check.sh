#!/bin/bash
# ==============================================================================
# Health Check Script
# ==============================================================================
#
# Checks the health of all components:
# - Local services (Redis, Postgres, webhook-server)
# - Claude CLI authentication
# - MCP servers
# - Network connectivity
#
# Usage:
#   ./scripts/health-check.sh              # Full health check
#   ./scripts/health-check.sh --quick      # Quick check (local only)
#   ./scripts/health-check.sh --verbose    # Detailed output
#
# ==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VERBOSE=false
QUICK=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --verbose|-v) VERBOSE=true ;;
        --quick|-q) QUICK=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  🏥 Health Check: AI Agent System${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

check_pass() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "  ${RED}❌ $1${NC}"
    if [ "$2" != "" ]; then
        echo -e "     ${RED}→ $2${NC}"
    fi
}

check_warn() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
    if [ "$2" != "" ]; then
        echo -e "     ${YELLOW}→ $2${NC}"
    fi
}

section() {
    echo ""
    echo -e "${YELLOW}▸ $1${NC}"
}

verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "  ${BLUE}ℹ️  $1${NC}"
    fi
}

# ==============================================================================
# Checks
# ==============================================================================

check_claude_cli() {
    section "Claude CLI"
    
    if command -v claude &> /dev/null; then
        check_pass "Claude CLI installed"
        
        # Get version
        local version=$(claude --version 2>/dev/null || echo "unknown")
        verbose "Version: $version"
        
        # Check credentials
        if [ -f "$HOME/.claude/.credentials.json" ]; then
            check_pass "Credentials file exists"
            
            # Check if token is expired
            local expires=$(python3 -c "import json; print(json.load(open('$HOME/.claude/.credentials.json')).get('expiry', 'unknown'))" 2>/dev/null || echo "unknown")
            verbose "Token expires: $expires"
        else
            check_fail "Credentials file missing" "Run: claude auth login"
        fi
    else
        check_fail "Claude CLI not installed" "Install from https://docs.anthropic.com/en/docs/claude-code"
    fi
}

check_redis() {
    section "Redis"
    
    # Check if redis-cli is available
    if command -v redis-cli &> /dev/null; then
        # Try to ping Redis
        local ping=$(redis-cli -h localhost ping 2>/dev/null || echo "FAILED")
        if [ "$ping" = "PONG" ]; then
            check_pass "Redis responding"
            
            # Check queue lengths
            local planning=$(redis-cli -h localhost llen planning_queue 2>/dev/null || echo "0")
            local execution=$(redis-cli -h localhost llen execution_queue 2>/dev/null || echo "0")
            verbose "Planning queue: $planning tasks"
            verbose "Execution queue: $execution tasks"
        else
            check_fail "Redis not responding" "Check if Redis is running"
        fi
    else
        # Try via Docker
        if docker ps 2>/dev/null | grep -q redis; then
            check_pass "Redis running (Docker)"
        else
            check_fail "Redis not available"
        fi
    fi
}

check_postgres() {
    section "PostgreSQL"
    
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h localhost -p 5432 &> /dev/null; then
            check_pass "PostgreSQL responding"
        else
            check_fail "PostgreSQL not responding"
        fi
    else
        # Try via Docker
        if docker ps 2>/dev/null | grep -q postgres; then
            check_pass "PostgreSQL running (Docker)"
        else
            check_warn "PostgreSQL status unknown"
        fi
    fi
}

check_webhook_server() {
    section "Webhook Server"
    
    # Check if webhook server is running
    if curl -s http://localhost:8000/health &> /dev/null; then
        check_pass "Webhook server responding"
        
        # Check individual endpoints
        if curl -s http://localhost:8000/webhook/github/test 2>/dev/null | grep -q "working"; then
            check_pass "GitHub webhook endpoint"
        fi
        if curl -s http://localhost:8000/webhook/slack/test 2>/dev/null | grep -q "working"; then
            check_pass "Slack webhook endpoint"
        fi
        if curl -s http://localhost:8000/webhook/jira/test 2>/dev/null | grep -q "working"; then
            check_pass "Jira webhook endpoint"
        fi
    else
        check_fail "Webhook server not responding" "Start with: make start"
    fi
}

check_mcp_servers() {
    section "MCP Servers"
    
    if [ "$QUICK" = true ]; then
        verbose "Skipping MCP checks (quick mode)"
        return
    fi
    
    # Check MCP config
    local mcp_config="$HOME/.claude/mcp.json"
    if [ -f "$mcp_config" ]; then
        check_pass "MCP config exists"
        
        # Parse and check servers
        local servers=$(python3 -c "import json; print(' '.join(json.load(open('$mcp_config')).get('mcpServers', {}).keys()))" 2>/dev/null || echo "")
        for server in $servers; do
            verbose "MCP server configured: $server"
        done
    else
        check_warn "MCP config not found"
    fi
    
    # Check if GitHub MCP works (requires Docker)
    if docker ps 2>/dev/null | grep -q "github-mcp-server"; then
        check_pass "GitHub MCP server running"
    else
        verbose "GitHub MCP not running (will start with claude)"
    fi
}

check_environment() {
    section "Environment Variables"
    
    # Required variables
    local required_vars=(
        "GITHUB_TOKEN"
    )
    
    # Optional but recommended
    local optional_vars=(
        "SLACK_BOT_TOKEN"
        "JIRA_API_TOKEN"
        "SENTRY_AUTH_TOKEN"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -n "${!var}" ]; then
            check_pass "$var configured"
        else
            check_fail "$var not set" "Required for operation"
        fi
    done
    
    for var in "${optional_vars[@]}"; do
        if [ -n "${!var}" ]; then
            check_pass "$var configured"
        else
            check_warn "$var not set (optional)"
        fi
    done
}

check_docker() {
    section "Docker"
    
    if command -v docker &> /dev/null; then
        check_pass "Docker installed"
        
        if docker ps &> /dev/null; then
            check_pass "Docker daemon running"
            
            # Check for agent containers
            local containers=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E 'planning|executor|webhook' | wc -l)
            verbose "Agent containers running: $containers"
        else
            check_fail "Docker daemon not running"
        fi
    else
        check_fail "Docker not installed"
    fi
}

check_skills() {
    section "Skills"
    
    local skills_dir="$HOME/.claude/skills"
    
    if [ -d "$skills_dir" ]; then
        local count=$(find "$skills_dir" -name "SKILL.md" | wc -l)
        if [ "$count" -gt 0 ]; then
            check_pass "$count skills installed"
            
            for skill_dir in "$skills_dir"/*/; do
                if [ -f "${skill_dir}SKILL.md" ]; then
                    verbose "Skill: $(basename "$skill_dir")"
                fi
            done
        else
            check_warn "Skills directory exists but no skills found"
        fi
    else
        check_warn "Skills not installed" "Run: ./scripts/setup-skills.sh"
    fi
}

check_tunnel() {
    section "Cloudflare Tunnel"
    
    if command -v cloudflared &> /dev/null; then
        check_pass "cloudflared installed"
        
        # Check if tunnel is running
        if pgrep -x cloudflared &> /dev/null; then
            check_pass "Tunnel running"
        else
            check_warn "Tunnel not running" "Start with: cloudflared tunnel run"
        fi
    else
        check_warn "cloudflared not installed" "Run: ./scripts/setup-tunnel.sh"
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    print_header
    
    check_docker
    check_claude_cli
    check_redis
    check_postgres
    check_webhook_server
    check_environment
    check_skills
    
    if [ "$QUICK" != true ]; then
        check_mcp_servers
        check_tunnel
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Health check complete!${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

main "$@"
