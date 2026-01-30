# Code Analysis Skill

## Purpose
Parse, analyze, and understand code structure, patterns, and relationships using AST and static analysis.

## Capabilities
- Parse Python code into Abstract Syntax Tree (AST)
- Identify functions, classes, methods, and variables
- Detect code patterns and anti-patterns
- Trace data flow and dependencies
- Calculate code complexity metrics
- Find code smells and violations

## Available Operations

### Parse File to AST
```python
parse_python_file(file_path: str) -> ast.Module
```
Returns AST representation of Python file.

### Extract Functions
```python
get_functions(module: ast.Module) -> list[FunctionDef]
```
Returns all function definitions with metadata.

### Extract Classes
```python
get_classes(module: ast.Module) -> list[ClassDef]
```
Returns all class definitions with methods.

### Find Function Calls
```python
find_calls(node: ast.Node, target_name: str) -> list[ast.Call]
```
Find all calls to a specific function.

### Calculate Complexity
```python
calculate_complexity(function: ast.FunctionDef) -> int
```
Calculate cyclomatic complexity (McCabe score).

### Detect Patterns
```python
detect_pattern(code: str, pattern_type: PatternType) -> list[Match]
```
Detect specific code patterns:
- `sql_injection`: Raw SQL with string concatenation
- `hardcoded_secret`: API keys, passwords in code
- `unsafe_eval`: Use of eval() or exec()
- `missing_type_hints`: Functions without type annotations

### Trace Data Flow
```python
trace_variable(var_name: str, scope: ast.Node) -> list[Assignment]
```
Trace all assignments and usages of a variable.

## When to Use
- Before making code changes: Understand structure
- During code review: Identify anti-patterns
- Bug investigation: Trace execution paths
- Refactoring: Understand dependencies
- Security scanning: Detect vulnerabilities

## Example Usage

### Find All API Endpoints
```python
ast_tree = parse_python_file("routes.py")
functions = get_functions(ast_tree)
endpoints = [f for f in functions if has_decorator(f, "app.route")]
```

### Check Type Safety
```python
functions = get_functions(ast_tree)
missing_types = [f for f in functions if not has_type_hints(f)]
```

### Find SQL Injection Risks
```python
patterns = detect_pattern(code, PatternType.SQL_INJECTION)
for pattern in patterns:
    report_vulnerability(pattern.location, pattern.description)
```

## Complexity Thresholds
- 1-10: Simple, easy to test
- 11-20: Moderate, acceptable
- 21-50: Complex, needs refactoring
- 50+: Very complex, split into smaller functions

## Limitations
- Python-specific (cannot parse other languages)
- Static analysis only (no runtime behavior)
- May produce false positives for patterns
- Cannot detect all security issues

## Integration with Other Skills
- **knowledge-graph**: Cross-reference with graph relationships
- **test-execution**: Verify complexity with test coverage
- **repo-context**: Combine with historical context
