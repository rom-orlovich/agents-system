---
name: slack-code-inquiry
description: Answer code questions from Slack. Research codebase and respond with context.
---

# Slack Code Inquiry Workflow

> User asks about code in Slack → Research → Answer

## Trigger
- Slack mention: `@agent how does X work?`
- Slack command: `/agent ask [question]`
- Direct message to bot

## Flow

```
1. PARSE QUESTION
   Extract: keywords, file references, function names
   Classify: explanation / location / usage / debug

2. CODE RESEARCH
   Invoke: discovery skill (read-only)
   Search: grep patterns, file names
   Analyze: relevant code sections

3. GENERATE ANSWER
   Format: concise, with code snippets
   Include: file paths, line numbers
   Limit: 2000 chars for Slack

4. RESPOND
   Invoke: slack-operations skill
   Post: threaded reply
```

## Response Format

```
📍 *Answer: {topic}*

{explanation}

*Relevant code:*
`{file_path}:{line}`
```python
{code_snippet}
```

*See also:* {related_files}
```

## Question Types

| Type | Example | Action |
|------|---------|--------|
| Explanation | "How does auth work?" | Explain flow + key files |
| Location | "Where is login handled?" | File paths + functions |
| Usage | "How to use TokenService?" | Usage examples |
| Debug | "Why does X fail?" | Analysis + suggestion |

## No Approval Required
Read-only research.
