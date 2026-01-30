# Claude Agent Container Configuration

## Overview
This directory contains the configuration for the agent container, including agents, skills, rules, commands, and hooks.

## Structure

### Agents (`/agents`)
Define specialized agent types with specific capabilities and behaviors.
- `planning.md`: Requirements analysis and task planning
- `coding.md`: Implementation and bug fixes

### Skills (`/skills`)
Reusable capabilities that agents can utilize.
- `analysis.md`: Code and system analysis
- `coding.md`: Writing production code
- `testing.md`: Test creation and TDD

### Rules (`/rules`)
Enforced standards that all code must follow.
- `type-safety.md`: No `any` types or force unwrapping
- `no-comments.md`: Self-explanatory code without comments
- `tdd.md`: Test-driven development process

### Commands (`/commands`)
Available commands for interacting with agents.
- `analyze`: Perform analysis on target
- `implement`: Implement features with TDD
- `fix`: Fix bugs and errors

### Hooks (`/hooks`)
Scripts that run at various stages.
- `pre-commit.sh`: Runs before commits (type checking, tests, linting)

## Agent Selection

Agents are automatically selected based on the command:
- `analyze` → planning agent
- `implement` → coding agent
- `fix` → coding agent

## Configuration

The agent container reads these files on startup and uses them to:
1. Route commands to appropriate agents
2. Load required skills for each task
3. Enforce rules during code generation
4. Run hooks at appropriate times

## Extensibility

To add new agents, skills, rules, or commands:
1. Create a new markdown file in the appropriate directory
2. Follow the existing format and structure
3. The system will automatically load and use the new configuration
