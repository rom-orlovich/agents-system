---
name: skill-generator
description: Generates new skills with proper structure and validation
user-invocable: true
---

Generate skills programmatically following Claude Code best practices. This skill contains templates and validation procedures for creating new skills.

## Quick Process

1. Collect requirements: skill name, description, purpose, use cases
2. Create `.claude/skills/{name}/` directory
3. Generate SKILL.md with frontmatter (50-150 lines, instructions only)
4. Create examples.md template if code examples needed
5. Create scripts/ directory if helper scripts needed
6. Validate: length, frontmatter format, no code in SKILL.md

## Skill Structure

```
skill-name/
├── SKILL.md          # Required: 50-150 lines, instructions only
├── examples.md       # Optional: Code examples, usage patterns
└── scripts/          # Optional: Helper scripts, utilities
```

## Frontmatter Template

```yaml
---
name: skill-name
description: Single sentence when to use (< 100 chars)
user-invocable: true|false
---
```

**Frontmatter Rules:**
- `name`: kebab-case, lowercase (e.g., `github-operations`)
- `description`: One sentence, action-oriented, < 100 chars
- `user-invocable`: `true` for `/skill-name` commands, `false` for agent-only skills

## SKILL.md Content Guidelines

**Keep in SKILL.md (50-150 lines):**
- Purpose and description
- When to use the skill
- Process/workflow steps
- Key principles and guidelines
- References to supporting files (examples.md, scripts/)

**Move to examples.md:**
- Full code examples
- Before/after comparisons
- Usage patterns
- Complete implementations

**Move to scripts/:**
- Executable helper scripts
- Validation tools
- Generation utilities

## Validation Rules

- SKILL.md: 50-150 lines, instructions only
- Frontmatter: name, description required
- Description: single sentence, < 100 chars
- Code examples: Must be in examples.md or scripts/, not SKILL.md
- Structure: SKILL.md + optional examples.md + optional scripts/

## Output

Creates skill directory with validated SKILL.md and optional supporting files following Claude Code best practices.
