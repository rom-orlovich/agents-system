"""
Execution Agent Implementation
==============================
Implements code according to plan, following TDD methodology.
"""

import json
import os
from typing import List, Optional
import structlog
from langchain_aws import ChatBedrock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import settings


logger = structlog.get_logger(__name__)


class ExecutionAgent:
    """Agent for executing implementation plans."""
    
    def __init__(self, agentcore_gateway):
        """Initialize the execution agent."""
        self.llm = ChatBedrock(
            model_id=settings.models.execution_model,
            region_name=settings.aws.region
        )
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.code_interpreter = agentcore_gateway.get_service("code-interpreter")
        
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "execution"
        )
        
        with open(os.path.join(prompts_dir, "system.md")) as f:
            self.system_prompt = f.read()
    
    async def execute_plan(self, plan: dict, pr_info: dict) -> dict:
        """Execute implementation plan task by task."""
        results = {
            "completed_tasks": [],
            "failed_tasks": [],
            "commits": []
        }
        
        await self.code_interpreter.execute(
            language="bash",
            code=f"""
            git clone https://github.com/{settings.github.org}/{pr_info['repo']}.git
            cd {pr_info['repo']}
            git checkout {pr_info['branch']}
            """
        )
        
        for task in sorted(plan.get('tasks', []), key=lambda t: t['id']):
            if not all(dep in results['completed_tasks'] for dep in task.get('dependencies', [])):
                results['failed_tasks'].append({
                    "task": task,
                    "reason": "Dependencies not met"
                })
                continue
            
            success = await self._execute_task(task, pr_info['repo'])
            
            if success:
                results['completed_tasks'].append(task['id'])
            else:
                results['failed_tasks'].append({"task": task, "reason": "Execution failed"})
                break
        
        return results
    
    async def _execute_task(self, task: dict, repo: str) -> bool:
        """Execute a single task with retry logic."""
        max_attempts = settings.retry.max_task_attempts
        
        for attempt in range(max_attempts):
            try:
                existing_code = None
                try:
                    existing_code = await self.github_mcp.get_file(
                        repo=repo,
                        path=task['file']
                    )
                except Exception:
                    pass
                
                new_code = await self._generate_code(task, existing_code)
                
                await self.code_interpreter.execute(
                    language="bash",
                    code=f"""
                    cd {repo}
                    mkdir -p $(dirname {task['file']})
                    cat > {task['file']} << 'ENDOFCODE'
{new_code}
ENDOFCODE
                    """
                )
                
                test_result = await self._run_tests(task, repo)
                
                if test_result['success']:
                    await self._commit_changes(task, repo)
                    return True
                else:
                    if attempt < max_attempts - 1:
                        await self._analyze_test_failure(test_result['output'])
                        continue
                    else:
                        logger.error("task_failed_after_retries", task=task['id'], attempts=max_attempts)
                        return False
            
            except Exception as e:
                logger.error("task_execution_error", task=task['id'], error=str(e))
                if attempt == max_attempts - 1:
                    return False
        
        return False
    
    async def _generate_code(self, task: dict, existing_code: Optional[str]) -> str:
        """Generate code for the task."""
        existing_context = f"Existing code to modify:\n{existing_code}" if existing_code else "This is a new file."
        
        prompt = f"""
        {self.system_prompt}
        
        Implement this task:
        
        Task: {task['description']}
        File: {task['file']}
        
        {existing_context}
        
        Requirements:
        1. Follow existing code patterns and style
        2. Handle edge cases and errors properly
        3. Add clear comments where needed
        4. Use meaningful variable/function names
        5. Make it production-ready
        
        Output ONLY the complete file content, no explanations.
        """
        
        response = await self.llm.ainvoke(prompt)
        return response.content
    
    async def _run_tests(self, task: dict, repo: str) -> dict:
        """Run tests related to this task."""
        test_file = task.get('testFile') or self._infer_test_file(task['file'])
        
        result = await self.code_interpreter.execute(
            language="bash",
            code=f"""
            cd {repo}
            
            if [ -f "package.json" ]; then
                npm test -- {test_file} 2>&1 || true
            elif [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
                pytest {test_file} -v 2>&1 || true
            elif [ -f "go.mod" ]; then
                go test {test_file} 2>&1 || true
            fi
            """,
            timeout_seconds=settings.code_interpreter.timeout_seconds
        )
        
        return {
            "success": result.return_code == 0,
            "output": result.stdout + result.stderr
        }
    
    def _infer_test_file(self, source_file: str) -> str:
        """Infer test file path from source file."""
        if source_file.startswith("src/"):
            return source_file.replace("src/", "tests/").replace(".py", "_test.py")
        return source_file.replace(".py", "_test.py")
    
    async def _analyze_test_failure(self, output: str) -> dict:
        """Analyze test failure output."""
        prompt = f"""
        Analyze this test failure and provide insights:
        
        ```
        {output[-2000:]}
        ```
        
        Return JSON:
        {{
          "failure_type": "assertion | import | syntax | timeout",
          "root_cause": "Brief description",
          "suggested_fix": "What to change"
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        return json.loads(response.content)
    
    async def _commit_changes(self, task: dict, repo: str):
        """Commit changes following org conventions."""
        commit_message = f"""{settings.conventions.commit_prefix_feature} {task['description']}

Task ID: {task['id']}
File: {task['file']}

Generated by AI Execution Agent"""
        
        await self.code_interpreter.execute(
            language="bash",
            code=f"""
            cd {repo}
            git add {task['file']}
            git commit -m "{commit_message}"
            git push origin HEAD
            """
        )


async def handler(event, context):
    """Lambda handler for execution agent."""
    from agents.shared.gateway import AgentCoreGateway
    
    gateway = AgentCoreGateway()
    agent = ExecutionAgent(gateway)
    
    result = await agent.execute_plan(
        plan=event.get("plan", {}),
        pr_info=event.get("prInfo", {})
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
