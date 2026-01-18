#!/usr/bin/env python3
"""
Single Agent System CLI
=======================
Command-line interface for running the agent workflow locally.
Demonstrates the full process that runs distributed in AWS.
"""

import json
import sys
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import settings
from agents import AgentOrchestrator

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.stdlib.NAME_TO_LEVEL.get(settings.execution.log_level.lower(), 20)
    ),
)

console = Console()
logger = structlog.get_logger(__name__)


def print_banner():
    """Print welcome banner."""
    console.print(Panel.fit(
        "[bold blue]🤖 Single Agent System[/bold blue]\n"
        "[dim]Local testing for distributed agent workflow[/dim]",
        border_style="blue"
    ))


def validate_settings():
    """Validate required settings are configured."""
    errors = settings.validate()
    if errors:
        console.print("[red]❌ Configuration errors:[/red]")
        for error in errors:
            console.print(f"   • {error}")
        console.print("\n[dim]Please update your .env file. See .env.example for reference.[/dim]")
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Single Agent System - Test the distributed workflow locally."""
    pass


@cli.command()
@click.option("--ticket", "-t", help="Jira ticket key (e.g., PROJ-123)")
@click.option("--description", "-d", help="Feature description (for local mode)")
@click.option("--title", help="Feature title (optional, for local mode)")
@click.option("--file", "-f", type=click.Path(exists=True), help="JSON file with ticket data")
@click.option("--dry-run", is_flag=True, help="Run without making changes")
@click.option("--wait-approval", is_flag=True, help="Wait for approval instead of auto-approving")
def run(ticket, description, title, file, dry_run, wait_approval):
    """Run the complete workflow (Discovery → Planning → Execution → CI/CD).
    
    This demonstrates the full agent process that runs distributed in AWS,
    but runs locally in a single process for testing.
    """
    print_banner()
    validate_settings()
    
    if dry_run:
        console.print("[yellow]⚠️ Dry-run mode enabled - no changes will be made[/yellow]\n")
        import os
        os.environ["DRY_RUN"] = "true"
    
    auto_approve = not wait_approval
    if wait_approval:
        console.print("[cyan]ℹ️ Will wait for approval after planning phase[/cyan]\n")
    
    orchestrator = AgentOrchestrator()
    
    # Determine input source
    if ticket:
        console.print(f"[cyan]📋 Loading ticket from Jira: {ticket}[/cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_from_jira(ticket, auto_approve=auto_approve)
            
    elif description:
        console.print(f"[cyan]📝 Running from description[/cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_from_description(description, title, auto_approve=auto_approve)
            
    elif file:
        console.print(f"[cyan]📄 Loading ticket from file: {file}[/cyan]")
        ticket_data = json.loads(Path(file).read_text())
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_full_workflow(ticket_data, auto_approve=auto_approve)
    else:
        console.print("[red]❌ Please provide --ticket, --description, or --file[/red]")
        sys.exit(1)
    
    # Display results
    display_results(result)


def display_results(result: dict):
    """Display workflow results in a nice format."""
    console.print("\n")
    
    phases = result.get("phases", {})
    
    # Discovery results
    discovery = phases.get("discovery", {})
    if discovery:
        console.print(Panel.fit("[bold]📍 Phase 1: Discovery[/bold]", border_style="green"))
        
        repos_table = Table(show_header=True, header_style="bold")
        repos_table.add_column("Repository")
        repos_table.add_column("Relevance")
        repos_table.add_column("Files")
        
        for repo in discovery.get("relevantRepos", [])[:5]:
            repos_table.add_row(
                repo["name"],
                f"{repo['relevance']:.2f}",
                str(len(repo.get("files", [])))
            )
        
        console.print(repos_table)
        console.print(f"[dim]Complexity: {discovery.get('estimatedComplexity', 'Unknown')}[/dim]")
        console.print(f"[dim]Keywords: {', '.join(discovery.get('keywords', [])[:5])}[/dim]\n")
    
    # Planning results
    planning = phases.get("planning", {})
    if planning:
        console.print(Panel.fit("[bold]📋 Phase 2: Planning[/bold]", border_style="blue"))
        
        tasks = planning.get("plan", {}).get("implementation", {}).get("tasks", [])
        if tasks:
            tasks_table = Table(show_header=True, header_style="bold")
            tasks_table.add_column("#")
            tasks_table.add_column("Task")
            tasks_table.add_column("Hours")
            
            for task in tasks[:10]:
                tasks_table.add_row(
                    str(task.get("id", "")),
                    task.get("description", "")[:50],
                    str(task.get("estimatedHours", 0))
                )
            
            console.print(tasks_table)
        
        console.print(f"[dim]Total hours: {planning.get('totalEstimatedHours', 0)}[/dim]")
        
        prs = planning.get("prsCreated", [])
        if prs:
            console.print(f"[dim]PRs: {', '.join(pr.get('prUrl', '') for pr in prs)}[/dim]")
        console.print()
    
    # Execution results
    execution = phases.get("execution", {})
    if execution:
        completed = len(execution.get("completedTasks", []))
        failed = len(execution.get("failedTasks", []))
        total = execution.get("totalTasks", completed + failed)
        
        status_color = "green" if failed == 0 else "yellow" if completed > 0 else "red"
        console.print(Panel.fit(f"[bold]⚡ Phase 3: Execution[/bold]", border_style=status_color))
        console.print(f"✅ Completed: {completed}/{total} tasks")
        console.print(f"❌ Failed: {failed}/{total} tasks\n")
    
    # CI/CD results
    cicd = phases.get("cicd", {})
    if cicd:
        console.print(Panel.fit("[bold]🔄 Phase 4: CI/CD[/bold]", border_style="cyan"))
        if cicd.get("skipped"):
            console.print(f"[dim]Skipped: {cicd.get('reason', 'N/A')}[/dim]")
        elif cicd.get("success"):
            console.print("✅ CI passed")
        else:
            console.print("❌ CI failed or pending")
        console.print()
    
    # Final status
    if result.get("success"):
        console.print(Panel.fit(
            f"[bold green]✅ Workflow Complete[/bold green]\n\n"
            f"Task ID: [cyan]{result.get('taskId', 'N/A')}[/cyan]\n"
            f"Output: [cyan]{settings.execution.output_dir}[/cyan]",
            border_style="green"
        ))
    elif result.get("awaitingApproval"):
        console.print(Panel.fit(
            f"[bold yellow]⏳ Awaiting Approval[/bold yellow]\n\n"
            f"Task ID: [cyan]{result.get('taskId', 'N/A')}[/cyan]\n"
            f"Use `/agent approve {result.get('taskId')}` to continue",
            border_style="yellow"
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]❌ Workflow Failed[/bold red]\n\n"
            f"Error: {result.get('error', 'Unknown error')}",
            border_style="red"
        ))


@cli.command()
def config():
    """Display current configuration."""
    print_banner()
    
    console.print("[bold]Current Configuration[/bold]\n")
    
    # Anthropic
    console.print("[cyan]Anthropic:[/cyan]")
    console.print(f"  API Key: {'✅ Set' if settings.anthropic.api_key else '❌ Not set'}")
    console.print(f"  Discovery Model: {settings.anthropic.discovery_model}")
    console.print(f"  Planning Model: {settings.anthropic.planning_model}")
    console.print(f"  Execution Model: {settings.anthropic.execution_model}")
    
    # GitHub
    console.print("\n[cyan]GitHub:[/cyan]")
    console.print(f"  Token: {'✅ Set' if settings.github.token else '❌ Not set'}")
    console.print(f"  Organization: {settings.github.org or '(not set)'}")
    
    # Jira
    console.print("\n[cyan]Jira:[/cyan]")
    console.print(f"  Base URL: {settings.jira.base_url or '(not set)'}")
    console.print(f"  Token: {'✅ Set' if settings.jira.api_token else '❌ Not set'}")
    console.print(f"  Project: {settings.jira.project_key}")
    
    # Slack
    console.print("\n[cyan]Slack:[/cyan]")
    console.print(f"  Bot Token: {'✅ Set' if settings.slack.bot_token else '❌ Not set'}")
    console.print(f"  Agents Channel: {settings.slack.channel_agents}")
    
    # Sentry
    console.print("\n[cyan]Sentry:[/cyan]")
    console.print(f"  Organization: {settings.sentry.org or '(not set)'}")
    console.print(f"  Token: {'✅ Set' if settings.sentry.auth_token else '❌ Not set'}")
    
    # Execution
    console.print("\n[cyan]Execution:[/cyan]")
    console.print(f"  Output Dir: {settings.execution.output_dir}")
    console.print(f"  Dry Run: {settings.execution.dry_run}")
    console.print(f"  Log Level: {settings.execution.log_level}")


@cli.command()
@click.argument("command", required=False, default="help")
@click.argument("args", nargs=-1)
def agent(command, args):
    """Simulate Slack /agent commands.
    
    Commands: status, approve, reject, retry, list, help
    """
    print_banner()
    
    orchestrator = AgentOrchestrator()
    result = orchestrator.handle_slack_command(command, list(args))
    
    console.print(result)


@cli.command()
@click.option("--project", "-p", help="Jira project key")
@click.option("--status", "-s", help="Filter by status")
def list_tickets(project, status):
    """List available Jira tickets."""
    print_banner()
    validate_settings()
    
    from services import JiraService
    jira = JiraService()
    
    issues = jira.get_project_issues(status=status)
    
    if not issues:
        console.print("[yellow]No tickets found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Summary")
    table.add_column("Status")
    table.add_column("Priority")
    
    for issue in issues[:20]:
        table.add_row(
            issue["key"],
            issue["summary"][:50],
            issue["status"],
            issue.get("priority", "Medium")
        )
    
    console.print(table)


@cli.command()
def monitor_sentry():
    """Run Sentry error monitoring (like hourly EventBridge trigger)."""
    print_banner()
    validate_settings()
    
    console.print("[cyan]🔍 Running Sentry monitoring...[/cyan]\n")
    
    orchestrator = AgentOrchestrator()
    result = orchestrator.run_sentry_monitoring()
    
    console.print(f"✅ Processed: {result.get('processed', 0)} issues")
    console.print(f"🎫 Tickets created: {result.get('tickets_created', 0)}")
    console.print(f"🔄 Deduplicated: {result.get('deduplicated', 0)}")


@cli.command()
def list_errors():
    """List recent errors from Sentry."""
    print_banner()
    validate_settings()
    
    from services import SentryService
    sentry = SentryService()
    
    issues = sentry.get_issues(limit=20)
    
    if not issues:
        console.print("[green]No errors found[/green]")
        return
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Level")
    table.add_column("Count")
    table.add_column("Escalate?")
    
    for issue in issues:
        should_escalate = "⚠️ Yes" if sentry.should_escalate(issue) else ""
        table.add_row(
            issue["id"][:8],
            issue["title"][:40],
            issue["level"],
            str(issue["count"]),
            should_escalate
        )
    
    console.print(table)


@cli.command()
@click.option("--port", "-p", default=None, type=int, help="Port to listen on (default: 8000)")
@click.option("--host", "-h", default=None, help="Host to bind to (default: 0.0.0.0)")
def serve(port, host):
    """Start the webhook server for local testing.
    
    This runs a FastAPI server that handles webhooks from:
    - Jira: /webhooks/jira
    - GitHub: /webhooks/github
    - Sentry: /webhooks/sentry
    - Slack: /webhooks/slack
    
    Use ngrok to expose this server to external services:
    
        ngrok http 8000
    
    Then configure your webhooks to point to the ngrok URL.
    """
    print_banner()
    validate_settings()
    
    # Use settings defaults if not specified
    actual_port = port or settings.webhook.port
    actual_host = host or settings.webhook.host
    
    console.print(f"[cyan]🌐 Starting webhook server on {actual_host}:{actual_port}[/cyan]")
    console.print("[dim]Endpoints:[/dim]")
    console.print(f"  • POST /webhooks/jira")
    console.print(f"  • POST /webhooks/github")
    console.print(f"  • POST /webhooks/sentry")
    console.print(f"  • POST /webhooks/slack")
    console.print(f"  • GET  /health")
    console.print(f"  • GET  /tasks")
    console.print()
    console.print("[yellow]💡 Tip: Use 'ngrok http {port}' to expose to external services[/yellow]".format(port=actual_port))
    console.print()
    
    from webhook_server import run_server
    run_server(host=actual_host, port=actual_port)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
