# Git Operations Skill

## Purpose
Perform git operations for repository management, branching, and change tracking.

## Capabilities
- Clone and update repositories
- Create and manage branches
- Stage and commit changes
- Query git history and diffs
- Checkout specific commits or PRs
- Tag releases

## Available Operations

### Clone Repository
```python
clone_repo(repo_url: str, target_dir: Path, depth: int = 1) -> Path
```
Clone repository with shallow clone for efficiency.

### Create Branch
```python
create_branch(branch_name: str, base: str = "main") -> bool
```
Create new branch from base branch.

### Checkout Branch
```python
checkout_branch(branch_name: str) -> bool
```
Switch to existing branch.

### Checkout PR
```python
checkout_pr(pr_number: int) -> bool
```
Fetch and checkout a pull request.

### Stage Files
```python
stage_files(file_patterns: list[str]) -> bool
```
Add files to staging area.

### Create Commit
```python
commit_changes(message: str, files: list[str] | None = None) -> str
```
Create commit with message, returns commit SHA.

### Get Diff
```python
get_diff(base: str, head: str, file_path: str | None = None) -> str
```
Get diff between two refs, optionally for specific file.

### Get File at Commit
```python
get_file_content(file_path: str, commit: str) -> str
```
Read file content at specific commit.

### Get Commit Log
```python
get_log(max_count: int = 10, since: str | None = None) -> list[Commit]
```
Retrieve commit history.

### Get Changed Files
```python
get_changed_files(base: str, head: str) -> list[str]
```
List files changed between commits.

## Branch Naming Conventions
- Feature: `feature/[issue-number]-[short-description]`
- Bug fix: `fix/[issue-number]-[short-description]`
- Hotfix: `hotfix/[issue-number]-[short-description]`
- Refactor: `refactor/[description]`
- Documentation: `docs/[description]`

## Commit Message Format
```
<type>: <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `docs`: Documentation changes
- `chore`: Maintenance tasks

### Example
```
fix: Resolve type safety violations in task_worker.py

Remove all Any type annotations and replace with proper Protocol types.
Added comprehensive test coverage for type-safe refactoring.

Closes #123
```

## When to Use
- Creating fix/feature branches
- Committing code changes
- Analyzing PR diffs
- Checking out specific versions
- Querying change history

## Example Workflows

### Bug Fix Workflow
```python
create_branch(f"fix/{issue_number}-{description}")
# Make changes
stage_files(["*.py"])
commit_changes(f"fix: {description}\n\nCloses #{issue_number}")
```

### PR Review Workflow
```python
checkout_pr(pr_number)
changed_files = get_changed_files("main", "HEAD")
for file in changed_files:
    diff = get_diff("main", "HEAD", file)
    analyze_changes(diff)
```

### Historical Analysis
```python
commits = get_log(max_count=50, since="2024-01-01")
for commit in commits:
    if "security" in commit.message.lower():
        analyze_security_commit(commit)
```

## Safety Rules
- NEVER force push to main/master
- NEVER commit secrets or credentials
- NEVER skip commit hooks without approval
- ALWAYS verify branch before destructive operations
- ALWAYS create backups before rebase/reset

## Integration with Other Skills
- **repo-context**: Load repository state and history
- **knowledge-graph**: Update graph after code changes
- **test-execution**: Run tests on specific commits
