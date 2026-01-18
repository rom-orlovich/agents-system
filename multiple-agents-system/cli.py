#!/usr/bin/env python3
"""
Multiple-Agents System CLI
==========================
Command-line interface for running the distributed agent system locally.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from dotenv import load_dotenv
load_dotenv()

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
)

console = Console()
logger = structlog.get_logger(__name__)


def print_banner():
    """Print welcome banner."""
    console.print(Panel.fit(
        "[bold blue]🤖 Multiple-Agents System (Local Mode)[/bold blue]\n"
        "[dim]Testing distributed agents locally[/dim]",
        border_style="blue"
    ))


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Multiple-Agents System - Run distributed agents locally for testing."""
    pass


@cli.command()
@click.option("--ticket", "-t", help="Jira ticket key (e.g., PROJ-123)")
@click.option("--description", "-d", help="Feature description (for local mode)")
@click.option("--title", help="Feature title (optional)")
@click.option("--file", "-f", type=click.Path(exists=True), help="JSON file with ticket data")
@click.option("--dry-run", is_flag=True, help="Run without making changes")
@click.option("--wait-approval", is_flag=True, help="Wait for approval instead of auto-approving")
def run(ticket, description, title, file, dry_run, wait_approval):
    """Run the complete workflow locally.
    
    This runs all agents in a single process, simulating the distributed
    AWS Step Functions workflow.
    """
    print_banner()
    
    if dry_run:
        console.print("[yellow]⚠️ Dry-run mode enabled[/yellow]\n")
        import os
        os.environ["DRY_RUN"] = "true"
    
    auto_approve = not wait_approval
    
    from local_runner import get_orchestrator
    orchestrator = get_orchestrator()
    
    if ticket:
        console.print(f"[cyan]📋 Loading ticket from Jira: {ticket}[/cyan]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_from_jira(ticket, auto_approve=auto_approve)
    
    elif description:
        console.print(f"[cyan]📝 Running from description[/cyan]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_from_description(description, title, auto_approve=auto_approve)
    
    elif file:
        console.print(f"[cyan]📄 Loading from file: {file}[/cyan]")
        ticket_data = json.loads(Path(file).read_text())
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_full_workflow(ticket_data, auto_approve=auto_approve)
    
    else:
        console.print("[red]❌ Please provide --ticket, --description, or --file[/red]")
        sys.exit(1)
    
    display_results(result)


def display_results(result: dict):
    """Display workflow results."""
    console.print("\n")
    
    if result.get("success"):
        console.print(Panel.fit(
            f"[bold green]✅ Workflow Complete[/bold green]\n\n"
            f"Task ID: [cyan]{result.get('taskId', 'N/A')}[/cyan]",
            border_style="green"
        ))
    elif result.get("awaitingApproval"):
        console.print(Panel.fit(
            f"[bold yellow]⏳ Awaiting Approval[/bold yellow]\n\n"
            f"Task ID: [cyan]{result.get('taskId', 'N/A')}[/cyan]",
            border_style="yellow"
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]❌ Workflow Failed[/bold red]\n\n"
            f"Error: {result.get('error', 'Unknown error')}",
            border_style="red"
        ))


@cli.command()
@click.option("--port", "-p", default=8001, type=int, help="Port to listen on")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
def serve(port, host):
    """Start the webhook server for local testing.
    
    This runs a FastAPI server that handles webhooks from:
    - Jira: /webhooks/jira
    - GitHub: /webhooks/github
    - Sentry: /webhooks/sentry
    - Slack: /webhooks/slack
    
    Use ngrok to expose to external services:
    
        ngrok http 8001
    """
    print_banner()
    
    console.print(f"[cyan]🌐 Starting webhook server on {host}:{port}[/cyan]")
    console.print("[dim]Endpoints:[/dim]")
    console.print(f"  • POST /webhooks/jira")
    console.print(f"  • POST /webhooks/github")
    console.print(f"  • POST /webhooks/sentry")
    console.print(f"  • POST /webhooks/slack")
    console.print(f"  • GET  /health")
    console.print()
    console.print(f"[yellow]💡 Tip: Use 'ngrok http {port}' to expose to external services[/yellow]")
    console.print()
    
    from webhook_server import run_server
    run_server(host=host, port=port)


@cli.command()
@click.argument("command", required=False, default="help")
@click.argument("args", nargs=-1)
def agent(command, args):
    """Simulate Slack /agent commands.
    
    Commands: status, approve, reject, retry, list, help
    """
    print_banner()
    
    from local_runner import get_orchestrator
    orchestrator = get_orchestrator()
    result = orchestrator.handle_slack_command(command, list(args))
    
    console.print(result)


@cli.command()
def monitor_sentry():
    """Run Sentry error monitoring."""
    print_banner()
    
    console.print("[cyan]🔍 Running Sentry monitoring...[/cyan]\n")
    
    from local_runner import get_orchestrator
    orchestrator = get_orchestrator()
    result = orchestrator.run_sentry_monitoring()
    
    console.print(f"✅ Processed: {result.get('processed', 0)} issues")
    console.print(f"🎫 Tickets created: {result.get('tickets_created', 0)}")


@cli.command()
def config():
    """Display current configuration."""
    print_banner()
    
    import os
    
    console.print("[bold]Current Configuration[/bold]\n")
    
    console.print("[cyan]Anthropic:[/cyan]")
    console.print(f"  API Key: {'✅ Set' if os.environ.get('ANTHROPIC_API_KEY') else '❌ Not set'}")
    
    console.print("\n[cyan]GitHub:[/cyan]")
    console.print(f"  Token: {'✅ Set' if os.environ.get('GITHUB_TOKEN') else '❌ Not set'}")
    console.print(f"  Organization: {os.environ.get('GITHUB_ORG', '(not set)')}")
    
    console.print("\n[cyan]Jira:[/cyan]")
    console.print(f"  Base URL: {os.environ.get('JIRA_BASE_URL', '(not set)')}")
    console.print(f"  Token: {'✅ Set' if os.environ.get('JIRA_API_TOKEN') else '❌ Not set'}")
    
    console.print("\n[cyan]Slack:[/cyan]")
    console.print(f"  Bot Token: {'✅ Set' if os.environ.get('SLACK_BOT_TOKEN') else '❌ Not set'}")
    
    console.print("\n[cyan]Sentry:[/cyan]")
    console.print(f"  Organization: {os.environ.get('SENTRY_ORG', '(not set)')}")
    console.print(f"  Token: {'✅ Set' if os.environ.get('SENTRY_AUTH_TOKEN') else '❌ Not set'}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
