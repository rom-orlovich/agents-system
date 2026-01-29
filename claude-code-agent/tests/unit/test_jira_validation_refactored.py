"""TDD tests for Jira validate_response_format refactoring (Phase 3)."""

import pytest
import json


class TestJiraValidateResponseFormat:
    """Test Jira validate_response_format is available in validation.py."""

    def test_validate_response_format_can_be_imported(self):
        """validate_response_format should be importable from jira.validation."""
        from api.webhooks.jira.validation import validate_response_format

        assert callable(validate_response_format)

    def test_validate_jira_adf_format_valid(self):
        """Validate correct Jira ADF JSON format passes."""
        from api.webhooks.jira.validation import validate_response_format

        valid_adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Test content"
                        }
                    ]
                }
            ]
        }

        valid_adf_json = json.dumps(valid_adf)
        is_valid, error_msg = validate_response_format(valid_adf_json, "jira")

        assert is_valid is True
        assert error_msg == ""

    def test_validate_jira_invalid_json(self):
        """Jira validation should fail for invalid JSON."""
        from api.webhooks.jira.validation import validate_response_format

        invalid_json = "{ this is not valid json }"
        is_valid, error_msg = validate_response_format(invalid_json, "jira")

        assert is_valid is False
        assert "JSON" in error_msg or "json" in error_msg

    def test_validate_jira_missing_doc_type(self):
        """Jira validation should fail when type is not 'doc'."""
        from api.webhooks.jira.validation import validate_response_format

        invalid_adf = {
            "type": "paragraph",
            "content": []
        }

        invalid_adf_json = json.dumps(invalid_adf)
        is_valid, error_msg = validate_response_format(invalid_adf_json, "jira")

        assert is_valid is False
        assert "doc" in error_msg.lower() or "type" in error_msg.lower()

    def test_validate_jira_missing_content_array(self):
        """Jira validation should fail when content array is missing."""
        from api.webhooks.jira.validation import validate_response_format

        invalid_adf = {
            "type": "doc",
            "version": 1
        }

        invalid_adf_json = json.dumps(invalid_adf)
        is_valid, error_msg = validate_response_format(invalid_adf_json, "jira")

        assert is_valid is False
        assert "content" in error_msg.lower()
