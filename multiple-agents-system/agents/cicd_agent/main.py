"""
CI/CD Monitoring Agent Implementation
======================================
Monitors GitHub Actions, analyzes failures, attempts auto-fixes.
"""

import json
import os
import asyncio
import structlog
from langchain_aws import ChatBedrock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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
    
    def __init__(self, agentcore_gateway):
        """Initialize the CI/CD agent."""
        self.llm = ChatBedrock(
            model_id=settings.models.cicd_model,
            region_name=settings.aws.region
        )
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.code_interpreter = agentcore_gateway.get_service("code-interpreter")
        self.slack = agentcore_gateway.get_tool("slack")
        
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "cicd"
        )
        
        with open(os.path.join(prompts_dir, "system.md")) as f:
            self.system_prompt = f.read()
    
    async def monitor_pr_ci(self, repo: str, pr_number: int) -> dict:
        """Monitor CI/CD pipeline for a PR."""
        max_fix_attempts = settings.retry.max_ci_fix_attempts
        attempt = 0
        
        while attempt < max_fix_attempts:
            workflow = await self._wait_for_workflow(repo, pr_number)
            
            if workflow['conclusion'] == 'success':
                await self.slack.send_message(
                    channel=settings.slack.channel_agents,
                    text=f"✅ CI passed for PR #{pr_number} in {repo}"
                )
                return {"success": True, "attempts": attempt}
            
            logs = await self.github_mcp.get_workflow_logs(
                repo=repo,
                run_id=workflow['id']
            )
            
            failure_analysis = await self._analyze_failure(logs)
            
            if failure_analysis['auto_fixable']:
                await self._apply_auto_fix(
                    repo=repo,
                    pr_number=pr_number,
                    failure=failure_analysis
                )
                attempt += 1
            else:
                await self._escalate_to_human(
                    repo=repo,
                    pr_number=pr_number,
                    failure=failure_analysis,
                    logs=logs
                )
                return {"success": False, "escalated": True}
        
        await self._escalate_to_human(
            repo=repo,
            pr_number=pr_number,
            reason=f"Failed after {max_fix_attempts} auto-fix attempts"
        )
        return {"success": False, "max_attempts_exceeded": True}
    
    async def _wait_for_workflow(self, repo: str, pr_number: int, timeout: int = 3600) -> dict:
        """Wait for workflow to complete."""
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            pr = await self.github_mcp.get_pull_request(repo=repo, pr_number=pr_number)
            head_sha = pr['head']['sha']
            
            runs = await self.github_mcp.get_workflow_runs(
                repo=repo,
                head_sha=head_sha
            )
            
            completed = [r for r in runs if r.get('status') == 'completed']
            if completed:
                return completed[0]
            
            await asyncio.sleep(30)
        
        raise TimeoutError("Workflow did not complete in time")
    
    async def _analyze_failure(self, logs: str) -> dict:
        """Analyze CI failure logs using LLM."""
        prompt = f"""
        Analyze these CI failure logs and determine:
        
        1. What failed (e.g., tests, linting, build)
        2. Root cause (specific error)
        3. Is it auto-fixable? (yes/no)
        4. If yes, what fix to apply
        
        Logs:
        ```
        {logs[-5000:]}
        ```
        
        Auto-fixable categories:
        - Lint errors (can run eslint --fix)
        - Format issues (can run prettier/black)
        - Simple import errors
        
        NOT auto-fixable:
        - Logic errors in tests
        - Compilation errors
        - Infrastructure failures
        - Security vulnerabilities
        
        Return JSON:
        {{
          "failure_type": "lint_error | test_failure | build_error | infrastructure",
          "root_cause": "Brief description",
          "auto_fixable": true/false,
          "fix_command": "command" or null
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        return json.loads(response.content)
    
    async def _apply_auto_fix(self, repo: str, pr_number: int, failure: dict):
        """Apply automatic fix."""
        logger.info("applying_auto_fix", repo=repo, pr=pr_number, fix=failure.get('fix_command'))
        
        pr = await self.github_mcp.get_pull_request(repo=repo, pr_number=pr_number)
        branch = pr['head']['ref']
        
        fix_result = await self.code_interpreter.execute(
            language="bash",
            code=f"""
            git clone https://github.com/{settings.github.org}/{repo}.git
            cd {repo}
            git checkout {branch}
            
            {failure.get('fix_command', 'echo "No fix command"')}
            
            git add -A
            git commit -m "fix: Auto-fix CI failure

{failure.get('root_cause', 'CI failure')}

Applied: {failure.get('fix_command', 'N/A')}

Auto-fixed by CI/CD Agent"
            git push origin {branch}
            """
        )
        
        if fix_result.return_code != 0:
            raise Exception(f"Auto-fix failed: {fix_result.stderr}")
    
    async def _escalate_to_human(self, repo: str, pr_number: int, **kwargs):
        """Escalate to human developer."""
        failure = kwargs.get('failure', {})
        reason = kwargs.get('reason', failure.get('root_cause', 'Cannot auto-fix'))
        
        await self.slack.send_message(
            channel=settings.slack.channel_agents,
            text=f"""⚠️ CI Failure - Human Review Required

*Repository:* {repo}
*PR:* #{pr_number}
*Reason:* {reason}

View PR: https://github.com/{settings.github.org}/{repo}/pull/{pr_number}"""
        )


async def handler(event, context):
    """Lambda handler for CI/CD agent."""
    from agents.shared.gateway import AgentCoreGateway
    
    gateway = AgentCoreGateway()
    agent = CICDAgent(gateway)
    
    result = await agent.monitor_pr_ci(
        repo=event.get("repo"),
        pr_number=event.get("prNumber")
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
