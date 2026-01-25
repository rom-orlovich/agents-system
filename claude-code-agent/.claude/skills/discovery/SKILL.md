---
name: discovery
description: Discovers relevant repositories and files for a task. Used by planning agent before creating PLAN.md.
---

# Discovery Skill

> Find ALL relevant code before planning. No blind implementation.

## When to Invoke

Planning agent invokes this skill at the start of any Standard/Complex task.

## Process

### 1. Extract Search Terms

From task input, identify:
- Technical keywords (OAuth, React, API, etc.)
- Error messages or stack traces
- Feature names or component references

### 2. Search for Relevant Code

```bash
# Find files by keyword
grep -rl "keyword" --include="*.{py,ts,js,go}" src/

# Find by function/class name
grep -rn "def function_name\|class ClassName" .

# Find related tests
find . -name "*test*" -type f | xargs grep -l "keyword"
```

### 3. Analyze Dependencies

- Check imports in relevant files
- Identify API calls between services
- Map data flow

### 4. Output Format

```json
{
  "relevant_files": [
    {"path": "src/auth/login.py", "reason": "Contains login logic", "relevance": 0.95}
  ],
  "dependencies": ["src/models/user.py", "src/utils/hash.py"],
  "test_files": ["tests/test_login.py"],
  "complexity": "medium",
  "estimated_scope": "3-5 files"
}
```

## Quality Criteria

- Return top 10 most relevant files
- Each file has clear relevance reason
- Include both source and test files
- Identify cross-file dependencies

## Hand-off to Planning

After discovery, planning agent uses output to:
1. Define accurate scope in PLAN.md
2. List affected files per sub-task
3. Identify verification commands
