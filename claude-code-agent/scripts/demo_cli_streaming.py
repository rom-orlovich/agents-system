#!/usr/bin/env python3
"""
Demo script to run Claude CLI and stream logs showing thinking + sub-agent output.

Usage:
    uv run python scripts/demo_cli_streaming.py

This demonstrates:
- Live streaming of Claude CLI output
- Main agent thinking/output
- Sub-agent thinking/output (if configured)
- JSON stream format parsing
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cli_runner import run_claude_cli, CLIResult
from core.subagent_config import get_default_subagents

# ANSI colors for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Message types
    MAIN_AGENT = "\033[36m"    # Cyan
    SUB_AGENT = "\033[35m"     # Magenta  
    THINKING = "\033[33m"      # Yellow
    TOOL = "\033[32m"          # Green
    ERROR = "\033[31m"         # Red
    INFO = "\033[34m"          # Blue
    RESULT = "\033[92m"        # Light green
    DEBUG = "\033[90m"         # Gray


async def pretty_print_stream(queue: asyncio.Queue, show_raw: bool = False):
    """
    Read from output queue and print formatted streaming output.
    
    This shows how you can parse and format the streaming logs.
    """
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        
        # Remove trailing newlines for cleaner display
        chunk = chunk.rstrip('\n')
        
        if not chunk:
            continue
        
        if show_raw:
            print(f"{Colors.DIM}[RAW] {chunk}{Colors.RESET}")
        
        # Try to colorize based on content
        if chunk.startswith("[LOG]"):
            # Log lines from stderr (debug/verbose output)
            log_content = chunk[5:].strip()
            if "error" in log_content.lower():
                print(f"{Colors.ERROR}⚠️  {log_content}{Colors.RESET}")
            elif "thinking" in log_content.lower():
                print(f"{Colors.THINKING}💭 {log_content}{Colors.RESET}")
            elif "debug" in log_content.lower():
                print(f"{Colors.DEBUG}🔍 {log_content}{Colors.RESET}")
            elif "subagent" in log_content.lower() or "sub-agent" in log_content.lower():
                print(f"{Colors.SUB_AGENT}🔧 SUB-AGENT: {log_content}{Colors.RESET}")
            else:
                print(f"{Colors.INFO}📋 {log_content}{Colors.RESET}")
        elif chunk.startswith("[assistant]"):
            # Main agent response
            content = chunk[11:].strip()
            print(f"{Colors.MAIN_AGENT}🤖 {content}{Colors.RESET}")
        elif chunk.startswith("[user]"):
            # User messages
            content = chunk[6:].strip()
            print(f"{Colors.BOLD}👤 {content}{Colors.RESET}")
        elif "subagent" in chunk.lower() or "sub-agent" in chunk.lower():
            # Sub-agent output
            print(f"{Colors.SUB_AGENT}🔧 {chunk}{Colors.RESET}")
        elif "tool_use" in chunk.lower() or "function" in chunk.lower():
            # Tool usage
            print(f"{Colors.TOOL}🛠️  {chunk}{Colors.RESET}")
        else:
            # Default: just print the chunk (this includes streaming text)
            # Print character by character for "typing" effect
            sys.stdout.write(f"{Colors.MAIN_AGENT}")
            sys.stdout.write(chunk)
            sys.stdout.write(f"{Colors.RESET}")
            sys.stdout.flush()


async def run_demo_task(use_subagents: bool = False, debug: bool = False):
    """
    Run a simple demo task to show streaming output.
    """
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}🚀 Claude CLI Streaming Demo{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    # Demo prompt - asking for step-by-step thinking
    demo_prompt = """
    Think step-by-step about this simple task:
    
    1. What are the 3 main benefits of TDD (Test-Driven Development)?
    2. Give a one-line summary.
    
    Show your reasoning process briefly.
    """
    
    # Use current directory as working dir
    working_dir = Path(__file__).parent.parent
    
    # Create output queue
    output_queue = asyncio.Queue()
    
    # Optional: enable sub-agents for demo
    subagents_json = get_default_subagents() if use_subagents else None
    
    print(f"{Colors.INFO}📁 Working directory: {working_dir}{Colors.RESET}")
    print(f"{Colors.INFO}🎯 Demo prompt: TDD benefits analysis{Colors.RESET}")
    print(f"{Colors.INFO}⏱️  Starting at: {datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.INFO}🔧 Sub-agents: {'Enabled' if use_subagents else 'Disabled'}{Colors.RESET}")
    print(f"{Colors.INFO}🔍 Debug mode: {'Enabled' if debug else 'Disabled'}{Colors.RESET}")
    print(f"\n{Colors.DIM}{'─'*60}{Colors.RESET}\n")
    print(f"{Colors.BOLD}📡 STREAMING OUTPUT:{Colors.RESET}\n")
    
    # Debug filter - show everything except statsig which is noisy
    debug_mode = "!statsig" if debug else None
    
    # Run CLI and stream output concurrently
    try:
        result, _ = await asyncio.gather(
            run_claude_cli(
                prompt=demo_prompt,
                working_dir=working_dir,
                output_queue=output_queue,
                task_id="demo-task-001",
                timeout_seconds=120,  # 2 min timeout for demo
                agents=subagents_json,  # Enable sub-agents if requested
                debug_mode=debug_mode,  # Enable debug if requested
            ),
            pretty_print_stream(output_queue, show_raw=False)
        )
        
        # Print final results
        print(f"\n\n{Colors.DIM}{'─'*60}{Colors.RESET}")
        print(f"\n{Colors.BOLD}📊 RESULTS:{Colors.RESET}")
        print(f"  {Colors.RESULT}✅ Success: {result.success}{Colors.RESET}")
        print(f"  💰 Cost: ${result.cost_usd:.4f}")
        print(f"  📊 Tokens: {result.input_tokens:,} in / {result.output_tokens:,} out")
        
        if result.error:
            print(f"  {Colors.ERROR}❌ Error: {result.error}{Colors.RESET}")
        
        return result
        
    except Exception as e:
        print(f"\n{Colors.ERROR}❌ Error running demo: {e}{Colors.RESET}")
        raise


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude CLI Streaming Demo")
    parser.add_argument("--subagents", action="store_true", help="Enable sub-agents")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for detailed logs")
    parser.add_argument("--raw", action="store_true", help="Show raw output chunks")
    args = parser.parse_args()
    
    print(f"""
{Colors.BOLD}Claude CLI Streaming Demo{Colors.RESET}
{Colors.DIM}─────────────────────────{Colors.RESET}

This demo shows how to:
1. Stream Claude CLI output in real-time
2. Parse JSON stream format
3. Display main agent + sub-agent thinking
4. Track costs and token usage

{Colors.INFO}Options:{Colors.RESET}
  --subagents  Enable sub-agent configuration
  --debug      Enable debug mode for detailed logs

{Colors.INFO}Requirements:{Colors.RESET}
- Claude CLI installed and authenticated (`claude login`)
- Environment properly configured

{Colors.INFO}Press Ctrl+C to cancel at any time.{Colors.RESET}
""")
    
    # Check if claude CLI is available
    import shutil
    if not shutil.which("claude"):
        print(f"\n{Colors.ERROR}❌ Claude CLI not found in PATH!{Colors.RESET}")
        print(f"{Colors.DIM}Install: https://code.claude.com{Colors.RESET}")
        return 1
    
    try:
        result = await run_demo_task(
            use_subagents=args.subagents,
            debug=args.debug
        )
        return 0 if result.success else 1
    except KeyboardInterrupt:
        print(f"\n\n{Colors.INFO}⏹️  Demo cancelled by user{Colors.RESET}")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
