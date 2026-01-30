# Repository Context Skill

## Purpose
Load and provide repository context including history, patterns, conventions, and domain knowledge.

## Capabilities
- Load repository metadata and structure
- Extract coding patterns and conventions
- Provide historical context from commits
- Identify domain-specific knowledge
- Access project documentation
- Understand codebase organization

## Available Operations

### Load Repository Metadata
```python
get_repo_metadata(repo_path: str) -> RepoMetadata
```
**Returns:**
```json
{
  "name": "agent-bot",
  "description": "AI agent for automated code tasks",
  "languages": {"Python": 95, "Shell": 3, "Dockerfile": 2},
  "total_files": 85,
  "total_lines": 5757,
  "primary_language": "Python",
  "creation_date": "2024-01-15"
}
```

### Get Coding Conventions
```python
extract_conventions(repo_path: str) -> Conventions
```
Analyze codebase to identify patterns:
- Naming conventions (snake_case, PascalCase)
- Import organization
- File structure patterns
- Test file naming
- Documentation style

**Returns:**
```json
{
  "naming": {
    "variables": "snake_case",
    "classes": "PascalCase",
    "constants": "UPPER_SNAKE_CASE"
  },
  "imports": "absolute imports preferred",
  "line_length": 88,
  "string_quotes": "double quotes",
  "type_hints": "required",
  "docstring_style": "Google"
}
```

### Get Project Structure
```python
get_project_structure(repo_path: str) -> ProjectStructure
```
**Returns:**
```json
{
  "type": "monorepo",
  "components": [
    {"name": "api-gateway", "type": "service", "language": "Python"},
    {"name": "agent-container", "type": "service", "language": "Python"},
    {"name": "integrations", "type": "packages", "sub_packages": 3}
  ],
  "entry_points": [
    "api-gateway/main.py",
    "agent-container/workers/task_worker.py"
  ]
}
```

### Find Similar Code
```python
find_similar_implementations(
    function_signature: str,
    repo_path: str
) -> list[CodeExample]
```
Find similar functions to understand patterns.

### Get Recent Changes
```python
get_recent_changes(
    file_path: str,
    max_commits: int = 10
) -> list[ChangeHistory]
```
Historical context for specific file.

### Load Documentation
```python
load_project_docs(repo_path: str) -> Documentation
```
Load README, architecture docs, .claude/ files.

### Get Domain Entities
```python
extract_domain_model(repo_path: str) -> DomainModel
```
Identify core domain entities and concepts.

**Returns:**
```json
{
  "entities": [
    {"name": "Task", "type": "dataclass", "module": "core.models"},
    {"name": "TaskLogger", "type": "class", "module": "core.task_logger"}
  ],
  "workflows": [
    "webhook_processing",
    "task_execution",
    "result_posting"
  ],
  "integrations": ["github", "jira", "slack", "sentry"]
}
```

## When to Use

### Before Implementation
Understand existing patterns:
```python
conventions = extract_conventions(repo_path)
similar = find_similar_implementations("async def process_*", repo_path)
```

### During Code Generation
Follow project style:
```python
conventions = extract_conventions(repo_path)
# Use conventions.naming["variables"] for variable names
# Use conventions.string_quotes for string literals
```

### Bug Investigation
Load historical context:
```python
changes = get_recent_changes("core/task_worker.py")
for change in changes:
    if "fix" in change.message.lower():
        analyze_previous_fix(change)
```

### Onboarding
Understand architecture:
```python
structure = get_project_structure(repo_path)
docs = load_project_docs(repo_path)
domain = extract_domain_model(repo_path)
```

## Context Layers

### 1. Structural Context
- Directory organization
- Component boundaries
- Module dependencies
- Entry points

### 2. Pattern Context
- Code conventions
- Architecture patterns
- Design patterns
- Testing patterns

### 3. Historical Context
- Change frequency
- Bug fix history
- Refactoring history
- Contributors

### 4. Domain Context
- Business entities
- Workflows
- Business rules
- Domain terminology

## Context Loading Strategy

### Initial Load (Pre-execution)
```python
context = {
    "metadata": get_repo_metadata(repo_path),
    "structure": get_project_structure(repo_path),
    "conventions": extract_conventions(repo_path),
    "domain": extract_domain_model(repo_path),
    "docs": load_project_docs(repo_path)
}
```

### Targeted Load (During Task)
```python
file_context = {
    "recent_changes": get_recent_changes(file_path),
    "similar_code": find_similar_implementations(signature, repo_path),
    "conventions": get_file_specific_conventions(file_path)
}
```

## Output Format

### Contextual Recommendations
```markdown
## Repository Context

**Project:** agent-bot (Python Monorepo)
**Conventions:**
- Type hints: Required
- Max line length: 88
- No comments: Self-explanatory code only
- Testing: pytest with TDD approach

**Relevant Patterns:**
Similar implementations found in:
- `core/result_poster.py`: Async result posting pattern
- `api/webhook_handler.py`: Webhook processing pattern

**Recent Changes:**
- 2024-01-20: Type safety refactoring (#123)
- 2024-01-15: Added MCP client protocol (#115)

**Domain Context:**
Core entities: Task, TaskLogger, MCPClient, ResultPoster
Main workflow: webhook → queue → agent → result_poster
```

## Cache Strategy
- Repository metadata: Cache for 1 hour
- Conventions: Cache per session
- Recent changes: Refresh every 5 minutes
- Documentation: Cache until repo update

## Integration with Other Skills
- **code-analysis**: Validate against conventions
- **knowledge-graph**: Combine structural with graph data
- **git-operations**: Access historical context
- **test-execution**: Verify pattern compliance
