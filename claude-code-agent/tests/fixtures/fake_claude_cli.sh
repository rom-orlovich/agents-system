#!/bin/bash
#
# Fake Claude CLI for Testing
# ===========================
#
# This script simulates Claude CLI behavior without making API calls.
# It reads the FAKE_CLAUDE_MODE environment variable to determine response.
#
# Usage:
#   export FAKE_CLAUDE_MODE=success
#   ./fake_claude_cli.sh -p "test prompt"
#
# Modes:
#   - success: Return successful JSON output
#   - error: Return API error
#   - timeout: Sleep indefinitely (for timeout tests)
#   - malformed: Return malformed JSON
#   - auth_error: Return authentication error
#   - syntax_error: Return unrecognized flag error
#

set -euo pipefail

# Default mode
MODE="${FAKE_CLAUDE_MODE:-success}"

# Parse flags to validate syntax
VALID_COMMAND=true
PROMPT=""
MODEL=""
ALLOWED_TOOLS=""
AGENTS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p)
            shift
            ;;
        --output-format)
            if [[ "$2" != "json" ]]; then
                echo "Error: --output-format only supports 'json'" >&2
                exit 1
            fi
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --allowedTools)
            ALLOWED_TOOLS="$2"
            shift 2
            ;;
        --agents)
            AGENTS="$2"
            shift 2
            ;;
        --dangerously-skip-permissions)
            shift
            ;;
        --)
            shift
            PROMPT="$*"
            break
            ;;
        --version)
            echo "Claude CLI v1.0.0 (fake)"
            exit 0
            ;;
        --help)
            cat <<EOF
Claude Code CLI (Fake for Testing)

Usage:
  claude [options] -- <prompt>

Options:
  -p                              Print mode (headless)
  --output-format json            Output format (only json supported)
  --model <model>                 Model to use (opus, sonnet, haiku)
  --allowedTools <tools>          Comma-separated list of allowed tools
  --agents <json>                 JSON sub-agent configuration
  --dangerously-skip-permissions  Skip permission prompts
  --version                       Show version
  --help                          Show this help

Environment Variables:
  FAKE_CLAUDE_MODE  Response mode (success, error, timeout, malformed, auth_error)
EOF
            exit 0
            ;;
        *)
            echo "Error: Unrecognized option: $1" >&2
            echo "Run 'claude --help' for usage information" >&2
            exit 2
            ;;
    esac
done

# Simulate different modes
case "$MODE" in
    success)
        # Simulate successful execution with JSON output
        cat <<EOF
{"type":"content","content":"Analyzing the prompt..."}
{"type":"content","content":"The answer is: 42"}
{"type":"result","cost_usd":0.001234,"input_tokens":150,"output_tokens":50}
EOF
        exit 0
        ;;

    error)
        # Simulate general error
        echo "Error: Task execution failed" >&2
        exit 1
        ;;

    timeout)
        # Simulate hanging process (for timeout tests)
        sleep 3600
        ;;

    malformed)
        # Simulate malformed JSON output
        echo '{"type":"content","content":"Test'
        echo 'Invalid JSON line'
        exit 0
        ;;

    auth_error)
        # Simulate authentication error
        cat >&2 <<EOF
Error: Authentication failed

Your API key is invalid or missing. Please check:
- ANTHROPIC_API_KEY environment variable
- ~/.config/claude/credentials.json

Visit https://console.anthropic.com to get your API key.
EOF
        exit 1
        ;;

    syntax_error)
        # Simulate unrecognized flag error
        echo "Error: Unrecognized option: --unknown-flag" >&2
        echo "Run 'claude --help' for usage information" >&2
        exit 2
        ;;

    model_error)
        # Simulate model not found
        echo "Error: Model '$MODEL' not found. Available models: opus, sonnet, haiku" >&2
        exit 1
        ;;

    tools_error)
        # Simulate invalid tools
        echo "Error: Unknown tool in --allowedTools: InvalidTool" >&2
        echo "Available tools: Read, Write, Edit, Bash, Glob, Grep" >&2
        exit 1
        ;;

    agents_error)
        # Simulate invalid agents JSON
        echo "Error: Invalid JSON in --agents flag" >&2
        echo "Expected format: {\"agent_name\":{\"description\":\"...\",\"skills\":[...]}}" >&2
        exit 1
        ;;

    streaming)
        # Simulate streaming output (slower)
        for i in {1..5}; do
            echo "{\"type\":\"content\",\"content\":\"Processing step $i...\"}"
            sleep 0.1
        done
        echo '{"type":"result","cost_usd":0.002,"input_tokens":200,"output_tokens":100}'
        exit 0
        ;;

    *)
        echo "Error: Unknown FAKE_CLAUDE_MODE: $MODE" >&2
        echo "Valid modes: success, error, timeout, malformed, auth_error, syntax_error" >&2
        exit 1
        ;;
esac
