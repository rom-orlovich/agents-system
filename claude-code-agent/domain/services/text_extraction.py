"""
Unified text extraction from various webhook payload formats.

This module consolidates the duplicated text extraction logic from:
- github/utils.py: extract_github_text
- slack/utils.py: extract_slack_text
- jira/utils.py: extract_jira_comment_text, _safe_string

Handles:
- Plain strings
- Lists of strings
- Dictionaries with 'text', 'body', 'content' keys
- Jira ADF (Atlassian Document Format)
- None values with defaults
"""

from typing import Any, Tuple


class TextExtractor:
    """
    Unified text extraction from various webhook payload formats.

    Handles cases where webhook fields might be strings, lists, dicts, or None.
    This can happen in edge cases or with certain webhook formats.
    """

    @staticmethod
    def extract(
        value: Any,
        default: str = "",
        keys_to_try: Tuple[str, ...] = ("text", "body", "content"),
    ) -> str:
        """
        Safely extract text from various structures.

        Args:
            value: Value to extract text from (can be str, list, dict, None, etc.)
            default: Default value to return if value is None or empty
            keys_to_try: Dictionary keys to try when extracting from dict

        Returns:
            String representation of the value

        Examples:
            >>> TextExtractor.extract("Hello World")
            'Hello World'
            >>> TextExtractor.extract(["Hello", "World"])
            'Hello World'
            >>> TextExtractor.extract({"text": "Hello"})
            'Hello'
            >>> TextExtractor.extract(None, default="N/A")
            'N/A'
        """
        if value is None:
            return default

        if isinstance(value, str):
            return value if value else default

        if isinstance(value, list):
            if not value:
                return default
            parts = []
            for item in value:
                if item is not None:
                    extracted = TextExtractor.extract(item, "")
                    if extracted:
                        parts.append(extracted)
            return " ".join(parts) if parts else default

        if isinstance(value, dict):
            # Try each key in order
            for key in keys_to_try:
                if key in value:
                    return TextExtractor.extract(value[key], default, keys_to_try)
            # Check for ADF format
            if "content" in value and isinstance(value.get("content"), list):
                return TextExtractor.extract_jira_adf(value)

        # Convert other types to string
        return str(value) if value else default

    @staticmethod
    def extract_jira_adf(adf_content: Any) -> str:
        """
        Extract text from Jira ADF (Atlassian Document Format).

        ADF is a JSON-based format used by Jira for rich text content.
        This method recursively extracts all text nodes.

        Args:
            adf_content: ADF content (dict with 'content' key or list of nodes)

        Returns:
            Extracted plain text

        Example ADF:
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "Hello "},
                            {"type": "text", "text": "World"}
                        ]
                    }
                ]
            }
        """
        if adf_content is None:
            return ""

        if isinstance(adf_content, str):
            return adf_content

        if isinstance(adf_content, dict):
            # Direct text node
            if "text" in adf_content:
                return adf_content["text"]
            # Container with content
            if "content" in adf_content:
                return TextExtractor.extract_jira_adf(adf_content["content"])
            return ""

        if isinstance(adf_content, list):
            texts = []
            for item in adf_content:
                extracted = TextExtractor.extract_jira_adf(item)
                if extracted:
                    texts.append(extracted)
            return " ".join(texts)

        return ""

    @staticmethod
    def safe_string(value: Any, default: str = "") -> str:
        """
        Safely convert value to string.

        Alias for extract() with no keys_to_try, just type conversion.

        Args:
            value: Value to convert
            default: Default if value is None/empty

        Returns:
            String representation
        """
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            # Handle Jira ADF format
            if "content" in value:
                return TextExtractor.extract_jira_adf(value)
            if "text" in value:
                return str(value.get("text", default))
        return str(value) if value else default
