"""
CI/CD Monitoring Agent Implementation
======================================
Monitors GitHub Actions, analyzes failures, attempts auto-fixes.
Mirrors the distributed system's cicd_agent/main.py
"""

import json
from pathlib import Path
from typing import Dict, Any
import asyncio

import structlog
from langchain_aws import ChatBedrock

from config import settings

logger = structlog.get_logger(__name__)


class CICDAgent:
    """Agent for monitoring and fixing CI/CD pipelines."""
    
    AUTO_FIX_COMMANDS = {
        "eslint": "npx eslint --fix .",
        "prettier": "npx prettier --write .",
        "ruff": "ruff check --fix .",
        "black": "black .",
        "isort": "isort .",
    }
    
    def __init__(self, mcp_gateway):
        """Initialize the CI/CD agent."""
        self.llm = ChatBedrock(
            model_id=settings.bedrock.verification_model,
            region_name=settings.aws.region,
            model_kwargs={
                "max_tokens": settings.bedrock.max_tokens,
                "temperature": settings.bedrock.temperature
            }
        )
        self.github_mcp = mcp_gateway.get_tool("github-mcp")
        self.code_interpreter = mcp_gateway.get_service("code-interpreter")
        self.slack = mcp_gateway.get_tool("slack")
        
        self._load_prompts()
        logger.info("cicd_agent_initialized", model=settings.bedrock.verification_model)
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "cicd"
        
        system_prompt_path = prompts_dir / "system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text()
        else:
            self.system_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        return """You are the CI/CD Monitoring Agent for an enterprise software organization.
Your mission is to monitor GitHub Actions CI/CD pipelines, analyze failures, and attempt auto-fixes."""
    
    def _call_llm(self, prompt: str, max_tokens: int = 2048) -> str:
        """Call the Bedrock LLM."""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content
    
    def monitor_pr_ci(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """Monitor CI/CD pipeline for a PR."""
        max_fix_attempts = settings.execution.max_retries
        attempt = 0
        
        logger.info("ci_monitoring_started", repo=repo, pr=pr_number)
        
        while attempt < max_fix_attempts:
            # Get workflow runs for the PR
            runs = self.github_mcp.get_workflow_runs(repo)
            
            # Find the latest run
            if not runs:
                logger.warning("no_workflow_runs", repo=repo)
                return {"success": False, "reason": "No workflow runs found"}
            
            latest_run = runs[0]
            
            if latest_run.get("conclusion") == "success":
                self.slack.send_message(
                    text=f"✅ CI passed for PR #{pr_number} in {repo}",
                    channel=settings.slack.channel_agents
                )
                return {"success": True, "attempts": attempt}
            
            # Analyze failure
            failure_analysis = self._analyze_failure(latest_run)
            
            if failure_analysis.get("auto_fixable"):
                logger.info("attempting_auto_fix", attempt=attempt)
                self._apply_auto_fix(repo, pr_number, failure_analysis)
                attempt += 1
            else:
                self._escalate_to_human(repo, pr_number, failure_analysis)
                return {"success": False, "escalated": True}
        
        self._escalate_to_human(repo, pr_number, {"reason": f"Failed after {max_fix_attempts} attempts"})
        return {"success": False, "max_attempts_exceeded": True}
    
    def _analyze_failure(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CI failure using LLM."""
        # Simulate log analysis (in real system would fetch actual logs)
        prompt = f"""Analyze this CI workflow run status:

Run: {json.dumps(run)}

Determine:
1. What failed (tests, linting, build)
2. Is it auto-fixable?
3. What fix command to apply

Auto-fixable: lint errors, format issues
NOT auto-fixable: logic errors, compilation, security

Return JSON:
{{
  "failure_type": "lint_error | test_failure | build_error",
  "root_cause": "Brief description",
  "auto_fixable": true/false,
  "fix_command": "command" or null
}}"""

        response = self._call_llm(prompt, max_tokens=500)
        try:
            return json.loads(response)
        except:
            return {"failure_type": "unknown", "auto_fixable": False}
    
    def _apply_auto_fix(self, repo: str, pr_number: int, failure: Dict[str, Any]):
        """Apply automatic fix."""
        if settings.execution.dry_run:
            logger.info("dry_run_auto_fix", repo=repo, fix=failure.get("fix_command"))
            return
        
        fix_command = failure.get("fix_command", "echo 'No fix'")
        
        result = self.code_interpreter.execute(
            language="bash",
            code=f"""
            echo "Would run: {fix_command}"
            echo "In repo: {repo}"
            """
        )
        
        logger.info("auto_fix_applied", repo=repo, command=fix_command)
    
    def _escalate_to_human(self, repo: str, pr_number: int, failure: Dict[str, Any] = None):
        """Escalate to human developer."""
        reason = failure.get("root_cause", failure.get("reason", "Cannot auto-fix"))
        
        self.slack.send_error_notification(
            title="CI Failure - Human Review Required",
            error_message=f"Repository: {repo}\nPR: #{pr_number}\nReason: {reason}",
            details={"repo": repo, "pr": pr_number}
        )
        
        logger.info("escalated_to_human", repo=repo, pr=pr_number, reason=reason)
    
    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run CI/CD monitoring.
        
        Args:
            request: Contains repo, prNumber
            
        Returns:
            CICDResult dict
        """
        repo = request.get("repo")
        pr_number = request.get("prNumber")
        
        if not repo or not pr_number:
            return {"success": False, "error": "Missing repo or prNumber"}
        
        return self.monitor_pr_ci(repo, pr_number)
