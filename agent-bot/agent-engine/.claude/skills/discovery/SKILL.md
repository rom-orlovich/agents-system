---
name: discovery
description: Code discovery and file search capabilities for finding files, searching code patterns, and navigating codebases. Use when searching for files, code patterns, symbols, or exploring project structure.
---

# Discovery Skill

Code discovery combining file-based search with knowledge graph-powered semantic search.

## Quick Reference

- **Templates**: See [templates.md](templates.md) for reporting discovery results

## Available Actions

### search_files

Find files by name pattern.

**Parameters:**

- `pattern` (required): Glob pattern to match (e.g., `*.py`, `test_*.ts`)
- `working_dir` (optional): Directory to search in

**Example:**

```json
{
  "action": "search_files",
  "parameters": {
    "pattern": "*.py",
    "working_dir": "/app/repos/agent-bot"
  }
}
```

### search_code

Search for code patterns using grep.

**Parameters:**

- `query` (required): Text or regex pattern to search for
- `file_types` (optional): Filter by file extensions (default: `*.py`)

**Example:**

```json
{
  "action": "search_code",
  "parameters": {
    "query": "async def process_",
    "file_types": ["*.py", "*.ts"]
  }
}
```

### list_directory

List contents of a directory.

**Parameters:**

- `path` (optional): Path relative to working directory (default: current directory)

**Example:**

```json
{
  "action": "list_directory",
  "parameters": {
    "path": "src/services"
  }
}
```

### get_file_info

Get detailed information about a file.

**Parameters:**

- `path` (required): Path to the file

**Example:**

```json
{
  "action": "get_file_info",
  "parameters": {
    "path": "src/main.py"
  }
}
```

### find_references

Find all references to a symbol in the codebase.

**Parameters:**

- `symbol` (required): Symbol name to search for

**Example:**

```json
{
  "action": "find_references",
  "parameters": {
    "symbol": "TaskWorker"
  }
}
```

### get_project_structure

Get an overview of the project file structure.

**Parameters:**

- None

**Example:**

```json
{
  "action": "get_project_structure",
  "parameters": {}
}
```

## Integration with Knowledge Graph

For enhanced semantic search, use the knowledge-graph skill which provides:

- Semantic code search by function/class names
- Dependency graph navigation
- Call graph analysis
- Symbol reference tracking across the entire codebase

## Workflow Example

### Basic Discovery Flow

1. Get project structure:

   ```
   get_project_structure()
   ```

2. List specific directory:

   ```
   list_directory(path="src/services")
   ```

3. Search for relevant files:

   ```
   search_files(pattern="*service*.py")
   ```

4. Search for specific code:

   ```
   search_code(query="class.*Service")
   ```

5. Find symbol references:
   ```
   find_references(symbol="AuthService")
   ```

### Combined with Knowledge Graph

For deeper analysis, combine with knowledge-graph skill:

1. Traditional search:

   ```
   search_code(query="async def authenticate")
   ```

2. Knowledge graph search:

   ```
   [Use knowledge-graph skill]
   search_codebase(query="authenticate", node_types=["function"])
   ```

3. Get dependencies:
   ```
   [Use knowledge-graph skill]
   find_dependencies(node_id="<result_id>")
   ```

## Output Format

All actions return structured data:

```json
{
  "success": true,
  "result": {
    "files": ["path/to/file1.py", "path/to/file2.py"],
    "count": 2
  }
}
```

Or on error:

```json
{
  "success": false,
  "error": "Error message"
}
```
