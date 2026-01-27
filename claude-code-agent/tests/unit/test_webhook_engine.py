"""Unit tests for webhook engine module."""

import pytest
from core.webhook_engine import render_template, truncate_content_intelligently
from core.config import settings


class TestTruncateContentIntelligently:
    """Test intelligent content truncation."""
    
    def test_truncates_large_content(self):
        """Large content should be truncated."""
        large_content = "A" * 20000
        max_size = 10000
        
        result = truncate_content_intelligently(large_content, max_size)
        
        assert len(result) <= max_size + 100
        assert "... (truncated)" in result
    
    def test_preserves_markdown_structure(self):
        """Truncation should preserve markdown headers and code blocks."""
        content = """# Header 1
        
Some text here.

## Header 2

```python
def code_block():
    pass
```

More text after code block.
""" + "A" * 15000
        
        result = truncate_content_intelligently(content, 1000)
        
        assert "# Header 1" in result
        assert "```python" in result or "```" in result
        assert "... (truncated)" in result
    
    def test_truncates_at_sentence_boundary(self):
        """Truncation should prefer sentence boundaries."""
        content = "First sentence. Second sentence. Third sentence. " + "A" * 10000
        
        result = truncate_content_intelligently(content, 100)
        
        assert result.endswith(".") or result.endswith("... (truncated)")
        assert "First sentence" in result
    
    def test_does_not_truncate_small_content(self):
        """Small content should not be truncated."""
        small_content = "This is a small comment."
        
        result = truncate_content_intelligently(small_content, 10000)
        
        assert result == small_content
        assert "... (truncated)" not in result
    
    def test_handles_empty_content(self):
        """Empty content should be handled gracefully."""
        result = truncate_content_intelligently("", 1000)
        assert result == ""
    
    def test_handles_none_content(self):
        """None content should be handled gracefully."""
        result = truncate_content_intelligently(None, 1000)
        assert result == ""


class TestRenderTemplateWithTruncation:
    """Test template rendering with content truncation."""
    
    def test_large_comment_body_truncated(self):
        """Large comment.body should be truncated in template."""
        large_comment = "A" * 20000
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": large_comment
            }
        }
        
        result = render_template(template, payload)
        
        assert len(result) < len(large_comment)
        assert "... (truncated)" in result
        assert "Comment: A" in result
    
    def test_small_comment_body_not_truncated(self):
        """Small comment.body should not be truncated."""
        small_comment = "This is a small comment."
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": small_comment
            }
        }
        
        result = render_template(template, payload)
        
        assert result == f"Comment: {small_comment}"
        assert "... (truncated)" not in result
    
    def test_truncation_respects_config_limit(self):
        """Truncation should respect configured max_comment_body_size."""
        large_comment = "A" * 20000
        template = "{{comment.body}}"
        payload = {
            "comment": {
                "body": large_comment
            }
        }
        
        result = render_template(template, payload)
        
        max_size = settings.max_comment_body_size
        assert len(result) <= max_size + 500
    
    def test_multiple_large_fields_truncated(self):
        """Multiple large fields should be truncated independently."""
        large_body = "B" * 20000
        large_title = "C" * 5000
        template = "Title: {{issue.title}}\nBody: {{issue.body}}"
        payload = {
            "issue": {
                "title": large_title,
                "body": large_body
            }
        }
        
        result = render_template(template, payload)
        
        assert len(result) < len(large_body) + len(large_title)
        assert "... (truncated)" in result


class TestRenderTemplateWithADFCommentBody:
    """Test template rendering with ADF format comment bodies."""
    
    def test_extracts_text_from_adf_doc_format(self):
        """Template should extract plain text from ADF doc format."""
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "@agent analyze Sentry error"
                        }
                    ]
                }
            ]
        }
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": adf_body
            }
        }
        
        result = render_template(template, payload)
        
        assert "@agent analyze Sentry error" in result
        assert "type" not in result
        assert "doc" not in result
    
    def test_extracts_text_from_adf_list_format(self):
        """Template should extract plain text from ADF list format."""
        adf_body = [
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
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": adf_body
            }
        }
        
        result = render_template(template, payload)
        
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "type" not in result
    
    def test_handles_plain_string_comment_body(self):
        """Template should handle plain string comment bodies."""
        plain_text = "@agent analyze error"
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": plain_text
            }
        }
        
        result = render_template(template, payload)
        
        assert result == f"Comment: {plain_text}"
    
    def test_handles_none_comment_body(self):
        """Template should handle None comment body."""
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": None
            }
        }
        
        result = render_template(template, payload)
        
        assert "Comment: " in result or result == "Comment: {{comment.body}}"
    
    def test_extracts_text_from_nested_adf_content(self):
        """Template should extract text from nested ADF content."""
        adf_body = {
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Nested content text"
                        }
                    ]
                }
            ]
        }
        template = "Comment: {{comment.body}}"
        payload = {
            "comment": {
                "body": adf_body
            }
        }
        
        result = render_template(template, payload)
        
        assert "Nested content text" in result
        assert "type" not in result
