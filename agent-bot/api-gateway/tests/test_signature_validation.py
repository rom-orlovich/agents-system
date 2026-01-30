import pytest
from webhooks.signature_validator import (
    GitHubSignatureValidator,
    JiraSignatureValidator,
    SlackSignatureValidator,
    SentrySignatureValidator,
)
import hashlib
import hmac
import time


@pytest.fixture
def github_secret():
    return "test-github-secret"


@pytest.fixture
def jira_secret():
    return "test-jira-secret"


@pytest.fixture
def slack_signing_secret():
    return "test-slack-secret"


@pytest.fixture
def sentry_secret():
    return "test-sentry-secret"


def test_github_signature_validation_success(github_secret: str):
    validator = GitHubSignatureValidator(github_secret)

    payload = b'{"action":"opened","number":1}'
    signature = "sha256=" + hmac.new(
        github_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    is_valid = validator.validate(payload, signature)

    assert is_valid is True


def test_github_signature_validation_failure(github_secret: str):
    validator = GitHubSignatureValidator(github_secret)

    payload = b'{"action":"opened","number":1}'
    invalid_signature = "sha256=invalid_signature"

    is_valid = validator.validate(payload, invalid_signature)

    assert is_valid is False


def test_github_signature_validation_missing_prefix(github_secret: str):
    validator = GitHubSignatureValidator(github_secret)

    payload = b'{"action":"opened","number":1}'
    signature_without_prefix = hmac.new(
        github_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    is_valid = validator.validate(payload, signature_without_prefix)

    assert is_valid is False


def test_slack_signature_validation_success(slack_signing_secret: str):
    validator = SlackSignatureValidator(slack_signing_secret)

    timestamp = str(int(time.time()))
    payload = b'{"type":"event_callback","event":{"text":"hello"}}'

    sig_basestring = f"v0:{timestamp}:".encode() + payload
    signature = (
        "v0="
        + hmac.new(
            slack_signing_secret.encode(), sig_basestring, hashlib.sha256
        ).hexdigest()
    )

    is_valid = validator.validate(payload, signature, timestamp)

    assert is_valid is True


def test_slack_signature_validation_expired_timestamp(slack_signing_secret: str):
    validator = SlackSignatureValidator(slack_signing_secret)

    old_timestamp = str(int(time.time()) - 400)
    payload = b'{"type":"event_callback"}'

    sig_basestring = f"v0:{old_timestamp}:".encode() + payload
    signature = (
        "v0="
        + hmac.new(
            slack_signing_secret.encode(), sig_basestring, hashlib.sha256
        ).hexdigest()
    )

    is_valid = validator.validate(payload, signature, old_timestamp)

    assert is_valid is False


def test_slack_signature_validation_invalid_signature(slack_signing_secret: str):
    validator = SlackSignatureValidator(slack_signing_secret)

    timestamp = str(int(time.time()))
    payload = b'{"type":"event_callback"}'
    invalid_signature = "v0=invalid"

    is_valid = validator.validate(payload, invalid_signature, timestamp)

    assert is_valid is False


def test_jira_signature_validation_success(jira_secret: str):
    validator = JiraSignatureValidator(jira_secret)

    payload = b'{"webhookEvent":"jira:issue_created"}'
    signature = hmac.new(jira_secret.encode(), payload, hashlib.sha256).hexdigest()

    is_valid = validator.validate(payload, signature)

    assert is_valid is True


def test_jira_signature_validation_failure(jira_secret: str):
    validator = JiraSignatureValidator(jira_secret)

    payload = b'{"webhookEvent":"jira:issue_created"}'
    invalid_signature = "invalid_signature"

    is_valid = validator.validate(payload, invalid_signature)

    assert is_valid is False


def test_sentry_signature_validation_success(sentry_secret: str):
    validator = SentrySignatureValidator(sentry_secret)

    payload = b'{"action":"created","data":{}}'
    signature = hmac.new(sentry_secret.encode(), payload, hashlib.sha256).hexdigest()

    is_valid = validator.validate(payload, signature)

    assert is_valid is True


def test_sentry_signature_validation_failure(sentry_secret: str):
    validator = SentrySignatureValidator(sentry_secret)

    payload = b'{"action":"created","data":{}}'
    invalid_signature = "invalid_signature"

    is_valid = validator.validate(payload, invalid_signature)

    assert is_valid is False
