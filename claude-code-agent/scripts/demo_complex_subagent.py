#!/usr/bin/env python3
"""
Demo script to test Claude CLI sub-agent Tasks features with complex prompts.

Usage:
    uv run python scripts/demo_complex_subagent.py

This demonstrates:
- Sub-agent delegation via Claude CLI --agents flag
- Multi-step task execution
- Native Tasks feature streaming
- Tool usage visibility
"""

import asyncio
import json
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
    
    MAIN_AGENT = "\033[36m"    # Cyan
    SUB_AGENT = "\033[35m"     # Magenta  
    THINKING = "\033[33m"      # Yellow
    TOOL = "\033[32m"          # Green
    ERROR = "\033[31m"         # Red
    INFO = "\033[34m"          # Blue
    RESULT = "\033[92m"        # Light green
    DEBUG = "\033[90m"         # Gray


async def pretty_print_stream(queue: asyncio.Queue):
    """Stream output with formatting."""
    line_count = 0
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        
        chunk = chunk.rstrip('\n')
        if not chunk:
            continue
        
        line_count += 1
        
        # Colorize based on content patterns
        if chunk.startswith("[LOG]"):
            log_content = chunk[5:].strip()
            if "subagent" in log_content.lower() or "agent" in log_content.lower():
                print(f"{Colors.SUB_AGENT}🔧 {log_content}{Colors.RESET}")
            elif "tool" in log_content.lower() or "bash" in log_content.lower():
                print(f"{Colors.TOOL}🛠️  {log_content}{Colors.RESET}")
            else:
                print(f"{Colors.DEBUG}📋 {log_content}{Colors.RESET}")
        elif "subagent" in chunk.lower() or "sub-agent" in chunk.lower() or "delegate" in chunk.lower():
            print(f"{Colors.SUB_AGENT}🔧 SUB-AGENT: {chunk}{Colors.RESET}")
        elif "tool_use" in chunk.lower() or "bash(" in chunk.lower() or "read(" in chunk.lower():
            print(f"{Colors.TOOL}🛠️  TOOL: {chunk}{Colors.RESET}")
        elif chunk.startswith("##") or chunk.startswith("**Step"):
            print(f"\n{Colors.BOLD}{Colors.THINKING}{chunk}{Colors.RESET}")
        elif chunk.startswith("```"):
            print(f"{Colors.DIM}{chunk}{Colors.RESET}")
        else:
            sys.stdout.write(f"{Colors.MAIN_AGENT}{chunk}{Colors.RESET}")
            sys.stdout.flush()
    
    return line_count


async def run_complex_task():
    """Run a complex multi-step task to test sub-agent delegation."""
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}🧪 Complex Sub-Agent Task Demo{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    # Complex prompt that should trigger sub-agent usage
    complex_prompt = """
You are testing sub-agent task delegation. This is a complex multi-step task.

## Task: Analyze and Plan a Feature

1. **Planning Phase** (use planning sub-agent):
   - Analyze what files exist in the /scripts directory
   - List the Python files and their purposes

2. **Analysis Phase**:
   - Read one of the demo scripts
   - Summarize what it does in 2-3 sentences

3. **Recommendation Phase**:
   - Suggest one improvement to the codebase

Keep your total response under 300 words. Show your step-by-step thinking.
    """
    
    working_dir = Path(__file__).parent.parent
    output_queue = asyncio.Queue()
    
    # Load sub-agents
    subagents_json = get_default_subagents()
    
    print(f"{Colors.INFO}📁 Working directory: {working_dir}{Colors.RESET}")
    print(f"{Colors.INFO}⏱️  Starting at: {datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.INFO}🔧 Sub-agents loaded: planning, implementation, testing, debugging{Colors.RESET}")
    print(f"\n{Colors.DIM}{'─'*70}{Colors.RESET}")
    print(f"\n{Colors.BOLD}📡 STREAMING OUTPUT:{Colors.RESET}\n")
    
    try:
        result, line_count = await asyncio.gather(
            run_claude_cli(
                prompt=complex_prompt,
                working_dir=working_dir,
                output_queue=output_queue,
                task_id="complex-subagent-demo",
                timeout_seconds=180,  # 3 min timeout
                agents=subagents_json,
                debug_mode="!statsig",  # Debug without statsig noise
            ),
            pretty_print_stream(output_queue)
        )
        
        # Print results
        print(f"\n\n{Colors.DIM}{'─'*70}{Colors.RESET}")
        print(f"\n{Colors.BOLD}📊 EXECUTION RESULTS:{Colors.RESET}")
        print(f"  {Colors.RESULT}✅ Success: {result.success}{Colors.RESET}")
        print(f"  💰 Cost: ${result.cost_usd:.4f}")
        print(f"  📊 Tokens: {result.input_tokens:,} in / {result.output_tokens:,} out")
        print(f"  📝 Lines streamed: {line_count}")
        
        if result.error:
            print(f"  {Colors.ERROR}❌ Error: {result.error}{Colors.RESET}")
        
        # Check if sub-agents were used
        output_lower = result.output.lower()
        subagent_indicators = ["subagent", "sub-agent", "delegate", "planning agent", "implementation agent"]
        used_subagents = any(indicator in output_lower for indicator in subagent_indicators)
        
        print(f"\n{Colors.BOLD}🔍 SUB-AGENT ANALYSIS:{Colors.RESET}")
        if used_subagents:
            print(f"  {Colors.SUB_AGENT}✅ Sub-agent patterns detected in output{Colors.RESET}")
        else:
            print(f"  {Colors.DIM}ℹ️  No explicit sub-agent patterns detected (may run in main context){Colors.RESET}")
        
        # Check for tool usage
        tool_indicators = ["bash", "read", "write", "edit", "glob", "grep"]
        tools_used = [t for t in tool_indicators if t in output_lower]
        if tools_used:
            print(f"  {Colors.TOOL}🛠️  Tools potentially used: {', '.join(tools_used)}{Colors.RESET}")
        
        return result
        
    except Exception as e:
        print(f"\n{Colors.ERROR}❌ Error: {e}{Colors.RESET}")
        raise


async def main():
    """Main entry point."""
    import shutil
    
    print(f"""
{Colors.BOLD}Complex Sub-Agent Task Demo{Colors.RESET}
{Colors.DIM}────────────────────────────{Colors.RESET}

This demo tests Claude Code's native Tasks features with sub-agents.
It sends a complex multi-step prompt that should:
1. Use Read/Glob/Bash tools
2. Potentially delegate to sub-agents
3. Show step-by-step reasoning

{Colors.INFO}Press Ctrl+C to cancel at any time.{Colors.RESET}
""")
    
    if not shutil.which("claude"):
        print(f"\n{Colors.ERROR}❌ Claude CLI not found in PATH!{Colors.RESET}")
        return 1
    
    try:
        result = await run_complex_task()
        return 0 if result.success else 1
    except KeyboardInterrupt:
        print(f"\n\n{Colors.INFO}⏹️  Demo cancelled{Colors.RESET}")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
