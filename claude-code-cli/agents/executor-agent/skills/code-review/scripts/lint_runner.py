"""Lint runner script for code review.

Detects and runs linters/formatters in the repository.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any
import json


class LintRunner:
    """Lint runner that detects and runs linters."""

    LINTER_FILES = {
        "ruff": ["pyproject.toml", "ruff.toml", ".ruff.toml"],
        "black": ["pyproject.toml", ".black"],
        "flake8": [".flake8", "setup.cfg", "tox.ini"],
        "eslint": [".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", "package.json"],
        "prettier": [".prettierrc", ".prettierrc.json", "package.json"],
        "golangci-lint": [".golangci.yml", ".golangci.yaml"],
        "clippy": ["Cargo.toml"],
    }

    LINTER_COMMANDS = {
        "ruff": ["ruff", "check", "."],
        "black": ["black", "--check", "."],
        "flake8": ["flake8", "."],
        "eslint": ["npx", "eslint", "."],
        "prettier": ["npx", "prettier", "--check", "."],
        "golangci-lint": ["golangci-lint", "run"],
        "clippy": ["cargo", "clippy", "--", "-D", "warnings"],
    }

    def __init__(self, working_dir: str):
        """Initialize lint runner.

        Args:
            working_dir: Directory to run linters in
        """
        self.working_dir = Path(working_dir)

    def detect_linters(self) -> list[str]:
        """Detect available linters in the repository.

        Returns:
            List of linter names
        """
        linters = []
        for linter, indicators in self.LINTER_FILES.items():
            for indicator in indicators:
                if (self.working_dir / indicator).exists():
                    # Additional check for package.json linters
                    if indicator == "package.json":
                        try:
                            with open(self.working_dir / "package.json") as f:
                                package = json.load(f)
                                deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
                                if linter in deps or f"eslint" in deps or "prettier" in deps:
                                    if linter not in linters:
                                        linters.append(linter)
                        except (json.JSONDecodeError, FileNotFoundError):
                            continue
                    elif linter not in linters:
                        linters.append(linter)
        return linters

    def run_linter(self, linter: str) -> Dict[str, Any]:
        """Run a specific linter.

        Args:
            linter: Name of the linter to run

        Returns:
            Dictionary with lint results
        """
        command = self.LINTER_COMMANDS.get(linter, [])
        if not command:
            return {
                "success": False,
                "linter": linter,
                "error": f"No command defined for {linter}",
                "output": "",
                "errors": 0,
                "warnings": 0,
            }

        try:
            result = subprocess.run(
                command,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            # Parse output to get error/warning counts
            errors, warnings = self._parse_lint_output(linter, result.stdout + result.stderr)

            return {
                "success": result.returncode == 0,
                "linter": linter,
                "output": result.stdout + result.stderr,
                "errors": errors,
                "warnings": warnings,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "linter": linter,
                "error": "Linter execution timed out (2 minutes)",
                "output": "",
                "errors": 0,
                "warnings": 0,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "linter": linter,
                "error": f"{linter} not found in PATH",
                "output": "",
                "errors": 0,
                "warnings": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "linter": linter,
                "error": str(e),
                "output": "",
                "errors": 0,
                "warnings": 0,
            }

    def run_all_linters(self) -> Dict[str, Any]:
        """Run all detected linters.

        Returns:
            Dictionary with combined results
        """
        linters = self.detect_linters()
        if not linters:
            return {
                "success": True,
                "linters": [],
                "message": "No linters detected",
                "errors": 0,
                "warnings": 0,
            }

        results = []
        total_errors = 0
        total_warnings = 0
        all_passed = True

        for linter in linters:
            result = self.run_linter(linter)
            results.append(result)
            total_errors += result.get("errors", 0)
            total_warnings += result.get("warnings", 0)
            if not result["success"]:
                all_passed = False

        return {
            "success": all_passed,
            "linters": results,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
        }

    def _parse_lint_output(self, linter: str, output: str) -> tuple[int, int]:
        """Parse lint output to extract error/warning counts.

        Args:
            linter: Linter name
            output: Lint output string

        Returns:
            Tuple of (errors, warnings)
        """
        errors, warnings = 0, 0

        if linter == "ruff":
            # Count lines with error/warning indicators
            for line in output.split("\n"):
                if " error " in line.lower():
                    errors += 1
                elif " warning " in line.lower():
                    warnings += 1

        elif linter in ["eslint", "prettier"]:
            # Look for summary line
            import re
            match = re.search(r'(\d+) error', output)
            if match:
                errors = int(match.group(1))
            match = re.search(r'(\d+) warning', output)
            if match:
                warnings = int(match.group(1))

        elif linter == "flake8":
            # Each line is an error
            errors = len([line for line in output.split("\n") if line.strip() and not line.startswith(".")])

        elif linter == "black":
            # If files would be reformatted, it's an error
            if "would reformat" in output:
                errors = output.count("would reformat")

        elif linter in ["golangci-lint", "clippy"]:
            # Count error/warning lines
            for line in output.split("\n"):
                if "error" in line.lower():
                    errors += 1
                elif "warning" in line.lower():
                    warnings += 1

        return errors, warnings


def main():
    """Main entry point for CLI usage."""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python lint_runner.py <working_dir>")
        sys.exit(1)

    working_dir = sys.argv[1]
    runner = LintRunner(working_dir)
    result = runner.run_all_linters()

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
