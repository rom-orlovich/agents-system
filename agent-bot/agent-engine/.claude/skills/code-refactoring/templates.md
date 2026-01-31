# Code Refactoring Response Templates

Templates for reporting refactoring results.

## Refactoring Complete Template

### Refactoring Summary

```markdown
## ✅ Refactoring Complete

**Scope:** {scope}
**Files Modified:** {file_count}

### Summary

{summary}

### Refactoring Applied

{refactoring_types_list}

### Changes Made

{changes_list}

### Files Modified

{files_list}

### Test Status

✅ All tests passing after refactoring

### Code Quality Improvements

{quality_improvements}

---

_Automated refactoring by Claude Agent_
```

## Specific Refactoring Templates

### Extract Method

````markdown
## 🔧 Extract Method Refactoring

**File:** `{file_path}`
**Method Extracted:** `{method_name}`

### Before

```{language}
{before_code}
```
````

### After

```{language}
{after_code}
```

### Benefits

- Reduced complexity: {complexity_before} → {complexity_after}
- Improved readability
- Reusable method

````

### Extract Constant

```markdown
## 🔧 Extract Constant Refactoring

**File:** `{file_path}`
**Constant:** `{constant_name}`

### Before
```{language}
{before_code}
````

### After

```{language}
{after_code}
```

### Benefits

- Single source of truth
- Easier maintenance
- Better readability

````

### Simplify Condition

```markdown
## 🔧 Simplify Condition Refactoring

**File:** `{file_path}`
**Location:** Line {line_number}

### Before
```{language}
{before_code}
````

### After

```{language}
{after_code}
```

### Benefits

- Reduced complexity
- Improved readability
- Easier to test

````

## Refactoring Analysis Template

### Code Smell Detection

```markdown
## 🔍 Code Smell Analysis

**File:** `{file_path}`

### Smells Detected
{smells_list}

### Recommendations
{recommendations_list}

### Priority
{priority_level}
````

## Error Response Template

### Refactoring Failed

````markdown
## ❌ Refactoring Failed

**Error:** {error_message}

### Details

{error_details}

### Original Code

```{language}
{original_code}
```
````

### Troubleshooting

{troubleshooting_steps}

```

## Best Practices

1. **Show before/after** - Code comparison
2. **Explain benefits** - Why refactoring improves code
3. **Include metrics** - Complexity reduction, line count
4. **Verify tests** - Confirm tests still pass
5. **List changes** - What was refactored
6. **Use code blocks** - For code examples
7. **Structure clearly** - Use headers and lists
```
