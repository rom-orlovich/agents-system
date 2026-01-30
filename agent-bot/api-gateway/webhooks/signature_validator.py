import hmac
import hashlib
import time
from abc import ABC, abstractmethod


class SignatureValidator(ABC):
    @abstractmethod
    def validate(self, payload: bytes, signature: str, **kwargs: str) -> bool:
        pass


class GitHubSignatureValidator(SignatureValidator):
    def __init__(self, secret: str):
        self.secret = secret

    def validate(self, payload: bytes, signature: str, **kwargs: str) -> bool:
        if not signature.startswith("sha256="):
            return False

        expected_signature = "sha256=" + hmac.new(
            self.secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class SlackSignatureValidator(SignatureValidator):
    def __init__(self, signing_secret: str, max_timestamp_age_seconds: int = 300):
        self.signing_secret = signing_secret
        self.max_timestamp_age_seconds = max_timestamp_age_seconds

    def validate(self, payload: bytes, signature: str, timestamp: str, **kwargs: str) -> bool:
        try:
            request_timestamp = int(timestamp)
            current_timestamp = int(time.time())

            if abs(current_timestamp - request_timestamp) > self.max_timestamp_age_seconds:
                return False
        except (ValueError, TypeError):
            return False

        if not signature.startswith("v0="):
            return False

        sig_basestring = f"v0:{timestamp}:".encode() + payload
        expected_signature = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(), sig_basestring, hashlib.sha256
            ).hexdigest()
        )

        return hmac.compare_digest(signature, expected_signature)


class JiraSignatureValidator(SignatureValidator):
    def __init__(self, secret: str):
        self.secret = secret

    def validate(self, payload: bytes, signature: str, **kwargs: str) -> bool:
        expected_signature = hmac.new(
            self.secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class SentrySignatureValidator(SignatureValidator):
    def __init__(self, secret: str):
        self.secret = secret

    def validate(self, payload: bytes, signature: str, **kwargs: str) -> bool:
        expected_signature = hmac.new(
            self.secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
