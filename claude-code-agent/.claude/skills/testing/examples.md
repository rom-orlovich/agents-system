# Testing Examples

This file contains examples from all testing phases: test creation, acceptance validation, regression prevention, resilience testing, and E2E patterns.

## Test Creation Examples

### Unit Test Examples
```python
def test_calculate_discount_applies_percentage():
    """Discount calculation applies percentage correctly."""
    result = calculate_discount(price=100, discount_percent=10)
    assert result == 90

def test_calculate_discount_rejects_negative_price():
    """Negative price is rejected."""
    with pytest.raises(ValueError, match="Price must be positive"):
        calculate_discount(price=-100, discount_percent=10)
```

### Integration Test Examples
```python
@pytest.mark.asyncio
async def test_user_registration_creates_account_and_sends_email():
    """User registration creates account and sends welcome email."""
    response = await register_user(
        email="test@example.com",
        password="secure123"
    )
    
    assert response.success is True
    assert user_exists("test@example.com")
    assert email_was_sent_to("test@example.com")
```

### Contract Test Examples
```python
def test_create_user_endpoint_returns_201():
    """POST /users returns 201 with user data."""
    response = client.post("/users", json={
        "email": "test@example.com",
        "password": "secure123"
    })
    
    assert response.status_code == 201
    assert "user_id" in response.json()
    assert response.json()["email"] == "test@example.com"

def test_create_user_endpoint_validates_email():
    """POST /users validates email format."""
    response = client.post("/users", json={
        "email": "invalid-email",
        "password": "secure123"
    })
    
    assert response.status_code == 400
    assert "email" in response.json()["errors"]
```

### Acceptance Test Example
```python
def test_password_reset_complete_workflow():
    """User can reset password via email link."""
    # Given: User exists
    user = create_user(email="test@example.com", password="oldpass")
    
    # When: User requests password reset
    request_password_reset(email="test@example.com")
    
    # Then: Email is sent with reset link
    assert email_was_sent_to("test@example.com")
    reset_link = extract_reset_link_from_email()
    
    # When: User clicks reset link and sets new password
    response = reset_password(link=reset_link, new_password="newpass123")
    
    # Then: Password is updated
    assert response.success is True
    assert can_login(email="test@example.com", password="newpass123")
    assert cannot_login(email="test@example.com", password="oldpass")
```

## Acceptance Validation Examples

### Acceptance Report Example
```markdown
# Acceptance Report: Password Reset Feature

## Requirement
As a user, I want to reset my password via email so that I can regain access if I forget my password.

## Acceptance Criteria Status

| # | Criteria | Test | Status |
|---|----------|------|--------|
| 1 | User receives email with reset link | test_password_reset_sends_email_to_valid_user | ✅ PASS |
| 2 | Link expires after 24 hours | test_password_reset_token_expires_after_24h | ✅ PASS |
| 3 | Old password no longer works | test_password_reset_invalidates_old_password | ✅ PASS |
| 4 | Rate limited to 3/hour | test_password_reset_rate_limits_requests | ✅ PASS |
| 5 | Invalid emails rejected | test_password_reset_rejects_invalid_email | ✅ PASS |

## Overall: ✅ ACCEPTED

All acceptance criteria have been met. Feature is ready for deployment.
```

### Edge Case Examples
```python
# Boundary Cases
def test_password_length_boundaries():
    assert is_valid_password("1234567") is False  # 7 chars
    assert is_valid_password("12345678") is True   # 8 chars (min)
    assert is_valid_password("12345678901234567890") is True  # 20 chars (max)
    assert is_valid_password("123456789012345678901") is False  # 21 chars

# Performance Criteria
def test_search_performance_meets_requirement():
    import time
    
    start = time.time()
    results = search(query="test query")
    duration = time.time() - start
    
    assert duration < 2.0, f"Search took {duration}s (required < 2s)"
```

## Regression Prevention Examples

### Coverage Comparison Script
```python
# scripts/compare_coverage.py
import json
import sys

def compare_coverage(baseline_file, current_file):
    with open(baseline_file) as f:
        baseline = json.load(f)
    
    with open(current_file) as f:
        current = json.load(f)
    
    baseline_pct = baseline['totals']['percent_covered']
    current_pct = current['totals']['percent_covered']
    
    diff = current_pct - baseline_pct
    
    print(f"Baseline Coverage: {baseline_pct:.2f}%")
    print(f"Current Coverage:  {current_pct:.2f}%")
    print(f"Difference:        {diff:+.2f}%")
    
    if diff < -2.0:
        print("❌ BLOCKED: Coverage dropped more than 2%")
        sys.exit(1)
    elif diff < 0:
        print("⚠️ WARNING: Coverage decreased")
    else:
        print("✅ Coverage maintained or improved")
    
    return diff

if __name__ == "__main__":
    compare_coverage(sys.argv[1], sys.argv[2])
```

### Regression Detection Workflow
```bash
# Before Changes
pytest tests/ -v --tb=short > baseline_tests.txt
pytest --cov=src --cov-report=json --cov-report=html -q
cp coverage.json baseline_coverage.json
pytest tests/benchmarks/ --benchmark-only --benchmark-json=baseline_bench.json

# After Changes
pytest tests/ -v --tb=short > new_tests.txt
diff baseline_tests.txt new_tests.txt
pytest --cov=src --cov-report=json -q
python scripts/compare_coverage.py baseline_coverage.json coverage.json
pytest tests/benchmarks/ --benchmark-only --benchmark-json=new_bench.json
python scripts/compare_benchmarks.py baseline_bench.json new_bench.json
```

## Resilience Testing Examples

### Error Handling Examples
```python
def test_handles_invalid_input():
    """System rejects invalid input gracefully."""
    response = process_data(data=None)
    
    assert response.success is False
    assert response.error == "Invalid input: data cannot be None"

def test_handles_type_mismatch():
    """System handles type mismatches gracefully."""
    response = calculate_total(price="not-a-number")
    
    assert response.success is False
    assert "must be numeric" in response.error
```

### Network Resilience Examples
```python
def test_retries_on_transient_failure():
    """System retries on transient network failures."""
    mock_api = Mock(side_effect=[
        NetworkError("Connection refused"),
        NetworkError("Connection refused"),
        {"data": "success"}
    ])
    
    response = call_external_api(mock_api)
    
    assert response.success is True
    assert mock_api.call_count == 3  # Retried twice

def test_circuit_breaker_opens_after_failures():
    """Circuit breaker opens after consecutive failures."""
    for i in range(5):
        with mock_service_failure():
            call_external_service()
    
    # Circuit should be open now
    response = call_external_service()
    assert response.error == "Circuit breaker open"
```

### Database Resilience Examples
```python
def test_transaction_rollback_on_error():
    """Transaction rolls back on error."""
    user_count_before = User.count()
    
    with pytest.raises(ValidationError):
        with transaction():
            create_user(email="test@example.com")
            create_user(email="invalid-email")  # This fails
    
    # No users should be created
    assert User.count() == user_count_before
```

### Load Resilience Examples
```python
def test_handles_concurrent_requests():
    """System handles concurrent requests correctly."""
    import concurrent.futures
    
    def make_request():
        return create_order(user_id=123, items=[{"id": 1, "qty": 1}])
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [f.result() for f in futures]
    
    # All requests should succeed
    assert all(r.success for r in results)
    # No duplicate orders
    assert len(set(r.order_id for r in results)) == 100
```

### Edge Cases Examples
```python
def test_handles_empty_input():
    """System handles empty input."""
    response = process_items(items=[])
    
    assert response.success is True
    assert response.processed_count == 0

def test_handles_unicode_and_special_characters():
    """System handles unicode and special characters."""
    special_names = [
        "José García",
        "北京",
        "Müller",
        "O'Brien",
        "user@domain.com"
    ]
    
    for name in special_names:
        response = create_user(name=name)
        assert response.success is True
```

## E2E Testing Examples

### Browser-Based E2E (Playwright)
```python
from playwright.sync_api import Page, expect

def test_user_registration_flow(page: Page):
    """Complete user registration workflow."""
    # Navigate to registration page
    page.goto("https://app.example.com/register")
    
    # Fill registration form
    page.fill("#email", "test@example.com")
    page.fill("#password", "secure123")
    page.fill("#name", "Test User")
    
    # Submit form
    page.click("button[type='submit']")
    
    # Verify success
    expect(page.locator(".success-message")).to_be_visible()
    expect(page.locator(".success-message")).to_contain_text("Registration successful")
    
    # Verify redirect to login
    expect(page).to_have_url("https://app.example.com/login")
```

### API-Based E2E
```python
def test_complete_api_workflow():
    """Complete API workflow from authentication to data operations."""
    # Authenticate
    auth_response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "secure123"
    })
    assert auth_response.status_code == 200
    token = auth_response.json()["token"]
    
    # Create resource
    create_response = client.post(
        "/resources",
        json={"name": "Test Resource"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_response.status_code == 201
    resource_id = create_response.json()["id"]
    
    # Retrieve resource
    get_response = client.get(
        f"/resources/{resource_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Resource"
    
    # Delete resource
    delete_response = client.delete(
        f"/resources/{resource_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 204
```

### CLI-Based E2E
```python
def test_cli_workflow():
    """Command-line workflow from initialization to deployment."""
    import subprocess
    
    # Initialize project
    result = subprocess.run(
        ["mycli", "init", "test-project"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Project initialized" in result.stdout
    
    # Build project
    result = subprocess.run(
        ["mycli", "build"],
        capture_output=True,
        text=True,
        cwd="test-project"
    )
    assert result.returncode == 0
    assert "Build successful" in result.stdout
    
    # Deploy project
    result = subprocess.run(
        ["mycli", "deploy", "--env", "staging"],
        capture_output=True,
        text=True,
        cwd="test-project"
    )
    assert result.returncode == 0
    assert "Deployment successful" in result.stdout
```
