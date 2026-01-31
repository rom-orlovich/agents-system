# Testing Response Templates

Templates for reporting test results and testing progress.

## Test Results Template

### Test Suite Results

````markdown
## ✅ Test Results

**Test Suite:** {suite_name}
**Status:** {status}
**Duration:** {duration}

### Summary

- **Total Tests:** {total}
- **Passed:** {passed} ✅
- **Failed:** {failed} ❌
- **Skipped:** {skipped} ⏭️
- **Coverage:** {coverage}%

### Failed Tests

{failed_tests_list}

### Test Output

```bash
{test_output}
```
````

### Next Steps

{next_steps}

````

### TDD Phase Results

#### Red Phase Complete

```markdown
## 🔴 Red Phase Complete

**Tests Written:** {test_count}
**Status:** All tests failing (as expected)

### Tests Created
{test_list}

### Expected Failures
{failure_details}

### Next Phase
Proceeding to GREEN phase - implement functionality.
````

#### Green Phase Complete

```markdown
## 🟢 Green Phase Complete

**Tests Passing:** {passing_count}/{total_count}
**Status:** All tests passing

### Implementation Summary

{implementation_summary}

### Tests Verified

{verified_tests_list}

### Next Phase

Proceeding to REFACTOR phase - improve code quality.
```

#### Refactor Phase Complete

```markdown
## 🔵 Refactor Phase Complete

**Status:** Code improved, all tests still passing

### Refactoring Changes

{refactoring_changes}

### Test Status

✅ All tests passing after refactoring

### Code Quality Improvements

{quality_improvements}
```

## Test Coverage Report

```markdown
## 📊 Test Coverage Report

**Overall Coverage:** {coverage}%

### Coverage by Module

{coverage_by_module}

### Files with Low Coverage

{low_coverage_files}

### Recommendations

{recommendations}
```

## Regression Test Results

```markdown
## 🔄 Regression Test Results

**Baseline:** {baseline_version}
**Current:** {current_version}

### Comparison

{comparison_results}

### New Failures

{new_failures}

### Fixed Issues

{fixed_issues}

### Status

{status}
```

## Error Response Template

### Test Execution Failed

```markdown
## ❌ Test Execution Failed

**Error:** {error_message}

### Details

{error_details}

### Failed Tests

{failed_tests_list}

### Troubleshooting

{troubleshooting_steps}
```

## Best Practices

1. **Include test counts** - Total, passed, failed, skipped
2. **Show coverage** - Percentage and by module
3. **List failures** - With error messages
4. **Provide test output** - Actual test results
5. **Use code blocks** - For test code and output
6. **Structure by phase** - RED → GREEN → REFACTOR
7. **Include next steps** - What to do next
