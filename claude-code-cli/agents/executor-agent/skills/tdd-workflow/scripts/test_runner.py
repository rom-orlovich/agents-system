"""Test runner script for TDD workflow.

Detects the test framework and runs tests in the repository.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any
import json


class TestRunner:
    """Test runner that detects and runs tests."""

    FRAMEWORK_FILES = {
        "pytest": ["pytest.ini", "pyproject.toml", "setup.cfg", "tests/"],
        "jest": ["jest.config.js", "jest.config.ts", "package.json"],
        "mocha": [".mocharc.json", ".mocharc.js", "package.json"],
        "go": ["go.mod", "go.sum"],
        "cargo": ["Cargo.toml"],
    }

    FRAMEWORK_COMMANDS = {
        "pytest": ["pytest", "-v", "--tb=short"],
        "jest": ["npm", "test"],
        "mocha": ["npm", "test"],
        "go": ["go", "test", "./..."],
        "cargo": ["cargo", "test"],
    }

    def __init__(self, working_dir: str):
        """Initialize test runner.

        Args:
            working_dir: Directory to run tests in
        """
        self.working_dir = Path(working_dir)

    def detect_framework(self) -> str | None:
        """Detect the test framework used in the repository.

        Returns:
            Framework name or None if no framework detected
        """
        for framework, indicators in self.FRAMEWORK_FILES.items():
            for indicator in indicators:
                if (self.working_dir / indicator).exists():
                    # Additional checks for package.json frameworks
                    if indicator == "package.json":
                        try:
                            with open(self.working_dir / "package.json") as f:
                                package = json.load(f)
                                deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
                                if framework in deps:
                                    return framework
                        except (json.JSONDecodeError, FileNotFoundError):
                            continue
                    else:
                        return framework
        return None

    def run_tests(self) -> Dict[str, Any]:
        """Run tests and return results.

        Returns:
            Dictionary with test results
        """
        framework = self.detect_framework()
        if not framework:
            return {
                "success": False,
                "framework": "unknown",
                "error": "No test framework detected",
                "output": "",
                "passed": 0,
                "failed": 0,
                "total": 0,
            }

        command = self.FRAMEWORK_COMMANDS.get(framework, [])
        if not command:
            return {
                "success": False,
                "framework": framework,
                "error": f"No command defined for {framework}",
                "output": "",
                "passed": 0,
                "failed": 0,
                "total": 0,
            }

        try:
            result = subprocess.run(
                command,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Parse output to get test counts
            passed, failed, total = self._parse_test_output(framework, result.stdout + result.stderr)

            return {
                "success": result.returncode == 0,
                "framework": framework,
                "output": result.stdout + result.stderr,
                "passed": passed,
                "failed": failed,
                "total": total,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "framework": framework,
                "error": "Test execution timed out (5 minutes)",
                "output": "",
                "passed": 0,
                "failed": 0,
                "total": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "framework": framework,
                "error": str(e),
                "output": "",
                "passed": 0,
                "failed": 0,
                "total": 0,
            }

    def _parse_test_output(self, framework: str, output: str) -> tuple[int, int, int]:
        """Parse test output to extract counts.

        Args:
            framework: Test framework name
            output: Test output string

        Returns:
            Tuple of (passed, failed, total)
        """
        passed, failed = 0, 0

        if framework == "pytest":
            # Look for patterns like "5 passed, 2 failed"
            import re
            match = re.search(r'(\d+) passed', output)
            if match:
                passed = int(match.group(1))
            match = re.search(r'(\d+) failed', output)
            if match:
                failed = int(match.group(1))

        elif framework in ["jest", "mocha"]:
            # Look for patterns like "Tests: 3 failed, 5 passed, 8 total"
            import re
            match = re.search(r'(\d+) passed', output)
            if match:
                passed = int(match.group(1))
            match = re.search(r'(\d+) failed', output)
            if match:
                failed = int(match.group(1))

        elif framework == "go":
            # Count PASS and FAIL lines
            passed = output.count("PASS")
            failed = output.count("FAIL")

        elif framework == "cargo":
            # Look for patterns like "test result: ok. 5 passed; 0 failed"
            import re
            match = re.search(r'(\d+) passed', output)
            if match:
                passed = int(match.group(1))
            match = re.search(r'(\d+) failed', output)
            if match:
                failed = int(match.group(1))

        total = passed + failed
        return passed, failed, total


def main():
    """Main entry point for CLI usage."""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py <working_dir>")
        sys.exit(1)

    working_dir = sys.argv[1]
    runner = TestRunner(working_dir)
    result = runner.run_tests()

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
