# Knowledge Graph Response Templates

Templates for reporting knowledge graph search and analysis results.

## Semantic Search Results Template

### Search Results

```markdown
## 🔍 Semantic Search Results

**Query:** {query}
**Results Found:** {count}

### Top Results

{results_list}

### Related Symbols

{related_symbols_list}

### Call Graph

{call_graph}

### Summary

{summary}
```

## Dependency Analysis Template

### Dependency Graph

````markdown
## 📦 Dependency Analysis

**Symbol:** {symbol_name}
**Type:** {symbol_type}

### Dependencies

{dependencies_list}

### Dependents

{dependents_list}

### Import Graph

```graph
{import_graph}
```
````

### Summary

{summary}

````

## Call Graph Analysis Template

### Call Chain Analysis

```markdown
## 🔗 Call Chain Analysis

**Function:** `{function_name}`
**File:** `{file_path}`

### Call Chain
{call_chain}

### Callers
{callers_list}

### Callees
{callees_list}

### Summary
{summary}
````

## Symbol Reference Template

### Symbol References

````markdown
## 📍 Symbol References

**Symbol:** `{symbol_name}`
**Type:** {symbol_type}

### Definition

**File:** `{file_path}`
**Line:** {line_number}

```{language}
{definition_code}
```
````

### References

{references_list}

### Summary

Found {count} references to `{symbol_name}`.

````

## Error Response Template

### Search Failed

```markdown
## ❌ Search Failed

**Error:** {error_message}

### Details
{error_details}

### Query Used
{query}

### Suggestions
{suggestions}
````

## Best Practices

1. **Include query/parameters** - What was searched
2. **Show result count** - How many matches found
3. **List top results** - Most relevant first
4. **Include graph visualizations** - Call graphs, dependency graphs
5. **Provide code context** - Show definitions and references
6. **Structure results** - Use lists and code blocks
7. **Include summary** - Brief overview of findings
