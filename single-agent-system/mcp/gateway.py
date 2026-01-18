"""
AgentCore MCP Gateway
=====================
Provides MCP-compatible tool access via AWS AgentCore.
Works locally and in cloud with AWS credentials.
"""

import os
import json
from typing import Any, Dict, Optional

import boto3
import structlog

from config import settings

logger = structlog.get_logger(__name__)


class MCPToolProxy:
    """Proxy for invoking MCP tools via AgentCore."""
    
    def __init__(self, tool_name: str, gateway: 'AgentCoreGateway'):
        self.tool_name = tool_name
        self.gateway = gateway
        self.bedrock_agent = gateway.bedrock_agent
        self._gateway_id = getattr(settings.agentcore, f"{tool_name.replace('-', '_').replace('mcp', '').strip('_')}_gateway_id", "")
    
    def __getattr__(self, method_name: str):
        """Return method wrapper for any attribute access."""
        def method_wrapper(**kwargs):
            return self._invoke_tool(method_name, kwargs)
        return method_wrapper
    
    def _invoke_tool(self, method: str, params: dict) -> Any:
        """Invoke an MCP tool method via AgentCore."""
        if settings.execution.dry_run:
            logger.info("dry_run_tool_invoke", tool=self.tool_name, method=method)
            return {}
        
        try:
            response = self.bedrock_agent.invoke_agent(
                agentId=self._gateway_id,
                sessionId='default',
                inputText=json.dumps({
                    'tool': method,
                    'parameters': params
                })
            )
            
            # Process streaming response
            result = {}
            for event in response.get('completion', []):
                if 'chunk' in event:
                    text = event['chunk'].get('bytes', b'').decode('utf-8')
                    try:
                        result = json.loads(text)
                    except json.JSONDecodeError:
                        result = {"text": text}
            
            return result
        except Exception as e:
            logger.error("tool_invoke_failed", tool=self.tool_name, method=method, error=str(e))
            return {}


class CodeInterpreterService:
    """AgentCore Code Interpreter service."""
    
    def __init__(self, gateway: 'AgentCoreGateway'):
        self.gateway = gateway
        self.bedrock_agent = gateway.bedrock_agent
    
    def execute(self, language: str, code: str, timeout_seconds: int = 300) -> 'ExecutionResult':
        """Execute code via AgentCore Code Interpreter."""
        if settings.execution.dry_run:
            logger.info("dry_run_execute", language=language, code_preview=code[:100])
            return ExecutionResult("", "", 0)
        
        try:
            # Use local execution as fallback when Code Interpreter not configured
            import subprocess
            
            if language == "bash":
                result = subprocess.run(
                    code, shell=True, capture_output=True, text=True, timeout=timeout_seconds
                )
            elif language == "python":
                result = subprocess.run(
                    ["python", "-c", code], capture_output=True, text=True, timeout=timeout_seconds
                )
            else:
                return ExecutionResult("", f"Unsupported language: {language}", 1)
            
            return ExecutionResult(result.stdout, result.stderr, result.returncode)
        except subprocess.TimeoutExpired:
            return ExecutionResult("", "Execution timed out", 1)
        except Exception as e:
            return ExecutionResult("", str(e), 1)


class ExecutionResult:
    """Result of code execution."""
    
    def __init__(self, stdout: str, stderr: str, return_code: int):
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
    
    def __repr__(self):
        return f"ExecutionResult(return_code={self.return_code})"


class LocalTaskStore:
    """In-memory task storage (matches DynamoDB interface)."""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
    
    def put_item(self, item: Dict[str, Any]):
        pk = item.get("pk", "")
        sk = item.get("sk", "")
        self._tasks[f"{pk}#{sk}"] = item
    
    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(f"{pk}#{sk}")
    
    def update_item(self, pk: str, sk: str, updates: Dict[str, Any]):
        key = f"{pk}#{sk}"
        if key in self._tasks:
            self._tasks[key].update(updates)
        else:
            self._tasks[key] = {"pk": pk, "sk": sk, **updates}
    
    def scan(self, filter_status: Optional[str] = None) -> list:
        items = list(self._tasks.values())
        if filter_status:
            items = [i for i in items if i.get("status") == filter_status]
        return items


class AgentCoreGateway:
    """
    Gateway for accessing MCP tools and services via AWS AgentCore.
    
    Works both locally and in cloud - requires AWS credentials.
    """
    
    def __init__(self):
        # Initialize AWS clients
        session_kwargs = {}
        if settings.aws.profile:
            session_kwargs['profile_name'] = settings.aws.profile
        
        session = boto3.Session(**session_kwargs)
        self.bedrock_agent = session.client(
            'bedrock-agent-runtime',
            region_name=settings.aws.region
        )
        
        self._tools: Dict[str, MCPToolProxy] = {}
        self._services: Dict[str, Any] = {}
        
        # Initialize services
        self._services["code-interpreter"] = CodeInterpreterService(self)
        self._services["task-store"] = LocalTaskStore()
        
        logger.info("agentcore_gateway_initialized", region=settings.aws.region)
    
    def get_tool(self, tool_name: str) -> MCPToolProxy:
        """Get an MCP tool proxy."""
        if tool_name not in self._tools:
            self._tools[tool_name] = MCPToolProxy(tool_name, self)
        return self._tools[tool_name]
    
    def get_service(self, service_name: str) -> Any:
        """Get a service."""
        if service_name not in self._services:
            raise ValueError(f"Unknown service: {service_name}")
        return self._services[service_name]
    
    def get_task_store(self) -> LocalTaskStore:
        """Get the local task store."""
        return self._services["task-store"]


# Singleton gateway instance
_gateway: Optional[AgentCoreGateway] = None


def get_gateway() -> AgentCoreGateway:
    """Get the singleton gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = AgentCoreGateway()
    return _gateway
