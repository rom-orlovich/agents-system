---
name: claude-md-creator
description: Create and optimize CLAUDE.md files following official best practices. Use when user asks to create CLAUDE.md, initialize project instructions, set up Claude configuration, or optimize existing CLAUDE.md files.
license: MIT
---

# Creating CLAUDE.md Files

Guide for creating CLAUDE.md files that follow Anthropic's official best practices (January 2026).

## Core Purpose

CLAUDE.md provides persistent context Claude can't infer from code alone. It's automatically loaded in every session to provide instructions about code style, testing workflows, and project-specific conventions.

## What to Include vs Exclude

**✅ Include:**

- Bash commands Claude can't guess
- Code style rules that differ from defaults
- Testing instructions and preferred test runners
- Repository etiquette (branch naming, PR conventions)
- Architectural decisions specific to your project
- Developer environment quirks (required environment variables)
- Common gotchas or non-obvious behaviors

**❌ Exclude:**

- Anything Claude can figure out by reading code
- Standard language conventions Claude already knows
- Detailed API documentation (link to docs instead)
- Information that changes frequently
- Long explanations or tutorials
- File-by-file descriptions of the codebase
- Self-evident practices like "write clean code"

## File Location Options

1. **Home folder** (`~/.claude/CLAUDE.md`): Applies to all Claude sessions globally
2. **Project root** (`./CLAUDE.md`): Check into git to share with your team, or use `CLAUDE.local.md` and `.gitignore` it for personal overrides
3. **Parent directories**: Useful for monorepos where both `root/CLAUDE.md` and `root/foo/CLAUDE.md` are pulled in automatically
4. **Child directories**: Claude pulls in child CLAUDE.md files on demand when working with files in those directories

## Example Structure

```markdown
# Code style

- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow

- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, not the whole test suite, for performance
```

## Import Syntax

Reference other files using the `@path/to/import` syntax:

```markdown
See @README.md for project overview and @package.json for available npm commands.

# Additional Instructions

- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

## Critical: Keep It Concise

**Bloated CLAUDE.md files cause Claude to ignore your actual instructions.** For each line, ask: _"Would removing this cause Claude to make mistakes?"_ If not, cut it.

**Warning signs your CLAUDE.md is too long:**

- Claude keeps doing something despite having a rule against it (the rule is getting lost)
- Claude asks questions that are answered in CLAUDE.md (phrasing might be ambiguous)

Treat CLAUDE.md like code: review it when things go wrong, prune it regularly, and test changes by observing whether Claude's behavior actually shifts.

## Emphasis for Important Rules

Add emphasis (e.g., "IMPORTANT" or "YOU MUST") to improve adherence to critical rules.

## Version Control

Check CLAUDE.md into git so your team can contribute. The file compounds in value over time as your team refines it.

## When to Use Alternatives

For domain knowledge or workflows that are only relevant sometimes, use **skills** instead of CLAUDE.md. Claude loads skills on demand without bloating every conversation. Skills are placed in `.claude/skills/` directories with a `SKILL.md` file and can define repeatable workflows you invoke directly with `/skill-name`.

## Custom Compaction Instructions

Customize how Claude handles context compaction by adding instructions to CLAUDE.md, such as: _"When compacting, always preserve the full list of modified files and any test commands"_ to ensure critical context survives summarization.

## Initialization

You can initialize CLAUDE.md using the `/init` command, which analyzes your codebase to detect:

- Build systems
- Test frameworks
- Code patterns

Then refine it based on actual usage patterns.

## Key Principle

**Ruthless minimalism** - only include what Claude genuinely needs and can't determine on its own.
