---
name: skill-creator
description: Create new Claude skills following official best practices. Use when user asks to create a skill, build a skill, add a new skill, or needs help structuring skill files.
license: MIT
---

# Creating Skills

Guide for creating skills that follow Anthropic's official best practices (January 2026).

## File Structure

```
your-skill-name/
├── SKILL.md              # Required - main skill file
├── scripts/              # Optional - executable code
│   ├── process_data.py
│   └── validate.sh
├── references/           # Optional - documentation
│   ├── api-guide.md
│   └── examples/
└── assets/               # Optional - templates
    └── report-template.md
```

**Critical naming rules:**

- SKILL.md must be exactly `SKILL.md` (case-sensitive)
- Folder name must use kebab-case: `notion-project-setup` ✅ not `Notion_Project_Setup` ❌
- No README.md inside skill folder

## YAML Frontmatter

**Minimal required format:**

```yaml
---
name: your-skill-name
description: What it does. Use when user asks to [specific phrases].
---
```

**Field requirements:**

- `name`: kebab-case only, max 64 characters, no spaces/capitals, must match folder name
- `description`: MUST include BOTH what the skill does AND when to use it, under 1024 characters, no XML tags
- `license`: Optional (e.g., MIT, Apache-2.0)
- `compatibility`: Optional, 1-500 characters describing environment requirements
- `metadata`: Optional custom key-value pairs (author, version, mcp-server, etc.)

**Good description examples:**

```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.

description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.
```

**Bad description examples:**

```yaml
description: Helps with documents  # Too vague
description: Processes data  # Missing triggers
```

## Core Principle: Be Concise

**Assume Claude is already very smart**. Only add context Claude doesn't already have.

**Good example (50 tokens):**

````markdown
## Extract PDF text

Use pdfplumber for text extraction:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages.extract_text()
```
````

````

**Bad example (150 tokens):**
```markdown
## Extract PDF text
PDF (Portable Document Format) files are a common file format...
To extract text from a PDF, you'll need to use a library...
There are many libraries available... [excessive explanation]
````

## Progressive Disclosure Architecture

Skills use a three-level system to minimize token usage:

1. **First level (YAML frontmatter)**: Always loaded in Claude's system prompt
2. **Second level (SKILL.md body)**: Loaded when skill is triggered
3. **Third level (Linked files)**: Loaded only as needed

**Example structure:**

```markdown
# PDF Processing

## Quick start

[Basic instructions here]

## Advanced features

**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
```

Claude only reads FORMS.md or REFERENCE.md when needed.

## Organizing Content by Domain

For skills with multiple domains, separate content:

```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── reference/
    ├── finance.md (revenue, billing metrics)
    ├── sales.md (opportunities, pipeline)
    └── product.md (API usage, features)
```

When a user asks about revenue, Claude only reads finance.md, not the other files.

## Reference Files Best Practices

**Keep references one level deep from SKILL.md**. Avoid nested references.

**Bad example (too deep):**

```
SKILL.md → advanced.md → details.md → actual information
```

**Good example (one level):**

```
SKILL.md → advanced.md (actual information)
SKILL.md → reference.md (actual information)
```

For files longer than 100 lines, include a table of contents at the top.

## Sequential Workflows with Checklists

Break complex operations into clear, sequential steps:

```markdown
## PDF form filling workflow

Copy this checklist and check off items as you complete them:
```

Task Progress:

- [ ] Step 1: Analyze the form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill the form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)

```

**Step 1: Analyze the form**
Run: `python scripts/analyze_form.py input.pdf`
[detailed instructions...]
```

## Validation Loops Pattern

Build validation into workflows:

```markdown
## Document editing process

1. Make your edits to `word/document.xml`
2. **Validate immediately**: `python ooxml/scripts/validate.py unpacked_dir/`
3. If validation fails:
   - Review the error message carefully
   - Fix the issues in the XML
   - Run validation again
4. **Only proceed when validation passes**
5. Rebuild and test
```

## Specifying Freedom Levels

Match instruction specificity to task requirements:

**High freedom** (text-based instructions): For creative/analytical tasks
**Medium freedom** (pseudocode with parameters): For customizable workflows
**Low freedom** (exact scripts): For critical operations requiring precision

## Output Templates

**For strict requirements:**

```markdown
## Report structure

ALWAYS use this exact template structure:
[exact template]
```

**For flexible guidance:**

```markdown
## Report structure

Here is a sensible default format, but use your best judgment:
[flexible template]
Adjust sections as needed for the specific analysis type.
```

## Examples and Decision Trees

Include input/output pairs:

```markdown
## Commit message format

**Example 1:**
Input: Added user authentication with JWT tokens
Output:
```

feat(auth): implement JWT-based authentication
Add login endpoint and token validation middleware

```

```

Guide Claude through decision points:

```markdown
## Document modification workflow

1. Determine the modification type:
   **Creating new content?** → Follow "Creation workflow" below
   **Editing existing content?** → Follow "Editing workflow" below
```

## Avoiding Time-Sensitive Content

Don't include information that will become outdated.

**Bad**: "If you're doing this before August 2025..."
**Good**: Use an "Old patterns" section with details collapsed:

```markdown
## Current method

Use the v2 API endpoint: `api.example.com/v2/messages`

## Old patterns

<details>
<summary>Legacy v1 API (deprecated 2025-08)</summary>
[historical context]
</details>
```

## Utility Scripts

Pre-made scripts offer advantages:

- More reliable and tested
- Don't consume context tokens
- Faster execution
- Handle edge cases explicitly

Make clear whether Claude should **execute** the script or **read** it as reference.

## Evaluation-Driven Development

Create evaluations BEFORE writing extensive documentation:

1. Start with minimal SKILL.md
2. Create test cases for core use cases
3. Iterate based on real usage
4. Expand only when gaps emerge

## Size Limits and Performance

- Keep SKILL.md under 500 lines for optimal performance
- Keep SKILL.md under 5,000 words
- Split longer content into separate reference files
- Use forward slashes in paths (Unix-style) for cross-platform compatibility

## MCP Integration

For skills using Model Context Protocol tools, always use fully qualified tool names:

```markdown
Use the BigQuery:bigquery_schema tool to retrieve table schemas.
Use the GitHub:create_issue tool to create issues.
```

Format: `ServerName:tool_name`

## Security Restrictions

Forbidden in frontmatter:

- XML angle brackets (< >)
- Skills with "claude" or "anthropic" in name (reserved)

## Testing Your Skills

Test three areas:

1. **Triggering tests**: Ensure skill loads at right times
2. **Functional tests**: Verify correct outputs and API calls
3. **Performance comparison**: Prove skill improves results vs baseline

## Key Success Metrics

- Skill triggers on 90% of relevant queries
- Completes workflows efficiently
- Zero failed API calls per workflow
- Users don't need to prompt about next steps

## Fundamental Principle

**Ruthless minimalism**. Only include what Claude genuinely needs and can't determine on its own.
