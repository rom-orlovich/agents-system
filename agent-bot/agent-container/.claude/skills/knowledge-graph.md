# Knowledge Graph Skill

## Purpose
Query code relationships and dependencies using graph database for impact analysis and navigation.

## Capabilities
- Query function call relationships
- Find class hierarchies
- Trace import dependencies
- Identify affected code by changes
- Discover test coverage relationships
- Navigate codebase structure

## Available MCP Tools

### get_function_callers
```python
get_function_callers(
    function_name: str,
    file_path: str | None = None
) -> list[dict]
```
Find all functions that call the specified function.

**Returns:**
```json
[
  {
    "caller_name": "process_task",
    "caller_file": "workers/task_worker.py",
    "caller_line": 45
  }
]
```

### get_class_hierarchy
```python
get_class_hierarchy(class_name: str) -> dict
```
Get complete inheritance hierarchy for a class.

**Returns:**
```json
{
  "class": "TaskWorker",
  "parents": ["BaseWorker", "ABC"],
  "children": ["AsyncTaskWorker"],
  "methods": ["process", "validate", "execute"]
}
```

### get_file_dependencies
```python
get_file_dependencies(file_path: str) -> dict
```
Get all files that this file imports/depends on.

**Returns:**
```json
{
  "file": "worker/task_worker.py",
  "imports": [
    {"path": "core/task_logger.py", "module": "TaskLogger"},
    {"path": "core/streaming_logger.py", "module": "StreamingLogger"}
  ]
}
```

### find_affected_by_change
```python
find_affected_by_change(file_path: str) -> list[str]
```
Find all files that would be affected by changes to this file (reverse dependencies).

**Returns:**
```json
[
  "workers/task_worker.py",
  "tests/test_result_poster.py",
  "api/webhook_handler.py"
]
```

### get_test_coverage
```python
get_test_coverage(function_name: str) -> dict
```
Find tests that cover a specific function.

**Returns:**
```json
{
  "function": "post_result",
  "coverage": 85,
  "tests": [
    {"name": "test_post_github_pr_result", "file": "tests/test_result_poster.py"},
    {"name": "test_post_jira_result", "file": "tests/test_result_poster.py"}
  ]
}
```

### search_by_pattern
```python
search_by_pattern(pattern: str, entity_type: str) -> list[dict]
```
Search for code entities matching pattern.

**Entity Types:**
- `function`: Search function names
- `class`: Search class names
- `file`: Search file paths
- `import`: Search import statements

## When to Use

### Before Making Changes
Query impact to understand what else might break:
```python
affected = find_affected_by_change("core/result_poster.py")
for file in affected:
    review_potential_impact(file)
```

### During Code Review
Understand call chains and dependencies:
```python
callers = get_function_callers("process_task")
for caller in callers:
    verify_error_handling(caller)
```

### Bug Investigation
Trace execution paths:
```python
hierarchy = get_class_hierarchy("TaskWorker")
for method in hierarchy["methods"]:
    callers = get_function_callers(method)
    analyze_call_chain(callers)
```

### Refactoring
Find all usages before renaming:
```python
usages = get_function_callers("old_function_name")
if len(usages) > 0:
    plan_migration(usages)
```

### Test Coverage Analysis
Identify untested code:
```python
coverage = get_test_coverage("critical_function")
if coverage["coverage"] < 80:
    generate_additional_tests(coverage["function"])
```

## Query Patterns

### Impact Analysis
```python
def analyze_change_impact(file_path: str) -> ImpactReport:
    affected_files = find_affected_by_change(file_path)

    impact = {
        "direct": len(affected_files),
        "tests": [],
        "critical_paths": []
    }

    for file in affected_files:
        if "test_" in file:
            impact["tests"].append(file)
        if any(critical in file for critical in ["auth", "payment", "api"]):
            impact["critical_paths"].append(file)

    return impact
```

### Orphan Detection
```python
def find_orphan_functions(module_path: str) -> list[str]:
    functions = get_functions_in_file(module_path)
    orphans = []

    for func in functions:
        callers = get_function_callers(func["name"], module_path)
        if len(callers) == 0 and not func["name"].startswith("test_"):
            orphans.append(func["name"])

    return orphans
```

### Dependency Cycle Detection
```python
def detect_circular_dependencies(start_file: str) -> list[list[str]]:
    visited = set()
    cycles = []

    def dfs(file_path: str, path: list[str]):
        if file_path in path:
            cycle = path[path.index(file_path):]
            cycles.append(cycle)
            return

        if file_path in visited:
            return

        visited.add(file_path)
        deps = get_file_dependencies(file_path)

        for dep in deps["imports"]:
            dfs(dep["path"], path + [file_path])

    dfs(start_file, [])
    return cycles
```

## Graph Update Strategy
- Index on repository clone/update
- Incremental updates on file changes
- Full re-index on major refactors
- Cache validity: 24 hours

## Limitations
- Graph must be indexed first (pre-execution hook)
- Limited to indexed languages (Python primary)
- May miss dynamic imports
- Reflection/metaprogramming not fully captured

## Integration with Other Skills
- **code-analysis**: Enhance with AST details
- **test-execution**: Verify coverage claims
- **git-operations**: Update graph after commits
- **repo-context**: Combined structural and historical context
