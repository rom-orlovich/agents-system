# Discovery Response Templates

Templates for reporting discovery results.

## Search Results Template

### File Search Results

```markdown
## 🔍 File Search Results

**Pattern:** `{pattern}`
**Files Found:** {count}

### Results

{files_list}

### Summary

{summary}
```

### Code Search Results

```markdown
## 🔍 Code Search Results

**Query:** `{query}`
**Matches Found:** {count}

### Top Matches

{matches_list}

### Files Analyzed

{files_list}

### Summary

{summary}
```

### Semantic Search Results

```markdown
## 🔍 Semantic Search Results

**Query:** {query}
**Results Found:** {count}

### Top Results

{results_list}

### Related Symbols

{related_symbols}

### Summary

{summary}
```

## Discovery Summary Template

### Project Structure Analysis

```markdown
## 📁 Project Structure Analysis

**Root Directory:** `{root_dir}`

### Structure

{structure_tree}

### Key Files

{key_files_list}

### Technologies Detected

{technologies_list}

### Summary

{summary}
```

### Dependency Analysis

```markdown
## 📦 Dependency Analysis

**Scope:** {scope}

### Dependencies Found

{dependencies_list}

### Import Graph

{import_graph}

### Summary

{summary}
```

## Error Response Template

### Search Failed

```markdown
## ❌ Search Failed

**Error:** {error_message}

### Details

{error_details}

### Suggestions

{suggestions}
```

## Best Practices

1. **Include search parameters** - Pattern, query, scope
2. **Show result count** - How many matches found
3. **List top results** - Most relevant matches first
4. **Provide summary** - Brief overview of findings
5. **Include file paths** - Where results were found
6. **Use code blocks** - For code snippets
7. **Structure results** - Use lists and sections
