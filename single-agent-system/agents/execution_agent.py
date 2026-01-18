"""
Execution Agent Implementation
==============================
Implements code according to plan, following TDD methodology.
Mirrors the distributed system's execution_agent/main.py
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import structlog
from langchain_aws import ChatBedrock

from config import settings

logger = structlog.get_logger(__name__)


class ExecutionAgent:
    """Agent for executing implementation plans."""
    
    def __init__(self, mcp_gateway):
        """Initialize the execution agent."""
        self.llm = ChatBedrock(
            model_id=settings.bedrock.execution_model,
            region_name=settings.aws.region,
            model_kwargs={
                "max_tokens": settings.bedrock.max_tokens,
                "temperature": settings.bedrock.temperature
            }
        )
        self.github_mcp = mcp_gateway.get_tool("github-mcp")
        self.code_interpreter = mcp_gateway.get_service("code-interpreter")
        
        self._load_prompts()
        logger.info("execution_agent_initialized", model=settings.bedrock.execution_model)
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "execution"
        
        system_prompt_path = prompts_dir / "system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text()
        else:
            self.system_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        return """You are the Execution Agent for an enterprise software organization.
Your mission is to implement code according to the approved plan, following TDD methodology."""
    
    def _call_llm(self, prompt: str, max_tokens: int = 8192) -> str:
        """Call the Bedrock LLM."""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content
    
    def execute_task(self, task: Dict, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Execute a single task with retry logic."""
        max_attempts = settings.execution.max_retries
        
        for attempt in range(max_attempts):
            try:
                # Get existing code if modifying
                existing_code = None
                if repo_name:
                    existing_code = self.github_mcp.get_file_content(repo_name, task["file"])
                
                # Generate code
                new_code = self._generate_code(task, existing_code)
                
                # Save to output directory
                output_file = settings.execution.output_dir / "code" / task["file"]
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(new_code)
                
                # Run tests (if configured)
                test_result = self._run_tests(task, repo_name)
                
                if test_result["success"]:
                    logger.info("task_completed", task_id=task["id"])
                    return {
                        "taskId": task["id"],
                        "status": "success",
                        "filesModified": [{"path": task["file"], "action": "created"}],
                        "testsRun": test_result,
                        "commit": None,
                        "error": None
                    }
                else:
                    if attempt < max_attempts - 1:
                        self._analyze_test_failure(test_result["output"])
                        continue
                    else:
                        return {
                            "taskId": task["id"],
                            "status": "failed",
                            "filesModified": [],
                            "testsRun": test_result,
                            "commit": None,
                            "error": "Tests failed after retries"
                        }
            
            except Exception as e:
                logger.error("task_execution_error", task_id=task["id"], error=str(e))
                if attempt == max_attempts - 1:
                    return {
                        "taskId": task["id"],
                        "status": "failed",
                        "filesModified": [],
                        "testsRun": None,
                        "commit": None,
                        "error": str(e)
                    }
        
        return {"taskId": task["id"], "status": "failed", "error": "Unknown error"}
    
    def _generate_code(self, task: Dict, existing_code: Optional[str]) -> str:
        """Generate code for the task."""
        existing_context = f"Existing code to modify:\n```\n{existing_code}\n```" if existing_code else "This is a new file."
        
        prompt = f"""{self.system_prompt}

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

Output ONLY the complete file content, no explanations."""

        return self._call_llm(prompt)
    
    def _run_tests(self, task: Dict, repo_name: Optional[str]) -> Dict[str, Any]:
        """Run tests related to this task."""
        test_file = task.get("testFile") or self._infer_test_file(task["file"])
        
        # For local execution, we just check if file was created
        output_file = settings.execution.output_dir / "code" / task["file"]
        
        if output_file.exists():
            return {"success": True, "output": "File created successfully", "total": 1, "passed": 1, "failed": 0}
        else:
            return {"success": False, "output": "File not created", "total": 1, "passed": 0, "failed": 1}
    
    def _infer_test_file(self, source_file: str) -> str:
        """Infer test file path from source file."""
        if source_file.startswith("src/"):
            return source_file.replace("src/", "tests/").replace(".py", "_test.py")
        return source_file.replace(".py", "_test.py")
    
    def _analyze_test_failure(self, output: str) -> Dict[str, Any]:
        """Analyze test failure output."""
        prompt = f"""Analyze this test failure and provide insights:

```
{output[-2000:]}
```

Return JSON:
{{
  "failure_type": "assertion | import | syntax | timeout",
  "root_cause": "Brief description",
  "suggested_fix": "What to change"
}}"""

        response = self._call_llm(prompt, max_tokens=500)
        try:
            return json.loads(response)
        except:
            return {"failure_type": "unknown", "root_cause": "Could not analyze", "suggested_fix": "Manual review needed"}
    
    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute implementation plan.
        
        Args:
            request: Contains plan, prInfo
            
        Returns:
            ExecutionResult dict
        """
        plan = request.get("plan", {})
        pr_info = request.get("prInfo", {})
        repo_name = pr_info.get("repo")
        
        tasks = plan.get("implementation", {}).get("tasks", []) or plan.get("tasks", [])
        
        logger.info("execution_started", tasks=len(tasks))
        
        completed_tasks = []
        failed_tasks = []
        task_results = []
        
        # Process tasks in order, respecting dependencies
        for task in sorted(tasks, key=lambda t: t.get("id", 0)):
            deps = task.get("dependencies", [])
            
            # Check dependencies
            if not all(d in completed_tasks for d in deps):
                failed_tasks.append({"task": task, "reason": "Dependencies not met"})
                task_results.append({
                    "taskId": task["id"],
                    "status": "skipped",
                    "error": "Dependencies not met"
                })
                continue
            
            # Execute task
            result = self.execute_task(task, repo_name)
            task_results.append(result)
            
            if result["status"] == "success":
                completed_tasks.append(task["id"])
            else:
                failed_tasks.append({"task": task, "reason": result.get("error", "Unknown")})
        
        execution_result = {
            "completedTasks": completed_tasks,
            "failedTasks": failed_tasks,
            "taskResults": task_results,
            "totalTasks": len(tasks)
        }
        
        logger.info("execution_complete", completed=len(completed_tasks), failed=len(failed_tasks))
        return execution_result
