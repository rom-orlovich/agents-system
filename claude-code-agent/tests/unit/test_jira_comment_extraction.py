"""
Unit tests for Jira comment text extraction utility.
"""

import pytest
from api.webhooks.jira.utils import extract_jira_comment_text


class TestExtractJiraCommentText:
    """Tests for extract_jira_comment_text function."""
    
    def test_handles_string_body(self):
        """Test that string bodies are returned as-is."""
        result = extract_jira_comment_text("Simple text comment")
        assert result == "Simple text comment"
    
    def test_handles_none_body(self):
        """Test that None returns empty string."""
        result = extract_jira_comment_text(None)
        assert result == ""
    
    def test_handles_empty_string(self):
        """Test that empty string returns empty string."""
        result = extract_jira_comment_text("")
        assert result == ""
    
    def test_handles_adf_doc_format(self):
        """Test extraction from ADF doc format."""
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "This is a test comment"
                        }
                    ]
                }
            ]
        }
        
        result = extract_jira_comment_text(adf_body)
        assert result == "This is a test comment"
    
    def test_handles_adf_with_multiple_paragraphs(self):
        """Test extraction from ADF with multiple paragraphs."""
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "First paragraph"
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Second paragraph"
                        }
                    ]
                }
            ]
        }
        
        result = extract_jira_comment_text(adf_body)
        assert "First paragraph" in result
        assert "Second paragraph" in result
    
    def test_handles_adf_list_format(self):
        """Test extraction from list-formatted ADF."""
        adf_body = [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "List item one"
                    }
                ]
            },
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "List item two"
                    }
                ]
            }
        ]
        
        result = extract_jira_comment_text(adf_body)
        assert "List item one" in result
        assert "List item two" in result
    
    def test_handles_nested_adf_content(self):
        """Test extraction from nested ADF content."""
        adf_body = {
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Nested content"
                        }
                    ]
                }
            ]
        }
        
        result = extract_jira_comment_text(adf_body)
        assert result == "Nested content"
    
    def test_handles_text_node_directly(self):
        """Test extraction from direct text node."""
        text_node = {
            "type": "text",
            "text": "Direct text node"
        }
        
        result = extract_jira_comment_text(text_node)
        assert result == "Direct text node"
    
    def test_handles_dict_with_text_key(self):
        """Test extraction from dict with text key."""
        body = {"text": "Text from dict"}
        result = extract_jira_comment_text(body)
        assert result == "Text from dict"
    
    def test_handles_mixed_content(self):
        """Test extraction from mixed content types."""
        adf_body = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Part one"},
                        {"type": "text", "text": " Part two"}
                    ]
                }
            ]
        }
        
        result = extract_jira_comment_text(adf_body)
        assert "Part one" in result
        assert "Part two" in result
    
    def test_handles_empty_adf(self):
        """Test extraction from empty ADF structure."""
        adf_body = {
            "type": "doc",
            "content": []
        }
        
        result = extract_jira_comment_text(adf_body)
        assert result == ""
    
    def test_handles_non_string_types(self):
        """Test that non-string types are converted to string."""
        result = extract_jira_comment_text(123)
        assert result == "123"
        
        result = extract_jira_comment_text(True)
        assert result == "True"
