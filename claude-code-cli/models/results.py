"""Test, lint, and execution result models."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

from types.enums import TestFramework


@dataclass
class TestResult:
    """Result of running tests."""
    framework: TestFramework
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    output: str
    failures: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class LintResult:
    """Result of running linter."""
    passed: bool
    error_count: int
    warning_count: int
    output: str
    fixable: int = 0


@dataclass
class ClaudeCodeResult:
    """Result from Claude Code CLI execution."""
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: Optional[int] = None
    pr_url: Optional[str] = None
    return_code: int = 0
