"""
Webhook signature validation utilities.
"""

import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebhookValidator:
    """
    Utilities for validating webhook signatures.

    Supports:
    - HMAC-SHA256 validation
    - Constant-time comparison
    """

    @staticmethod
    def validate_hmac_sha256(
        payload: bytes,
        signature: str,
        secret: str,
        signature_prefix: str = ""
    ) -> bool:
        """
        Validate HMAC-SHA256 signature.

        Args:
            payload: Raw payload bytes
            signature: Signature from webhook headers
            secret: Webhook secret key
            signature_prefix: Optional prefix to strip from signature (e.g., "sha256=")

        Returns:
            True if signature is valid, False otherwise
        """
        if not secret:
            logger.error("Webhook secret is not configured")
            return False

        # Strip prefix if present
        if signature_prefix and signature.startswith(signature_prefix):
            signature = signature[len(signature_prefix):]

        # Calculate expected signature
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(signature, expected)

        if not is_valid:
            logger.warning("Webhook signature validation failed")

        return is_valid

    @staticmethod
    def validate_hmac_sha1(
        payload: bytes,
        signature: str,
        secret: str,
        signature_prefix: str = ""
    ) -> bool:
        """
        Validate HMAC-SHA1 signature (for older services).

        Args:
            payload: Raw payload bytes
            signature: Signature from webhook headers
            secret: Webhook secret key
            signature_prefix: Optional prefix to strip from signature (e.g., "sha1=")

        Returns:
            True if signature is valid, False otherwise
        """
        if not secret:
            logger.error("Webhook secret is not configured")
            return False

        # Strip prefix if present
        if signature_prefix and signature.startswith(signature_prefix):
            signature = signature[len(signature_prefix):]

        # Calculate expected signature
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha1
        ).hexdigest()

        # Constant-time comparison
        is_valid = hmac.compare_digest(signature, expected)

        if not is_valid:
            logger.warning("Webhook signature validation failed")

        return is_valid

    @staticmethod
    def generate_signature(payload: bytes, secret: str, algorithm: str = "sha256") -> str:
        """
        Generate HMAC signature for testing.

        Args:
            payload: Payload bytes
            secret: Secret key
            algorithm: Hash algorithm ("sha256" or "sha1")

        Returns:
            Hex signature string
        """
        hash_func = hashlib.sha256 if algorithm == "sha256" else hashlib.sha1

        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hash_func
        ).hexdigest()
