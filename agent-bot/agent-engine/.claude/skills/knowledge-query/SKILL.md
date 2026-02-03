# Knowledge Query Skill

Query the organization's knowledge base for relevant context using hybrid search (vectors + code graph).

## Purpose

This skill enables searching across:
- **Code repositories** - Semantic search through indexed source code
- **Jira tickets** - Find related bugs, stories, and tasks
- **Confluence documentation** - Search technical docs and architecture guides
- **Code relationships** - Analyze dependencies, call graphs, and class hierarchies

## When to Use

- Before implementing code changes (find similar implementations)
- When analyzing bugs (find related tickets and documentation)
- When understanding system architecture (query documentation)
- When finding dependencies and call graphs (use GKG)
- When looking for code patterns or examples

## MCP Tools Available

### LlamaIndex MCP (llamaindex)

1. **knowledge_query** - Hybrid search across all sources
   ```
   Args:
     - query: Natural language query
     - org_id: Organization ID
     - source_types: "code,jira,confluence" (comma-separated)
     - top_k: Number of results (default: 10)
   ```

2. **code_search** - Search code specifically
   ```
   Args:
     - query: Code or natural language query
     - org_id: Organization ID
     - repo_filter: Repository glob pattern (e.g., "backend-*")
     - language: Programming language filter
     - top_k: Number of results
   ```

3. **search_jira_tickets** - Search Jira tickets
   ```
   Args:
     - query: Natural language query
     - org_id: Organization ID
     - project: Project key filter
     - status: Status filter (Open, In Progress, Done, *)
     - top_k: Number of results
   ```

4. **search_confluence** - Search documentation
   ```
   Args:
     - query: Natural language query
     - org_id: Organization ID
     - space: Space key filter
     - top_k: Number of results
   ```

5. **find_related_code** - Find related code via graph
   ```
   Args:
     - entity: Entity name (function, class, module)
     - entity_type: Type (function, class, module, file)
     - org_id: Organization ID
     - relationship: Relationship type (calls, imports, extends, all)
   ```

### GKG MCP (gkg)

1. **analyze_dependencies** - Analyze file dependencies
   ```
   Args:
     - file_path: Path to the file
     - org_id: Organization ID
     - repo: Repository name
     - depth: Traversal depth (default: 3)
   ```

2. **find_usages** - Find symbol usages
   ```
   Args:
     - symbol: Symbol name to search
     - org_id: Organization ID
     - repo: Repository filter
   ```

3. **get_call_graph** - Get function call graph
   ```
   Args:
     - function_name: Function name
     - org_id: Organization ID
     - repo: Repository name
     - direction: "callers", "callees", or "both"
     - depth: Traversal depth
   ```

4. **get_class_hierarchy** - Get class inheritance hierarchy
   ```
   Args:
     - class_name: Class name
     - org_id: Organization ID
     - repo: Repository filter
   ```

## Workflow

### Step 1: Identify Query Intent

Determine what type of information is needed:
- Code implementation → use `code_search` or `knowledge_query`
- Bug investigation → use `search_jira_tickets`
- Architecture understanding → use `search_confluence`
- Dependency analysis → use `analyze_dependencies`
- Impact analysis → use `find_usages` or `get_call_graph`

### Step 2: Execute Query

Use the appropriate MCP tool with relevant filters:

```
# Example: Find authentication-related code
llamaindex:code_search(
  query="user authentication OAuth token validation",
  org_id="acme",
  language="python",
  top_k=10
)

# Example: Find related Jira tickets
llamaindex:search_jira_tickets(
  query="login authentication failure",
  org_id="acme",
  project="ENG",
  status="Open"
)

# Example: Analyze function callers
gkg:get_call_graph(
  function_name="authenticate_user",
  org_id="acme",
  repo="backend-api",
  direction="callers"
)
```

### Step 3: Analyze Results

- Review relevance scores
- Cross-reference code with documentation
- Identify patterns and relationships
- Extract actionable context for the task

### Step 4: Apply Context

Use gathered information to:
- Understand existing implementations
- Identify potential impact of changes
- Find similar solutions to reference
- Ensure consistency with existing patterns

## Best Practices

1. **Start broad, narrow down** - Begin with `knowledge_query` then use specific tools
2. **Cross-reference sources** - Combine code search with ticket search
3. **Use graph queries for impact** - Before modifying code, check `find_usages`
4. **Filter by relevance** - Use project/repo filters to reduce noise
5. **Check documentation first** - Search Confluence before implementing

## Example Usage

### Bug Fix Scenario

```
1. Search for related tickets:
   search_jira_tickets(query="authentication timeout", org_id="acme")

2. Find relevant code:
   code_search(query="auth timeout handling", org_id="acme", repo_filter="backend-*")

3. Analyze impact:
   get_call_graph(function_name="handle_auth_timeout", org_id="acme", repo="backend-api")

4. Check documentation:
   search_confluence(query="authentication architecture timeout", org_id="acme")
```

### Feature Implementation Scenario

```
1. Find similar implementations:
   knowledge_query(query="user preference settings implementation", org_id="acme")

2. Understand dependencies:
   analyze_dependencies(file_path="src/settings/preferences.py", org_id="acme", repo="backend-api")

3. Find patterns:
   code_search(query="settings CRUD operations", org_id="acme", language="python")
```
