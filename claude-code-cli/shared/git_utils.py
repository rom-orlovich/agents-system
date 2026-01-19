"""Git utilities for repository operations.

This module provides typed, async git operations with proper error handling.
All operations are logged and return typed results.

Usage:
    from shared.git_utils import GitUtils
    
    git = GitUtils()
    
    # Clone a repository
    result = await git.clone_repository(repo)
    if result.success:
        print(f"Cloned to {git.get_repo_path(repo)}")
    
    # Run tests
    test_result = await git.run_tests(repo_path)
    if not test_result.passed:
        print(f"Tests failed: {test_result.output}")
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Optional, Tuple, List
import logging

from .types import (
    GitRepository, 
    GitOperationResult, 
    TestResult,
    LintResult,
)
from .enums import GitOperation, TestFramework
from .constants import TIMEOUT_CONFIG, WORKSPACE_DIR, GITHUB_TOKEN

logger = logging.getLogger("git_utils")


class GitUtils:
    """Git operations utility class.
    
    Provides async git operations with:
    - Automatic credential injection
    - Timeout handling
    - Typed results
    - Test framework detection
    
    Attributes:
        workspace_dir: Base directory for repositories
    
    Example:
        git = GitUtils()
        
        repo = GitRepository.from_full_name("org/repo")
        result = await git.clone_repository(repo)
        
        if result.success:
            test_result = await git.run_tests(git.get_repo_path(repo))
    """
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize Git utilities.
        
        Args:
            workspace_dir: Base directory for repositories.
        """
        self.workspace_dir = Path(workspace_dir or WORKSPACE_DIR)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
    
    def get_repo_path(self, repository: GitRepository) -> Path:
        """Get local path for a repository.
        
        Args:
            repository: Repository info
            
        Returns:
            Path to local clone
        """
        return self.workspace_dir / repository.name
    
    # =========================================================================
    # Clone & Pull
    # =========================================================================
    
    async def clone_repository(
        self,
        repository: GitRepository,
        depth: int = 50,
        branch: Optional[str] = None,
    ) -> GitOperationResult:
        """Clone a repository.
        
        Args:
            repository: Repository to clone
            depth: Clone depth (shallow clone for speed)
            branch: Specific branch to clone
            
        Returns:
            GitOperationResult
        """
        repo_path = self.get_repo_path(repository)
        
        # Check if already exists
        if (repo_path / ".git").exists():
            logger.info(f"Repository exists at {repo_path}, pulling instead")
            return await self.pull(repo_path)
        
        # Build clone URL with token
        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or GITHUB_TOKEN
        
        if github_token:
            clone_url = f"https://{github_token}@github.com/{repository.full_name}.git"
        else:
            clone_url = repository.clone_url
            logger.warning("No GitHub token - clone may fail for private repos")
        
        logger.info(f"Cloning {repository.full_name} to {repo_path}")
        
        cmd = ["git", "clone", "--depth", str(depth)]
        
        if branch:
            cmd.extend(["--branch", branch])
        
        cmd.extend([clone_url, str(repo_path)])
        
        try:
            result = await self._run_command(
                cmd,
                timeout=TIMEOUT_CONFIG.git_clone,
            )
            
            if result[0] != 0:
                # Hide token from error message
                error_msg = result[2]
                if github_token:
                    error_msg = error_msg.replace(github_token, "***")
                
                return GitOperationResult(
                    operation=GitOperation.CLONE,
                    success=False,
                    output="",
                    error=error_msg,
                )
            
            logger.info(f"Successfully cloned {repository.full_name}")
            
            return GitOperationResult(
                operation=GitOperation.CLONE,
                success=True,
                output=result[1],
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Git clone timed out after {TIMEOUT_CONFIG.git_clone}s")
            return GitOperationResult(
                operation=GitOperation.CLONE,
                success=False,
                output="",
                error=f"Clone timed out after {TIMEOUT_CONFIG.git_clone} seconds",
            )
    
    async def pull(self, repo_path: Path) -> GitOperationResult:
        """Pull latest changes.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            GitOperationResult
        """
        logger.info(f"Pulling latest changes in {repo_path}")
        
        result = await self._run_git(repo_path, ["pull", "origin", "HEAD"])
        
        return GitOperationResult(
            operation=GitOperation.PULL,
            success=result[0] == 0,
            output=result[1],
            error=result[2] if result[0] != 0 else None,
        )
    
    # =========================================================================
    # Branch Operations
    # =========================================================================
    
    async def create_branch(
        self,
        repo_path: Path,
        branch_name: str,
        base_branch: str = "main",
    ) -> GitOperationResult:
        """Create and checkout a new branch.
        
        Args:
            repo_path: Path to repository
            branch_name: Name for new branch
            base_branch: Branch to create from
            
        Returns:
            GitOperationResult
        """
        logger.info(f"Creating branch {branch_name} from {base_branch}")
        
        # Fetch latest
        await self._run_git(repo_path, ["fetch", "origin", base_branch])
        
        # Create and checkout
        result = await self._run_git(
            repo_path,
            ["checkout", "-b", branch_name, f"origin/{base_branch}"],
        )
        
        return GitOperationResult(
            operation=GitOperation.BRANCH,
            success=result[0] == 0,
            output=result[1],
            error=result[2] if result[0] != 0 else None,
        )
    
    async def checkout(
        self,
        repo_path: Path,
        branch_name: str,
    ) -> GitOperationResult:
        """Checkout an existing branch.
        
        Args:
            repo_path: Path to repository
            branch_name: Branch to checkout
            
        Returns:
            GitOperationResult
        """
        result = await self._run_git(repo_path, ["checkout", branch_name])
        
        return GitOperationResult(
            operation=GitOperation.CHECKOUT,
            success=result[0] == 0,
            output=result[1],
            error=result[2] if result[0] != 0 else None,
        )
    
    # =========================================================================
    # Commit & Push
    # =========================================================================
    
    async def commit(
        self,
        repo_path: Path,
        message: str,
        files: Optional[List[str]] = None,
    ) -> GitOperationResult:
        """Stage files and create commit.
        
        Args:
            repo_path: Path to repository
            message: Commit message (should follow conventional commits)
            files: Specific files to stage (None = all changed)
            
        Returns:
            GitOperationResult with commit SHA
        """
        # Stage files
        if files:
            for file in files:
                await self._run_git(repo_path, ["add", file])
        else:
            await self._run_git(repo_path, ["add", "-A"])
        
        # Check if there's anything to commit
        status_result = await self._run_git(repo_path, ["status", "--porcelain"])
        if not status_result[1].strip():
            return GitOperationResult(
                operation=GitOperation.COMMIT,
                success=False,
                output="",
                error="Nothing to commit",
            )
        
        # Create commit
        result = await self._run_git(repo_path, ["commit", "-m", message])
        
        if result[0] != 0:
            return GitOperationResult(
                operation=GitOperation.COMMIT,
                success=False,
                output=result[1],
                error=result[2],
            )
        
        # Get commit SHA
        sha_result = await self._run_git(repo_path, ["rev-parse", "HEAD"])
        commit_sha = sha_result[1].strip() if sha_result[0] == 0 else None
        
        return GitOperationResult(
            operation=GitOperation.COMMIT,
            success=True,
            output=result[1],
            commit_sha=commit_sha,
        )
    
    async def push(
        self,
        repo_path: Path,
        branch: str,
        force: bool = False,
        set_upstream: bool = True,
    ) -> GitOperationResult:
        """Push branch to remote.
        
        Args:
            repo_path: Path to repository
            branch: Branch to push
            force: Use force-with-lease (never plain force!)
            set_upstream: Set upstream tracking
            
        Returns:
            GitOperationResult
        """
        cmd = ["push"]
        
        if force:
            cmd.append("--force-with-lease")
        
        if set_upstream:
            cmd.extend(["-u", "origin", branch])
        else:
            cmd.extend(["origin", branch])
        
        result = await self._run_git(repo_path, cmd)
        
        return GitOperationResult(
            operation=GitOperation.PUSH,
            success=result[0] == 0,
            output=result[1],
            error=result[2] if result[0] != 0 else None,
        )
    
    # =========================================================================
    # Status & Info
    # =========================================================================
    
    async def get_current_branch(self, repo_path: Path) -> Optional[str]:
        """Get current branch name.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Branch name or None
        """
        result = await self._run_git(repo_path, ["branch", "--show-current"])
        
        if result[0] == 0:
            return result[1].strip()
        return None
    
    async def get_status(self, repo_path: Path) -> GitOperationResult:
        """Get repository status.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            GitOperationResult with status output
        """
        result = await self._run_git(repo_path, ["status"])
        
        return GitOperationResult(
            operation=GitOperation.STATUS,
            success=result[0] == 0,
            output=result[1],
            error=result[2] if result[0] != 0 else None,
        )
    
    async def get_diff(
        self,
        repo_path: Path,
        staged: bool = False,
    ) -> GitOperationResult:
        """Get diff of changes.
        
        Args:
            repo_path: Path to repository
            staged: Show staged changes only
            
        Returns:
            GitOperationResult with diff output
        """
        cmd = ["diff"]
        if staged:
            cmd.append("--staged")
        
        result = await self._run_git(repo_path, cmd)
        
        return GitOperationResult(
            operation=GitOperation.DIFF,
            success=result[0] == 0,
            output=result[1],
        )
    
    # =========================================================================
    # Test Framework Detection & Running
    # =========================================================================
    
    async def detect_test_framework(self, repo_path: Path) -> TestFramework:
        """Detect which test framework the repository uses.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Detected TestFramework
        """
        # Check for Node.js
        package_json = repo_path / "package.json"
        if package_json.exists():
            return TestFramework.NPM
        
        # Check for Python
        if (repo_path / "pytest.ini").exists():
            return TestFramework.PYTEST
        if (repo_path / "pyproject.toml").exists():
            return TestFramework.PYTEST
        if (repo_path / "setup.py").exists():
            return TestFramework.PYTEST
        if (repo_path / "requirements.txt").exists():
            return TestFramework.PYTEST
        
        # Check for Go
        if (repo_path / "go.mod").exists():
            return TestFramework.GO_TEST
        
        # Check for Java
        if (repo_path / "pom.xml").exists():
            return TestFramework.MAVEN
        if (repo_path / "build.gradle").exists():
            return TestFramework.GRADLE
        
        return TestFramework.UNKNOWN
    
    async def run_tests(self, repo_path: Path) -> TestResult:
        """Run tests for the repository.
        
        Automatically detects the test framework and runs appropriate commands.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            TestResult with pass/fail status
        """
        import time
        
        framework = await self.detect_test_framework(repo_path)
        
        test_commands = {
            TestFramework.NPM: ["npm", "test"],
            TestFramework.PYTEST: ["pytest", "-v", "--tb=short"],
            TestFramework.GO_TEST: ["go", "test", "-v", "./..."],
            TestFramework.MAVEN: ["mvn", "test", "-q"],
            TestFramework.GRADLE: ["./gradlew", "test", "--quiet"],
        }
        
        if framework == TestFramework.UNKNOWN:
            return TestResult(
                framework=framework,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                duration_seconds=0,
                output="Could not detect test framework",
            )
        
        # For npm, install dependencies first
        if framework == TestFramework.NPM:
            if (repo_path / "package-lock.json").exists():
                await self._run_command(["npm", "ci"], cwd=repo_path, timeout=120)
            else:
                await self._run_command(["npm", "install"], cwd=repo_path, timeout=120)
        
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *test_commands[framework],
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env={**os.environ, "CI": "true"},
                ),
                timeout=TIMEOUT_CONFIG.test_run,
            )
            
            stdout, _ = await result.communicate()
            output = stdout.decode("utf-8", errors="replace")
            duration = time.time() - start_time
            
            # Parse test counts (simplified)
            total, passed, failed, skipped = self._parse_test_output(output, framework)
            
            return TestResult(
                framework=framework,
                passed=result.returncode == 0,
                total_tests=total,
                passed_tests=passed,
                failed_tests=failed,
                skipped_tests=skipped,
                duration_seconds=duration,
                output=output,
            )
            
        except asyncio.TimeoutError:
            return TestResult(
                framework=framework,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                skipped_tests=0,
                duration_seconds=TIMEOUT_CONFIG.test_run,
                output=f"Tests timed out after {TIMEOUT_CONFIG.test_run} seconds",
            )
    
    async def run_lint(self, repo_path: Path) -> LintResult:
        """Run linter for the repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            LintResult with error counts
        """
        framework = await self.detect_test_framework(repo_path)
        
        lint_commands = {
            TestFramework.NPM: ["npm", "run", "lint", "--if-present"],
            TestFramework.PYTEST: ["flake8", "."],
        }
        
        cmd = lint_commands.get(framework, ["echo", "No linter configured"])
        
        result = await self._run_command(cmd, cwd=repo_path, timeout=60)
        
        return LintResult(
            passed=result[0] == 0,
            error_count=0 if result[0] == 0 else 1,
            warning_count=0,
            output=result[1] + result[2],
        )
    
    def _parse_test_output(
        self,
        output: str,
        framework: TestFramework,
    ) -> Tuple[int, int, int, int]:
        """Parse test output to extract counts.
        
        Returns:
            Tuple of (total, passed, failed, skipped)
        """
        # Simple regex patterns for common formats
        if framework == TestFramework.PYTEST:
            # "5 passed, 1 failed, 2 skipped"
            match = re.search(r"(\d+) passed", output)
            passed = int(match.group(1)) if match else 0
            
            match = re.search(r"(\d+) failed", output)
            failed = int(match.group(1)) if match else 0
            
            match = re.search(r"(\d+) skipped", output)
            skipped = int(match.group(1)) if match else 0
            
            total = passed + failed + skipped
            return (total, passed, failed, skipped)
        
        # Default: just check return code
        return (0, 0, 0, 0)
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    async def _run_git(
        self,
        repo_path: Path,
        args: List[str],
    ) -> Tuple[int, str, str]:
        """Run a git command.
        
        Args:
            repo_path: Path to repository
            args: Git arguments
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        return await self._run_command(
            ["git"] + args,
            cwd=repo_path,
            timeout=60,
        )
    
    async def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 60,
    ) -> Tuple[int, str, str]:
        """Run a shell command.
        
        Args:
            cmd: Command and arguments
            cwd: Working directory
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(cwd) if cwd else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=timeout,
            )
            
            stdout, stderr = await process.communicate()
            
            return (
                process.returncode,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
            
        except asyncio.TimeoutError:
            return (1, "", f"Command timed out after {timeout}s")
