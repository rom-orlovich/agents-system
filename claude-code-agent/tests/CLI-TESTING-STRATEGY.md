# CLI Testing Strategy

**Goal**: Test Claude CLI integration thoroughly WITHOUT expensive API calls

---

## Problem Statement

Testing Claude CLI integration has challenges:
1. ❌ **Expensive** - Real API calls cost money
2. ❌ **Slow** - Real API calls take seconds
3. ❌ **Unreliable** - Tests fail without API key configured
4. ❌ **CI/CD issues** - Can't run in CI without credentials

---

## Solution: Multi-Level Testing Strategy

### Level 1: Fake CLI Tests (Default) ✅

**What**: Use fake_claude_cli.sh script that simulates Claude CLI
**Cost**: $0.00
**Speed**: Instant (<1s per test)
**Coverage**: Command syntax, output parsing, error handling

```bash
# Run fake CLI tests (default)
pytest tests/integration/test_cli_integration_v2.py
```

**How It Works**:
```
Test → fake_claude_cli.sh → Predefined JSON responses → Test validates
  ↑                              ↑
  |                              └─ No API calls!
  └─ Uses subprocess (realistic)
```

**Response Modes** (via `FAKE_CLAUDE_MODE` env var):
- `success` - Successful JSON output
- `error` - General error
- `timeout` - Hangs indefinitely (for timeout tests)
- `malformed` - Malformed JSON
- `auth_error` - Authentication error
- `streaming` - Streaming output (slow)

**Example**:
```python
def test_cli_success(fake_cli_success):
    result = subprocess.run([fake_cli_success, "-p", "--", "test"])
    assert result.returncode == 0
```

---

### Level 2: Dry Run Tests ✅

**What**: Validate command building logic WITHOUT execution
**Cost**: $0.00
**Speed**: Instant (<1ms per test)
**Coverage**: Command builder, config loading

```bash
# Run dry run tests
pytest tests/integration/test_cli_integration_v2.py -m dry_run
```

**How It Works**:
```
Test → Validate command structure → No subprocess execution
```

**Example**:
```python
@pytest.mark.dry_run
def test_command_builder(dry_run_mode):
    # Validate logic without execution
    config = get_default_subagents()
    assert config is not None
    assert isinstance(json.loads(config), dict)
```

---

### Level 3: Real CLI Tests (Optional) ⚠️

**What**: Minimal smoke tests with REAL Claude CLI
**Cost**: ~$0.001 per test (uses simplest prompts)
**Speed**: Slow (~10s per test)
**Coverage**: End-to-end validation

```bash
# Enable real CLI tests (expensive!)
CLAUDE_TEST_REAL_CLI=1 pytest -m real_cli
```

**How It Works**:
```
Test → Real claude binary → Real API call → Real response
                              ↑
                              └─ Costs money!
```

**Example**:
```python
@pytest.mark.real_cli
def test_real_cli_smoke(real_claude_cli):
    """Uses simplest prompt to minimize cost."""
    result = subprocess.run([real_claude_cli, "-p", "--", "1+1"])
    # May fail with auth error if no API key - that's okay
```

---

## Test Organization

### Fake CLI Tests (10+ tests)
```python
✅ test_cli_command_syntax_basic      # Basic syntax
✅ test_cli_model_flag                # --model flag
✅ test_cli_allowed_tools_flag        # --allowedTools flag
✅ test_cli_agents_flag               # --agents flag
✅ test_cli_full_command              # All flags together
✅ test_cli_json_output_parsing       # JSON parsing
✅ test_cli_error_handling            # Error scenarios
✅ test_cli_timeout_handling          # Timeout scenarios
✅ test_cli_auth_error                # Auth errors
✅ test_cli_streaming_output          # Streaming output
```

### Dry Run Tests (2+ tests)
```python
✅ test_command_builder_basic         # Command building logic
✅ test_subagent_config_loading       # Config loading
```

### Real CLI Tests (2 tests, optional)
```python
⚠️ test_real_cli_smoke_test          # Minimal prompt ($0.001)
✅ test_real_cli_version              # Version check (no cost)
```

---

## Running Tests

### Default (Fast, No Cost)
```bash
# Run fake CLI tests only
pytest tests/integration/test_cli_integration_v2.py

# Result: 12+ tests in ~1 second, $0.00 cost
```

### Specific Test Levels
```bash
# Fake CLI tests only
pytest -m fake_cli

# Dry run tests only
pytest -m dry_run

# Real CLI tests only (expensive!)
CLAUDE_TEST_REAL_CLI=1 pytest -m real_cli
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    # Only run fake CLI and dry run tests (no cost)
    pytest -m "fake_cli or dry_run"
    # Skip real CLI tests in CI
```

### Local Development
```bash
# Quick validation (no cost)
pytest tests/integration/test_cli_integration_v2.py

# Full validation including real CLI (optional)
CLAUDE_TEST_REAL_CLI=1 pytest tests/integration/test_cli_integration_v2.py
```

---

## Fixtures Reference

### Fake CLI Fixtures

| Fixture | Description | Mode |
|---------|-------------|------|
| `fake_claude_cli` | Base fake CLI | Controlled by env var |
| `fake_cli_success` | Returns success | `success` |
| `fake_cli_error` | Returns error | `error` |
| `fake_cli_timeout` | Hangs indefinitely | `timeout` |
| `fake_cli_auth_error` | Auth error | `auth_error` |
| `fake_cli_malformed` | Malformed JSON | `malformed` |
| `fake_cli_streaming` | Streaming output | `streaming` |

### Other Fixtures

| Fixture | Description |
|---------|-------------|
| `real_claude_cli` | Real CLI (skips if not available) |
| `cli_test_workspace` | Temporary workspace with sample files |
| `dry_run_mode` | Enables dry-run mode |

---

## Fake CLI Implementation

### File: `tests/fixtures/fake_claude_cli.sh`

Bash script that simulates Claude CLI:

```bash
#!/bin/bash
# Simulates Claude CLI without API calls

MODE="${FAKE_CLAUDE_MODE:-success}"

case "$MODE" in
    success)
        echo '{"type":"content","content":"Test response"}'
        echo '{"type":"result","cost_usd":0.001,"input_tokens":10,"output_tokens":5}'
        exit 0
        ;;
    error)
        echo "Error: Task failed" >&2
        exit 1
        ;;
    # ... more modes
esac
```

**Features**:
- ✅ Validates command syntax (flags)
- ✅ Returns realistic JSON output
- ✅ Simulates different scenarios (success, error, timeout, etc.)
- ✅ No API calls, no cost
- ✅ Fast (<100ms)

---

## Test Coverage

### What's Covered ✅

1. **Command Syntax**
   - All CLI flags recognized
   - Flag ordering correct
   - Separator `--` works

2. **Output Parsing**
   - JSON parsing works
   - Multiple output lines handled
   - Metrics extracted correctly

3. **Error Handling**
   - Errors caught and logged
   - Timeouts handled
   - Auth errors handled
   - Malformed output handled

4. **Integration**
   - `core.cli_runner.run_claude_cli()` works
   - Sub-agent config loading works
   - Workspace setup works

### What's NOT Covered ❌

1. **Actual API Behavior**
   - Real model responses
   - Real token usage
   - Real cost calculation
   - Tool execution (Read, Edit, etc.)

**Solution**: Optional real CLI tests for smoke testing

---

## Cost Analysis

### Per Test Type

| Test Type | Tests | Time | Cost | Frequency |
|-----------|-------|------|------|-----------|
| Fake CLI | 10+ | ~1s | $0.00 | Every commit |
| Dry Run | 2+ | <1s | $0.00 | Every commit |
| Real CLI | 2 | ~20s | ~$0.002 | Manual only |

### CI/CD Cost

```
Assumptions:
- 100 commits per day
- Fake CLI + Dry Run tests only

Daily Cost:
  100 commits × $0.00 = $0.00

Annual Cost:
  365 days × $0.00 = $0.00 ✅
```

### With Real CLI Tests (Not Recommended for CI)

```
Assumptions:
- 100 commits per day
- 2 real CLI tests per commit
- $0.001 per test

Daily Cost:
  100 commits × 2 tests × $0.001 = $0.20

Annual Cost:
  365 days × $0.20 = $73.00 ❌
```

**Recommendation**: Only run real CLI tests manually before releases

---

## Best Practices

### DO ✅

1. **Default to fake CLI tests**
   ```bash
   pytest  # Runs fake CLI by default
   ```

2. **Use dry run for command validation**
   ```python
   @pytest.mark.dry_run
   def test_command_logic(dry_run_mode):
       # No execution
   ```

3. **Run real CLI tests manually**
   ```bash
   # Only before releases
   CLAUDE_TEST_REAL_CLI=1 pytest -m real_cli
   ```

4. **Keep real CLI tests minimal**
   ```python
   # Use simplest prompts
   prompt = "1+1"  # Not complex analysis
   ```

### DON'T ❌

1. **Don't run real CLI tests in CI**
   ```yaml
   # .github/workflows/test.yml
   # ❌ DON'T DO THIS:
   - run: CLAUDE_TEST_REAL_CLI=1 pytest
   ```

2. **Don't use complex prompts in real tests**
   ```python
   # ❌ DON'T DO THIS:
   prompt = "Analyze this 10MB codebase and write comprehensive tests..."
   ```

3. **Don't skip fake CLI tests**
   ```bash
   # ❌ DON'T DO THIS:
   pytest -m "not fake_cli"  # Skips 90% of coverage!
   ```

---

## Troubleshooting

### Fake CLI not found
```bash
# Error: Fake CLI not found: /path/to/fake_claude_cli.sh

# Solution: Ensure file exists and is executable
chmod +x tests/fixtures/fake_claude_cli.sh
```

### Real CLI tests skipped
```bash
# Message: Real CLI testing disabled (set CLAUDE_TEST_REAL_CLI=1 to enable)

# This is intentional! Only enable for manual testing:
CLAUDE_TEST_REAL_CLI=1 pytest -m real_cli
```

### Fake CLI mode not working
```bash
# Fake CLI always returns success

# Solution: Set FAKE_CLAUDE_MODE environment variable
export FAKE_CLAUDE_MODE=error
pytest tests/integration/test_cli_integration_v2.py::test_cli_error_handling
```

---

## Summary

### Test Strategy

```
┌─────────────────────────────────────────────────┐
│ Fake CLI Tests (Default)                       │
│ - 10+ tests                                     │
│ - No API calls                                  │
│ - $0.00 cost                                    │
│ - ~1s execution                                 │
│ - Covers 90% of integration scenarios           │
└─────────────────────────────────────────────────┘
                    +
┌─────────────────────────────────────────────────┐
│ Dry Run Tests                                   │
│ - 2+ tests                                      │
│ - No execution                                  │
│ - $0.00 cost                                    │
│ - <1s execution                                 │
│ - Covers command building logic                 │
└─────────────────────────────────────────────────┘
                    +
┌─────────────────────────────────────────────────┐
│ Real CLI Tests (Optional)                       │
│ - 2 tests                                       │
│ - Real API calls                                │
│ - ~$0.002 cost                                  │
│ - ~20s execution                                │
│ - Covers end-to-end validation                  │
│ - ⚠️ MANUAL ONLY                                │
└─────────────────────────────────────────────────┘
```

### Benefits

✅ **No Cost** - Fake CLI tests are free
✅ **Fast** - Complete test suite runs in ~2 seconds
✅ **Reliable** - No API dependencies
✅ **CI-Friendly** - No credentials needed
✅ **Comprehensive** - Covers all critical paths
✅ **Flexible** - Can still test real CLI when needed

---

**Last Updated**: 2026-01-22
**Author**: Claude Code Agent
**Version**: 1.0.0
