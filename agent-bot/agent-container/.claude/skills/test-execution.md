# Test Execution Skill

## Purpose
Execute tests, measure coverage, and verify code quality through automated testing.

## Capabilities
- Run unit tests with pytest
- Execute integration and E2E tests
- Measure code coverage
- Generate coverage reports
- Identify untested code paths
- Run specific test suites or files

## Available Operations

### Run All Tests
```python
run_tests(path: str = "tests/") -> TestResult
```
Execute all tests in directory.

### Run Specific Tests
```python
run_test_file(file_path: str) -> TestResult
```
Execute tests from specific file.

### Run with Coverage
```python
run_with_coverage(path: str = "tests/") -> CoverageReport
```
Run tests and measure code coverage.

### Run Specific Test
```python
run_single_test(test_path: str) -> TestResult
```
Execute single test function (e.g., "tests/test_foo.py::test_bar").

### Get Coverage for File
```python
get_file_coverage(source_file: str) -> FileCoverage
```
Get coverage metrics for specific source file.

### Find Untested Functions
```python
find_untested_code(module_path: str) -> list[UncoveredItem]
```
Identify functions/methods without test coverage.

### Run Tests by Marker
```python
run_marked_tests(marker: str) -> TestResult
```
Run tests with specific pytest marker (e.g., "slow", "integration").

## Test Result Format
```python
@dataclass
class TestResult:
    passed: int
    failed: int
    skipped: int
    total: int
    duration_seconds: float
    failures: list[TestFailure]
    success: bool
```

## Coverage Report Format
```python
@dataclass
class CoverageReport:
    total_coverage_pct: float
    files: dict[str, FileCoverage]
    uncovered_lines: dict[str, list[int]]

@dataclass
class FileCoverage:
    file_path: str
    coverage_pct: float
    statements: int
    missing: int
    excluded: int
```

## Pytest Configuration
Default pytest settings:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
markers =
    slow: Slow-running tests
    integration: Integration tests
    unit: Unit tests
```

## Coverage Thresholds
- **Excellent**: ≥ 90%
- **Good**: 80-89%
- **Acceptable**: 70-79%
- **Needs Improvement**: < 70%

## When to Use
- After code changes: Verify no regressions
- During development: TDD workflow
- Code review: Check test coverage
- CI/CD pipeline: Automated validation
- Before merge: Final verification

## Example Workflows

### TDD Workflow
```python
write_test("test_new_feature.py")
result = run_test_file("tests/test_new_feature.py")
assert result.failed > 0  # RED phase

implement_feature("feature.py")
result = run_test_file("tests/test_new_feature.py")
assert result.success  # GREEN phase
```

### Coverage Analysis
```python
coverage = run_with_coverage("tests/")
for file, cov in coverage.files.items():
    if cov.coverage_pct < 80:
        untested = find_untested_code(file)
        generate_tests_for(untested)
```

### Regression Detection
```python
baseline = run_tests()
make_changes()
current = run_tests()

if current.failed > baseline.failed:
    report_regression(current.failures)
```

## Test Execution Flags
```python
run_tests(
    path="tests/",
    verbose=True,           # Show detailed output
    fail_fast=True,         # Stop on first failure
    capture=False,          # Show print statements
    markers="not slow",     # Skip slow tests
    parallel=4              # Run tests in parallel
)
```

## Interpreting Failures

### Common Failure Types
1. **AssertionError**: Expected value mismatch
2. **TypeError**: Type incompatibility
3. **AttributeError**: Missing attribute/method
4. **ImportError**: Missing dependency
5. **TimeoutError**: Async test timeout

### Failure Analysis
```python
for failure in result.failures:
    print(f"Test: {failure.test_name}")
    print(f"Error: {failure.error_type}")
    print(f"Location: {failure.file}:{failure.line}")
    print(f"Message: {failure.message}")
```

## Performance Metrics
- Unit tests: < 100ms per test
- Integration tests: < 1s per test
- E2E tests: < 10s per test
- Full suite: < 5 minutes

## Integration with Other Skills
- **code-analysis**: Identify complex code needing tests
- **knowledge-graph**: Find test coverage gaps
- **git-operations**: Run tests on specific commits
